"""SQLAlchemy models for FastAPI-native material purchase orders."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
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


class LyMaterialPurchaseInvoice(Base):
    """FastAPI-native purchase invoice and payable document."""

    __tablename__ = "ly_material_purchase_invoice"
    __table_args__ = (
        Index("uk_ly_material_purchase_invoice_company_no", "company", "purchase_invoice", unique=True),
        Index("uk_ly_material_purchase_invoice_company_idem", "company", "idempotency_key", unique=True),
        Index("uk_ly_material_purchase_invoice_company_source", "company", "source_ref", unique=True),
        Index("idx_ly_material_purchase_invoice_order", "company", "purchase_no"),
        Index("idx_ly_material_purchase_invoice_supplier", "company", "supplier_name"),
        CheckConstraint(
            "status IN ('submitted','partly_paid','paid','cancelled')",
            name="ck_ly_material_purchase_invoice_status",
        ),
        CheckConstraint("qty > 0", name="ck_ly_material_purchase_invoice_qty_positive"),
        CheckConstraint("grand_total >= 0", name="ck_ly_material_purchase_invoice_total_nonnegative"),
        CheckConstraint("paid_amount >= 0", name="ck_ly_material_purchase_invoice_paid_nonnegative"),
        CheckConstraint("outstanding_amount >= 0", name="ck_ly_material_purchase_invoice_outstanding_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生采购发票与应付"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    purchase_invoice = Column(String(140), nullable=False)
    purchase_order_id = Column(IDType, ForeignKey("ly_schema.ly_material_purchase_order.id"), nullable=False)
    purchase_no = Column(String(140), nullable=False)
    supplier_name = Column(String(255), nullable=False)
    material_item_code = Column(String(140), nullable=False)
    material_name = Column(String(255), nullable=False, default="")
    warehouse = Column(String(140), nullable=True)
    qty = Column(Numeric(18, 6), nullable=False)
    uom = Column(String(32), nullable=False, default="米")
    rate = Column(Numeric(18, 6), nullable=False, default=0)
    grand_total = Column(Numeric(18, 6), nullable=False, default=0)
    paid_amount = Column(Numeric(18, 6), nullable=False, default=0)
    outstanding_amount = Column(Numeric(18, 6), nullable=False, default=0)
    posting_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="submitted")
    docstatus = Column(Integer, nullable=False, default=1)
    source_ref = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyMaterialPurchasePayment(Base):
    """FastAPI-native supplier payment entry allocated to one purchase invoice."""

    __tablename__ = "ly_material_purchase_payment"
    __table_args__ = (
        Index("uk_ly_material_purchase_payment_company_no", "company", "payment_entry", unique=True),
        Index("uk_ly_material_purchase_payment_company_idem", "company", "idempotency_key", unique=True),
        Index("uk_ly_material_purchase_payment_company_source", "company", "source_ref", unique=True),
        Index("idx_ly_material_purchase_payment_invoice", "company", "purchase_invoice"),
        Index("idx_ly_material_purchase_payment_supplier", "company", "supplier_name"),
        CheckConstraint("status IN ('submitted','cancelled')", name="ck_ly_material_purchase_payment_status"),
        CheckConstraint("paid_amount > 0", name="ck_ly_material_purchase_payment_amount_positive"),
        CheckConstraint("allocated_amount > 0", name="ck_ly_material_purchase_payment_allocated_positive"),
        CheckConstraint("outstanding_before >= 0", name="ck_ly_material_purchase_payment_before_nonnegative"),
        CheckConstraint("outstanding_after >= 0", name="ck_ly_material_purchase_payment_after_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生采购付款单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    payment_entry = Column(String(140), nullable=False)
    purchase_invoice_id = Column(IDType, ForeignKey("ly_schema.ly_material_purchase_invoice.id"), nullable=False)
    purchase_invoice = Column(String(140), nullable=False)
    purchase_no = Column(String(140), nullable=False)
    supplier_name = Column(String(255), nullable=False)
    posting_date = Column(Date, nullable=False)
    paid_amount = Column(Numeric(18, 6), nullable=False)
    allocated_amount = Column(Numeric(18, 6), nullable=False)
    outstanding_before = Column(Numeric(18, 6), nullable=False)
    outstanding_after = Column(Numeric(18, 6), nullable=False)
    mode_of_payment = Column(String(140), nullable=False, default="Bank Transfer")
    reference_no = Column(String(140), nullable=True)
    reference_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="submitted")
    docstatus = Column(Integer, nullable=False, default=1)
    source_ref = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


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
