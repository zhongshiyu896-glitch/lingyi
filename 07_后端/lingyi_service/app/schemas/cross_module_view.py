"""Schemas for cross-module read-only trail views (TASK-040C)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API envelope."""

    code: str
    message: str
    data: T


class CrossModuleWorkOrderData(BaseModel):
    """Work Order basic snapshot."""

    work_order_id: str
    company: str | None = None
    production_item: str | None = None


class CrossModuleStockEntryData(BaseModel):
    """Stock movement fact associated to a trail."""

    voucher_no: str
    voucher_type: str | None = None
    company: str | None = None
    item_code: str | None = None
    warehouse: str | None = None
    posting_date: date | None = None
    posting_time: str | None = None
    actual_qty: Decimal


class CrossModuleQualityInspectionData(BaseModel):
    """Read-only quality inspection fact row for cross-module trail."""

    inspection_id: int
    inspection_no: str
    company: str
    source_type: str
    item_code: str
    warehouse: str | None = None
    work_order: str | None = None
    sales_order: str | None = None
    inspection_date: date
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    status: str
    result: str


class CrossModuleWorkOrderTrailSummary(BaseModel):
    """Summary for work-order based trail."""

    material_issue_qty: Decimal
    output_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    stock_entry_count: int
    quality_inspection_count: int


class CrossModuleWorkOrderTrailData(BaseModel):
    """Work Order -> stock -> quality trail payload."""

    work_order: CrossModuleWorkOrderData
    stock_entries: list[CrossModuleStockEntryData]
    quality_inspections: list[CrossModuleQualityInspectionData]
    summary: CrossModuleWorkOrderTrailSummary


class CrossModuleSalesOrderData(BaseModel):
    """Sales Order basic snapshot."""

    sales_order_id: str
    company: str | None = None
    customer: str | None = None
    transaction_date: date | None = None
    delivery_date: date | None = None
    status: str | None = None


class CrossModuleDeliveryNoteData(BaseModel):
    """Delivery fact row associated to a sales-order trail."""

    delivery_note: str
    company: str | None = None
    item_code: str | None = None
    warehouse: str | None = None
    posting_date: date | None = None
    posting_time: str | None = None
    delivered_qty: Decimal


class CrossModuleSalesOrderTrailSummary(BaseModel):
    """Summary for sales-order based trail."""

    ordered_qty: Decimal
    delivered_qty: Decimal
    quality_inspection_count: int
    defect_qty: Decimal


class CrossModuleSalesOrderTrailData(BaseModel):
    """Sales Order -> delivery/inventory -> quality trail payload."""

    sales_order: CrossModuleSalesOrderData
    delivery_notes: list[CrossModuleDeliveryNoteData]
    quality_inspections: list[CrossModuleQualityInspectionData]
    summary: CrossModuleSalesOrderTrailSummary
