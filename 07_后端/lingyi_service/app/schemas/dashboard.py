"""Pydantic schemas for dashboard overview read-only baseline (TASK-060A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
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
    source_type: str = "actual"
    source_note: str | None = None


class DashboardKanbanFlowNodeData(BaseModel):
    """Flow node shown in bulk-management kanban."""

    key: str
    label: str
    status: str
    route: str | None = None
    source_type: str = "config"
    status_note: str | None = "流程节点状态为系统导航配置，不代表业务闭环完成。"


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
    group: str = "quality"
    route: str | None = None
    status: str = "complete"
    source_note: str | None = None


class DashboardHomeTodoItemData(BaseModel):
    """Homepage todo/warning summary card."""

    key: str
    title: str
    count: int
    status: str
    action_label: str
    route: str | None = None


class DashboardHomeTrendPointData(BaseModel):
    """Trend point for homepage forecast chart/table."""

    period: str
    forecast_sales: Decimal
    forecast_cost: Decimal
    forecast_profit: Decimal


class DashboardHomeChartSeriesData(BaseModel):
    """Series metadata for homepage real-data chart."""

    key: str
    label: str
    unit: str | None = None


class DashboardHomeChartPointData(BaseModel):
    """One time bucket for homepage real-data chart."""

    period: str
    values: dict[str, Decimal]
    meta: dict[str, Any] | None = None


class DashboardHomeChartData(BaseModel):
    """Homepage chart payload backed by readonly aggregation."""

    key: str
    title: str
    chart_type: str = "line"
    unit: str | None = None
    source_note: str | None = None
    series: list[DashboardHomeChartSeriesData]
    points: list[DashboardHomeChartPointData]


class DashboardWorkbenchAlertData(BaseModel):
    """Top-priority dashboard alert backed by readonly aggregation."""

    key: str
    label: str
    count: int
    tone: str
    route: str | None = None
    source_note: str | None = None


class DashboardWorkbenchKpiData(BaseModel):
    """Dashboard KPI card for the rebuilt homepage."""

    key: str
    label: str
    value: Decimal
    unit: str | None = None
    sub_value: str | None = None
    trend: str | None = None
    trend_direction: str = "flat"
    route: str | None = None
    tone: str = "blue"
    source_note: str | None = None


class DashboardWorkbenchTrendPointData(BaseModel):
    """Monthly shipment and collection trend point."""

    period: str
    shipment_amount: Decimal
    collection_amount: Decimal


class DashboardWorkbenchStageData(BaseModel):
    """Order pipeline stage count. The same rows feed chart and admin board."""

    key: str
    label: str
    count: int
    route: str | None = None
    action_label: str | None = None
    tone: str = "blue"
    source_note: str | None = None


class DashboardWorkbenchDueOrderData(BaseModel):
    """Order due within seven days."""

    sales_order: str
    customer: str
    style_no: str
    due_date: date
    days_left: int
    ordered_qty: Decimal
    finished_qty: Decimal
    completion_rate: Decimal
    route: str | None = None


class DashboardWorkbenchCustomerShareData(BaseModel):
    """Top customer share by shipment amount."""

    customer: str
    amount: Decimal
    ratio: Decimal


class DashboardWorkbenchExceptionData(BaseModel):
    """Actionable dashboard exception row."""

    key: str
    title: str
    severity: str
    route: str | None = None
    action_label: str = "去处理"
    source_note: str | None = None


class DashboardWorkbenchRecentOrderData(BaseModel):
    """Recent order row for admin dashboard."""

    sales_order: str
    customer: str
    style_no: str
    qty: Decimal
    status: str
    next_action: str
    route: str | None = None


class DashboardWorkbenchQuickActionData(BaseModel):
    """Configured quick action shown on the dashboard."""

    key: str
    label: str
    route: str
    icon: str


class DashboardWorkbenchSourceData(BaseModel):
    """Reader-facing data provenance for one dashboard module."""

    module: str
    api: str
    fields: list[str]
    note: str | None = None


class DashboardWorkbenchData(BaseModel):
    """Formal homepage workbench payload. All numbers are real readonly data."""

    alerts: list[DashboardWorkbenchAlertData]
    kpis: list[DashboardWorkbenchKpiData]
    shipment_collection_trend: list[DashboardWorkbenchTrendPointData]
    stage_distribution: list[DashboardWorkbenchStageData]
    due_orders: list[DashboardWorkbenchDueOrderData]
    customer_shares: list[DashboardWorkbenchCustomerShareData]
    pipeline: list[DashboardWorkbenchStageData]
    quick_actions: list[DashboardWorkbenchQuickActionData]
    exceptions: list[DashboardWorkbenchExceptionData]
    recent_orders: list[DashboardWorkbenchRecentOrderData]
    data_sources: list[DashboardWorkbenchSourceData]
    todo_notes: list[str]


class DashboardHomeOverviewData(BaseModel):
    """Homepage enhancement block payload."""

    summary_title: str
    metric_cards: list[DashboardHomeMetricCardData]
    todo_items: list[DashboardHomeTodoItemData]
    warnings: list[str]
    business_summary: list[str]
    recent_activities: list[str]
    trend_points: list[DashboardHomeTrendPointData]
    charts: list[DashboardHomeChartData]
    primary_actions: list[str]
    workbench: DashboardWorkbenchData | None = None


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
