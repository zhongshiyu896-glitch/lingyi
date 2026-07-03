"""Schemas for finance readonly analysis endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel
from pydantic import Field


class OrderProfitAnalysisItem(BaseModel):
    """One sales-order quoted gross-profit projection row."""

    id: int
    company: str
    sales_order: str
    customer: str | None = None
    style_no: str
    style_name: str
    order_qty: Decimal
    order_date: date | None = None
    delivery_date: date | None = None
    order_status: str
    production_status: str
    production_status_label: str
    sales_amount: Decimal
    material_cost: Decimal | None = None
    labor_cost: Decimal | None = None
    management_fee: Decimal | None = None
    other_fee: Decimal | None = None
    total_cost: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin_rate: Decimal | None = None
    profit_status: str
    profit_status_code: str
    quote_no: str | None = None
    cost_source: str


class OrderProfitAnalysisSummary(BaseModel):
    """Summary for the current filtered order-profit result."""

    order_count: int = 0
    analyzed_count: int = 0
    missing_cost_count: int = 0
    missing_sales_count: int = 0
    low_profit_count: int = 0
    negative_profit_count: int = 0
    sales_amount: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")


class OrderProfitAnalysisListData(BaseModel):
    """Paginated order quoted gross-profit projection rows."""

    items: list[OrderProfitAnalysisItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    summary: OrderProfitAnalysisSummary
