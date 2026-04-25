"""Pydantic schemas for warehouse read-only ledger and alerts (TASK-050A)."""

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
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class WarehouseStockLedgerItem(BaseModel):
    """Read-only stock ledger row."""

    company: str
    warehouse: str
    item_code: str
    posting_date: date
    voucher_type: str | None = None
    voucher_no: str | None = None
    actual_qty: Decimal
    qty_after_transaction: Decimal
    valuation_rate: Decimal


class WarehouseStockLedgerData(BaseModel):
    """Paginated stock ledger response."""

    items: list[WarehouseStockLedgerItem]
    total: int
    page: int
    page_size: int


class WarehouseStockSummaryItem(BaseModel):
    """Warehouse stock aggregation row."""

    company: str
    warehouse: str
    item_code: str
    actual_qty: Decimal
    projected_qty: Decimal
    reserved_qty: Decimal
    ordered_qty: Decimal
    reorder_level: Decimal | None = None
    safety_stock: Decimal | None = None
    threshold_missing: bool = False
    is_below_reorder: bool = False
    is_below_safety: bool = False


class WarehouseStockSummaryData(BaseModel):
    """Warehouse stock aggregation response."""

    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    items: list[WarehouseStockSummaryItem]


class WarehouseAlertItem(BaseModel):
    """Warehouse stock alert row."""

    company: str
    warehouse: str
    item_code: str
    alert_type: str
    current_qty: Decimal
    threshold_qty: Decimal | None = None
    gap_qty: Decimal | None = None
    last_movement_date: date | None = None
    severity: str


class WarehouseAlertsData(BaseModel):
    """Warehouse alert list response."""

    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    alert_type: str | None = None
    items: list[WarehouseAlertItem]


class WarehouseBatchItem(BaseModel):
    """Warehouse batch read-only projection row."""

    company: str
    batch_no: str
    item_code: str
    warehouse: str
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    disabled: bool
    qty: Decimal


class WarehouseBatchListData(BaseModel):
    """Warehouse batch list response."""

    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    batch_no: str | None = None
    total: int
    items: list[WarehouseBatchItem]


class WarehouseBatchDetailData(BaseModel):
    """Warehouse batch detail response."""

    batch_no: str
    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    total: int
    items: list[WarehouseBatchItem]


class WarehouseSerialNumberItem(BaseModel):
    """Warehouse serial-number read-only projection row."""

    company: str
    serial_no: str
    item_code: str
    warehouse: str
    batch_no: str | None = None
    status: str
    delivery_document_no: str | None = None
    purchase_document_no: str | None = None


class WarehouseSerialNumberListData(BaseModel):
    """Warehouse serial-number list response."""

    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    batch_no: str | None = None
    serial_no: str | None = None
    total: int
    items: list[WarehouseSerialNumberItem]


class WarehouseSerialNumberDetailData(BaseModel):
    """Warehouse serial-number detail response."""

    serial_no: str
    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    total: int
    items: list[WarehouseSerialNumberItem]


class WarehouseTraceabilityItem(BaseModel):
    """Warehouse traceability ledger row."""

    company: str
    warehouse: str
    item_code: str
    posting_date: date
    voucher_type: str | None = None
    voucher_no: str | None = None
    actual_qty: Decimal
    qty_after_transaction: Decimal
    batch_no: str | None = None
    serial_no: str | None = None


class WarehouseTraceabilityData(BaseModel):
    """Warehouse traceability list response."""

    company: str | None = None
    warehouse: str | None = None
    item_code: str | None = None
    batch_no: str | None = None
    serial_no: str | None = None
    page: int
    page_size: int
    total: int
    items: list[WarehouseTraceabilityItem]


class WarehouseDiagnosticData(BaseModel):
    """Warehouse diagnostic summary response."""

    adapter_configured: bool
    supported_datasets: list[str]
    export_supported_formats: list[str]
    write_boundary: str
    last_checked_at: datetime


class WarehouseStockEntryDraftItemCreateRequest(BaseModel):
    """Stock-entry draft line create payload."""

    item_code: str
    qty: Decimal
    uom: str
    batch_no: str | None = None
    serial_no: str | None = None
    source_warehouse: str | None = None
    target_warehouse: str | None = None


class WarehouseFinishedGoodsInboundCandidateItem(BaseModel):
    """Finished-goods inbound candidate row."""

    source_id: str
    source_label: str
    item_code: str
    qty: Decimal
    uom: str
    disabled: bool
    disabled_reason: str | None = None


class WarehouseFinishedGoodsInboundCandidatesData(BaseModel):
    """Finished-goods inbound candidate response."""

    company: str | None = None
    show_completed_forced: bool = True
    disabled_entry_label: str
    disabled_entry_reason: str
    allocation_contract: str
    items: list[WarehouseFinishedGoodsInboundCandidateItem]


