"""Pydantic schemas for subcontract module (TASK-002)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class SubcontractCreateRequest(BaseModel):
    """Request payload of creating subcontract order."""

    supplier: str = Field(..., min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    company: Optional[str] = Field(default=None, max_length=140)
    bom_id: int = Field(..., ge=1)
    planned_qty: Decimal = Field(..., gt=0)
    process_name: str = Field(..., min_length=1, max_length=100)


class SubcontractCreateData(BaseModel):
    """Create subcontract order response data."""

    name: str
    company: str


class SubcontractListQuery(BaseModel):
    """List query parameters."""

    supplier: Optional[str] = None
    status: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class SubcontractListItem(BaseModel):
    """Subcontract order list row."""

    id: int
    subcontract_no: str
    supplier: str
    item_code: str
    company: Optional[str] = None
    bom_id: int
    process_name: str
    planned_qty: Decimal
    subcontract_rate: Decimal = Decimal("0")
    issued_qty: Decimal = Decimal("0")
    received_qty: Decimal = Decimal("0")
    inspected_qty: Decimal = Decimal("0")
    rejected_qty: Decimal = Decimal("0")
    accepted_qty: Decimal = Decimal("0")
    gross_amount: Decimal = Decimal("0")
    deduction_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    status: str
    resource_scope_status: str = "ready"
    latest_issue_outbox_id: Optional[int] = None
    latest_issue_sync_status: Optional[str] = None
    latest_issue_stock_entry_name: Optional[str] = None
    latest_issue_idempotency_key: Optional[str] = None
    latest_issue_error_code: Optional[str] = None
    latest_receipt_outbox_id: Optional[int] = None
    latest_receipt_sync_status: Optional[str] = None
    latest_receipt_stock_entry_name: Optional[str] = None
    latest_receipt_idempotency_key: Optional[str] = None
    latest_receipt_error_code: Optional[str] = None
    created_at: datetime


class SubcontractListData(BaseModel):
    """List result payload."""

    items: List[SubcontractListItem]
    total: int
    page: int
    page_size: int


class SubcontractSettlementSummary(BaseModel):
    """Settlement summary for candidates/preview/lock responses."""

    line_count: int
    total_qty: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal


class SubcontractSettlementCandidateItem(BaseModel):
    """Settlement candidate row based on inspection fact."""

    inspection_id: int
    settlement_line_key: Optional[str] = None
    subcontract_id: int
    subcontract_no: str
    company: str
    supplier: str
    item_code: str
    process_name: str
    receipt_batch_no: str
    inspected_at: Optional[datetime] = None
    inspected_by: Optional[str] = None
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    rejected_rate: Decimal
    subcontract_rate: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    settlement_status: str
    statement_id: Optional[int] = None
    statement_no: Optional[str] = None


class SubcontractSettlementCandidatesData(BaseModel):
    """Settlement candidate list payload."""

    items: List[SubcontractSettlementCandidateItem]
    total: int
    page: int
    page_size: int
    summary: SubcontractSettlementSummary


class SubcontractSettlementPreviewRequest(BaseModel):
    """Settlement preview request."""

    inspection_ids: Optional[List[int]] = None
    company: Optional[str] = Field(default=None, max_length=140)
    supplier: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    item_code: Optional[str] = Field(default=None, max_length=140)
    process_name: Optional[str] = Field(default=None, max_length=100)


class SubcontractSettlementPreviewData(BaseModel):
    """Settlement preview response."""

    company: Optional[str] = None
    supplier: Optional[str] = None
    line_count: int
    total_qty: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    items: List[SubcontractSettlementCandidateItem]


class SubcontractSettlementLockRequest(BaseModel):
    """Settlement lock request."""

    statement_id: Optional[int] = Field(default=None, ge=1)
    statement_no: Optional[str] = Field(default=None, max_length=64)
    inspection_ids: List[int] = Field(default_factory=list)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    remark: Optional[str] = Field(default=None, max_length=200)


class SubcontractSettlementLockData(BaseModel):
    """Settlement lock response."""

    operation_id: int
    idempotency_key: str
    idempotent_replay: bool
    locked_count: int
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    locked_items: List[SubcontractSettlementCandidateItem]


class SubcontractSettlementReleaseRequest(BaseModel):
    """Settlement lock release request."""

    statement_id: Optional[int] = Field(default=None, ge=1)
    statement_no: Optional[str] = Field(default=None, max_length=64)
    inspection_ids: List[int] = Field(default_factory=list)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=200)


class SubcontractSettlementReleaseData(BaseModel):
    """Settlement lock release response."""

    operation_id: int
    idempotency_key: str
    idempotent_replay: bool
    released_count: int
    released_items: List[SubcontractSettlementCandidateItem]


class SubcontractReceiptDetailItem(BaseModel):
    """Receipt detail row in subcontract detail response."""

    receipt_batch_no: str
    receipt_warehouse: Optional[str] = None
    item_code: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    batch_no: Optional[str] = None
    uom: Optional[str] = None
    received_qty: Decimal
    sync_status: str
    stock_entry_name: Optional[str] = None
    inspect_status: Optional[str] = None
    idempotency_key: Optional[str] = None
    received_by: Optional[str] = None
    received_at: Optional[datetime] = None


class SubcontractDetailData(BaseModel):
    """Subcontract detail payload."""

    id: int
    subcontract_no: str
    supplier: str
    item_code: str
    company: Optional[str] = None
    bom_id: int
    process_name: str
    planned_qty: Decimal
    subcontract_rate: Decimal = Decimal("0")
    issued_qty: Decimal = Decimal("0")
    received_qty: Decimal = Decimal("0")
    inspected_qty: Decimal = Decimal("0")
    rejected_qty: Decimal = Decimal("0")
    accepted_qty: Decimal = Decimal("0")
    gross_amount: Decimal = Decimal("0")
    deduction_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    status: str
    settlement_status: Optional[str] = None
    resource_scope_status: str
    scope_error_code: Optional[str] = None
    latest_issue_outbox_id: Optional[int] = None
    latest_issue_sync_status: Optional[str] = None
    latest_issue_stock_entry_name: Optional[str] = None
    latest_issue_idempotency_key: Optional[str] = None
    latest_receipt_outbox_id: Optional[int] = None
    latest_receipt_sync_status: Optional[str] = None
    latest_receipt_stock_entry_name: Optional[str] = None
    latest_receipt_idempotency_key: Optional[str] = None
    receipts: List[SubcontractReceiptDetailItem] = Field(default_factory=list)
    inspections: List["SubcontractInspectionDetailItem"] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IssueMaterialItem(BaseModel):
    """Material issue line input."""

    material_item_code: str = Field(..., min_length=1, max_length=140)
    required_qty: Decimal = Field(..., gt=0)
    issued_qty: Decimal = Field(..., gt=0)

    @model_validator(mode="before")
    @classmethod
    def _compat_item_alias(cls, value):
        if isinstance(value, dict) and "material_item_code" not in value:
            item_code = value.get("item_code")
            if isinstance(item_code, str):
                value["material_item_code"] = item_code
        return value


class IssueMaterialRequest(BaseModel):
    """Issue material request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    warehouse: str = Field(..., min_length=1, max_length=140)
    materials: List[IssueMaterialItem] | None = None

    @model_validator(mode="before")
    @classmethod
    def _compat_materials_alias(cls, value):
        if isinstance(value, dict) and "materials" not in value and "items" in value:
            value["materials"] = value.get("items")
        return value


