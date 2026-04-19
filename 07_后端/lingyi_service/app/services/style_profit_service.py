"""Style profit snapshot calculation service (TASK-005D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from decimal import Decimal
from decimal import InvalidOperation
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.models.subcontract import LySubcontractOrder
from app.schemas.style_profit import StyleProfitMaterialSourceDTO
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.schemas.style_profit import StyleProfitSnapshotResult
from app.services.style_profit_source_service import StyleProfitSourceService


STYLE_PROFIT_IDEMPOTENCY_CONFLICT = "STYLE_PROFIT_IDEMPOTENCY_CONFLICT"
STYLE_PROFIT_INVALID_PERIOD = "STYLE_PROFIT_INVALID_PERIOD"
STYLE_PROFIT_INVALID_REVENUE_MODE = "STYLE_PROFIT_INVALID_REVENUE_MODE"
STYLE_PROFIT_INVALID_FORMULA_VERSION = "STYLE_PROFIT_INVALID_FORMULA_VERSION"
STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY = "STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY"
STYLE_PROFIT_SALES_ORDER_REQUIRED = "STYLE_PROFIT_SALES_ORDER_REQUIRED"
STYLE_PROFIT_SOURCE_READ_FAILED = "STYLE_PROFIT_SOURCE_READ_FAILED"
STYLE_PROFIT_INTERNAL_ERROR = "STYLE_PROFIT_INTERNAL_ERROR"


class StyleProfitService:
    """Build immutable style-profit snapshots with idempotent replay."""

    _ALLOWED_REVENUE_MODES = {"actual_first", "actual_only", "estimated_only"}
    _ALLOWED_FORMULA_VERSIONS = {"STYLE_PROFIT_V1"}

    def __init__(self, source_service: StyleProfitSourceService | None = None) -> None:
        self.source_service = source_service or StyleProfitSourceService(session=None)

    def create_snapshot(
        self,
        session: Session,
        request: StyleProfitSnapshotCreateRequest | dict[str, Any],
        operator: str,
    ) -> StyleProfitSnapshotResult:
        payload = (
            request
            if isinstance(request, StyleProfitSnapshotCreateRequest)
            else StyleProfitSnapshotCreateRequest.model_validate(request)
        )
        self._validate_payload(payload)

        request_hash = self.source_service.build_snapshot_request_hash(payload.model_dump(mode="json"))
        company = self._normalize_text(payload.company)
        idempotency_key = self._normalize_text(payload.idempotency_key)

        try:
            existing = (
                session.query(LyStyleProfitSnapshot)
                .filter(
                    LyStyleProfitSnapshot.company == company,
                    LyStyleProfitSnapshot.idempotency_key == idempotency_key,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed("利润快照查询失败") from exc

        if existing is not None:
            if str(existing.request_hash or "") == request_hash:
                return self._to_result(existing, idempotent_replay=True)
            raise BusinessException(
                code=STYLE_PROFIT_IDEMPOTENCY_CONFLICT,
                message="幂等键冲突，且请求内容不一致",
            )

        sales_order = self._normalize_text(payload.sales_order)
        try:
            with session.begin_nested():
                snapshot = LyStyleProfitSnapshot(
                    snapshot_no=self._build_snapshot_no(),
                    company=company,
                    sales_order=sales_order,
                    item_code=self._normalize_text(payload.item_code),
                    from_date=payload.from_date,
                    to_date=payload.to_date,
                    revenue_mode=payload.revenue_mode,
                    formula_version=payload.formula_version,
                    include_provisional_subcontract=bool(payload.include_provisional_subcontract),
                    allocation_status="not_enabled",
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    created_by=self._normalize_text(operator) or "system",
                )
                session.add(snapshot)
                session.flush()

                unresolved_count = 0
                line_no = 1

                revenue_ctx = self._resolve_revenue(payload)
                line_no, unresolved_count = self._persist_revenue_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    revenue_ctx=revenue_ctx,
                    unresolved_count=unresolved_count,
                )

                standard_material_cost, line_no, unresolved_count = self._persist_standard_material_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    payload=payload,
                    unresolved_count=unresolved_count,
                )

                standard_operation_cost, line_no, unresolved_count = self._persist_standard_operation_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    payload=payload,
                    unresolved_count=unresolved_count,
                )

                material_resolution = self.source_service.resolve_material_cost_sources(
                    company=payload.company,
                    sales_order=payload.sales_order,
                    style_item_code=payload.item_code,
                    work_order=payload.work_order,
                    stock_ledger_rows=payload.stock_ledger_rows,
                    purchase_receipt_rows=payload.purchase_receipt_rows,
                    allowed_material_item_codes=set(payload.allowed_material_item_codes),
                )

                line_no, unresolved_count = self._persist_material_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    material_resolution=material_resolution,
                    unresolved_count=unresolved_count,
                )
                actual_material_cost = material_resolution.actual_material_cost

                actual_workshop_cost, line_no, unresolved_count = self._persist_workshop_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    payload=payload,
                    unresolved_count=unresolved_count,
                )

                actual_subcontract_cost, line_no, unresolved_count = self._persist_subcontract_details(
                    session=session,
                    snapshot=snapshot,
                    line_no=line_no,
                    payload=payload,
                    unresolved_count=unresolved_count,
                )

                standard_total_cost = standard_material_cost + standard_operation_cost
                actual_total_cost = (
                    actual_material_cost + actual_workshop_cost + actual_subcontract_cost + Decimal("0")
                )
                revenue_amount = revenue_ctx["revenue_amount"]
                profit_amount = revenue_amount - actual_total_cost
                profit_rate = None if revenue_amount == Decimal("0") else (profit_amount / revenue_amount)

                snapshot.revenue_status = revenue_ctx["revenue_status"]
                snapshot.estimated_revenue_amount = revenue_ctx["estimated_revenue_amount"]
                snapshot.actual_revenue_amount = revenue_ctx["actual_revenue_amount"]
                snapshot.revenue_amount = revenue_amount
                snapshot.standard_material_cost = standard_material_cost
                snapshot.standard_operation_cost = standard_operation_cost
                snapshot.standard_total_cost = standard_total_cost
                snapshot.actual_material_cost = actual_material_cost
                snapshot.actual_workshop_cost = actual_workshop_cost
                snapshot.actual_subcontract_cost = actual_subcontract_cost
                snapshot.allocated_overhead_amount = Decimal("0")
                snapshot.actual_total_cost = actual_total_cost
                snapshot.profit_amount = profit_amount
                snapshot.profit_rate = profit_rate
                snapshot.unresolved_count = unresolved_count
                snapshot.snapshot_status = "complete" if unresolved_count == 0 else "incomplete"

                session.flush()
                result = self._to_result(snapshot, idempotent_replay=False)
            return result
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed("利润快照写入失败") from exc
        except Exception as exc:
            raise BusinessException(code=STYLE_PROFIT_INTERNAL_ERROR, message="利润快照计算失败") from exc

    def _validate_payload(self, payload: StyleProfitSnapshotCreateRequest) -> None:
        if payload.from_date > payload.to_date:
            raise BusinessException(code=STYLE_PROFIT_INVALID_PERIOD, message="from_date 不能晚于 to_date")
        if payload.revenue_mode not in self._ALLOWED_REVENUE_MODES:
            raise BusinessException(code=STYLE_PROFIT_INVALID_REVENUE_MODE, message="revenue_mode 非法")
        if payload.formula_version not in self._ALLOWED_FORMULA_VERSIONS:
            raise BusinessException(
                code=STYLE_PROFIT_INVALID_FORMULA_VERSION,
                message="formula_version 非法",
            )
        if not self._normalize_text(payload.company):
            raise BusinessException(code=STYLE_PROFIT_SOURCE_READ_FAILED, message="company 不能为空")
        if not self._normalize_text(payload.item_code):
            raise BusinessException(code=STYLE_PROFIT_SOURCE_READ_FAILED, message="item_code 不能为空")
        if not self._normalize_text(payload.sales_order):
            raise BusinessException(code=STYLE_PROFIT_SALES_ORDER_REQUIRED, message="sales_order 不能为空")
        idempotency_key = self._normalize_text(payload.idempotency_key)
        if not idempotency_key:
            raise BusinessException(code=STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY, message="idempotency_key 不能为空")
        if len(idempotency_key) > 128:
            raise BusinessException(code=STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY, message="idempotency_key 不能超过128个字符")

    def _resolve_revenue(self, payload: StyleProfitSnapshotCreateRequest) -> dict[str, Any]:
        if payload.revenue_mode == "actual_only":
            actual_rows = self.source_service.resolve_revenue_sources(
                company=payload.company,
                sales_order=payload.sales_order,
                item_code=payload.item_code,
                sales_invoice_rows=payload.sales_invoice_rows,
                sales_order_rows=[],
            )
            if actual_rows:
                actual_amount = sum((row.amount for row in actual_rows), Decimal("0"))
                return {
                    "revenue_status": "actual",
                    "actual_rows": actual_rows,
                    "estimated_rows": [],
                    "actual_revenue_amount": actual_amount,
                    "estimated_revenue_amount": Decimal("0"),
                    "revenue_amount": actual_amount,
                    "missing_actual": False,
                    "unresolved_reason": None,
                }
            return {
                "revenue_status": "unresolved",
                "actual_rows": [],
                "estimated_rows": [],
                "actual_revenue_amount": Decimal("0"),
                "estimated_revenue_amount": Decimal("0"),
                "revenue_amount": Decimal("0"),
                "missing_actual": True,
                "unresolved_reason": "missing_submitted_sales_invoice",
            }

        if payload.revenue_mode == "estimated_only":
            estimated_rows = self.source_service.resolve_revenue_sources(
                company=payload.company,
                sales_order=payload.sales_order,
                item_code=payload.item_code,
                sales_invoice_rows=[],
                sales_order_rows=payload.sales_order_rows,
            )
            estimated_amount = sum((row.amount for row in estimated_rows), Decimal("0"))
            status = "estimated" if estimated_rows else "unresolved"
            return {
                "revenue_status": status,
                "actual_rows": [],
                "estimated_rows": estimated_rows,
                "actual_revenue_amount": Decimal("0"),
                "estimated_revenue_amount": estimated_amount,
                "revenue_amount": estimated_amount,
                "missing_actual": False,
                "unresolved_reason": None if estimated_rows else "missing_submitted_sales_order",
            }

        resolved = self.source_service.resolve_revenue_sources(
            company=payload.company,
            sales_order=payload.sales_order,
            item_code=payload.item_code,
            sales_invoice_rows=payload.sales_invoice_rows,
            sales_order_rows=payload.sales_order_rows,
        )
        if resolved and resolved[0].revenue_status == "actual":
            actual_amount = sum((row.amount for row in resolved), Decimal("0"))
            return {
                "revenue_status": "actual",
                "actual_rows": resolved,
                "estimated_rows": [],
                "actual_revenue_amount": actual_amount,
                "estimated_revenue_amount": Decimal("0"),
                "revenue_amount": actual_amount,
                "missing_actual": False,
            }

        estimated_amount = sum((row.amount for row in resolved), Decimal("0"))
        status = "estimated" if resolved else "unresolved"
        return {
            "revenue_status": status,
            "actual_rows": [],
            "estimated_rows": resolved,
            "actual_revenue_amount": Decimal("0"),
            "estimated_revenue_amount": estimated_amount,
            "revenue_amount": estimated_amount,
            "missing_actual": False,
            "unresolved_reason": None if resolved else "missing_submitted_revenue_source",
        }

    def _persist_revenue_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        revenue_ctx: dict[str, Any],
        unresolved_count: int,
    ) -> tuple[int, int]:
        for row in revenue_ctx["actual_rows"] + revenue_ctx["estimated_rows"]:
            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="revenue",
                source_type=row.source_type,
                source_name=row.source_name,
                item_code=row.item_code,
                qty=row.qty,
                unit_rate=row.unit_rate,
                amount=row.amount,
                formula_code="REV_ACTUAL" if row.revenue_status == "actual" else "REV_ESTIMATED",
                is_unresolved=False,
                unresolved_reason=None,
                raw_ref={
                    "source_type": row.source_type,
                    "source_name": row.source_name,
                    "source_line_no": row.source_line_no,
                },
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=row.item_code,
                    source_system="erpnext",
                    source_doctype=row.source_type,
                    source_status=row.source_status or "unknown",
                    source_name=row.source_name,
                    source_line_no=row.source_line_no,
                    qty=row.qty,
                    unit_rate=row.unit_rate,
                    amount=row.amount,
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={
                        "source_type": row.source_type,
                        "source_name": row.source_name,
                        "source_line_no": row.source_line_no,
                    },
                    include_in_profit=True,
                    mapping_status="mapped",
                    unresolved_reason=None,
                )
            )
            line_no += 1

        if revenue_ctx["revenue_status"] == "unresolved":
            unresolved_reason = revenue_ctx.get("unresolved_reason") or (
                "missing_submitted_sales_invoice" if revenue_ctx["missing_actual"] else "missing_submitted_revenue_source"
            )
            unresolved_source_type = (
                "Sales Invoice"
                if unresolved_reason == "missing_submitted_sales_invoice"
                else "Sales Order"
                if unresolved_reason == "missing_submitted_sales_order"
                else "Revenue Source"
            )
            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="unresolved",
                source_type=unresolved_source_type,
                source_name=unresolved_reason.upper(),
                item_code=str(snapshot.item_code),
                qty=Decimal("0"),
                unit_rate=Decimal("0"),
                amount=Decimal("0"),
                formula_code="REV_ACTUAL_ONLY",
                is_unresolved=True,
                unresolved_reason=unresolved_reason,
                raw_ref={"reason": unresolved_reason},
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=str(snapshot.item_code),
                    source_system="manual",
                    source_doctype=unresolved_source_type,
                    source_status="unknown",
                    source_name=unresolved_reason.upper(),
                    source_line_no="",
                    qty=Decimal("0"),
                    unit_rate=Decimal("0"),
                    amount=Decimal("0"),
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={"reason": unresolved_reason},
                    include_in_profit=False,
                    mapping_status="unresolved",
                    unresolved_reason=unresolved_reason,
                )
            )
            line_no += 1
            unresolved_count += 1

        return line_no, unresolved_count

    def _persist_standard_material_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        payload: StyleProfitSnapshotCreateRequest,
        unresolved_count: int,
    ) -> tuple[Decimal, int, int]:
        total = Decimal("0")
        for row in payload.bom_material_rows:
            item_code = self._normalize_text(row.get("item_code")) or self._normalize_text(row.get("material_item_code"))
            required_qty = self._to_decimal(
                row.get("bom_required_qty_with_loss")
                if row.get("bom_required_qty_with_loss") is not None
                else row.get("required_qty")
            )
            if required_qty == Decimal("0"):
                required_qty = self._to_decimal(row.get("qty"))

            unit_cost, unit_cost_source = self._resolve_standard_unit_cost(row)
            if unit_cost is None:
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type="BOM Item",
                    source_name=item_code or "UNKNOWN",
                    item_code=item_code or None,
                    qty=required_qty,
                    unit_rate=Decimal("0"),
                    amount=Decimal("0"),
                    formula_code="STD_MAT_V1",
                    is_unresolved=True,
                    unresolved_reason="standard_unit_cost_unresolved",
                    raw_ref={"item_code": item_code, "required_qty": str(required_qty)},
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=str(snapshot.company),
                        sales_order=snapshot.sales_order,
                        style_item_code=str(snapshot.item_code),
                        source_item_code=item_code or None,
                        source_system="fastapi",
                        source_doctype="BOM Item",
                        source_status="unknown",
                        source_name=item_code or "UNKNOWN",
                        source_line_no=self._normalize_text(row.get("line_no")) or "",
                        qty=required_qty,
                        unit_rate=Decimal("0"),
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"reason": "standard_unit_cost_unresolved"},
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason="standard_unit_cost_unresolved",
                    )
                )
                unresolved_count += 1
                line_no += 1
                continue

            amount = required_qty * unit_cost
            total += amount
            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="standard_material",
                source_type="BOM Item",
                source_name=item_code or "UNKNOWN",
                item_code=item_code or None,
                qty=required_qty,
                unit_rate=unit_cost,
                amount=amount,
                formula_code="STD_MAT_V1",
                is_unresolved=False,
                unresolved_reason=None,
                raw_ref={"unit_cost_source": unit_cost_source},
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=item_code or None,
                    source_system="fastapi",
                    source_doctype="BOM Item",
                    source_status="submitted",
                    source_name=item_code or "UNKNOWN",
                    source_line_no=self._normalize_text(row.get("line_no")) or "",
                    qty=required_qty,
                    unit_rate=unit_cost,
                    amount=amount,
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={"unit_cost_source": unit_cost_source},
                    include_in_profit=True,
                    mapping_status="mapped",
                    unresolved_reason=None,
                )
            )
            line_no += 1
        return total, line_no, unresolved_count

    def _persist_standard_operation_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        payload: StyleProfitSnapshotCreateRequest,
        unresolved_count: int,
    ) -> tuple[Decimal, int, int]:
        total = Decimal("0")
        for row in payload.bom_operation_rows:
            source_name = self._normalize_text(row.get("operation")) or self._normalize_text(row.get("name")) or "OP"
            rate, has_rate = self._extract_decimal_by_keys(
                row,
                "bom_operation_rate",
                "operation_rate",
                "rate",
            )
            planned_qty = self._to_decimal(row.get("planned_qty"))
            if planned_qty == Decimal("0"):
                planned_qty = self._to_decimal(row.get("qty"))

            if not has_rate or rate is None:
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type="BOM Operation",
                    source_name=source_name,
                    item_code=str(snapshot.item_code),
                    qty=planned_qty,
                    unit_rate=Decimal("0"),
                    amount=Decimal("0"),
                    formula_code="STD_OP_V1",
                    is_unresolved=True,
                    unresolved_reason="operation_rate_unresolved",
                    raw_ref={"operation": source_name},
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=str(snapshot.company),
                        sales_order=snapshot.sales_order,
                        style_item_code=str(snapshot.item_code),
                        source_item_code=str(snapshot.item_code),
                        source_system="fastapi",
                        source_doctype="BOM Operation",
                        source_status="unknown",
                        source_name=source_name,
                        source_line_no=self._normalize_text(row.get("line_no")) or "",
                        qty=planned_qty,
                        unit_rate=Decimal("0"),
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"reason": "operation_rate_unresolved"},
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason="operation_rate_unresolved",
                    )
                )
                line_no += 1
                unresolved_count += 1
                continue

            amount = self._to_decimal_or_none(row.get("amount"))
            if amount is None:
                amount = rate * planned_qty
            total += amount

            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="standard_operation",
                source_type="BOM Operation",
                source_name=source_name,
                item_code=str(snapshot.item_code),
                qty=planned_qty,
                unit_rate=rate,
                amount=amount,
                formula_code="STD_OP_V1",
                is_unresolved=False,
                unresolved_reason=None,
                raw_ref={"operation": source_name},
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=str(snapshot.item_code),
                    source_system="fastapi",
                    source_doctype="BOM Operation",
                    source_status="submitted",
                    source_name=source_name,
                    source_line_no=self._normalize_text(row.get("line_no")) or "",
                    qty=planned_qty,
                    unit_rate=rate,
                    amount=amount,
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={"operation": source_name},
                    include_in_profit=True,
                    mapping_status="mapped",
                    unresolved_reason=None,
                )
            )
            line_no += 1

        return total, line_no, unresolved_count

    def _persist_material_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        material_resolution: Any,
        unresolved_count: int,
    ) -> tuple[int, int]:
        for row in material_resolution.mapped_sources:
            line_no = self._persist_material_detail(
                session=session,
                snapshot=snapshot,
                line_no=line_no,
                source=row,
                cost_type="actual_material",
                is_unresolved=False,
                unresolved_reason=None,
            )

        for row in material_resolution.unresolved_sources:
            line_no = self._persist_material_detail(
                session=session,
                snapshot=snapshot,
                line_no=line_no,
                source=row,
                cost_type="unresolved",
                is_unresolved=True,
                unresolved_reason=row.unresolved_reason or "unable_to_link_order_or_material_scope",
            )
            unresolved_count += 1

        for row in material_resolution.reference_sources:
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=None,
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=row.source_item_code,
                    production_plan_id=row.production_plan_id,
                    work_order=row.work_order,
                    job_card=row.job_card,
                    source_system=row.source_system,
                    source_doctype=row.source_doctype,
                    source_status=row.source_status or "unknown",
                    source_name=row.source_name,
                    source_line_no=row.source_line_no,
                    qty=row.qty,
                    unit_rate=row.unit_rate,
                    amount=row.amount,
                    currency=row.currency,
                    warehouse=row.warehouse,
                    posting_date=row.posting_date,
                    raw_ref=row.raw_ref,
                    include_in_profit=False,
                    mapping_status="excluded",
                    unresolved_reason=row.unresolved_reason or "purchase_receipt_reference_only",
                )
            )

        return line_no, unresolved_count

    def _persist_material_detail(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        source: StyleProfitMaterialSourceDTO,
        cost_type: str,
        is_unresolved: bool,
        unresolved_reason: str | None,
    ) -> int:
        detail = LyStyleProfitDetail(
            snapshot_id=int(snapshot.id),
            line_no=line_no,
            cost_type=cost_type,
            source_type=source.source_doctype,
            source_name=source.source_name,
            item_code=source.source_item_code,
            qty=source.qty,
            unit_rate=source.unit_rate,
            amount=source.amount if not is_unresolved else Decimal("0"),
            formula_code="ACT_MAT_V1",
            is_unresolved=is_unresolved,
            unresolved_reason=unresolved_reason,
            raw_ref=source.raw_ref,
        )
        session.add(detail)
        session.flush()
        session.add(
            LyStyleProfitSourceMap(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                company=str(snapshot.company),
                sales_order=snapshot.sales_order,
                style_item_code=str(snapshot.item_code),
                source_item_code=source.source_item_code,
                production_plan_id=source.production_plan_id,
                work_order=source.work_order,
                job_card=source.job_card,
                source_system=source.source_system,
                source_doctype=source.source_doctype,
                source_status=source.source_status or "unknown",
                source_name=source.source_name,
                source_line_no=source.source_line_no,
                qty=source.qty,
                unit_rate=source.unit_rate,
                amount=source.amount,
                currency=source.currency,
                warehouse=source.warehouse,
                posting_date=source.posting_date,
                raw_ref=source.raw_ref,
                include_in_profit=not is_unresolved,
                mapping_status="unresolved" if is_unresolved else "mapped",
                unresolved_reason=unresolved_reason,
            )
        )
        return line_no + 1

    def _persist_workshop_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        payload: StyleProfitSnapshotCreateRequest,
        unresolved_count: int,
    ) -> tuple[Decimal, int, int]:
        total = Decimal("0")
        for row in payload.workshop_ticket_rows:
            source_name = self._normalize_text(row.get("ticket_no")) or self._normalize_text(row.get("name")) or "TICKET"
            source_status = self._normalize_text(row.get("status")).lower() or "unknown"
            source_line_no = self._normalize_text(row.get("line_no")) or ""
            register_qty = self._to_decimal(row.get("register_qty"))
            reversal_qty = self._to_decimal(row.get("reversal_qty"))
            net_qty = register_qty - reversal_qty
            wage_rate, has_wage_rate = self._extract_decimal_by_keys(
                row,
                "wage_rate_snapshot",
                "wage_rate",
                "unit_rate",
            )
            row_company = self._normalize_text(row.get("company"))
            row_item_code = self._normalize_text(row.get("item_code") or row.get("style_item_code"))
            row_sales_order = self._normalize_text(row.get("sales_order"))
            row_work_order = self._normalize_text(row.get("work_order"))
            row_job_card = self._normalize_text(row.get("job_card"))
            row_job_card_work_order = self._normalize_text(
                row.get("job_card_work_order")
                or row.get("job_card_work_order_no")
                or row.get("job_card_parent_work_order")
            )
            row_production_plan_id = self._normalize_text(row.get("production_plan_id"))
            scope_status, scope_reason = self._match_profit_scope(
                snapshot=snapshot,
                payload=payload,
                source_type="Workshop Ticket",
                row_company=row_company,
                row_item_code=row_item_code,
                row_sales_order=row_sales_order,
                row_work_order=row_work_order,
                row_job_card=row_job_card,
                row_job_card_work_order=row_job_card_work_order,
                row_production_plan_id=row_production_plan_id,
                row_subcontract_order="",
            )
            source_item_code = row_item_code or None

            if scope_status == "excluded":
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=None,
                        company=row_company or str(snapshot.company),
                        sales_order=row_sales_order or snapshot.sales_order,
                        style_item_code=row_item_code or str(snapshot.item_code),
                        source_item_code=source_item_code,
                        work_order=row_work_order or None,
                        job_card=row_job_card or None,
                        source_system="fastapi",
                        source_doctype="Workshop Ticket",
                        source_status=source_status or "unknown",
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=net_qty,
                        unit_rate=wage_rate,
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"scope_reason": scope_reason},
                        include_in_profit=False,
                        mapping_status="excluded",
                        unresolved_reason=scope_reason,
                    )
                )
                continue

            if scope_status == "unresolved":
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type="Workshop Ticket",
                    source_name=source_name,
                    item_code=source_item_code,
                    qty=net_qty,
                    unit_rate=wage_rate,
                    amount=Decimal("0"),
                    formula_code="WORKSHOP_V1",
                    is_unresolved=True,
                    unresolved_reason=scope_reason,
                    raw_ref={"scope_reason": scope_reason},
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=row_company or str(snapshot.company),
                        sales_order=row_sales_order or snapshot.sales_order,
                        style_item_code=row_item_code or str(snapshot.item_code),
                        source_item_code=source_item_code,
                        work_order=row_work_order or None,
                        job_card=row_job_card or None,
                        source_system="fastapi",
                        source_doctype="Workshop Ticket",
                        source_status=source_status or "unknown",
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=net_qty,
                        unit_rate=wage_rate,
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"scope_reason": scope_reason},
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason=scope_reason,
                    )
                )
                unresolved_count += 1
                line_no += 1
                continue

            if source_status in {"unknown", "", "draft", "cancelled", "canceled"}:
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type="Workshop Ticket",
                    source_name=source_name,
                    item_code=str(snapshot.item_code),
                    qty=net_qty,
                    unit_rate=wage_rate,
                    amount=Decimal("0"),
                    formula_code="WORKSHOP_V1",
                    is_unresolved=True,
                    unresolved_reason="source_status_unknown",
                    raw_ref={"ticket_no": source_name},
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=str(snapshot.company),
                        sales_order=snapshot.sales_order,
                        style_item_code=str(snapshot.item_code),
                        source_item_code=str(snapshot.item_code),
                        source_system="fastapi",
                        source_doctype="Workshop Ticket",
                        source_status=source_status or "unknown",
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=net_qty,
                        unit_rate=wage_rate,
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"ticket_no": source_name},
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason="source_status_unknown",
                    )
                )
                unresolved_count += 1
                line_no += 1
                continue

            if net_qty <= Decimal("0"):
                continue

            if not has_wage_rate or wage_rate is None:
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type="Workshop Ticket",
                    source_name=source_name,
                    item_code=str(snapshot.item_code),
                    qty=net_qty,
                    unit_rate=Decimal("0"),
                    amount=Decimal("0"),
                    formula_code="WORKSHOP_V1",
                    is_unresolved=True,
                    unresolved_reason="workshop_wage_rate_unresolved",
                    raw_ref={"ticket_no": source_name},
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=str(snapshot.company),
                        sales_order=snapshot.sales_order,
                        style_item_code=str(snapshot.item_code),
                        source_item_code=str(snapshot.item_code),
                        source_system="fastapi",
                        source_doctype="Workshop Ticket",
                        source_status=source_status or "unknown",
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=net_qty,
                        unit_rate=Decimal("0"),
                        amount=Decimal("0"),
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={"reason": "workshop_wage_rate_unresolved"},
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason="workshop_wage_rate_unresolved",
                    )
                )
                unresolved_count += 1
                line_no += 1
                continue

            amount = net_qty * wage_rate
            total += amount
            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="workshop",
                source_type="Workshop Ticket",
                source_name=source_name,
                item_code=str(snapshot.item_code),
                qty=net_qty,
                unit_rate=wage_rate,
                amount=amount,
                formula_code="WORKSHOP_V1",
                is_unresolved=False,
                unresolved_reason=None,
                raw_ref={"register_qty": str(register_qty), "reversal_qty": str(reversal_qty)},
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=source_item_code,
                    source_system="fastapi",
                    source_doctype="Workshop Ticket",
                    source_status=source_status or "submitted",
                    source_name=source_name,
                    source_line_no=source_line_no,
                    qty=net_qty,
                    unit_rate=wage_rate,
                    amount=amount,
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={"register_qty": str(register_qty), "reversal_qty": str(reversal_qty)},
                    include_in_profit=True,
                    mapping_status="mapped",
                    unresolved_reason=None,
                )
            )
            line_no += 1

        return total, line_no, unresolved_count

    def _persist_subcontract_details(
        self,
        *,
        session: Session,
        snapshot: LyStyleProfitSnapshot,
        line_no: int,
        payload: StyleProfitSnapshotCreateRequest,
        unresolved_count: int,
    ) -> tuple[Decimal, int, int]:
        total = Decimal("0")
        for row in payload.subcontract_rows:
            settlement_locked = self._to_decimal_or_none(row.get("settlement_locked_net_amount"))
            provisional = self._to_decimal_or_none(
                row.get("provisional_inspection_net_amount")
                if row.get("provisional_inspection_net_amount") is not None
                else row.get("inspection_net_amount")
            )
            source_line_no = self._normalize_text(row.get("line_no")) or ""
            source_name = self._normalize_text(row.get("statement_no")) or self._normalize_text(row.get("inspection_no"))
            if not source_name:
                source_name = self._normalize_text(row.get("name")) or "SUBCONTRACT"
            row_company = self._normalize_text(row.get("company"))
            row_item_code = self._normalize_text(row.get("item_code") or row.get("style_item_code"))
            row_sales_order = self._normalize_text(row.get("sales_order"))
            row_work_order = self._normalize_text(row.get("work_order"))
            row_job_card = self._normalize_text(row.get("job_card"))
            row_job_card_work_order = self._normalize_text(
                row.get("job_card_work_order")
                or row.get("job_card_work_order_no")
                or row.get("job_card_parent_work_order")
            )
            row_production_plan_id = self._normalize_text(row.get("production_plan_id"))
            row_subcontract_order = self._normalize_text(row.get("subcontract_order"))
            row_profit_scope_status = self._normalize_text(row.get("profit_scope_status")).lower()
            row_profit_scope_error = self._normalize_text(row.get("profit_scope_error_code")) or "SUBCONTRACT_SCOPE_UNTRUSTED"
            bridge_source = self._normalize_text(row.get("bridge_source")) or None
            row_inspected_at = self._none_if_empty(row.get("inspected_at"))
            diagnostic_raw_ref = self._subcontract_diagnostic_raw_ref(row=row)
            if not row_inspected_at:
                scope_status, scope_reason = "unresolved", "SUBCONTRACT_INSPECTED_AT_REQUIRED"
            elif row_profit_scope_status != "ready":
                if row_profit_scope_status in {"", "unknown"}:
                    scope_status, scope_reason = "unresolved", "SUBCONTRACT_SCOPE_STATUS_REQUIRED"
                else:
                    scope_status, scope_reason = "unresolved", row_profit_scope_error
            else:
                resolved_bridge_work_order, bridge_lookup_status = self._resolve_subcontract_bridge_work_order(
                    session=session,
                    expected_company=self._normalize_text(snapshot.company),
                    expected_item=self._normalize_text(snapshot.item_code),
                    expected_sales_order=self._normalize_text(snapshot.sales_order),
                    row_job_card=row_job_card,
                    row_job_card_work_order=row_job_card_work_order,
                    row_production_plan_id=row_production_plan_id,
                    row_subcontract_order=row_subcontract_order,
                )
                scope_status, scope_reason = self._match_subcontract_profit_scope(
                    expected_company=self._normalize_text(snapshot.company),
                    expected_item=self._normalize_text(snapshot.item_code),
                    expected_sales_order=self._normalize_text(snapshot.sales_order),
                    expected_work_order=self._normalize_text(payload.work_order),
                    row_company=row_company,
                    row_item_code=row_item_code,
                    row_sales_order=row_sales_order,
                    row_work_order=row_work_order,
                    resolved_bridge_work_order=resolved_bridge_work_order,
                    bridge_lookup_status=bridge_lookup_status,
                )
            source_item_code = row_item_code or None

            if settlement_locked is not None:
                scope_source_doctype = "Subcontract Settlement"
                scope_source_status = "submitted"
                scope_amount = settlement_locked
            elif provisional is not None:
                scope_source_doctype = "Subcontract Inspection"
                scope_source_status = "provisional"
                scope_amount = provisional
            else:
                scope_source_doctype = "Subcontract Source"
                scope_source_status = self._normalize_text(row.get("status")).lower() or "unknown"
                scope_amount = Decimal("0")

            if scope_status == "excluded":
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=None,
                        company=row_company or str(snapshot.company),
                        sales_order=row_sales_order or snapshot.sales_order,
                        style_item_code=row_item_code or str(snapshot.item_code),
                        source_item_code=source_item_code,
                        work_order=row_work_order or None,
                        job_card=row_job_card or None,
                        source_system="fastapi",
                        source_doctype=scope_source_doctype,
                        source_status=scope_source_status,
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=None,
                        unit_rate=None,
                        amount=scope_amount,
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={
                            "scope_reason": scope_reason,
                            "bridge_source": bridge_source,
                            "inspected_at": row_inspected_at,
                            **diagnostic_raw_ref,
                        },
                        include_in_profit=False,
                        mapping_status="excluded",
                        unresolved_reason=scope_reason,
                    )
                )
                continue

            if scope_status == "unresolved":
                detail = LyStyleProfitDetail(
                    snapshot_id=int(snapshot.id),
                    line_no=line_no,
                    cost_type="unresolved",
                    source_type=scope_source_doctype,
                    source_name=source_name,
                    item_code=source_item_code,
                    qty=None,
                    unit_rate=None,
                    amount=Decimal("0"),
                    formula_code="SUBCONTRACT_V1",
                    is_unresolved=True,
                    unresolved_reason=scope_reason,
                    raw_ref={
                        "scope_reason": scope_reason,
                        "bridge_source": bridge_source,
                        "inspected_at": row_inspected_at,
                        **diagnostic_raw_ref,
                    },
                )
                session.add(detail)
                session.flush()
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=int(detail.id),
                        company=row_company or str(snapshot.company),
                        sales_order=row_sales_order or snapshot.sales_order,
                        style_item_code=row_item_code or str(snapshot.item_code),
                        source_item_code=source_item_code,
                        work_order=row_work_order or None,
                        job_card=row_job_card or None,
                        source_system="fastapi",
                        source_doctype=scope_source_doctype,
                        source_status=scope_source_status,
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=None,
                        unit_rate=None,
                        amount=scope_amount,
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={
                            "scope_reason": scope_reason,
                            "bridge_source": bridge_source,
                            "inspected_at": row_inspected_at,
                            **diagnostic_raw_ref,
                        },
                        include_in_profit=False,
                        mapping_status="unresolved",
                        unresolved_reason=scope_reason,
                    )
                )
                unresolved_count += 1
                line_no += 1
                continue

            if scope_source_status in {"cancelled", "canceled"}:
                session.add(
                    LyStyleProfitSourceMap(
                        snapshot_id=int(snapshot.id),
                        detail_id=None,
                        company=row_company or str(snapshot.company),
                        sales_order=row_sales_order or snapshot.sales_order,
                        style_item_code=row_item_code or str(snapshot.item_code),
                        source_item_code=source_item_code,
                        work_order=row_work_order or None,
                        job_card=row_job_card or None,
                        source_system="fastapi",
                        source_doctype=scope_source_doctype,
                        source_status=scope_source_status,
                        source_name=source_name,
                        source_line_no=source_line_no,
                        qty=None,
                        unit_rate=None,
                        amount=scope_amount,
                        currency=None,
                        warehouse=None,
                        posting_date=None,
                        raw_ref={
                            "reason": "SUBCONTRACT_CANCELLED",
                            "inspected_at": row_inspected_at,
                            **diagnostic_raw_ref,
                        },
                        include_in_profit=False,
                        mapping_status="excluded",
                        unresolved_reason="SUBCONTRACT_CANCELLED",
                    )
                )
                continue

            if settlement_locked is not None:
                amount = settlement_locked
                source_doctype = "Subcontract Settlement"
                source_status = "submitted"
            elif payload.include_provisional_subcontract and provisional is not None:
                amount = provisional
                source_doctype = "Subcontract Inspection"
                source_status = "provisional"
            else:
                if provisional is not None:
                    session.add(
                        LyStyleProfitSourceMap(
                            snapshot_id=int(snapshot.id),
                            detail_id=None,
                            company=str(snapshot.company),
                            sales_order=snapshot.sales_order,
                            style_item_code=str(snapshot.item_code),
                            source_item_code=str(snapshot.item_code),
                            source_system="fastapi",
                            source_doctype="Subcontract Inspection",
                            source_status="provisional",
                            source_name=source_name,
                            source_line_no=source_line_no,
                            qty=None,
                            unit_rate=None,
                                amount=provisional,
                                currency=None,
                                warehouse=None,
                                posting_date=None,
                                raw_ref={
                                    "reason": "SUBCONTRACT_UNSETTLED_EXCLUDED",
                                    "bridge_source": bridge_source,
                                    "inspected_at": row_inspected_at,
                                    **diagnostic_raw_ref,
                                },
                                include_in_profit=False,
                                mapping_status="excluded",
                                unresolved_reason="SUBCONTRACT_UNSETTLED_EXCLUDED",
                            )
                    )
                else:
                    session.add(
                        LyStyleProfitSourceMap(
                            snapshot_id=int(snapshot.id),
                            detail_id=None,
                            company=row_company or str(snapshot.company),
                            sales_order=row_sales_order or snapshot.sales_order,
                            style_item_code=row_item_code or str(snapshot.item_code),
                            source_item_code=source_item_code,
                            work_order=row_work_order or None,
                            job_card=row_job_card or None,
                            source_system="fastapi",
                            source_doctype=scope_source_doctype,
                            source_status=scope_source_status,
                            source_name=source_name,
                            source_line_no=source_line_no,
                            qty=None,
                            unit_rate=None,
                                amount=Decimal("0"),
                                currency=None,
                                warehouse=None,
                                posting_date=None,
                                raw_ref={
                                    "reason": "SUBCONTRACT_UNSETTLED_EXCLUDED",
                                    "bridge_source": bridge_source,
                                    "inspected_at": row_inspected_at,
                                    **diagnostic_raw_ref,
                                },
                                include_in_profit=False,
                                mapping_status="excluded",
                                unresolved_reason="SUBCONTRACT_UNSETTLED_EXCLUDED",
                            )
                    )
                continue

            total += amount
            detail = LyStyleProfitDetail(
                snapshot_id=int(snapshot.id),
                line_no=line_no,
                cost_type="subcontract",
                source_type=source_doctype,
                source_name=source_name,
                item_code=source_item_code,
                qty=None,
                unit_rate=None,
                amount=amount,
                formula_code="SUBCONTRACT_V1",
                is_unresolved=False,
                unresolved_reason=None,
                raw_ref={
                    "source_doctype": source_doctype,
                    "bridge_source": bridge_source,
                    "inspected_at": row_inspected_at,
                    **diagnostic_raw_ref,
                },
            )
            session.add(detail)
            session.flush()
            session.add(
                LyStyleProfitSourceMap(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    company=str(snapshot.company),
                    sales_order=snapshot.sales_order,
                    style_item_code=str(snapshot.item_code),
                    source_item_code=source_item_code,
                    source_system="fastapi",
                    source_doctype=source_doctype,
                    source_status=source_status,
                    source_name=source_name,
                    source_line_no=source_line_no,
                    qty=None,
                    unit_rate=None,
                    amount=amount,
                    currency=None,
                    warehouse=None,
                    posting_date=None,
                    raw_ref={
                        "source_doctype": source_doctype,
                        "bridge_source": bridge_source,
                        "inspected_at": row_inspected_at,
                        **diagnostic_raw_ref,
                    },
                    include_in_profit=True,
                    mapping_status="mapped",
                    unresolved_reason=None,
                )
            )
            line_no += 1

        return total, line_no, unresolved_count

    def _subcontract_diagnostic_raw_ref(self, *, row: dict[str, Any]) -> dict[str, Any]:
        diagnostic_total_missing = self._normalize_text(row.get("diagnostic_total_missing_inspected_at"))
        diagnostic_truncated_count = self._normalize_text(row.get("diagnostic_truncated_count"))
        extra: dict[str, Any] = {}
        if diagnostic_total_missing:
            extra["diagnostic_total_missing_inspected_at"] = diagnostic_total_missing
        if diagnostic_truncated_count:
            extra["diagnostic_truncated_count"] = diagnostic_truncated_count
        return extra

    @staticmethod
    def _match_subcontract_profit_scope(
        *,
        expected_company: str,
        expected_item: str,
        expected_sales_order: str,
        expected_work_order: str,
        row_company: str,
        row_item_code: str,
        row_sales_order: str,
        row_work_order: str,
        resolved_bridge_work_order: str,
        bridge_lookup_status: str,
    ) -> tuple[str, str | None]:
        if row_company and row_company != expected_company:
            return "excluded", "SUBCONTRACT_COMPANY_MISMATCH"
        if row_item_code and row_item_code != expected_item:
            return "excluded", "SUBCONTRACT_ITEM_MISMATCH"
        if row_sales_order and row_sales_order != expected_sales_order:
            return "excluded", "SUBCONTRACT_SCOPE_UNTRUSTED"

        if not row_company:
            return "unresolved", "company_scope_missing"
        if not row_item_code:
            return "unresolved", "item_scope_missing"
        if not row_sales_order:
            return "unresolved", "SUBCONTRACT_SCOPE_UNTRUSTED"

        if not expected_work_order:
            return "mapped", None

        if row_work_order:
            if row_work_order == expected_work_order:
                return "mapped", None
            return "excluded", "SUBCONTRACT_WORK_ORDER_MISMATCH"

        if bridge_lookup_status == "resolved" and resolved_bridge_work_order:
            if resolved_bridge_work_order == expected_work_order:
                return "mapped", None
            return "excluded", "SUBCONTRACT_WORK_ORDER_MISMATCH"
        if bridge_lookup_status == "mismatch":
            return "excluded", "SUBCONTRACT_WORK_ORDER_MISMATCH"
        return "unresolved", "SUBCONTRACT_WORK_ORDER_UNTRUSTED"

    def _resolve_subcontract_bridge_work_order(
        self,
        *,
        session: Session,
        expected_company: str,
        expected_item: str,
        expected_sales_order: str,
        row_job_card: str,
        row_job_card_work_order: str,
        row_production_plan_id: str,
        row_subcontract_order: str,
    ) -> tuple[str, str]:
        """Resolve trusted Work Order bridge for subcontract rows.

        Returns:
            (resolved_work_order, lookup_status)
            lookup_status in {"resolved", "mismatch", "untrusted"}
        """

        if row_subcontract_order:
            try:
                order = (
                    session.query(LySubcontractOrder)
                    .filter(LySubcontractOrder.subcontract_no == row_subcontract_order)
                    .one_or_none()
                )
            except SQLAlchemyError:
                return "", "untrusted"
            if order is not None:
                order_company = self._normalize_text(order.company)
                order_item = self._normalize_text(order.item_code)
                order_sales_order = self._normalize_text(order.sales_order)
                if (
                    order_company != expected_company
                    or order_item != expected_item
                    or order_sales_order != expected_sales_order
                ):
                    return "", "mismatch"
                order_work_order = self._normalize_text(order.work_order)
                if order_work_order:
                    return order_work_order, "resolved"

        if row_production_plan_id:
            try:
                plan_id = int(row_production_plan_id)
            except (TypeError, ValueError):
                plan_id = None
            if plan_id is not None:
                try:
                    plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one_or_none()
                except SQLAlchemyError:
                    return "", "untrusted"
                if plan is not None:
                    plan_company = self._normalize_text(plan.company)
                    plan_item = self._normalize_text(plan.item_code)
                    plan_sales_order = self._normalize_text(plan.sales_order)
                    if (
                        plan_company != expected_company
                        or plan_item != expected_item
                        or plan_sales_order != expected_sales_order
                    ):
                        return "", "mismatch"
                    try:
                        link_rows = (
                            session.query(LyProductionWorkOrderLink.work_order)
                            .filter(LyProductionWorkOrderLink.plan_id == plan_id)
                            .all()
                        )
                    except SQLAlchemyError:
                        return "", "untrusted"
                    work_orders = {
                        self._normalize_text(row.work_order)
                        for row in link_rows
                        if self._normalize_text(row.work_order)
                    }
                    if len(work_orders) == 1:
                        return next(iter(work_orders)), "resolved"

        if row_job_card:
            try:
                link = (
                    session.query(LyProductionJobCardLink)
                    .filter(LyProductionJobCardLink.job_card == row_job_card)
                    .order_by(LyProductionJobCardLink.id.desc())
                    .first()
                )
            except SQLAlchemyError:
                return "", "untrusted"
            if link is not None:
                try:
                    plan = (
                        session.query(LyProductionPlan)
                        .filter(LyProductionPlan.id == link.plan_id)
                        .one_or_none()
                    )
                except SQLAlchemyError:
                    return "", "untrusted"
                if plan is not None:
                    plan_company = self._normalize_text(plan.company)
                    plan_item = self._normalize_text(plan.item_code)
                    plan_sales_order = self._normalize_text(plan.sales_order)
                    if (
                        plan_company == expected_company
                        and plan_item == expected_item
                        and plan_sales_order == expected_sales_order
                    ):
                        link_work_order = self._normalize_text(link.work_order)
                        if link_work_order:
                            return link_work_order, "resolved"
                    else:
                        return "", "mismatch"

        if row_job_card_work_order:
            # Keep strict fail-closed: unverified bridge hints cannot be trusted directly.
            return "", "untrusted"

        return "", "untrusted"

    def _match_profit_scope(
        self,
        *,
        snapshot: LyStyleProfitSnapshot,
        payload: StyleProfitSnapshotCreateRequest,
        source_type: str,
        row_company: str,
        row_item_code: str,
        row_sales_order: str,
        row_work_order: str,
        row_job_card: str,
        row_job_card_work_order: str,
        row_production_plan_id: str,
        row_subcontract_order: str,
    ) -> tuple[str, str | None]:
        expected_company = self._normalize_text(snapshot.company)
        expected_item = self._normalize_text(snapshot.item_code)
        expected_sales_order = self._normalize_text(snapshot.sales_order)
        expected_work_order = self._normalize_text(payload.work_order)

        hard_status, hard_reason = self._validate_required_scope_fields(
            source_type=source_type,
            expected_company=expected_company,
            expected_item=expected_item,
            expected_sales_order=expected_sales_order,
            row_company=row_company,
            row_item_code=row_item_code,
            row_sales_order=row_sales_order,
        )
        if hard_status != "bridge":
            return hard_status, hard_reason

        return self._match_scope_bridge(
            source_type=source_type,
            expected_work_order=expected_work_order,
            row_work_order=row_work_order,
            row_job_card=row_job_card,
            row_job_card_work_order=row_job_card_work_order,
            row_production_plan_id=row_production_plan_id,
            row_subcontract_order=row_subcontract_order,
            hard_reason=hard_reason,
        )

    def _validate_required_scope_fields(
        self,
        *,
        source_type: str,
        expected_company: str,
        expected_item: str,
        expected_sales_order: str,
        row_company: str,
        row_item_code: str,
        row_sales_order: str,
    ) -> tuple[str, str | None]:
        is_subcontract = source_type == "Subcontract"
        if row_company and row_company != expected_company:
            return "excluded", "SUBCONTRACT_COMPANY_MISMATCH" if is_subcontract else "company_scope_mismatch"
        if row_item_code and row_item_code != expected_item:
            return "excluded", "SUBCONTRACT_ITEM_MISMATCH" if is_subcontract else "item_scope_mismatch"
        if row_sales_order and row_sales_order != expected_sales_order:
            return "excluded", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "sales_order_scope_mismatch"

        if row_company and row_item_code and row_sales_order:
            return "mapped", None

        if not row_company:
            return "bridge", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "company_scope_missing"
        if not row_item_code:
            return "bridge", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "item_scope_missing"
        if not row_sales_order:
            return "bridge", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "unable_to_link_profit_scope"
        return "bridge", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "unable_to_link_profit_scope"

    def _match_scope_bridge(
        self,
        *,
        source_type: str,
        expected_work_order: str,
        row_work_order: str,
        row_job_card: str,
        row_job_card_work_order: str,
        row_production_plan_id: str,
        row_subcontract_order: str,
        hard_reason: str | None,
    ) -> tuple[str, str | None]:
        # TASK-005D3: without trusted bridge lookups for company/item/sales_order triad,
        # bridge references alone cannot map records into profit scope.
        _ = (row_job_card, row_production_plan_id, row_subcontract_order)
        is_subcontract = source_type == "Subcontract"
        if expected_work_order and row_work_order and row_work_order != expected_work_order:
            return "excluded", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "work_order_scope_mismatch"
        if expected_work_order and row_job_card_work_order and row_job_card_work_order != expected_work_order:
            return "excluded", "SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "work_order_scope_mismatch"
        return "unresolved", hard_reason or ("SUBCONTRACT_SCOPE_UNTRUSTED" if is_subcontract else "unable_to_link_profit_scope")

    @staticmethod
    def _resolve_standard_unit_cost(row: dict[str, Any]) -> tuple[Decimal | None, str | None]:
        if row.get("standard_unit_cost") is not None:
            return Decimal(str(row.get("standard_unit_cost"))), "standard_unit_cost"
        if row.get("item_price") is not None:
            return Decimal(str(row.get("item_price"))), "item_price"
        if row.get("valuation_rate") is not None:
            return Decimal(str(row.get("valuation_rate"))), "valuation_rate"
        return None, None

    @staticmethod
    def _to_result(snapshot: LyStyleProfitSnapshot, *, idempotent_replay: bool) -> StyleProfitSnapshotResult:
        return StyleProfitSnapshotResult(
            snapshot_id=int(snapshot.id),
            snapshot_no=str(snapshot.snapshot_no),
            company=str(snapshot.company),
            item_code=str(snapshot.item_code),
            sales_order=str(snapshot.sales_order) if snapshot.sales_order else None,
            revenue_status=str(snapshot.revenue_status),
            revenue_amount=Decimal(str(snapshot.revenue_amount)),
            actual_total_cost=Decimal(str(snapshot.actual_total_cost)),
            standard_total_cost=Decimal(str(snapshot.standard_total_cost)),
            profit_amount=Decimal(str(snapshot.profit_amount)),
            profit_rate=Decimal(str(snapshot.profit_rate)) if snapshot.profit_rate is not None else None,
            snapshot_status=str(snapshot.snapshot_status),
            allocation_status=str(snapshot.allocation_status),
            include_provisional_subcontract=bool(snapshot.include_provisional_subcontract),
            unresolved_count=int(snapshot.unresolved_count or 0),
            idempotency_key=str(snapshot.idempotency_key),
            request_hash=str(snapshot.request_hash),
            idempotent_replay=idempotent_replay,
        )

    @staticmethod
    def _build_snapshot_no() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"SP-{ts}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _none_if_empty(cls, value: Any) -> str | None:
        normalized = cls._normalize_text(value)
        return normalized if normalized else None

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _to_decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    @classmethod
    def _extract_decimal_by_keys(cls, row: dict[str, Any], *keys: str) -> tuple[Decimal | None, bool]:
        has_candidate = False
        for key in keys:
            if key not in row:
                continue
            has_candidate = True
            value = row.get(key)
            parsed = cls._to_decimal_or_none(value)
            if parsed is None:
                continue
            return parsed, True
        if has_candidate:
            return None, False
        return None, False