class WarehouseStockEntryDraftCreateRequest(BaseModel):
    """Create warehouse stock-entry draft payload."""

    company: str
    purpose: Literal["Material Issue", "Material Receipt", "Material Transfer"]
    source_type: str
    source_id: str
    finished_goods_source_id: str | None = None
    source_warehouse: str | None = None
    target_warehouse: str | None = None
    items: list[WarehouseStockEntryDraftItemCreateRequest] = Field(min_length=1)
    idempotency_key: str


class WarehouseStockEntryDraftCancelRequest(BaseModel):
    """Cancel warehouse stock-entry draft payload."""

    reason: str


class WarehouseStockEntryDraftItemData(BaseModel):
    """Warehouse stock-entry draft line response."""

    id: int
    draft_id: int
    item_code: str
    qty: Decimal
    uom: str
    batch_no: str | None = None
    serial_no: str | None = None
    source_warehouse: str | None = None
    target_warehouse: str | None = None


class WarehouseStockEntryOutboxStatusData(BaseModel):
    """Warehouse outbox status response."""

    draft_id: int
    event_id: int
    event_type: str
    status: Literal["in_pending", "processing", "succeeded", "failed", "dead", "cancelled"]
    retry_count: int
    external_ref: str | None = None
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class WarehouseStockEntryDraftData(BaseModel):
    """Warehouse stock-entry draft detail response."""

    id: int
    company: str
    purpose: str
    source_type: str
    source_id: str
    source_warehouse: str | None = None
    target_warehouse: str | None = None
    status: Literal["draft", "pending_outbox", "cancelled"]
    created_by: str
    created_at: datetime
    cancelled_by: str | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    idempotency_key: str
    event_key: str
    allocation_mode: Literal["strict_alloc", "zero_placeholder_fallback"] | None = None
    strict_failure_reason: str | None = None
    show_completed_forced: bool | None = None
    items: list[WarehouseStockEntryDraftItemData]
    outbox: WarehouseStockEntryOutboxStatusData | None = None


class WarehouseInventoryCountItemCreateRequest(BaseModel):
    """Inventory-count line create payload."""

    item_code: str
    batch_no: str | None = None
    serial_no: str | None = None
    system_qty: Decimal
    counted_qty: Decimal
    variance_reason: str | None = None


class WarehouseInventoryCountCreateRequest(BaseModel):
    """Create inventory-count draft payload."""

    company: str
    warehouse: str
    count_date: date
    items: list[WarehouseInventoryCountItemCreateRequest] = Field(min_length=1)
    remark: str | None = None


class WarehouseInventoryCountVarianceReviewItemRequest(BaseModel):
    """Variance-review decision per item."""

    item_id: int
    review_status: Literal["accepted", "rejected"]
    variance_reason: str | None = None


class WarehouseInventoryCountVarianceReviewRequest(BaseModel):
    """Variance-review payload."""

    items: list[WarehouseInventoryCountVarianceReviewItemRequest] = Field(min_length=1)


class WarehouseInventoryCountCancelRequest(BaseModel):
    """Cancel inventory-count payload."""

    reason: str


class WarehouseInventoryCountItemData(BaseModel):
    """Inventory-count line response."""

    id: int
    count_id: int
    item_code: str
    batch_no: str | None = None
    serial_no: str | None = None
    system_qty: Decimal
    counted_qty: Decimal
    variance_qty: Decimal
    variance_reason: str | None = None
    review_status: Literal["pending", "accepted", "rejected"]


class WarehouseInventoryCountVarianceStatsData(BaseModel):
    """Aggregated variance stats for one inventory count."""

    total_items: int
    variance_items: int
    pending_review_items: int
    accepted_items: int
    rejected_items: int


class WarehouseInventoryCountData(BaseModel):
    """Inventory-count detail response."""

    id: int
    company: str
    warehouse: str
    status: Literal["draft", "counted", "variance_review", "confirmed", "cancelled"]
    count_no: str
    count_date: date
    created_by: str
    created_at: datetime
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    cancelled_by: str | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    remark: str | None = None
    items: list[WarehouseInventoryCountItemData]
    variance_stats: WarehouseInventoryCountVarianceStatsData


class WarehouseInventoryCountListData(BaseModel):
    """Inventory-count list response."""

    total: int
    items: list[WarehouseInventoryCountData]


class WarehouseStockEntryWorkerRunOnceRequest(BaseModel):
    """Warehouse stock-entry outbox run-once payload."""

    batch_size: int = Field(default=10, ge=1, le=50)
    dry_run: bool = False


class WarehouseStockEntryWorkerRunOnceData(BaseModel):
    """Warehouse stock-entry outbox run-once result."""

    dry_run: bool
    processed_count: int
    skipped_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int
