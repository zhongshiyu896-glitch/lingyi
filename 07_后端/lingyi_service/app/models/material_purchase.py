"""SQLAlchemy models for FastAPI-native material purchase orders."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.models.quality import IDType

Base = declarative_base()


class LyMaterialPurchaseOrder(Base):
    """Material purchase order header for existing purchase pages."""

    __tablename__ = "ly_material_purchase_order"
    __table_args__ = (
        Index("uk_ly_material_purchase_order_company_no", "company", "purchase_no", unique=True),
        Index("idx_ly_material_purchase_order_supplier_status", "company", "supplier_name", "status"),
        CheckConstraint(
            "status IN ('draft','partially_received','received','cancelled')",
            name="ck_ly_material_purchase_order_status",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生物料采购单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    purchase_no = Column(String(140), nullable=False)
    supplier_name = Column(String(255), nullable=False)
    transaction_date = Column(Date, nullable=True)
    expected_delivery_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    total_qty = Column(Numeric(18, 6), nullable=False, default=0)
    received_qty = Column(Numeric(18, 6), nullable=False, default=0)
    total_amount = Column(Numeric(18, 6), nullable=False, default=0)
    currency = Column(String(32), nullable=False, default="CNY")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyMaterialPurchaseOrderItem(Base):
    """Material purchase order line."""

    __tablename__ = "ly_material_purchase_order_item"
    __table_args__ = (
        Index("idx_ly_material_purchase_order_item_order", "order_id"),
        Index("idx_ly_material_purchase_order_item_material", "company", "material_item_code"),
        CheckConstraint("qty > 0", name="ck_ly_material_purchase_order_item_qty_positive"),
        CheckConstraint("received_qty >= 0", name="ck_ly_material_purchase_order_item_received_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生物料采购单明细"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    order_id = Column(IDType, ForeignKey("ly_schema.ly_material_purchase_order.id"), nullable=False)
    company = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    material_item_code = Column(String(140), nullable=False)
    material_name = Column(String(255), nullable=False, default="")
    qty = Column(Numeric(18, 6), nullable=False)
    received_qty = Column(Numeric(18, 6), nullable=False, default=0)
    uom = Column(String(32), nullable=False, default="米")
    unit_price = Column(Numeric(18, 6), nullable=False, default=0)
    amount = Column(Numeric(18, 6), nullable=False, default=0)
    warehouse = Column(String(140), nullable=True)


class LyMaterialPurchaseIdempotency(Base):
    """Idempotency ledger for purchase order writes."""

    __tablename__ = "ly_material_purchase_idempotency"
    __table_args__ = (
        Index("uk_ly_material_purchase_idem_company_key", "company", "idempotency_key", unique=True),
        {"schema": "ly_schema", "comment": "物料采购写入幂等记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    request_hash = Column(String(64), nullable=False)
    record_id = Column(IDType, nullable=False)
    response_data = Column(JSON, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
