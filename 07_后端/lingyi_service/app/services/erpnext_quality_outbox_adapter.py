"""Quality-specific ERPNext Stock Entry write adapter (TASK-030D)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import os
from typing import Any

from app.core.error_codes import ERPNEXT_STOCK_ENTRY_STATUS_INVALID
from app.core.error_codes import QUALITY_INVALID_QTY
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.core.exceptions import BusinessException
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService


class ERPNextQualityOutboxAdapter:
    """Create/submit ERPNext Stock Entry for quality outbox events."""

    def __init__(self, *, stock_entry_service: ERPNextStockEntryService | None = None):
        self.stock_entry_service = stock_entry_service or ERPNextStockEntryService()

    def sync_stock_entry(
        self,
        *,
        event_key: str,
        payload_json: dict[str, Any],
    ) -> str:
        existing = self.stock_entry_service.find_by_event_key(event_key=event_key)
        if existing is not None:
            if int(existing.docstatus) == 1:
                return existing.name
            if int(existing.docstatus) == 0:
                self.stock_entry_service.submit_stock_entry(stock_entry_name=existing.name)
                return existing.name
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                message="ERPNext Stock Entry 状态非法，禁止继续同步",
            )

        stock_payload = self._build_stock_entry_payload(
            event_key=event_key,
            payload_json=payload_json,
        )
        stock_entry_name = self.stock_entry_service.create_material_issue(payload_json=stock_payload)
        self.stock_entry_service.submit_stock_entry(stock_entry_name=stock_entry_name)
        return stock_entry_name

    def _build_stock_entry_payload(
        self,
        *,
        event_key: str,
        payload_json: dict[str, Any],
    ) -> dict[str, Any]:
        company = str(payload_json.get("company") or "").strip()
        item_code = str(payload_json.get("item_code") or "").strip()
        source_warehouse = str(payload_json.get("warehouse") or "").strip()
        inspection_no = str(payload_json.get("inspection_no") or "").strip() or None
        posting_date = self._resolve_posting_date(payload_json=payload_json)

        accepted_qty = self._to_decimal(payload_json.get("accepted_qty"))
        rejected_qty = self._to_decimal(payload_json.get("rejected_qty"))
        if accepted_qty <= Decimal("0") and rejected_qty <= Decimal("0"):
            raise BusinessException(code=QUALITY_INVALID_QTY, message="accepted_qty/rejected_qty 至少一项大于 0")
        if not source_warehouse:
            raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺少来源仓库 warehouse，禁止同步")

        accepted_warehouse = str(payload_json.get("accepted_warehouse") or "").strip() or os.getenv(
            "QUALITY_ACCEPTED_WAREHOUSE",
            "",
        ).strip()
        rejected_warehouse = str(payload_json.get("rejected_warehouse") or "").strip() or os.getenv(
            "QUALITY_REJECTED_WAREHOUSE",
            "",
        ).strip()

        items: list[dict[str, Any]] = []
        if accepted_qty > Decimal("0"):
            if not accepted_warehouse:
                raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺少合格品目标仓库，禁止同步")
            items.append(
                {
                    "item_code": item_code,
                    "qty": float(accepted_qty),
                    "s_warehouse": source_warehouse,
                    "t_warehouse": accepted_warehouse,
                }
            )
        if rejected_qty > Decimal("0"):
            if not rejected_warehouse:
                raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺少不合格品目标仓库，禁止同步")
            items.append(
                {
                    "item_code": item_code,
                    "qty": float(rejected_qty),
                    "s_warehouse": source_warehouse,
                    "t_warehouse": rejected_warehouse,
                }
            )

        if not company or not item_code:
            raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺少 company/item_code，禁止同步")

        payload: dict[str, Any] = {
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "purpose": "Material Transfer",
            "company": company,
            "posting_date": posting_date.isoformat(),
            "custom_ly_outbox_event_key": str(event_key),
            "remarks": f"Quality inspection {inspection_no or '-'} outbox sync",
            "items": items,
        }
        return payload

    @staticmethod
    def _resolve_posting_date(*, payload_json: dict[str, Any]) -> date:
        raw = payload_json.get("confirmed_at")
        if isinstance(raw, str) and raw.strip():
            text = raw.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(text)
                return parsed.date()
            except ValueError:
                pass
        return date.today()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal("0")
        text = str(value).strip()
        if not text:
            return Decimal("0")
        try:
            return Decimal(text)
        except Exception:
            raise BusinessException(code=QUALITY_INVALID_QTY, message=f"数量字段非法: {value}")
