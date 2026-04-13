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
    item_code: Optional[str] = None
    company: Optional[str] = None
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
