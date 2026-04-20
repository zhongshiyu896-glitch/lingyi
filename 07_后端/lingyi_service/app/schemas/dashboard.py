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