class IssueMaterialData(BaseModel):
    """Issue material response payload."""

    outbox_id: int
    issue_batch_no: str
    sync_status: str
    stock_entry_name: Optional[str] = None


class ReceiveRequest(BaseModel):
    """Receive subcontract goods request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    receipt_warehouse: str = Field(..., min_length=1, max_length=140)
    received_qty: Decimal = Field(..., gt=0)
    item_code: Optional[str] = Field(default=None, max_length=140)
    color: Optional[str] = Field(default=None, max_length=64)
    size: Optional[str] = Field(default=None, max_length=64)
    batch_no: Optional[str] = Field(default=None, max_length=140)
    uom: Optional[str] = Field(default=None, max_length=32)


class ReceiveData(BaseModel):
    """Receive response data."""

    outbox_id: int
    receipt_batch_no: str
    sync_status: str
    stock_entry_name: Optional[str] = None


class InspectRequest(BaseModel):
    """Inspect subcontract goods request."""

    receipt_batch_no: str = Field(..., min_length=1, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    inspected_qty: Decimal = Field(..., gt=0)
    rejected_qty: Decimal = Field(..., ge=0)
    deduction_amount_per_piece: Decimal = Field(default=Decimal("0"), ge=0)
    remark: Optional[str] = Field(default=None, max_length=200)


class InspectData(BaseModel):
    """Inspect response data."""

    inspection_no: str
    receipt_batch_no: str
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    rejected_rate: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    status: str


class SubcontractInspectionDetailItem(BaseModel):
    """Inspection detail row in subcontract detail response."""

    inspection_no: str
    receipt_batch_no: str
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    rejected_rate: Decimal
    subcontract_rate: Decimal
    gross_amount: Decimal
    deduction_amount_per_piece: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    inspected_by: Optional[str] = None
    inspected_at: Optional[datetime] = None
    remark: Optional[str] = None


class SubcontractStockSyncRetryRequest(BaseModel):
    """Manual stock sync retry target selector."""

    outbox_id: int = Field(..., ge=1)
    stock_action: str = Field(..., min_length=1, max_length=32)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=200)


class SubcontractStockSyncRetryData(BaseModel):
    """Manual stock sync retry response."""

    outbox_id: int
    stock_action: str
    status: str
    next_retry_at: Optional[datetime] = None


class SubcontractStockSyncRunOnceData(BaseModel):
    """Internal stock sync worker run result."""

    dry_run: bool
    batch_size: int
    would_process_count: int
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int
