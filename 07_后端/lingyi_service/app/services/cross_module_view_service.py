"""Cross-module read-only aggregation service (TASK-040C)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.quality import LyQualityInspection
from app.schemas.cross_module_view import CrossModuleDeliveryNoteData
from app.schemas.cross_module_view import CrossModuleQualityInspectionData
from app.schemas.cross_module_view import CrossModuleSalesOrderData
from app.schemas.cross_module_view import CrossModuleSalesOrderTrailData
from app.schemas.cross_module_view import CrossModuleSalesOrderTrailSummary
from app.schemas.cross_module_view import CrossModuleStockEntryData
from app.schemas.cross_module_view import CrossModuleWorkOrderData
from app.schemas.cross_module_view import CrossModuleWorkOrderTrailData
from app.schemas.cross_module_view import CrossModuleWorkOrderTrailSummary
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


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
        return Decimal("0")


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


class CrossModuleViewService:
    """Build read-only cross-module trails from existing facts."""

    def __init__(
        self,
        *,
        session: Session,
        request_obj: Request,
        sales_adapter: ERPNextSalesInventoryAdapter | None = None,
        job_card_adapter: ERPNextJobCardAdapter | None = None,
    ):
        self.session = session
        self.request_obj = request_obj
        self.sales_adapter = sales_adapter or ERPNextSalesInventoryAdapter(request_obj=request_obj)
        self.job_card_adapter = job_card_adapter or ERPNextJobCardAdapter(request_obj=request_obj)

    def get_work_order_trail(
        self,
        *,
        work_order_id: str,
        company: str | None = None,
    ) -> CrossModuleWorkOrderTrailData | None:
        work_order_no = _text(work_order_id)
        if work_order_no is None:
            return None

        work_order = self.job_card_adapter.get_work_order(work_order=work_order_no)
        if work_order is None:
            return None
        work_order_company = _text(work_order.company)
        if company and work_order_company and company != work_order_company:
            return None
        effective_company = company or work_order_company

        stock_entry_names = self._list_stock_entry_names_for_work_order(
            work_order_id=work_order_no,
            company=effective_company,
        )
        stock_entries = self._list_stock_ledger_for_vouchers(
            voucher_type="Stock Entry",
            voucher_nos=stock_entry_names,
            company=effective_company,
        )
        quality_rows = self._list_quality_inspections(
            company=effective_company,
            work_order=work_order_no,
            sales_order=None,
        )

        summary = CrossModuleWorkOrderTrailSummary(
            material_issue_qty=sum((abs(row.actual_qty) for row in stock_entries if row.actual_qty < 0), Decimal("0")),
            output_qty=sum((row.actual_qty for row in stock_entries if row.actual_qty > 0), Decimal("0")),
            accepted_qty=sum((row.accepted_qty for row in quality_rows), Decimal("0")),
            rejected_qty=sum((row.rejected_qty for row in quality_rows), Decimal("0")),
            defect_qty=sum((row.defect_qty for row in quality_rows), Decimal("0")),
            stock_entry_count=len(stock_entries),
            quality_inspection_count=len(quality_rows),
        )
        return CrossModuleWorkOrderTrailData(
            work_order=CrossModuleWorkOrderData(
                work_order_id=work_order_no,
                company=work_order_company,
                production_item=_text(work_order.production_item),
            ),
            stock_entries=stock_entries,
            quality_inspections=quality_rows,
            summary=summary,
        )

    def get_sales_order_trail(
        self,
        *,
        sales_order_id: str,
        company: str | None = None,
    ) -> CrossModuleSalesOrderTrailData | None:
        sales_order_no = _text(sales_order_id)
        if sales_order_no is None:
            return None

        sales_order = self.sales_adapter.get_sales_order(name=sales_order_no)
        sales_order_company = _text(sales_order.get("company"))
        if company and sales_order_company and company != sales_order_company:
            return None
        effective_company = company or sales_order_company

        delivery_note_names = self._list_delivery_note_names_for_sales_order(
            sales_order_id=sales_order_no,
            company=effective_company,
        )
        delivery_notes = self._list_delivery_facts(
            delivery_note_names=delivery_note_names,
            company=effective_company,
        )
        quality_rows = self._list_quality_inspections(
            company=effective_company,
            work_order=None,
            sales_order=sales_order_no,
        )

        items = sales_order.get("items") if isinstance(sales_order.get("items"), list) else []
        summary = CrossModuleSalesOrderTrailSummary(
            ordered_qty=sum((_decimal(row.get("qty")) for row in items if isinstance(row, dict)), Decimal("0")),
            delivered_qty=sum((row.delivered_qty for row in delivery_notes), Decimal("0")),
            quality_inspection_count=len(quality_rows),
            defect_qty=sum((row.defect_qty for row in quality_rows), Decimal("0")),
        )
        return CrossModuleSalesOrderTrailData(
            sales_order=CrossModuleSalesOrderData(
                sales_order_id=sales_order_no,
                company=sales_order_company,
                customer=_text(sales_order.get("customer")),
                transaction_date=_to_date(sales_order.get("transaction_date")),
                delivery_date=_to_date(sales_order.get("delivery_date")),
                status=_text(sales_order.get("status")),
            ),
            delivery_notes=delivery_notes,
            quality_inspections=quality_rows,
            summary=summary,
        )

    def _list_stock_entry_names_for_work_order(self, *, work_order_id: str, company: str | None) -> list[str]:
        filters: list[list[Any]] = [["docstatus", "=", 1], ["work_order", "=", work_order_id]]
        if company:
            filters.append(["company", "=", company])
        rows = self.sales_adapter._list_resource(
            doctype="Stock Entry",
            fields=["name"],
            filters=filters,
            page=1,
            page_size=500,
            order_by="name desc",
        )
        names: list[str] = []
        for row in rows:
            name = _text(row.get("name"))
            if name and name not in names:
                names.append(name)
        return names

    def _list_delivery_note_names_for_sales_order(self, *, sales_order_id: str, company: str | None) -> list[str]:
        filters: list[list[Any]] = [["docstatus", "=", 1], ["items", "against_sales_order", "=", sales_order_id]]
        if company:
            filters.append(["company", "=", company])
        rows = self.sales_adapter._list_resource(
            doctype="Delivery Note",
            fields=["name"],
            filters=filters,
            page=1,
            page_size=500,
            order_by="name desc",
        )
        names: list[str] = []
        for row in rows:
            name = _text(row.get("name"))
            if name and name not in names:
                names.append(name)
        return names

    def _list_stock_ledger_for_vouchers(
        self,
        *,
        voucher_type: str,
        voucher_nos: list[str],
        company: str | None,
    ) -> list[CrossModuleStockEntryData]:
        if not voucher_nos:
            return []
        filters: list[list[Any]] = [["voucher_type", "=", voucher_type], ["voucher_no", "in", voucher_nos]]
        if company:
            filters.append(["company", "=", company])
        rows = self.sales_adapter._list_resource(
            doctype="Stock Ledger Entry",
            fields=self.sales_adapter.SLE_FIELDS,
            filters=filters,
            page=1,
            page_size=max(500, len(voucher_nos) * 20),
            order_by="posting_date desc, posting_time desc, name desc",
        )
        result: list[CrossModuleStockEntryData] = []
        for row in rows:
            normalized = self.sales_adapter._normalize_sle_row(row)
            if normalized is None:
                continue
            voucher_no = _text(normalized.get("voucher_no"))
            if voucher_no is None:
                continue
            result.append(
                CrossModuleStockEntryData(
                    voucher_no=voucher_no,
                    voucher_type=_text(normalized.get("voucher_type")),
                    company=_text(normalized.get("company")),
                    item_code=_text(normalized.get("item_code")),
                    warehouse=_text(normalized.get("warehouse")),
                    posting_date=_to_date(normalized.get("posting_date")),
                    posting_time=_text(normalized.get("posting_time")),
                    actual_qty=_decimal(normalized.get("actual_qty")),
                )
            )
        return result

    def _list_delivery_facts(
        self,
        *,
        delivery_note_names: list[str],
        company: str | None,
    ) -> list[CrossModuleDeliveryNoteData]:
        stock_rows = self._list_stock_ledger_for_vouchers(
            voucher_type="Delivery Note",
            voucher_nos=delivery_note_names,
            company=company,
        )
        return [
            CrossModuleDeliveryNoteData(
                delivery_note=row.voucher_no,
                company=row.company,
                item_code=row.item_code,
                warehouse=row.warehouse,
                posting_date=row.posting_date,
                posting_time=row.posting_time,
                delivered_qty=abs(row.actual_qty),
            )
            for row in stock_rows
        ]

    def _list_quality_inspections(
        self,
        *,
        company: str | None,
        work_order: str | None,
        sales_order: str | None,
    ) -> list[CrossModuleQualityInspectionData]:
        query = self.session.query(LyQualityInspection).filter(LyQualityInspection.status != "cancelled")
        if company:
            query = query.filter(LyQualityInspection.company == company)
        if work_order:
            query = query.filter(LyQualityInspection.work_order == work_order)
        if sales_order:
            query = query.filter(LyQualityInspection.sales_order == sales_order)
        rows = (
            query.order_by(LyQualityInspection.inspection_date.desc(), LyQualityInspection.id.desc())
            .limit(500)
            .all()
        )
        return [
            CrossModuleQualityInspectionData(
                inspection_id=int(row.id),
                inspection_no=str(row.inspection_no),
                company=str(row.company),
                source_type=str(row.source_type),
                item_code=str(row.item_code),
                warehouse=_text(row.warehouse),
                work_order=_text(row.work_order),
                sales_order=_text(row.sales_order),
                inspection_date=row.inspection_date,
                accepted_qty=_decimal(row.accepted_qty),
                rejected_qty=_decimal(row.rejected_qty),
                defect_qty=_decimal(row.defect_qty),
                status=str(row.status),
                result=str(row.result),
            )
            for row in rows
        ]
