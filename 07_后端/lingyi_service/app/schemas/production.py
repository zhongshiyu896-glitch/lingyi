"""Pydantic schemas for production planning module (TASK-004A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

from app.schemas.sales_inventory import SalesOrderDraftData

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
    scenario_tag: Optional[str] = Field(default=None, max_length=40)
    operation: Optional[str] = Field(default=None, max_length=40)
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
    page_size: int = Field(default=20, ge=1, le=100)


class ProductionWorkOrderOutboxSummary(BaseModel):
    """Latest work order outbox summary for list/detail display."""

    outbox_id: int
    status: str
    erpnext_work_order: Optional[str] = None
    error_code: Optional[str] = None


class ProductionTrackingSummary(BaseModel):
    """Production tracking summary derived for list display."""

    current_node_key: Optional[str] = None
    current_node_name: Optional[str] = None
    current_node_status: str = "pending"
    current_node_progress: int = 0
    open_exception_count: int = 0
    blocker_count: int = 0
    latest_tracking_at: Optional[datetime] = None


class ProductionPlanListItem(BaseModel):
    """Production plan list row."""

    id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    color: Optional[str] = None
    size: Optional[str] = None
    sales_order_item_qty: Optional[Decimal] = None
    bom_id: int
    bom_version: Optional[str] = None
    planned_qty: Decimal
    planned_start_date: Optional[date] = None
    status: str
    material_ready: bool = False
    required_qty_total: Decimal = Decimal("0")
    available_qty_total: Decimal = Decimal("0")
    shortage_qty_total: Decimal = Decimal("0")
    pending_requirement_count: int = 0
    purchase_status: str = "not_calculated"
    latest_work_order_outbox: Optional[ProductionWorkOrderOutboxSummary] = None
    tracking_summary: ProductionTrackingSummary = Field(default_factory=ProductionTrackingSummary)
    created_at: datetime


class ProductionPlanListData(BaseModel):
    """Production plan list result."""

    items: List[ProductionPlanListItem]
    total: int
    page: int
    page_size: int


class ProductionTrackingExceptionItem(BaseModel):
    """Production tracking exception row."""

    id: int
    exception_no: str
    plan_id: int
    company: str
    plan_no: str
    sales_order: str
    sales_order_item: str
    item_code: str
    exception_type: str
    severity: str
    status: str
    description: str
    owner: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductionTrackingExceptionCreateRequest(BaseModel):
    """Register a production tracking exception from existing order tracking page."""

    company: Optional[str] = Field(default=None, max_length=140)
    exception_type: Optional[str] = Field(default="progress", max_length=64)
    severity: Optional[str] = Field(default="medium", max_length=32)
    status: Optional[str] = Field(default="open", max_length=32)
    description: str = Field(..., min_length=1, max_length=1000)
    owner: Optional[str] = Field(default=None, max_length=140)
    operation: Optional[str] = Field(default=None, max_length=40)
    scenario_tag: Optional[str] = Field(default=None, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    plan_id: Optional[int] = Field(default=None, ge=1)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionTrackingReconcileQuery(BaseModel):
    """样板单到大货订单对账列表查询。"""

    company: Optional[str] = Field(default=None, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    diff_status: Optional[str] = Field(default=None, max_length=32)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProductionTrackingReconcileListItem(BaseModel):
    """样板单到大货订单对账列表行。"""

    id: int
    reconcile_no: str
    batch_no: str
    company: str
    sample_order_id: int
    sample_no: str
    style_no: str
    style_name: str
    image_tone: str
    customer: str
    sample_type: str
    sealed_date: Optional[date] = None
    sales_order: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_item_id: Optional[int] = None
    sample_qty: Decimal
    order_qty: Decimal
    sample_price: Decimal
    unit_price: Decimal
    diff_status: str
    remark: str
    owner: str
    created_by: str
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProductionTrackingReconcileListData(BaseModel):
    """样板单到大货订单对账分页结果。"""

    items: List[ProductionTrackingReconcileListItem]
    total: int
    page: int
    page_size: int


class ProductionTrackingReconcileGenerateRequest(BaseModel):
    """按筛选条件生成样板单到大货订单对账快照。"""

    company: str = Field(..., min_length=1, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    diff_status: Optional[str] = Field(default=None, max_length=32)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    operation: Optional[str] = Field(default=None, max_length=40)
    scenario_tag: Optional[str] = Field(default=None, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionTrackingReconcileGenerateData(BaseModel):
    """生成样板单到大货订单对账响应。"""

    batch_no: str
    company: str
    created_count: int
    updated_count: int
    matched_count: int
    unmatched_count: int
    items: List[ProductionTrackingReconcileListItem]


class ProductionWorkOrderQuery(BaseModel):
    """Production work-order list query."""

    sales_order: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    turnover_no: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    sync_status: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProductionWorkOrderListItem(BaseModel):
    """Production work-order list row."""

    plan_id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    bom_id: Optional[int] = None
    bom_version: Optional[str] = None
    work_order: str
    planned_qty: Decimal
    produced_qty: Decimal = Decimal("0")
    status: str
    erpnext_docstatus: Optional[int] = None
    erpnext_status: Optional[str] = None
    sync_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductionWorkOrderListData(BaseModel):
    """Production work-order list result."""

    items: List[ProductionWorkOrderListItem]
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


class ProductionQuoteCreateRequest(BaseModel):
    """Create a saved production quote from an existing production plan."""

    plan_id: int = Field(..., ge=1)
    company: Optional[str] = Field(default=None, max_length=140)
    quote_no: Optional[str] = Field(default=None, max_length=140)
    quote_qty: Optional[Decimal] = Field(default=None, gt=0)
    labor_cost: Decimal = Field(default=Decimal("0"), ge=0)
    management_fee: Decimal = Field(default=Decimal("0"), ge=0)
    valid_until: Optional[date] = None
    status: Optional[str] = Field(default="draft", max_length=32)
    remark: Optional[str] = Field(default=None, max_length=500)
    operation: Optional[str] = Field(default="create", max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionQuoteConvertRequest(BaseModel):
    """Convert a saved production quote into a FastAPI-native sales-order draft."""

    company: Optional[str] = Field(default=None, max_length=140)
    sales_order_no: Optional[str] = Field(default=None, max_length=140)
    transaction_date: Optional[date] = None
    delivery_date: Optional[date] = None
    operation: Optional[str] = Field(default="convert", max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionQuoteCopyRequest(BaseModel):
    """Copy a saved production quote into an independent draft snapshot."""

    company: Optional[str] = Field(default=None, max_length=140)
    quote_no: Optional[str] = Field(default=None, max_length=140)
    valid_until: Optional[date] = None
    status: Optional[str] = Field(default="draft", max_length=32)
    remark: Optional[str] = Field(default=None, max_length=500)
    operation: Optional[str] = Field(default="copy", max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionQuoteVoidRequest(BaseModel):
    """Void a saved production quote that has not been converted."""

    company: Optional[str] = Field(default=None, max_length=140)
    reason: Optional[str] = Field(default=None, max_length=500)
    operation: Optional[str] = Field(default="void", max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionQuoteListItem(BaseModel):
    """Production quote list row."""

    quote_id: Optional[int] = None
    plan_id: int
    quote_no: str
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    quote_qty: Decimal
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    management_fee: Decimal = Decimal("0")
    quote_unit_price: Decimal
    quote_amount: Decimal
    gross_margin: Decimal = Decimal("0")
    currency: str = "CNY"
    quoted_at: Optional[datetime] = None
    delivery_date: Optional[date] = None
    valid_until: Optional[date] = None
    status: str
    source: str = "derived"


class ProductionQuoteListData(BaseModel):
    """Production quote list result."""

    items: List[ProductionQuoteListItem]
    total: int
    page: int
    page_size: int


class ProductionQuoteConvertData(BaseModel):
    """Quote conversion result."""

    quote: ProductionQuoteListItem
    sales_order: SalesOrderDraftData


class ProductionFollowupTemplateQuery(BaseModel):
    """Production follow-up template list query."""

    company: Optional[str] = Field(default=None, max_length=140)
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


class ProductionFollowupTemplateNodeItem(BaseModel):
    """Production follow-up template node row."""

    id: int
    template_id: int
    company: str
    node_name: str
    owner: str
    lead_time_hours: int
    status: str
    gate: str
    output: str
    reminder: str
    sequence_no: int
    updated_at: datetime


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
    nodes: List[ProductionFollowupTemplateNodeItem] = Field(default_factory=list)


class ProductionFollowupTemplateListData(BaseModel):
    """Production follow-up template list result."""

    items: List[ProductionFollowupTemplateListItem]
    total: int
    page: int
    page_size: int


class ProductionFollowupTemplateCreateRequest(BaseModel):
    """Create a FastAPI-native production follow-up template."""

    company: str = Field(..., min_length=1, max_length=140)
    template_no: Optional[str] = Field(default=None, max_length=140)
    template_name: str = Field(..., min_length=1, max_length=255)
    template_type: Optional[str] = Field(default="基础跟进", max_length=140)
    trigger_node: Optional[str] = Field(default="制单草稿", max_length=140)
    followup_role: Optional[str] = Field(default="业务跟单", max_length=140)
    followup_frequency: Optional[str] = Field(default="每日", max_length=64)
    sla_hours: int = Field(default=24, ge=0, le=10000)
    item_code: Optional[str] = Field(default="", max_length=140)
    status: Optional[str] = Field(default="enabled", max_length=32)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateUpdateRequest(BaseModel):
    """Update a FastAPI-native production follow-up template."""

    company: str = Field(..., min_length=1, max_length=140)
    template_no: Optional[str] = Field(default=None, max_length=140)
    template_name: Optional[str] = Field(default=None, max_length=255)
    template_type: Optional[str] = Field(default=None, max_length=140)
    trigger_node: Optional[str] = Field(default=None, max_length=140)
    followup_role: Optional[str] = Field(default=None, max_length=140)
    followup_frequency: Optional[str] = Field(default=None, max_length=64)
    sla_hours: Optional[int] = Field(default=None, ge=0, le=10000)
    item_code: Optional[str] = Field(default=None, max_length=140)
    status: Optional[str] = Field(default=None, max_length=32)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateCopyRequest(BaseModel):
    """Copy an existing production follow-up template into a new template."""

    company: str = Field(..., min_length=1, max_length=140)
    template_no: Optional[str] = Field(default=None, max_length=140)
    template_name: Optional[str] = Field(default=None, max_length=255)
    item_code: Optional[str] = Field(default=None, max_length=140)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateActionRequest(BaseModel):
    """Action request for a production follow-up template."""

    company: str = Field(..., min_length=1, max_length=140)
    reason: Optional[str] = Field(default=None, max_length=255)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateNodeCreateRequest(BaseModel):
    """Create one FastAPI-native production follow-up template node."""

    company: str = Field(..., min_length=1, max_length=140)
    node_name: str = Field(..., min_length=1, max_length=255)
    owner: Optional[str] = Field(default="", max_length=140)
    lead_time_hours: int = Field(default=0, ge=0, le=10000)
    status: Optional[str] = Field(default="required", max_length=32)
    gate: Optional[str] = Field(default="", max_length=1000)
    output: Optional[str] = Field(default="", max_length=1000)
    reminder: Optional[str] = Field(default="", max_length=1000)
    sequence_no: int = Field(default=10, ge=0)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateNodeUpdateRequest(BaseModel):
    """Update one FastAPI-native production follow-up template node."""

    company: str = Field(..., min_length=1, max_length=140)
    node_name: Optional[str] = Field(default=None, max_length=255)
    owner: Optional[str] = Field(default=None, max_length=140)
    lead_time_hours: Optional[int] = Field(default=None, ge=0, le=10000)
    status: Optional[str] = Field(default=None, max_length=32)
    gate: Optional[str] = Field(default=None, max_length=1000)
    output: Optional[str] = Field(default=None, max_length=1000)
    reminder: Optional[str] = Field(default=None, max_length=1000)
    sequence_no: Optional[int] = Field(default=None, ge=0)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateNodeActionRequest(BaseModel):
    """Action request for a production follow-up template node."""

    company: str = Field(..., min_length=1, max_length=140)
    reason: Optional[str] = Field(default=None, max_length=255)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class ProductionFollowupTemplateNodeDeleteData(BaseModel):
    """Delete result for a production follow-up template node."""

    id: int
    template_id: int
    deleted: bool


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


class FactoryPackingCreateRequest(BaseModel):
    """Create one FastAPI-native factory packing in/out registration."""

    plan_id: int = Field(..., ge=1)
    company: Optional[str] = Field(default=None, max_length=140)
    packing_no: Optional[str] = Field(default=None, max_length=64)
    inbound_qty: Decimal = Field(default=Decimal("0"), ge=0)
    outbound_qty: Decimal = Field(default=Decimal("0"), ge=0)
    carton_qty: Decimal = Field(default=Decimal("0"), ge=0)
    box_spec: Optional[str] = Field(default=None, max_length=140)
    source_ref: Optional[str] = Field(default=None, max_length=140)
    remark: Optional[str] = Field(default=None, max_length=500)
    operation: Optional[str] = Field(default=None, max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class FactoryPackingData(BaseModel):
    """Factory packing registration returned to the UI."""

    id: int
    packing_no: str
    company: str
    plan_id: int
    plan_no: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    inbound_qty: Decimal
    outbound_qty: Decimal
    carton_qty: Decimal
    box_spec: str = ""
    source_ref: str = ""
    remark: str = ""
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


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
    inbound_ref_count: int = 0
    outbound_ref_count: int = 0
    inbound_refs: List[str] = Field(default_factory=list)
    outbound_refs: List[str] = Field(default_factory=list)
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


class ProductionReportSuiteQuery(BaseModel):
    """Existing frontend production report-suite query."""

    report_key: str = Field(..., min_length=1, max_length=80)
    company: Optional[str] = Field(default=None, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    customer: Optional[str] = Field(default=None, max_length=140)
    owner: Optional[str] = Field(default=None, max_length=140)
    status: Optional[str] = Field(default=None, max_length=80)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=30, ge=1, le=100)


class ProductionReportSuiteTrendPoint(BaseModel):
    """Small chart point for existing production report pages."""

    label: str
    amount: Decimal
    profit: Decimal = Decimal("0")


class ProductionReportSuiteCompositionItem(BaseModel):
    """Composition chart item for existing production report pages."""

    label: str
    value: Decimal
    color: str


class ProductionReportSuiteData(BaseModel):
    """Rows and chart data for the existing production report-suite pages."""

    report_key: str
    title: str
    items: List[dict[str, Any]]
    total: int
    page: int
    page_size: int
    trend: List[ProductionReportSuiteTrendPoint] = Field(default_factory=list)
    composition: List[ProductionReportSuiteCompositionItem] = Field(default_factory=list)
    data_basis: List[str] = Field(default_factory=list)
    pending_b_phase_fields: List[str] = Field(default_factory=list)


class ProductionPlanMaterialSnapshotItem(BaseModel):
    """Material check snapshot row."""

    bom_item_id: Optional[int] = None
    material_item_code: str
    warehouse: Optional[str] = None
    uom: str = "米"
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


class ProductionTrackingNodeItem(BaseModel):
    """Derived production tracking node based on persisted plan facts."""

    event_id: Optional[int] = None
    node_key: str
    node_name: str
    owner: str
    status: str
    progress: int
    source_type: str
    source_ref: Optional[str] = None
    remark: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProductionTrackingNodeEventRequest(BaseModel):
    """Advance a production tracking node from the existing tracking page."""

    company: Optional[str] = Field(default=None, max_length=140)
    node_key: str = Field(..., min_length=1, max_length=64)
    node_name: Optional[str] = Field(default=None, max_length=140)
    owner: Optional[str] = Field(default=None, max_length=140)
    status: str = Field(..., min_length=1, max_length=32)
    progress: int = Field(..., ge=0, le=100)
    remark: Optional[str] = Field(default=None, max_length=1000)
    operation: Optional[str] = Field(default="tracking_node", max_length=40)
    scenario_tag: Optional[str] = Field(default=None, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    plan_id: Optional[int] = Field(default=None, ge=1)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionTrackingNodeEventData(BaseModel):
    """Persisted production tracking node event."""

    id: int
    event_no: str
    plan_id: int
    company: str
    plan_no: str
    sales_order: str
    sales_order_item: str
    item_code: str
    node_key: str
    node_name: str
    owner: str
    status: str
    progress: int
    remark: str
    source_type: str
    source_ref: Optional[str] = None
    created_by: str
    created_at: datetime


class ProductionPlanDetailData(BaseModel):
    """Production plan detail result."""

    id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    customer: Optional[str] = None
    item_code: str
    color: Optional[str] = None
    size: Optional[str] = None
    sales_order_item_qty: Optional[Decimal] = None
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
    material_ready: bool = False
    required_qty_total: Decimal = Decimal("0")
    available_qty_total: Decimal = Decimal("0")
    shortage_qty_total: Decimal = Decimal("0")
    pending_requirement_count: int = 0
    purchase_status: str = "not_calculated"
    material_snapshots: List[ProductionPlanMaterialSnapshotItem] = Field(default_factory=list)
    tracking_nodes: List[ProductionTrackingNodeItem] = Field(default_factory=list)
    job_cards: List[ProductionJobCardLinkItem] = Field(default_factory=list)
    tracking_exceptions: List[ProductionTrackingExceptionItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProductionMaterialCheckData(BaseModel):
    """Material check result payload."""

    plan_id: int
    snapshot_count: int
    items: List[ProductionPlanMaterialSnapshotItem]


class ProductionSalesOrderMaterialCheckRequest(BaseModel):
    """Material-check all sales-order lines through existing production plans."""

    warehouse: str = Field(..., min_length=1, max_length=140)
    company: Optional[str] = Field(default=None, max_length=140)
    planned_start_date: Optional[date] = None
    operation: Optional[str] = Field(default="sales_order_material_check", max_length=40)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    scenario_tag: Optional[str] = Field(default=None, max_length=40)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionSalesOrderMaterialCheckPlanItem(BaseModel):
    """Per-plan material-check result under a sales order."""

    plan_id: int
    plan_no: str
    sales_order_item: str
    item_code: str
    planned_qty: Decimal
    created_plan: bool = False
    snapshot_count: int
    required_qty_total: Decimal = Decimal("0")
    available_qty_total: Decimal = Decimal("0")
    shortage_qty_total: Decimal = Decimal("0")


class ProductionSalesOrderMaterialCheckData(BaseModel):
    """Order-level material-check result."""

    sales_order: str
    company: str
    warehouse: str
    plan_count: int
    created_plan_count: int
    snapshot_count: int
    required_qty_total: Decimal = Decimal("0")
    available_qty_total: Decimal = Decimal("0")
    shortage_qty_total: Decimal = Decimal("0")
    items: List[ProductionSalesOrderMaterialCheckPlanItem]


class ProductionMaterialIssueItem(BaseModel):
    """Production material issue draft line."""

    material_item_code: str
    warehouse: str
    qty: Decimal
    uom: str


class ProductionMaterialIssueData(BaseModel):
    """Production material issue draft result."""

    plan_id: int
    draft_id: int
    source_id: str
    stock_entry_status: str
    event_key: str
    items: List[ProductionMaterialIssueItem]


class ProductionMaterialIssueQuery(BaseModel):
    """Production material issue readonly query."""

    company: Optional[str] = Field(default=None, max_length=140)
    keyword: Optional[str] = Field(default=None, max_length=140)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    material_item_code: Optional[str] = Field(default=None, max_length=140)
    warehouse: Optional[str] = Field(default=None, max_length=140)
    status: Optional[str] = Field(default=None, max_length=40)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProductionMaterialIssueListItem(BaseModel):
    """Production material issue readonly row."""

    plan_id: int
    plan_no: str
    work_order: Optional[str] = None
    company: str
    sales_order: str
    sales_order_item: str
    item_code: str
    material_item_code: str
    warehouse: str
    required_qty: Decimal
    available_qty: Decimal
    issued_qty: Decimal
    shortage_qty: Decimal
    status: str
    draft_id: Optional[int] = None
    source_id: Optional[str] = None
    stock_entry_status: Optional[str] = None
    checked_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None


class ProductionMaterialIssueListData(BaseModel):
    """Production material issue readonly list result."""

    items: List[ProductionMaterialIssueListItem]
    total: int
    page: int
    page_size: int


class ProductionMaterialIssueRequest(BaseModel):
    """Create material issue draft from checked production plan materials."""

    warehouse: Optional[str] = Field(default=None, max_length=140)
    business_date: date
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    scenario_tag: Optional[str] = Field(default=None, max_length=40)
    operation: Optional[str] = Field(default=None, max_length=40)
    plan_id: Optional[int] = Field(default=None, ge=1)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    bom_id: Optional[int] = Field(default=None, ge=1)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionMaterialCheckRequest(BaseModel):
    """Material-check request payload."""

    warehouse: Optional[str] = Field(default=None, max_length=140)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    scenario_tag: Optional[str] = Field(default=None, max_length=40)
    operation: Optional[str] = Field(default=None, max_length=40)
    plan_id: Optional[int] = Field(default=None, ge=1)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    bom_id: Optional[int] = Field(default=None, ge=1)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionCreateWorkOrderRequest(BaseModel):
    """Create-work-order request payload."""

    fg_warehouse: Optional[str] = Field(default=None, max_length=140)
    wip_warehouse: Optional[str] = Field(default=None, max_length=140)
    start_date: Optional[date] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    scenario_tag: Optional[str] = Field(default=None, max_length=40)
    operation: Optional[str] = Field(default=None, max_length=40)
    plan_id: Optional[int] = Field(default=None, ge=1)
    sales_order: Optional[str] = Field(default=None, max_length=140)
    sales_order_item: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    bom_id: Optional[int] = Field(default=None, ge=1)
    request_id: Optional[str] = Field(default=None, max_length=64)


class ProductionCreateWorkOrderData(BaseModel):
    """Create work-order outbox response."""

    plan_id: int
    outbox_id: int
    event_key: str
    sync_status: str
    work_order: Optional[str] = None


class ProductionSyncJobCardsRequest(BaseModel):
    """Sync-job-cards request payload."""

    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    scenario_tag: Optional[str] = Field(default=None, max_length=64)
    operation: Optional[str] = Field(default=None, max_length=64)
    plan_id: Optional[int] = Field(default=None, ge=1)
    plan_no_or_work_order: Optional[str] = Field(default=None, max_length=140)
    company: Optional[str] = Field(default=None, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    source_ref: Optional[str] = Field(default=None, max_length=255)
    request_id: Optional[str] = Field(default=None, max_length=64)


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
