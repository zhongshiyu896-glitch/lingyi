"""Pydantic schemas for dashboard overview read-only baseline (TASK-060A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class DashboardQualityOverviewData(BaseModel):
    """Quality module summary for dashboard overview."""

    inspection_count: int
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_count: int
    pass_rate: Decimal


class DashboardSalesInventoryOverviewData(BaseModel):
    """Sales-inventory module summary for dashboard overview."""

    item_count: int
    total_actual_qty: Decimal
    below_safety_count: int
    below_reorder_count: int


class DashboardWarehouseOverviewData(BaseModel):
    """Warehouse module summary for dashboard overview."""

    alert_count: int
    critical_alert_count: int
    warning_alert_count: int


class DashboardSourceStatusData(BaseModel):
    """Per-source status row for dashboard overview aggregation."""

    module: str
    status: str


class DashboardKanbanFlowNodeData(BaseModel):
    """Flow node shown in bulk-management kanban."""

    key: str
    label: str
    status: str
    route: str | None = None


class DashboardKanbanFlowLinkData(BaseModel):
    """Flow edge between two kanban nodes."""

    from_key: str
    to_key: str


class DashboardKanbanMessageRowData(BaseModel):
    """Read-only kanban message row mapped from evidence table headers."""

    image: str | None = None
    order_no: str
    customer: str
    style_no: str
    style_name: str
    ordered_qty: Decimal
    overdue: str
    sun: str
    mon: str
    tue: str
    wed: str
    thu: str
    fri: str
    sat: str
    title: str
    sent_at: datetime
    status: str
    sender: str


class DashboardKanbanData(BaseModel):
    """Read-only bulk-management kanban payload."""

    board_name: str
    quick_filters: list[str]
    flow_nodes: list[DashboardKanbanFlowNodeData]
    flow_links: list[DashboardKanbanFlowLinkData]
    messages: list[DashboardKanbanMessageRowData]


class DashboardHomeMetricCardData(BaseModel):
    """Homepage metric card row for P1 dashboard enhancement."""

    key: str
    label: str
    value: str
    unit: str | None = None
    trend: str | None = None


class DashboardHomeTodoItemData(BaseModel):
    """Homepage todo/warning summary card."""

    key: str
    title: str
    count: int
    status: str
    action_label: str


class DashboardHomeTrendPointData(BaseModel):
    """Trend point for homepage forecast chart/table."""

    period: str
    forecast_sales: Decimal
    forecast_cost: Decimal
    forecast_profit: Decimal


class DashboardHomeOverviewData(BaseModel):
    """Homepage enhancement block payload."""

    summary_title: str
    metric_cards: list[DashboardHomeMetricCardData]
    todo_items: list[DashboardHomeTodoItemData]
    warnings: list[str]
    business_summary: list[str]
    recent_activities: list[str]
    trend_points: list[DashboardHomeTrendPointData]
    primary_actions: list[str]


class DashboardOverviewData(BaseModel):
    """Dashboard overview response payload."""

    company: str
    from_date: date | None = None
    to_date: date | None = None
    generated_at: datetime
    quality: DashboardQualityOverviewData
    sales_inventory: DashboardSalesInventoryOverviewData
    warehouse: DashboardWarehouseOverviewData
    source_status: list[DashboardSourceStatusData]
    kanban: DashboardKanbanData | None = None
    home_overview: DashboardHomeOverviewData | None = None
