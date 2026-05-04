"""Pydantic schemas for production planning module (TASK-004A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class ProductionPlanCreateRequest(BaseModel):
    """Create production plan request."""

    sales_order: str = Field(..., min_length=1, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    bom_id: Optional[int] = Field(default=None, ge=1)
    planned_qty: Decimal = Field(..., gt=0)
    planned_start_date: Optional[date] = None
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    company: Optional[str] = Field(default=None, max_length=140)


class ProductionPlanCreateData(BaseModel):
    """Create production plan response."""

    plan_id: int
    plan_no: str
    status: str
    company: str


class ProductionPlanQuery(BaseModel):
    """Production plan list query."""

    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = None
    company: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionWorkOrderOutboxSummary(BaseModel):
    """Latest work order outbox summary for list/detail display."""

    outbox_id: int
    status: str
    erpnext_work_order: Optional[str] = None
    error_code: Optional[str] = None


class ProductionPlanListItem(BaseModel):
    """Production plan list row."""

    id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    bom_id: int
    bom_version: Optional[str] = None
    planned_qty: Decimal
    planned_start_date: Optional[date] = None
    status: str
    latest_work_order_outbox: Optional[ProductionWorkOrderOutboxSummary] = None
    created_at: datetime


class ProductionPlanListData(BaseModel):
    """Production plan list result."""

    items: List[ProductionPlanListItem]
    total: int
    page: int
    page_size: int


class ProductionMaterialCostQuery(BaseModel):
    """Production material-cost list query."""

    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    material_item_code: Optional[str] = Field(default=None, max_length=140)
    supplier: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionMaterialCostListItem(BaseModel):
    """Production material-cost detail row."""

    plan_id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    item_code: str
    material_item_code: str
    supplier: Optional[str] = None
    qty_per_piece: Decimal
    loss_rate: Decimal
    required_qty: Decimal
    estimated_unit_price: Decimal
    estimated_material_cost: Decimal
    currency: str = "CNY"
    status: str
    planned_start_date: Optional[date] = None
    checked_at: Optional[datetime] = None


class ProductionMaterialCostListData(BaseModel):
    """Production material-cost detail list result."""

    items: List[ProductionMaterialCostListItem]
    total: int
    page: int
    page_size: int


class ProductionSalesForecastQuery(BaseModel):
    """Production sales-forecast list query."""

    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionSalesForecastListItem(BaseModel):
    """Production sales-forecast detail row."""

    plan_id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    forecast_qty: Decimal
    forecast_unit_price: Decimal
    forecast_amount: Decimal
    currency: str = "CNY"
    delivery_date: Optional[date] = None
    status: str
    checked_at: Optional[datetime] = None


class ProductionSalesForecastListData(BaseModel):
    """Production sales-forecast detail list result."""

    items: List[ProductionSalesForecastListItem]
    total: int
    page: int
    page_size: int


class ProductionQuoteQuery(BaseModel):
    """Production quote list query."""

    quote_no: Optional[str] = Field(default=None, max_length=140)
    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionQuoteListItem(BaseModel):
    """Production quote list row."""

    plan_id: int
    quote_no: str
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    quote_qty: Decimal
    quote_unit_price: Decimal
    quote_amount: Decimal
    currency: str = "CNY"
    quoted_at: Optional[datetime] = None
    delivery_date: Optional[date] = None
    status: str


class ProductionQuoteListData(BaseModel):
    """Production quote list result."""

    items: List[ProductionQuoteListItem]
    total: int
    page: int
    page_size: int


class ProductionFollowupTemplateQuery(BaseModel):
    """Production follow-up template list query."""

    template_no: Optional[str] = Field(default=None, max_length=140)
    template_name: Optional[str] = Field(default=None, max_length=140)
    template_type: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=40)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionFollowupTemplateListItem(BaseModel):
    """Production follow-up template row."""

    template_id: int
    template_no: str
    template_name: str
    template_type: str
    trigger_node: str
    followup_role: str
    followup_frequency: str
    sla_hours: int
    item_code: str
    company: str
    status: str
    updated_at: datetime


class ProductionFollowupTemplateListData(BaseModel):
    """Production follow-up template list result."""

    items: List[ProductionFollowupTemplateListItem]
    total: int
    page: int
    page_size: int


class ProductionOrderIOQuantityQuery(BaseModel):
    """Production order in/out quantity list query."""

    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    io_status: Optional[str] = Field(default=None, max_length=40)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionOrderIOQuantityListItem(BaseModel):
    """Production order in/out quantity row."""

    plan_id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    ordered_qty: Decimal
    inbound_qty: Decimal
    outbound_qty: Decimal
    pending_inbound_qty: Decimal
    pending_outbound_qty: Decimal
    inbound_progress: Decimal
    outbound_progress: Decimal
    io_status: str
    status: str
    planned_start_date: Optional[date] = None
    updated_at: Optional[datetime] = None


class ProductionOrderIOQuantityListData(BaseModel):
    """Production order in/out quantity list result."""

    items: List[ProductionOrderIOQuantityListItem]
    total: int
    page: int
    page_size: int


class ProductionSalespersonPerformanceQuery(BaseModel):
    """Production salesperson performance list query."""

    salesperson: Optional[str] = Field(default=None, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    status: Optional[str] = Field(default=None, max_length=40)
    performance_status: Optional[str] = Field(default=None, max_length=40)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ProductionSalespersonPerformanceListItem(BaseModel):
    """Production salesperson performance row."""

    plan_id: int
    plan_no: str
    company: str
    salesperson: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    ordered_qty: Decimal
    completed_qty: Decimal
    completion_rate: Decimal
    settled_amount: Decimal
    pending_amount: Decimal
    currency: str = "CNY"
    performance_status: str
    status: str
    updated_at: Optional[datetime] = None


class ProductionSalespersonPerformanceListData(BaseModel):
    """Production salesperson performance list result."""

    items: List[ProductionSalespersonPerformanceListItem]
    total: int
    page: int
    page_size: int


class ProductionPlanMaterialSnapshotItem(BaseModel):
    """Material check snapshot row."""

    bom_item_id: Optional[int] = None
    material_item_code: str
    warehouse: Optional[str] = None
    qty_per_piece: Decimal
    loss_rate: Decimal
    required_qty: Decimal
    available_qty: Decimal
    shortage_qty: Decimal
    checked_at: Optional[datetime] = None


class ProductionJobCardLinkItem(BaseModel):
    """Local Job Card mapping row."""

    job_card: str
    operation: Optional[str] = None
    operation_sequence: Optional[int] = None
    company: Optional[str] = None
    item_code: Optional[str] = None
    expected_qty: Decimal
    completed_qty: Decimal
    erpnext_status: Optional[str] = None
    synced_at: Optional[datetime] = None


class ProductionPlanDetailData(BaseModel):
    """Production plan detail result."""

    id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    bom_id: int
    bom_version: Optional[str] = None
    planned_qty: Decimal
    planned_start_date: Optional[date] = None
    status: str
    work_order: Optional[str] = None
    erpnext_docstatus: Optional[int] = None
    erpnext_status: Optional[str] = None
    sync_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    latest_work_order_outbox: Optional[ProductionWorkOrderOutboxSummary] = None
    write_entry_frozen: bool = True
    write_entry_frozen_reason: Optional[str] = None
    material_snapshots: List[ProductionPlanMaterialSnapshotItem] = Field(default_factory=list)
    job_cards: List[ProductionJobCardLinkItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProductionMaterialCheckData(BaseModel):
    """Material check result payload."""

    plan_id: int
    snapshot_count: int
    items: List[ProductionPlanMaterialSnapshotItem]


class ProductionMaterialCheckRequest(BaseModel):
    """Material-check request payload."""

    warehouse: Optional[str] = Field(default=None, max_length=140)


class ProductionCreateWorkOrderRequest(BaseModel):
    """Create-work-order request payload."""

    fg_warehouse: Optional[str] = Field(default=None, max_length=140)
    wip_warehouse: Optional[str] = Field(default=None, max_length=140)
    start_date: Optional[date] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


class ProductionCreateWorkOrderData(BaseModel):
    """Create work-order outbox response."""

    plan_id: int
    outbox_id: int
    event_key: str
    sync_status: str
    work_order: Optional[str] = None


class ProductionSyncJobCardsData(BaseModel):
    """Manual Job Card sync result."""

    work_order: str
    plan_id: int
    synced_count: int
    items: List[ProductionJobCardLinkItem]


class ProductionWorkerRunOnceRequest(BaseModel):
    """Internal worker run-once request."""

    batch_size: int = Field(default=20, ge=1, le=200)
    dry_run: bool = False


class ProductionWorkerRunOnceData(BaseModel):
    """Internal worker run-once response."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int
