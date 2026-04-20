"""Pydantic schemas for sales/inventory read-only APIs (TASK-011B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
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


class SalesInventoryListData(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int


class SalesOrderListItem(BaseModel):
    """Read-only Sales Order list row."""

    name: str
    company: str
    customer: str | None = None
    transaction_date: date | None = None
    delivery_date: date | None = None
    status: str | None = None
    docstatus: int
    grand_total: Decimal | None = None
    currency: str | None = None


class SalesOrderLineItem(BaseModel):
    """Read-only Sales Order item row."""

    name: str | None = None
    item_code: str
    item_name: str | None = None
    qty: Decimal
    delivered_qty: Decimal | None = None
    rate: Decimal | None = None
    amount: Decimal | None = None
    warehouse: str | None = None
    delivery_date: date | None = None


class SalesOrderDetailData(BaseModel):
    """Read-only Sales Order detail payload."""

    name: str
    company: str
    customer: str | None = None
    transaction_date: date | None = None
    delivery_date: date | None = None
    status: str | None = None
    docstatus: int
    grand_total: Decimal | None = None
    currency: str | None = None
    items: list[SalesOrderLineItem]


class StockSummaryItem(BaseModel):
    """Current stock summary by warehouse."""

    company: str
    item_code: str
    warehouse: str
    balance_qty: Decimal
    latest_posting_date: date | None = None
    latest_posting_time: str | None = None


class StockSummaryData(BaseModel):
    """Stock summary response."""

    item_code: str
    company: str | None = None
    warehouse: str | None = None
    items: list[StockSummaryItem]
    dropped_count: int = 0


class StockLedgerItem(BaseModel):
    """Read-only Stock Ledger Entry row."""

    name: str | None = None
    company: str
    item_code: str
    warehouse: str
    posting_date: date
    posting_time: str | None = None
    actual_qty: Decimal
    qty_after_transaction: Decimal
    voucher_type: str | None = None
    voucher_no: str | None = None


class StockLedgerData(BaseModel):
    """Stock ledger response."""

    items: list[StockLedgerItem]
    total: int
    page: int
    page_size: int
    dropped_count: int = 0


class WarehouseItem(BaseModel):
    """Read-only Warehouse row."""

    name: str
    company: str | None = None
    warehouse_name: str | None = None
    disabled: bool | None = None


class CustomerItem(BaseModel):
    """Read-only Customer row."""

    name: str
    customer_name: str | None = None
    disabled: bool | None = None


class DiagnosticData(BaseModel):
    """Read-only diagnostic payload."""

    source: str = "erpnext"
    status: str
    checked_at: datetime


class InventoryAggregationItem(BaseModel):
    """Inventory aggregation by item + warehouse."""

    item_code: str
    warehouse: str
    actual_qty: Decimal
    ordered_qty: Decimal
    indented_qty: Decimal
    safety_stock: Decimal
    reorder_level: Decimal
    is_below_safety: bool
    is_below_reorder: bool


class InventoryAggregationData(BaseModel):
    """Inventory aggregation response."""

    company: str | None = None
    item_code: str | None = None
    warehouse: str | None = None
    items: list[InventoryAggregationItem]


class SalesOrderFulfillmentItem(BaseModel):
    """Sales order fulfillment row."""

    company: str | None = None
    sales_order: str
    item_code: str
    warehouse: str | None = None
    ordered_qty: Decimal
    actual_qty: Decimal
    fulfillment_rate: Decimal


class SalesOrderFulfillmentData(BaseModel):
    """Sales order fulfillment response."""

    company: str | None = None
    items: list[SalesOrderFulfillmentItem]
