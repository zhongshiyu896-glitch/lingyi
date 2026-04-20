"""Incoming Purchase Receipt auto-trigger for draft quality inspections (TASK-030G)."""

from __future__ import annotations

from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.error_codes import QUALITY_INVALID_QTY
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.core.error_codes import QUALITY_INVALID_STATUS
from app.core.exceptions import BusinessException
from app.models.quality import LyQualityInspection
from app.schemas.quality import QualityInspectionCreateRequest
from app.schemas.quality import QualityInspectionDetailData
from app.schemas.quality import QualityInspectionItemInput
from app.services.quality_service import QualityService
from app.services.quality_service import QualitySourceValidator

SUPPORTED_EVENT_TYPES = {"purchase_receipt_created", "purchase_receipt_submitted"}
SOURCE_TYPE_INCOMING_MATERIAL = "incoming_material"
DEFAULT_ACTOR = "quality.auto.trigger"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        raise BusinessException(code=QUALITY_INVALID_QTY, message="来料事件 qty 非法") from None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_event(event: dict[str, Any]) -> tuple[str, str, str, str, list[dict[str, Any]], date, str | None]:
    event_type = _text(event.get("event_type"))
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件类型不受支持")

    source_id = _text(event.get("purchase_receipt_id")) or _text(event.get("name"))
    if source_id is None:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件缺少 purchase_receipt_id/name")

    company = _text(event.get("company"))
    if company is None:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件缺少 company")

    supplier = _text(event.get("supplier"))
    if supplier is None:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件缺少 supplier")

    warehouse = _text(event.get("warehouse"))
    items = event.get("items")
    if not isinstance(items, list) or not items:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件缺少有效 items")

    inspection_date = (
        _to_date(event.get("posting_date"))
        or _to_date(event.get("receipt_date"))
        or _to_date(event.get("inspection_date"))
        or datetime.now(UTC).date()
    )
    request_id = _text(event.get("event_id")) or _text(event.get("request_id"))
    return source_id, company, supplier, warehouse or "", items, inspection_date, request_id


def _normalize_items(
    *,
    items: list[dict[str, Any]],
    fallback_warehouse: str | None,
) -> tuple[str, list[QualityInspectionItemInput], Decimal]:
    normalized: list[QualityInspectionItemInput] = []
    total_qty = Decimal("0")
    header_item_code: str | None = None

    for raw in items:
        if not isinstance(raw, dict):
            raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件 items 存在非法行")
        item_code = _text(raw.get("item_code"))
        if item_code is None:
            raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件 item_code 缺失")
        qty = _decimal(raw.get("qty"))
        if qty <= 0:
            raise BusinessException(code=QUALITY_INVALID_QTY, message="来料事件 qty 必须大于 0")
        if header_item_code is None:
            header_item_code = item_code
        normalized.append(
            QualityInspectionItemInput(
                item_code=item_code,
                sample_qty=qty,
                accepted_qty=qty,
                rejected_qty=Decimal("0"),
                defect_qty=Decimal("0"),
                result="pass",
                remark=_text(raw.get("item_name")) or None,
            )
        )
        total_qty += qty

    if header_item_code is None:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="来料事件未解析出 item_code")
    # fallback_warehouse 由上层用于质检单头字段，明细不单独存仓库字段
    _ = fallback_warehouse
    return header_item_code, normalized, total_qty


class QualityPurchaseReceiptListener:
    """Create quality draft inspection from submitted Purchase Receipt events."""

    def __init__(
        self,
        *,
        session: Session,
        source_validator: QualitySourceValidator | None = None,
    ):
        self.session = session
        self.source_validator = source_validator or QualitySourceValidator()

    def handle_event(
        self,
        event: dict[str, Any],
        *,
        actor: str = DEFAULT_ACTOR,
    ) -> QualityInspectionDetailData:
        source_id, company, supplier, warehouse, raw_items, inspection_date, request_id = _parse_event(event)
        item_code, items, total_qty = _normalize_items(items=raw_items, fallback_warehouse=_text(warehouse))

        existing_query = (
            self.session.query(LyQualityInspection)
            .filter(LyQualityInspection.company == company)
            .filter(LyQualityInspection.source_type == SOURCE_TYPE_INCOMING_MATERIAL)
            .filter(LyQualityInspection.source_id == source_id)
        )
        existing_active = (
            existing_query.filter(LyQualityInspection.status != "cancelled")
            .order_by(LyQualityInspection.id.desc())
            .first()
        )
        if existing_active is not None:
            return QualityService(session=self.session, source_validator=self.source_validator).get_detail_data(
                int(existing_active.id)
            )

        existing_cancelled = (
            existing_query.filter(LyQualityInspection.status == "cancelled")
            .order_by(LyQualityInspection.id.desc())
            .first()
        )
        if existing_cancelled is not None:
            raise BusinessException(
                code=QUALITY_INVALID_STATUS,
                message="同 source 已存在 cancelled 记录，自动触发拒绝重建",
            )

        payload = QualityInspectionCreateRequest(
            company=company,
            source_type=SOURCE_TYPE_INCOMING_MATERIAL,
            source_id=source_id,
            item_code=item_code,
            supplier=supplier,
            warehouse=_text(warehouse),
            inspection_date=inspection_date,
            inspected_qty=total_qty,
            accepted_qty=total_qty,
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
            result="pass",
            items=items,
            defects=[],
            remark=f"auto_trigger_from_purchase_receipt:{source_id}",
        )
        return QualityService(session=self.session, source_validator=self.source_validator).create_inspection(
            payload=payload,
            operator=actor,
            request_id=request_id or f"auto-pr:{source_id}",
        )


def handle_purchase_receipt_event(
    session: Session,
    event: dict[str, Any],
    *,
    actor: str = DEFAULT_ACTOR,
    source_validator: QualitySourceValidator | None = None,
) -> QualityInspectionDetailData:
    """Convenience function for direct event handling in tests/integration entry."""
    listener = QualityPurchaseReceiptListener(session=session, source_validator=source_validator)
    return listener.handle_event(event=event, actor=actor)

