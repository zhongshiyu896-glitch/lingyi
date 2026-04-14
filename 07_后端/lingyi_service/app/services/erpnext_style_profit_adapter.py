"""ERPNext/local fact adapter for style-profit API source collection (TASK-005F)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
import json
import os
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import Request
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import STYLE_PROFIT_BOM_REQUIRED
from app.core.error_codes import STYLE_PROFIT_SOURCE_UNAVAILABLE
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.workshop import YsWorkshopTicket
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder


class ERPNextStyleProfitAdapter:
    """Load trusted source facts for style-profit snapshot creation.

    Rules:
    - Revenue/stock facts come from ERPNext REST read APIs.
    - BOM/workshop/subcontract bridge facts come from local DB.
    - Any ERPNext source failure is fail-closed with STYLE_PROFIT_SOURCE_UNAVAILABLE.
    """
    _SUBCONTRACT_DIAGNOSTIC_LIMIT_ENV = "STYLE_PROFIT_SUBCONTRACT_DIAGNOSTIC_LIMIT"
    _DEFAULT_SUBCONTRACT_DIAGNOSTIC_LIMIT = 200

    def __init__(self, *, session: Session, request_obj: Request | None = None) -> None:
        self.session = session
        self.request_obj = request_obj
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    # -----------------------------
    # Revenue facts
    # -----------------------------
    def load_submitted_sales_invoice_rows(self, selector: Any) -> list[dict[str, Any]]:
        """Load submitted Sales Invoice rows matching selector scope."""
        headers = self._list_sales_invoice_headers(selector)
        rows: list[dict[str, Any]] = []
        for header in headers:
            invoice_name = self._normalize_text(header.get("name"))
            if not invoice_name:
                continue
            doc = self._get_sales_invoice_doc(invoice_name)
            if not self._is_submitted_doc(doc):
                continue

            company = self._normalize_text(doc.get("company"))
            if company and company != self._normalize_text(selector.company):
                continue

            status = self._normalize_text(doc.get("status")).lower() or "submitted"
            header_order = self._normalize_text(doc.get("sales_order"))
            items = doc.get("items") if isinstance(doc.get("items"), list) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_code = self._normalize_text(item.get("item_code"))
                if item_code != self._normalize_text(selector.item_code):
                    continue
                sales_order = self._normalize_text(item.get("sales_order")) or header_order
                if sales_order != self._normalize_text(selector.sales_order):
                    continue
                rows.append(
                    {
                        "docstatus": 1,
                        "status": status,
                        "company": company,
                        "sales_order": sales_order,
                        "item_code": item_code,
                        "name": invoice_name,
                        "line_no": self._normalize_text(item.get("idx") or item.get("name") or ""),
                        "qty": self._decimal_text(item.get("qty")),
                        "rate": self._decimal_text(item.get("rate")),
                        "base_net_amount": self._decimal_text(
                            item.get("base_net_amount", item.get("base_amount", item.get("amount")))
                        ),
                        "posting_date": self._normalize_text(doc.get("posting_date")),
                    }
                )
        rows.sort(key=lambda row: (str(row.get("name") or ""), str(row.get("line_no") or "")))
        return rows

    def load_submitted_sales_order_rows(self, selector: Any) -> list[dict[str, Any]]:
        """Load submitted Sales Order rows as estimated revenue fallback."""
        sales_order = self._normalize_text(selector.sales_order)
        if not sales_order:
            return []

        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Sales%20Order/{parse.quote(sales_order, safe='')}"
                f"?fields={parse.quote('[\"name\",\"docstatus\",\"status\",\"company\",\"items\"]', safe='')}"
            ),
            allow_404=True,
        )
        if payload is None:
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            raise self._source_unavailable("Sales Order 返回结构异常")
        if not self._is_submitted_doc(data):
            return []

        company = self._normalize_text(data.get("company"))
        if company and company != self._normalize_text(selector.company):
            return []

        status = self._normalize_text(data.get("status")).lower() or "submitted"
        rows: list[dict[str, Any]] = []
        items = data.get("items") if isinstance(data.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_code = self._normalize_text(item.get("item_code"))
            if item_code != self._normalize_text(selector.item_code):
                continue
            rows.append(
                {
                    "docstatus": 1,
                    "status": status,
                    "company": company,
                    "sales_order": sales_order,
                    "item_code": item_code,
                    "name": self._normalize_text(data.get("name") or sales_order),
                    "line_no": self._normalize_text(item.get("idx") or item.get("name") or ""),
                    "qty": self._decimal_text(item.get("qty")),
                    "rate": self._decimal_text(item.get("rate")),
                    "base_amount": self._decimal_text(
                        item.get("base_amount", item.get("base_net_amount", item.get("amount")))
                    ),
                }
            )
        rows.sort(key=lambda row: (str(row.get("name") or ""), str(row.get("line_no") or "")))
        return rows

    # -----------------------------
    # BOM facts (local DB)
    # -----------------------------
    def load_active_default_bom_rows(
        self,
        *,
        company: str,
        item_code: str,
        planned_qty: Decimal,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        """Load active+default BOM material/operation rows from local DB."""
        _ = company  # reserved for future per-company BOM constraints
        try:
            bom = (
                self.session.query(LyApparelBom)
                .filter(
                    LyApparelBom.item_code == self._normalize_text(item_code),
                    LyApparelBom.status == "active",
                    LyApparelBom.is_default.is_(True),
                )
                .order_by(LyApparelBom.updated_at.desc(), LyApparelBom.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc

        if bom is None:
            raise BusinessException(code=STYLE_PROFIT_BOM_REQUIRED, message="缺少 active/default BOM，无法创建利润快照")

        try:
            bom_items = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == int(bom.id))
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
            bom_operations = (
                self.session.query(LyBomOperation)
                .filter(LyBomOperation.bom_id == int(bom.id))
                .order_by(LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc

        safe_planned_qty = planned_qty if planned_qty > Decimal("0") else Decimal("1")
        material_rows: list[dict[str, Any]] = []
        allowed_codes: list[str] = []
        for row in bom_items:
            material_code = self._normalize_text(row.material_item_code)
            if not material_code:
                continue
            qty_per_piece = self._to_decimal(row.qty_per_piece)
            loss_rate = self._to_decimal(row.loss_rate)
            required_qty = qty_per_piece * safe_planned_qty * (Decimal("1") + loss_rate)

            unit_cost, unit_cost_source = self._resolve_material_unit_cost(
                material_item_code=material_code,
                company=self._normalize_text(company),
            )

            payload: dict[str, Any] = {
                "line_no": str(row.id),
                "material_item_code": material_code,
                "item_code": material_code,
                "qty_per_piece": self._decimal_text(qty_per_piece),
                "loss_rate": self._decimal_text(loss_rate),
                "bom_required_qty_with_loss": self._decimal_text(required_qty),
                "required_qty": self._decimal_text(required_qty),
            }
            if unit_cost is not None and unit_cost_source == "item_price":
                payload["item_price"] = self._decimal_text(unit_cost)
            elif unit_cost is not None and unit_cost_source == "valuation_rate":
                payload["valuation_rate"] = self._decimal_text(unit_cost)

            material_rows.append(payload)
            allowed_codes.append(material_code)

        operation_rows: list[dict[str, Any]] = []
        for row in bom_operations:
            operation_rows.append(
                {
                    "line_no": str(row.id),
                    "operation": self._normalize_text(row.process_name) or f"OP-{row.sequence_no}",
                    "bom_operation_rate": (
                        self._decimal_text(row.wage_rate) if row.wage_rate is not None else None
                    ),
                    "planned_qty": self._decimal_text(safe_planned_qty),
                }
            )

        allowed_codes_sorted = sorted({code for code in allowed_codes if code})
        return material_rows, operation_rows, allowed_codes_sorted

    # -----------------------------
    # Material facts (ERPNext)
    # -----------------------------
    def load_stock_ledger_rows(
        self,
        selector: Any,
        *,
        allowed_material_item_codes: list[str],
    ) -> list[dict[str, Any]]:
        """Load ERPNext SLE rows; caller still applies allow-list fail-closed filter."""
        if not allowed_material_item_codes:
            return []

        rows: list[dict[str, Any]] = []
        for material_code in sorted({self._normalize_text(code) for code in allowed_material_item_codes if self._normalize_text(code)}):
            filters = [
                ["company", "=", self._normalize_text(selector.company)],
                ["item_code", "=", material_code],
                ["posting_date", ">=", selector.from_date.isoformat()],
                ["posting_date", "<=", selector.to_date.isoformat()],
            ]
            payload = self._request_json(
                method="GET",
                path=(
                    "/api/resource/Stock%20Ledger%20Entry"
                    f"?fields={parse.quote(json.dumps(['name','voucher_type','voucher_no','item_code','warehouse','actual_qty','valuation_rate','stock_value_difference','posting_date','company','docstatus','status','is_cancelled','sales_order','work_order','production_plan_id','job_card','custom_ly_sales_order','custom_ly_work_order','custom_ly_production_plan','custom_ly_job_card','currency'], ensure_ascii=False), safe='')}"
                    f"&filters={parse.quote(json.dumps(filters, ensure_ascii=False), safe='')}"
                    "&limit_page_length=2000"
                ),
                allow_404=True,
            )
            if payload is None:
                continue
            data = payload.get("data")
            if not isinstance(data, list):
                raise self._source_unavailable("Stock Ledger Entry 返回结构异常")
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                rows.append(
                    {
                        "name": self._normalize_text(entry.get("name")),
                        "voucher_type": self._normalize_text(entry.get("voucher_type")) or "Stock Ledger Entry",
                        "voucher_no": self._normalize_text(entry.get("voucher_no")),
                        "item_code": self._normalize_text(entry.get("item_code")),
                        "warehouse": self._normalize_text(entry.get("warehouse")) or None,
                        "actual_qty": self._decimal_text(entry.get("actual_qty")),
                        "valuation_rate": self._decimal_text(entry.get("valuation_rate")),
                        "stock_value_difference": self._decimal_text(entry.get("stock_value_difference")),
                        "posting_date": self._normalize_text(entry.get("posting_date")),
                        "company": self._normalize_text(entry.get("company")) or None,
                        "docstatus": entry.get("docstatus"),
                        "status": self._normalize_text(entry.get("status")) or None,
                        "is_cancelled": entry.get("is_cancelled"),
                        "sales_order": self._normalize_text(
                            entry.get("sales_order") or entry.get("custom_ly_sales_order")
                        )
                        or None,
                        "work_order": self._normalize_text(
                            entry.get("work_order") or entry.get("custom_ly_work_order")
                        )
                        or None,
                        "production_plan_id": entry.get("production_plan_id", entry.get("custom_ly_production_plan")),
                        "job_card": self._normalize_text(
                            entry.get("job_card") or entry.get("custom_ly_job_card")
                        )
                        or None,
                        "custom_ly_sales_order": self._normalize_text(entry.get("custom_ly_sales_order")) or None,
                        "custom_ly_work_order": self._normalize_text(entry.get("custom_ly_work_order")) or None,
                        "custom_ly_production_plan": entry.get("custom_ly_production_plan"),
                        "custom_ly_job_card": self._normalize_text(entry.get("custom_ly_job_card")) or None,
                        "currency": self._normalize_text(entry.get("currency")) or None,
                        "line_no": self._normalize_text(entry.get("name")),
                    }
                )
        rows.sort(
            key=lambda row: (
                str(row.get("posting_date") or ""),
                str(row.get("voucher_no") or ""),
                str(row.get("name") or ""),
            )
        )
        return rows

    def load_purchase_receipt_rows(
        self,
        selector: Any,
        *,
        allowed_material_item_codes: list[str],
    ) -> list[dict[str, Any]]:
        """Purchase Receipt is reference-only for tracing in V1.

        We keep this lightweight and optional in TASK-005F.
        """
        _ = (selector, allowed_material_item_codes)
        return []

    # -----------------------------
    # Local workshop / subcontract facts
    # -----------------------------
    def load_workshop_ticket_rows(self, selector: Any) -> list[dict[str, Any]]:
        """Load workshop tickets from trusted local facts with scope bridge."""
        try:
            query = (
                self.session.query(YsWorkshopTicket, LyProductionJobCardLink, LyProductionPlan)
                .outerjoin(LyProductionJobCardLink, LyProductionJobCardLink.job_card == YsWorkshopTicket.job_card)
                .outerjoin(LyProductionPlan, LyProductionPlan.id == LyProductionJobCardLink.plan_id)
                .filter(
                    YsWorkshopTicket.work_date >= selector.from_date,
                    YsWorkshopTicket.work_date <= selector.to_date,
                    YsWorkshopTicket.item_code == self._normalize_text(selector.item_code),
                )
                .order_by(YsWorkshopTicket.work_date.asc(), YsWorkshopTicket.id.asc())
            )
            rows = query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc

        payload_rows: list[dict[str, Any]] = []
        expected_company = self._normalize_text(selector.company)
        expected_order = self._normalize_text(selector.sales_order)
        expected_work_order = self._normalize_text(getattr(selector, "work_order", None))

        for ticket, link, plan in rows:
            derived_company = self._normalize_text(
                (plan.company if plan is not None else None)
                or (link.company if link is not None else None)
            )
            derived_item_code = self._normalize_text(ticket.item_code) or self._normalize_text(
                (plan.item_code if plan is not None else None)
                or (link.item_code if link is not None else None)
            )
            derived_sales_order = self._normalize_text((plan.sales_order if plan is not None else None))
            derived_work_order = self._normalize_text(ticket.work_order) or self._normalize_text(
                (link.work_order if link is not None else None)
            )

            # Candidate narrowing: keep rows only if they can be linked by order/work_order.
            has_scope_hint = False
            if expected_order and derived_sales_order and derived_sales_order == expected_order:
                has_scope_hint = True
            if expected_work_order and derived_work_order and derived_work_order == expected_work_order:
                has_scope_hint = True
            if not has_scope_hint:
                continue

            register_qty = ticket.qty if self._normalize_text(ticket.operation_type).lower() == "register" else Decimal("0")
            reversal_qty = ticket.qty if self._normalize_text(ticket.operation_type).lower() == "reversal" else Decimal("0")
            source_status = "submitted"
            if self._normalize_text(ticket.sync_status).lower() in {"failed", "dead"}:
                source_status = "unknown"

            payload_rows.append(
                {
                    "ticket_no": self._normalize_text(ticket.ticket_no) or self._normalize_text(ticket.id),
                    "name": self._normalize_text(ticket.ticket_no) or self._normalize_text(ticket.id),
                    "line_no": self._normalize_text(ticket.id),
                    "status": source_status,
                    "company": derived_company or expected_company,
                    "item_code": derived_item_code,
                    "style_item_code": derived_item_code,
                    "sales_order": derived_sales_order or None,
                    "work_order": derived_work_order or None,
                    "job_card": self._normalize_text(ticket.job_card) or None,
                    "register_qty": self._decimal_text(register_qty),
                    "reversal_qty": self._decimal_text(reversal_qty),
                    "wage_rate_snapshot": self._decimal_text(ticket.unit_wage),
                    "work_date": ticket.work_date.isoformat() if isinstance(ticket.work_date, date) else None,
                }
            )

        payload_rows.sort(key=lambda row: (str(row.get("name") or ""), str(row.get("line_no") or "")))
        return payload_rows

    def load_subcontract_rows(self, selector: Any) -> list[dict[str, Any]]:
        """Load subcontract candidates with bridge snapshot preference.

        Priority:
        1. Inspection bridge snapshot fields (inspection-first immutable fact).
        2. If inspection bridge is missing and order is ready, fallback to order bridge.
        3. If both are missing/untrusted, keep unresolved candidate for traceability.
        """
        expected_company = self._normalize_text(selector.company)
        expected_item_code = self._normalize_text(selector.item_code)
        expected_sales_order = self._normalize_text(selector.sales_order)
        expected_work_order = self._normalize_text(getattr(selector, "work_order", None))
        diagnostic_limit = self._subcontract_diagnostic_limit()

        merged_sales_order = func.coalesce(LySubcontractInspection.sales_order, LySubcontractOrder.sales_order)
        merged_work_order = func.coalesce(LySubcontractInspection.work_order, LySubcontractOrder.work_order)
        merged_company = func.coalesce(LySubcontractInspection.company, LySubcontractOrder.company)
        merged_item_code = func.coalesce(LySubcontractInspection.item_code, LySubcontractOrder.item_code)

        try:
            base_query = (
                self.session.query(LySubcontractInspection, LySubcontractOrder)
                .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
                .filter(
                    merged_company == expected_company,
                    merged_item_code == expected_item_code,
                )
            )
            if expected_sales_order:
                base_query = base_query.filter(
                    or_(
                        merged_sales_order == expected_sales_order,
                        merged_sales_order.is_(None),
                    )
                )
            if expected_work_order:
                base_query = base_query.filter(
                    or_(
                        merged_work_order == expected_work_order,
                        merged_work_order.is_(None),
                    )
                )

            period_from = datetime.combine(selector.from_date, datetime.min.time())
            period_to = datetime.combine(selector.to_date, datetime.max.time())
            period_query = (
                base_query.filter(
                    LySubcontractInspection.inspected_at.is_not(None),
                    LySubcontractInspection.inspected_at >= period_from,
                    LySubcontractInspection.inspected_at <= period_to,
                )
                .order_by(LySubcontractInspection.inspected_at.asc(), LySubcontractInspection.id.asc())
            )
            period_rows = period_query.all()

            missing_inspected_at_base = base_query.filter(LySubcontractInspection.inspected_at.is_(None))
            missing_inspected_at_total = int(missing_inspected_at_base.count())
            missing_inspected_at_rows = (
                missing_inspected_at_base.order_by(LySubcontractInspection.id.asc()).limit(diagnostic_limit).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc

        payload_rows: list[dict[str, Any]] = []

        def _append_payload_row(
            inspection: LySubcontractInspection,
            order: LySubcontractOrder,
            *,
            diagnostic_summary: dict[str, Any] | None = None,
        ) -> None:
            inspected_at_value = getattr(inspection, "inspected_at", None)
            if isinstance(inspected_at_value, datetime):
                inspected_at_text = inspected_at_value.isoformat()
                inspected_at_missing = False
            elif isinstance(inspected_at_value, date):
                inspected_at_text = inspected_at_value.isoformat()
                inspected_at_missing = False
            else:
                inspected_at_text = None
                inspected_at_missing = True

            settlement_status = self._normalize_text(inspection.settlement_status).lower()
            row_status = (
                self._normalize_text(inspection.status)
                or self._normalize_text(order.status)
                or "unknown"
            ).lower()
            net_amount = self._to_decimal_or_none(inspection.net_amount) or Decimal("0")
            locked_amount: str | None = None
            provisional_amount: str | None = None
            if settlement_status in {"locked", "settled"}:
                locked_amount = self._decimal_text(net_amount)
            elif net_amount > Decimal("0"):
                provisional_amount = self._decimal_text(net_amount)

            inspection_bridge = {
                "sales_order": self._normalize_text(getattr(inspection, "sales_order", None)) or None,
                "sales_order_item": self._normalize_text(getattr(inspection, "sales_order_item", None)) or None,
                "production_plan_id": getattr(inspection, "production_plan_id", None),
                "work_order": self._normalize_text(getattr(inspection, "work_order", None)) or None,
                "job_card": self._normalize_text(getattr(inspection, "job_card", None)) or None,
                "profit_scope_status": self._normalize_text(getattr(inspection, "profit_scope_status", None))
                or "unresolved",
                "profit_scope_error_code": self._normalize_text(getattr(inspection, "profit_scope_error_code", None)) or None,
            }
            order_bridge = {
                "sales_order": self._normalize_text(getattr(order, "sales_order", None)) or None,
                "sales_order_item": self._normalize_text(getattr(order, "sales_order_item", None)) or None,
                "production_plan_id": getattr(order, "production_plan_id", None),
                "work_order": self._normalize_text(getattr(order, "work_order", None)) or None,
                "job_card": self._normalize_text(getattr(order, "job_card", None)) or None,
                "profit_scope_status": self._normalize_text(getattr(order, "profit_scope_status", None)) or "unresolved",
                "profit_scope_error_code": self._normalize_text(getattr(order, "profit_scope_error_code", None)) or None,
            }
            use_order_bridge = False
            if not any(
                (
                    inspection_bridge["sales_order"],
                    inspection_bridge["work_order"],
                    inspection_bridge["production_plan_id"] is not None,
                    inspection_bridge["job_card"],
                )
            ):
                if order_bridge["profit_scope_status"] == "ready" and any(
                    (
                        order_bridge["sales_order"],
                        order_bridge["work_order"],
                        order_bridge["production_plan_id"] is not None,
                        order_bridge["job_card"],
                    )
                ):
                    use_order_bridge = True

            bridge = order_bridge if use_order_bridge else inspection_bridge
            bridge_source = "subcontract_order" if use_order_bridge else "subcontract_inspection"
            if not any(
                (
                    bridge["sales_order"],
                    bridge["work_order"],
                    bridge["production_plan_id"] is not None,
                    bridge["job_card"],
                )
            ):
                bridge["profit_scope_status"] = "unresolved"
                bridge["profit_scope_error_code"] = (
                    bridge["profit_scope_error_code"] or "SUBCONTRACT_SCOPE_UNTRUSTED"
                )
            if inspected_at_missing:
                bridge["profit_scope_status"] = "unresolved"
                bridge["profit_scope_error_code"] = "SUBCONTRACT_INSPECTED_AT_REQUIRED"
            payload = {
                "name": self._normalize_text(inspection.inspection_no) or f"SUB-{inspection.id}",
                "line_no": self._normalize_text(inspection.id),
                "inspection_no": self._normalize_text(inspection.inspection_no) or None,
                "statement_no": self._normalize_text(inspection.statement_no) or None,
                "subcontract_order": self._normalize_text(order.subcontract_no) or None,
                "company": self._normalize_text(inspection.company or order.company) or None,
                "item_code": self._normalize_text(inspection.item_code or order.item_code) or None,
                "sales_order": bridge["sales_order"],
                "sales_order_item": bridge["sales_order_item"],
                "work_order": bridge["work_order"],
                "production_plan_id": bridge["production_plan_id"],
                "job_card": bridge["job_card"],
                "bridge_source": bridge_source,
                "profit_scope_status": bridge["profit_scope_status"],
                "profit_scope_error_code": bridge["profit_scope_error_code"],
                "status": row_status,
                "settlement_status": settlement_status or None,
                "settlement_locked_net_amount": locked_amount,
                "provisional_inspection_net_amount": provisional_amount,
                "inspected_at": inspected_at_text,
            }
            if diagnostic_summary:
                payload.update(diagnostic_summary)
            payload_rows.append(payload)

        for inspection, order in period_rows:
            _append_payload_row(inspection, order)

        for inspection, order in missing_inspected_at_rows:
            _append_payload_row(inspection, order)

        if missing_inspected_at_total > diagnostic_limit:
            payload_rows.append(
                {
                    "name": "SUBCONTRACT-MISSING-INSPECTED-AT-DIAGNOSTIC",
                    "line_no": "diagnostic-missing-inspected-at",
                    "inspection_no": None,
                    "statement_no": None,
                    "subcontract_order": None,
                    "company": expected_company or None,
                    "item_code": expected_item_code or None,
                    "sales_order": expected_sales_order or None,
                    "sales_order_item": None,
                    "work_order": expected_work_order or None,
                    "production_plan_id": None,
                    "job_card": None,
                    "bridge_source": "diagnostic_aggregate",
                    "profit_scope_status": "unresolved",
                    "profit_scope_error_code": "SUBCONTRACT_INSPECTED_AT_REQUIRED",
                    "status": "unknown",
                    "settlement_status": None,
                    "settlement_locked_net_amount": None,
                    "provisional_inspection_net_amount": None,
                    "inspected_at": None,
                    "diagnostic_total_missing_inspected_at": str(missing_inspected_at_total),
                    "diagnostic_truncated_count": str(missing_inspected_at_total - diagnostic_limit),
                }
            )

        return payload_rows

    @classmethod
    def _subcontract_diagnostic_limit(cls) -> int:
        raw = str(os.getenv(cls._SUBCONTRACT_DIAGNOSTIC_LIMIT_ENV, "") or "").strip()
        if not raw:
            return cls._DEFAULT_SUBCONTRACT_DIAGNOSTIC_LIMIT
        try:
            parsed = int(raw)
        except ValueError:
            return cls._DEFAULT_SUBCONTRACT_DIAGNOSTIC_LIMIT
        if parsed <= 0:
            return cls._DEFAULT_SUBCONTRACT_DIAGNOSTIC_LIMIT
        return parsed

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _list_sales_invoice_headers(self, selector: Any) -> list[dict[str, Any]]:
        filters = [
            ["docstatus", "=", 1],
            ["company", "=", self._normalize_text(selector.company)],
            ["posting_date", ">=", selector.from_date.isoformat()],
            ["posting_date", "<=", selector.to_date.isoformat()],
        ]
        payload = self._request_json(
            method="GET",
            path=(
                "/api/resource/Sales%20Invoice"
                f"?fields={parse.quote(json.dumps(['name','docstatus','status','company','posting_date'], ensure_ascii=False), safe='')}"
                f"&filters={parse.quote(json.dumps(filters, ensure_ascii=False), safe='')}"
                "&limit_page_length=200"
            ),
            allow_404=True,
        )
        if payload is None:
            return []
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise self._source_unavailable("Sales Invoice 列表返回结构异常")
        return [row for row in rows if isinstance(row, dict)]

    def _get_sales_invoice_doc(self, invoice_name: str) -> dict[str, Any]:
        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Sales%20Invoice/{parse.quote(invoice_name, safe='')}"
                f"?fields={parse.quote('[\"name\",\"docstatus\",\"status\",\"company\",\"posting_date\",\"items\",\"sales_order\"]', safe='')}"
            ),
            allow_404=False,
        )
        if payload is None:
            raise self._source_unavailable("Sales Invoice 不存在")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise self._source_unavailable("Sales Invoice 返回结构异常")
        return data

    def _resolve_material_unit_cost(self, *, material_item_code: str, company: str) -> tuple[Decimal | None, str | None]:
        item_price = self._load_item_price(material_item_code=material_item_code, company=company)
        if item_price is not None:
            return item_price, "item_price"
        valuation_rate = self._load_item_valuation_rate(material_item_code=material_item_code)
        if valuation_rate is not None:
            return valuation_rate, "valuation_rate"
        return None, None

    def _load_item_price(self, *, material_item_code: str, company: str) -> Decimal | None:
        if not self.base_url:
            return None
        filters = [
            ["item_code", "=", material_item_code],
            ["buying", "=", 1],
        ]
        if company:
            filters.append(["company", "=", company])
        payload = self._request_json(
            method="GET",
            path=(
                "/api/resource/Item%20Price"
                f"?fields={parse.quote(json.dumps(['price_list_rate','valid_from','name'], ensure_ascii=False), safe='')}"
                f"&filters={parse.quote(json.dumps(filters, ensure_ascii=False), safe='')}"
                "&order_by=valid_from desc&limit_page_length=1"
            ),
            allow_404=True,
        )
        if payload is None:
            return None
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows:
            return None
        first = rows[0]
        if not isinstance(first, dict):
            return None
        return self._to_decimal_or_none(first.get("price_list_rate"))

    def _load_item_valuation_rate(self, *, material_item_code: str) -> Decimal | None:
        if not self.base_url:
            return None
        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Item/{parse.quote(material_item_code, safe='')}"
                f"?fields={parse.quote('[\"name\",\"valuation_rate\"]', safe='')}"
            ),
            allow_404=True,
        )
        if payload is None:
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        return self._to_decimal_or_none(data.get("valuation_rate"))

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        allow_404: bool,
    ) -> dict[str, Any] | None:
        if not self.base_url:
            raise self._source_unavailable("ERPNext 服务未配置")

        headers = self._build_headers()
        req = request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            raise self._source_unavailable(f"ERPNext 请求失败: {exc.code}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise self._source_unavailable("ERPNext 服务不可用") from exc
        except Exception as exc:  # pragma: no cover
            raise self._source_unavailable("ERPNext 调用异常") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise self._source_unavailable("ERPNext 返回非 JSON") from exc
        if not isinstance(payload, dict):
            raise self._source_unavailable("ERPNext 返回结构异常")
        return payload

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.request_obj is not None:
            authorization = self.request_obj.headers.get("Authorization")
            cookie = self.request_obj.headers.get("Cookie")
            if authorization:
                headers["Authorization"] = authorization
            if cookie:
                headers["Cookie"] = cookie
        return headers

    @staticmethod
    def _is_submitted_doc(doc: dict[str, Any]) -> bool:
        try:
            return int(doc.get("docstatus", 0)) == 1
        except Exception:
            return False

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @classmethod
    def _to_decimal_or_none(cls, value: Any) -> Decimal | None:
        text = cls._normalize_text(value)
        if not text:
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    @classmethod
    def _decimal_text(cls, value: Any) -> str:
        decimal_value = cls._to_decimal(value)
        normalized = format(decimal_value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized in {"", "-0"}:
            normalized = "0"
        return normalized

    @staticmethod
    def _source_unavailable(message: str) -> BusinessException:
        return BusinessException(code=STYLE_PROFIT_SOURCE_UNAVAILABLE, message=message)
