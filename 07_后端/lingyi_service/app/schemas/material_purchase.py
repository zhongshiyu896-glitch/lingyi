"""Pydantic schemas for FastAPI-native material purchase orders."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

PurchaseOrderStatus = Literal["draft", "partially_received", "received", "cancelled"]


class MaterialPurchaseOrderLineCreate(BaseModel):
    """Create payload line."""

    item_code: str | None = Field(default=None, max_length=140)
    material_item_code: str = Field(..., min_length=1, max_length=140)
    material_name: str = Field(default="", max_length=255)
    qty: Decimal = Field(..., gt=0)
    uom: str = Field(default="米", min_length=1, max_length=32)
    unit_price: Decimal = Field(default=0, ge=0)
    warehouse: str | None = Field(default=None, max_length=140)


class MaterialPurchaseOrderCreateRequest(BaseModel):
    """Create purchase order request."""

    operation: Literal["create"] = "create"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    purchase_no: str | None = Field(default=None, max_length=140)
    supplier_name: str = Field(..., min_length=1, max_length=255)
    transaction_date: date | None = None
    expected_delivery_date: date | None = None
    currency: str = Field(default="CNY", min_length=1, max_length=32)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    items: list[MaterialPurchaseOrderLineCreate] = Field(min_length=1)


class MaterialPurchaseOrderListItem(BaseModel):
    """Purchase order row returned to existing frontend table."""

    id: int
    order_id: int
    line_id: int
    company: str
    purchase_no: str
    supplier_name: str
    item_code: str
    material_item_code: str
    material_name: str
    qty: Decimal
    received_qty: Decimal
    uom: str
    unit_price: Decimal
    total_amount: Decimal
    expected_delivery_date: date | None = None
    transaction_date: date | None = None
    status: PurchaseOrderStatus
    warehouse: str | None = None
    currency: str = "CNY"
    created_at: datetime | None = None


class MaterialPurchaseOrderData(BaseModel):
    """Paginated purchase order rows."""

    items: list[MaterialPurchaseOrderListItem]
    total: int
    page: int
    page_size: int


class MaterialPurchaseOrderCreateData(BaseModel):
    """Create response."""

    id: int
    purchase_no: str
    company: str
    supplier_name: str
    status: PurchaseOrderStatus
    total_qty: Decimal
    received_qty: Decimal
    total_amount: Decimal
    currency: str
    idempotency_key: str
    created_at: datetime | None = None
    items: list[MaterialPurchaseOrderListItem]
