"""Pydantic schemas for sales/inventory read-only APIs (TASK-011B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import Literal
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

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


class DeliveryNoteItem(BaseModel):
    """Read-only delivery note projection."""

    delivery_note: str
    company: str
    sales_order: str
    customer: str
    item_code: str
    warehouse: str
    delivered_qty: Decimal
    posting_date: date
    status: str


class DeliveryNoteListData(BaseModel):
    """Paginated delivery note response."""

    items: list[DeliveryNoteItem]
    total: int
    page: int
    page_size: int


class SalesInvoiceItem(BaseModel):
    """Read-only sales invoice projection."""

    sales_invoice: str
    company: str
    sales_order: str
    customer: str
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    posting_date: date
    status: str


class SalesInvoiceListData(BaseModel):
    """Paginated sales invoice response."""

    items: list[SalesInvoiceItem]
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


class SalesOrderDraftLineItemCreateRequest(BaseModel):
    """Create local sales-order draft line payload."""

    item_code: str
    qty: Decimal
    rate: Decimal | None = None
    uom: str = "Nos"
    warehouse: str | None = None


class SalesOrderDraftCreateRequest(BaseModel):
    """Create local sales-order draft payload."""

    company: str
    customer: str | None = None
    operation: str
    scenario_tag: str
    sales_order_no: str
    source_order_ref: str
    idempotency_key: str
    transaction_date: date | None = None
    delivery_date: date | None = None
    currency: str | None = None
    items: list[SalesOrderDraftLineItemCreateRequest] = Field(min_length=1)


class SalesOrderDraftCancelRequest(BaseModel):
    """Cancel local sales-order draft payload."""

    operation: str
    scenario_tag: str
    idempotency_key: str
    sales_order_no_or_source_order_ref: str
    company: str
    reason: str


class SalesOrderDraftLineItemData(BaseModel):
    """Local sales-order draft line response."""

    id: int
    draft_id: int
    item_code: str
    qty: Decimal
    rate: Decimal | None = None
    amount: Decimal | None = None
    uom: str
    warehouse: str | None = None


class SalesOrderDraftData(BaseModel):
    """Local sales-order draft response."""

    id: int
    sales_order_no: str
    source_order_ref: str
    company: str
    customer: str | None = None
    status: Literal["draft", "pending_outbox", "cancelled"]
    transaction_date: date | None = None
    delivery_date: date | None = None
    currency: str | None = None
    grand_total: Decimal | None = None
    idempotency_key: str
    scenario_tag: str
    created_by: str
    created_at: datetime
    cancelled_by: str | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    items: list[SalesOrderDraftLineItemData]


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


class MaterialTransferItem(BaseModel):
    """Read-only material transfer row."""

    transfer_no: str
    material_code: str
    material_name: str
    source_warehouse: str
    target_warehouse: str
    transfer_qty: Decimal
    inbound_qty: Decimal
    diff_qty: Decimal
    operator: str
    status: str
    transfer_date: date
    warehouse: str | None = None
    company: str | None = None


class MaterialTransferData(BaseModel):
    """Read-only material transfer response."""

    items: list[MaterialTransferItem]
    total: int
    page: int
    page_size: int


class MaterialCountItem(BaseModel):
    """Read-only material count row."""

    count_no: str
    material_code: str
    material_name: str
    warehouse: str
    book_qty: Decimal
    counted_qty: Decimal
    diff_qty: Decimal
    count_status: str
    review_status: str
    count_date: date
    owner: str
    company: str | None = None


class MaterialCountData(BaseModel):
    """Read-only material count response."""

    items: list[MaterialCountItem]
    total: int
    page: int
    page_size: int


class MaterialInventoryReportItem(BaseModel):
    """Read-only material inventory report row."""

    report_no: str
    material_code: str
    material_name: str
    warehouse: str
    business_type: str
    in_qty: Decimal
    out_qty: Decimal
    balance_qty: Decimal
    status: str
    biz_date: date
    owner: str
    ref_no: str
    company: str | None = None


class MaterialInventoryReportData(BaseModel):
    """Read-only material inventory report response."""

    items: list[MaterialInventoryReportItem]
    total: int
    page: int
    page_size: int


class InventoryMaterialRetentionReportItem(BaseModel):
    """Read-only inventory material retention report row."""

    report_no: str
    material_code: str
    material_name: str
    warehouse: str
    retention_level: str
    retention_days: Decimal
    current_qty: Decimal
    stagnant_qty: Decimal
    turnover_days: Decimal
    status: str
    biz_date: date
    owner: str
    ref_no: str
    company: str | None = None


class InventoryMaterialRetentionReportData(BaseModel):
    """Read-only inventory material retention report response."""

    items: list[InventoryMaterialRetentionReportItem]
    total: int
    page: int
    page_size: int


class SemiFinishedInventoryItem(BaseModel):
    """Read-only semi-finished inventory row."""

    record_no: str
    material_code: str
    material_name: str
    warehouse: str
    process_stage: str
    opening_qty: Decimal
    in_qty: Decimal
    out_qty: Decimal
    closing_qty: Decimal
    status: str
    biz_date: date
    owner: str
    ref_no: str
    company: str | None = None


class SemiFinishedInventoryData(BaseModel):
    """Read-only semi-finished inventory response."""

    items: list[SemiFinishedInventoryItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsReservedInboundItem(BaseModel):
    """Read-only finished goods reserved inbound row."""

    reservation_no: str
    item_code: str
    item_name: str
    warehouse: str
    reserve_qty: Decimal
    inbound_qty: Decimal
    pending_inbound_qty: Decimal
    reserve_status: str
    inbound_status: str
    reserved_date: date
    expected_inbound_date: date
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsReservedInboundData(BaseModel):
    """Read-only finished goods reserved inbound response."""

    items: list[FinishedGoodsReservedInboundItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsShippingNoticeItem(BaseModel):
    """Read-only finished goods shipping notice row."""

    notice_no: str
    item_code: str
    item_name: str
    warehouse: str
    planned_ship_qty: Decimal
    shipped_qty: Decimal
    pending_ship_qty: Decimal
    notice_status: str
    logistics_status: str
    notice_date: date
    expected_delivery_date: date
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsShippingNoticeData(BaseModel):
    """Read-only finished goods shipping notice response."""

    items: list[FinishedGoodsShippingNoticeItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsOtherInboundItem(BaseModel):
    """Read-only finished goods other inbound row."""

    inbound_no: str
    item_code: str
    item_name: str
    warehouse: str
    planned_inbound_qty: Decimal
    actual_inbound_qty: Decimal
    pending_inbound_qty: Decimal
    inbound_status: str
    settlement_status: str
    inbound_date: date
    source_doc_no: str
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsOtherInboundData(BaseModel):
    """Read-only finished goods other inbound response."""

    items: list[FinishedGoodsOtherInboundItem]
    total: int
    page: int
    page_size: int


class CustomerReturnApplicationItem(BaseModel):
    """Read-only customer return application row."""

    application_no: str
    item_code: str
    item_name: str
    warehouse: str
    requested_return_qty: Decimal
    confirmed_return_qty: Decimal
    pending_return_qty: Decimal
    application_status: str
    approval_status: str
    application_date: date
    source_doc_no: str
    owner: str
    ref_no: str
    company: str | None = None


class CustomerReturnApplicationData(BaseModel):
    """Read-only customer return application response."""

    items: list[CustomerReturnApplicationItem]
    total: int
    page: int
    page_size: int


class CustomerReturnInboundItem(BaseModel):
    """Read-only customer return inbound row."""

    inbound_no: str
    application_no: str
    item_code: str
    item_name: str
    warehouse: str
    planned_inbound_qty: Decimal
    actual_inbound_qty: Decimal
    pending_inbound_qty: Decimal
    inbound_status: str
    review_status: str
    inbound_date: date
    source_doc_no: str
    owner: str
    ref_no: str
    company: str | None = None


class CustomerReturnInboundData(BaseModel):
    """Read-only customer return inbound response."""

    items: list[CustomerReturnInboundItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsOtherOutboundItem(BaseModel):
    """Read-only finished goods other outbound row."""

    outbound_no: str
    item_code: str
    item_name: str
    warehouse: str
    planned_outbound_qty: Decimal
    actual_outbound_qty: Decimal
    pending_outbound_qty: Decimal
    outbound_status: str
    review_status: str
    outbound_date: date
    source_doc_no: str
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsOtherOutboundData(BaseModel):
    """Read-only finished goods other outbound response."""

    items: list[FinishedGoodsOtherOutboundItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsCountItem(BaseModel):
    """Read-only finished goods count row."""

    count_no: str
    item_code: str
    item_name: str
    warehouse: str
    book_qty: Decimal
    counted_qty: Decimal
    diff_qty: Decimal
    count_status: str
    review_status: str
    count_date: date
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsCountData(BaseModel):
    """Read-only finished goods count response."""

    items: list[FinishedGoodsCountItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsAdjustmentItem(BaseModel):
    """Read-only finished goods adjustment row."""

    adjustment_no: str
    item_code: str
    item_name: str
    warehouse: str
    before_qty: Decimal
    adjusted_qty: Decimal
    diff_qty: Decimal
    adjustment_status: str
    review_status: str
    adjustment_date: date
    adjust_reason: str
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsAdjustmentData(BaseModel):
    """Read-only finished goods adjustment response."""

    items: list[FinishedGoodsAdjustmentItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsTransferItem(BaseModel):
    """Read-only finished goods transfer row."""

    transfer_no: str
    item_code: str
    item_name: str
    source_warehouse: str
    target_warehouse: str
    planned_transfer_qty: Decimal
    actual_transfer_qty: Decimal
    pending_transfer_qty: Decimal
    transfer_status: str
    review_status: str
    transfer_date: date
    transfer_reason: str
    owner: str
    ref_no: str
    company: str | None = None


class FinishedGoodsTransferData(BaseModel):
    """Read-only finished goods transfer response."""

    items: list[FinishedGoodsTransferItem]
    total: int
    page: int
    page_size: int


class FinishedGoodsReportItem(BaseModel):
    """Read-only finished goods in/out report row."""

    image_url: str | None = None
    processing_no: str | None = None
    production_order: str | None = None
    order_no: str
    item_code: str
    item_name: str | None = None
    warehouse: str | None = None
    season: str | None = None
    style_type: str | None = None
    qty: Decimal
    receipt_date: date | None = None
    company: str | None = None
    customer: str | None = None
    week_day_0: str | None = None
    week_day_1: str | None = None
    week_day_2: str | None = None
    week_day_3: str | None = None
    week_day_4: str | None = None
    week_day_5: str | None = None
    week_day_6: str | None = None
    message_title: str | None = None
    sent_at: str | None = None
    message_status: str | None = None
    sender: str | None = None


class FinishedGoodsReportData(BaseModel):
    """Finished goods report response."""

    items: list[FinishedGoodsReportItem]
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


class SupplierItem(BaseModel):
    """Read-only Supplier row."""

    name: str
    supplier_name: str | None = None
    disabled: bool | None = None


class ReferenceDraftCreateRequest(BaseModel):
    """Create local reference draft payload."""

    operation: Literal["create_draft"]
    scenario_tag: str
    company: str
    reference_no: str
    reference_name: str
    idempotency_key: str


class ReferenceDraftDeactivateRequest(BaseModel):
    """Deactivate local reference draft payload."""

    operation: Literal["deactivate_draft"]
    scenario_tag: str
    company: str
    idempotency_key: str
    reason: str


class ReferenceDraftData(BaseModel):
    """Local reference draft response."""

    id: int
    reference_type: Literal["customer", "supplier"]
    reference_no: str
    reference_name: str
    company: str
    status: Literal["active", "inactive"]
    source: Literal["local_draft"] = "local_draft"
    scenario_tag: str
    idempotency_key: str
    created_by: str
    created_at: datetime
    deactivated_by: str | None = None
    deactivated_at: datetime | None = None
    deactivate_reason: str | None = None


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
