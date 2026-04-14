"""Pydantic schemas for style profit source mapping skeleton (TASK-005C)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import TypeVar
from typing import Any

from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API envelope."""

    code: str
    message: str
    data: T


class StyleProfitRevenueSourceDTO(BaseModel):
    """Resolved revenue source row."""

    source_type: str
    source_name: str
    source_line_no: str
    item_code: str
    qty: Decimal
    unit_rate: Decimal
    amount: Decimal
    revenue_status: str
    source_status: str = "unknown"


class StyleProfitMaterialSourceDTO(BaseModel):
    """Resolved material cost source row."""

    source_system: str
    source_doctype: str
    source_status: str = "unknown"
    source_name: str
    source_line_no: str
    company: str
    style_item_code: str
    source_item_code: str | None = None
    sales_order: str | None = None
    production_plan_id: int | None = None
    work_order: str | None = None
    job_card: str | None = None
    detail_id: int | None = None
    snapshot_id: int | None = None
    source_type: str | None = None
    warehouse: str | None = None
    posting_date: date | None = None
    qty: Decimal | None = None
    unit_rate: Decimal | None = None
    currency: str | None = None
    stock_value_difference: Decimal
    amount_basis: str | None = None
    amount: Decimal
    include_in_profit: bool = False
    mapping_status: str = "unresolved"
    unresolved_reason: str | None = None
    raw_ref: dict[str, Any] = Field(default_factory=dict)


class StyleProfitMaterialSourceResolutionDTO(BaseModel):
    """Material source resolution payload for later snapshot computation."""

    actual_material_cost: Decimal
    mapped_sources: list[StyleProfitMaterialSourceDTO] = Field(default_factory=list)
    unresolved_sources: list[StyleProfitMaterialSourceDTO] = Field(default_factory=list)
    excluded_sources: list[StyleProfitMaterialSourceDTO] = Field(default_factory=list)
    reference_sources: list[StyleProfitMaterialSourceDTO] = Field(default_factory=list)


class StyleProfitSnapshotCreateRequest(BaseModel):
    """Service-level request for immutable style profit snapshot creation."""

    company: str
    item_code: str
    sales_order: str | None = None
    from_date: date
    to_date: date
    revenue_mode: str = "actual_first"
    include_provisional_subcontract: bool = False
    formula_version: str = "STYLE_PROFIT_V1"
    idempotency_key: str

    sales_invoice_rows: list[dict[str, Any]] = Field(default_factory=list)
    sales_order_rows: list[dict[str, Any]] = Field(default_factory=list)
    bom_material_rows: list[dict[str, Any]] = Field(default_factory=list)
    bom_operation_rows: list[dict[str, Any]] = Field(default_factory=list)
    stock_ledger_rows: list[dict[str, Any]] = Field(default_factory=list)
    purchase_receipt_rows: list[dict[str, Any]] = Field(default_factory=list)
    workshop_ticket_rows: list[dict[str, Any]] = Field(default_factory=list)
    subcontract_rows: list[dict[str, Any]] = Field(default_factory=list)
    allowed_material_item_codes: list[str] = Field(default_factory=list)
    work_order: str | None = None


class StyleProfitSnapshotResult(BaseModel):
    """Created or replayed style profit snapshot summary."""

    snapshot_id: int
    snapshot_no: str
    company: str
    item_code: str
    sales_order: str | None
    revenue_status: str
    revenue_amount: Decimal
    actual_total_cost: Decimal
    standard_total_cost: Decimal
    profit_amount: Decimal
    profit_rate: Decimal | None
    snapshot_status: str
    unresolved_count: int
    idempotency_key: str
    request_hash: str
    idempotent_replay: bool = False


class StyleProfitSnapshotSelectorRequest(BaseModel):
    """Client selector for API snapshot creation."""

    company: str = Field(..., min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    sales_order: str = Field(..., min_length=1, max_length=140)
    from_date: date
    to_date: date
    revenue_mode: str = Field(default="actual_first", min_length=1, max_length=32)
    include_provisional_subcontract: bool = False
    formula_version: str = Field(default="STYLE_PROFIT_V1", min_length=1, max_length=32)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    work_order: str | None = Field(default=None, max_length=140)


class StyleProfitSnapshotListItem(BaseModel):
    """Snapshot list row."""

    id: int
    snapshot_no: str
    company: str
    item_code: str
    sales_order: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    revenue_status: str
    revenue_amount: Decimal
    actual_total_cost: Decimal
    profit_amount: Decimal
    profit_rate: Decimal | None
    snapshot_status: str
    formula_version: str
    unresolved_count: int
    created_at: datetime


class StyleProfitSnapshotListData(BaseModel):
    """Snapshot list payload."""

    items: list[StyleProfitSnapshotListItem]
    total: int
    page: int
    page_size: int


class StyleProfitDetailItem(BaseModel):
    """Snapshot detail line payload."""

    id: int
    line_no: int
    cost_type: str
    source_type: str
    source_name: str
    item_code: str | None = None
    qty: Decimal | None = None
    unit_rate: Decimal | None = None
    amount: Decimal
    formula_code: str | None = None
    is_unresolved: bool
    unresolved_reason: str | None = None
    raw_ref: dict[str, Any] | None = None
    created_at: datetime


class StyleProfitSourceMapItem(BaseModel):
    """Snapshot source map payload."""

    id: int
    detail_id: int | None = None
    company: str
    sales_order: str | None = None
    style_item_code: str
    source_item_code: str | None = None
    source_system: str
    source_doctype: str
    source_status: str
    source_name: str
    source_line_no: str
    qty: Decimal | None = None
    unit_rate: Decimal | None = None
    amount: Decimal
    currency: str | None = None
    warehouse: str | None = None
    posting_date: date | None = None
    include_in_profit: bool
    mapping_status: str
    unresolved_reason: str | None = None
    raw_ref: dict[str, Any] | None = None
    created_at: datetime


class StyleProfitSnapshotDetailData(BaseModel):
    """Snapshot detail API payload."""

    snapshot: StyleProfitSnapshotResult
    details: list[StyleProfitDetailItem]
    source_maps: list[StyleProfitSourceMapItem]
