"""FastAPI-native sales order models for existing production pages."""

from __future__ import annotations

from sqlalchemy import BigInteger
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LySalesOrder(Base):
    """FastAPI-native big-order draft header."""

    __tablename__ = "ly_sales_order"
    __table_args__ = (
        Index("uk_ly_sales_order_company_no", "company", "sales_order_no", unique=True),
        Index("idx_ly_sales_order_company_status", "company", "status"),
        Index("idx_ly_sales_order_customer", "customer"),
        CheckConstraint("status IN ('draft','planned','cancelled')", name="ck_ly_sales_order_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生大货销售订单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    sales_order_no = Column(String(140), nullable=False)
    source_order_ref = Column(String(140), nullable=True)
    company = Column(String(140), nullable=False)
    customer = Column(String(140), nullable=True)
    status = Column(String(32), nullable=False, server_default="draft")
    docstatus = Column(Integer, nullable=False, server_default="0")
    transaction_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)
    currency = Column(String(16), nullable=False, server_default="CNY")
    grand_total = Column(Numeric(18, 6), nullable=False, server_default="0")
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    payload = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(255), nullable=True)


class LySalesOrderItem(Base):
    """FastAPI-native big-order line item."""

    __tablename__ = "ly_sales_order_item"
    __table_args__ = (
        Index("uk_ly_sales_order_item_line", "sales_order_id", "line_no", unique=True),
        Index("idx_ly_sales_order_item_order", "sales_order_id"),
        Index("idx_ly_sales_order_item_code", "company", "item_code"),
        Index("idx_ly_sales_order_item_material_calc", "company", "ys_material_calc_state"),
        CheckConstraint("qty > 0", name="ck_ly_sales_order_item_qty_positive"),
        CheckConstraint("ys_material_calc_state IN ('待算料','已算料')", name="ck_ly_sales_order_item_calc_state"),
        {"schema": "ly_schema", "comment": "FastAPI 原生大货销售订单明细"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    sales_order_id = Column(IDType, ForeignKey("ly_schema.ly_sales_order.id"), nullable=False)
    company = Column(String(140), nullable=False)
    line_no = Column(Integer, nullable=False)
    sales_order_item = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    item_name = Column(String(255), nullable=True)
    color = Column(String(64), nullable=True)
    size = Column(String(64), nullable=True)
    qty = Column(Numeric(18, 6), nullable=False)
    planned_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    delivered_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    ys_material_calc_state = Column(String(32), nullable=False, server_default="待算料")
    rate = Column(Numeric(18, 6), nullable=True)
    amount = Column(Numeric(18, 6), nullable=True)
    uom = Column(String(32), nullable=False, server_default="Nos")
    warehouse = Column(String(140), nullable=True)
    delivery_date = Column(Date, nullable=True)


class LySalesOrderIdempotency(Base):
    """Idempotency ledger for FastAPI-native sales order mutations."""

    __tablename__ = "ly_sales_order_idempotency"
    __table_args__ = (
        Index("uk_ly_sales_order_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_sales_order_idem_order", "sales_order_id"),
        CheckConstraint("operation IN ('create_draft','cancel_draft')", name="ck_ly_sales_order_idem_operation"),
        {"schema": "ly_schema", "comment": "FastAPI 原生大货销售订单幂等记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    operation = Column(String(32), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    sales_order_id = Column(IDType, nullable=False)
    response_json = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyDeliveryInvoice(Base):
    """FastAPI-native delivery note + sales invoice document."""

    __tablename__ = "ly_delivery_invoice"
    __table_args__ = (
        Index("uk_ly_delivery_invoice_company_dn", "company", "delivery_note", unique=True),
        Index("uk_ly_delivery_invoice_company_si", "company", "sales_invoice", unique=True),
        Index("uk_ly_delivery_invoice_company_idem", "company", "idempotency_key", unique=True),
        Index("uk_ly_delivery_invoice_company_source", "company", "source_ref", unique=True),
        Index("idx_ly_delivery_invoice_order", "company", "sales_order"),
        Index("idx_ly_delivery_invoice_customer", "company", "customer"),
        CheckConstraint(
            "status IN ('submitted','partly_paid','paid','cancelled')",
            name="ck_ly_delivery_invoice_status",
        ),
        CheckConstraint("delivered_qty > 0", name="ck_ly_delivery_invoice_qty_positive"),
        CheckConstraint("grand_total >= 0", name="ck_ly_delivery_invoice_grand_total_nonnegative"),
        CheckConstraint("paid_amount >= 0", name="ck_ly_delivery_invoice_paid_nonnegative"),
        CheckConstraint("outstanding_amount >= 0", name="ck_ly_delivery_invoice_outstanding_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生发货开票单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    delivery_note = Column(String(140), nullable=False)
    sales_invoice = Column(String(140), nullable=False)
    sales_order = Column(String(140), nullable=False)
    customer = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)
    item_name = Column(String(255), nullable=True)
    warehouse = Column(String(140), nullable=False)
    delivered_qty = Column(Numeric(18, 6), nullable=False)
    uom = Column(String(32), nullable=False, server_default="Nos")
    rate = Column(Numeric(18, 6), nullable=True)
    grand_total = Column(Numeric(18, 6), nullable=False, server_default="0")
    paid_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    outstanding_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    posting_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, server_default="submitted")
    docstatus = Column(Integer, nullable=False, server_default="1")
    source_ref = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    warehouse_draft_id = Column(IDType, nullable=True)
    payload = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(255), nullable=True)


class LySalesPaymentEntry(Base):
    """FastAPI-native customer payment entry allocated to one sales invoice."""

    __tablename__ = "ly_sales_payment_entry"
    __table_args__ = (
        Index("uk_ly_sales_payment_company_no", "company", "payment_entry", unique=True),
        Index("uk_ly_sales_payment_company_idem", "company", "idempotency_key", unique=True),
        Index("uk_ly_sales_payment_company_source", "company", "source_ref", unique=True),
        Index("idx_ly_sales_payment_invoice", "company", "sales_invoice"),
        Index("idx_ly_sales_payment_customer", "company", "customer"),
        CheckConstraint("status IN ('submitted','cancelled')", name="ck_ly_sales_payment_status"),
        CheckConstraint("paid_amount > 0", name="ck_ly_sales_payment_amount_positive"),
        CheckConstraint("allocated_amount > 0", name="ck_ly_sales_payment_allocated_positive"),
        CheckConstraint("outstanding_before >= 0", name="ck_ly_sales_payment_before_nonnegative"),
        CheckConstraint("outstanding_after >= 0", name="ck_ly_sales_payment_after_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生销售回款单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    payment_entry = Column(String(140), nullable=False)
    delivery_invoice_id = Column(IDType, nullable=False)
    delivery_note = Column(String(140), nullable=False)
    sales_invoice = Column(String(140), nullable=False)
    sales_order = Column(String(140), nullable=False)
    customer = Column(String(140), nullable=True)
    posting_date = Column(Date, nullable=False)
    paid_amount = Column(Numeric(18, 6), nullable=False)
    allocated_amount = Column(Numeric(18, 6), nullable=False)
    outstanding_before = Column(Numeric(18, 6), nullable=False)
    outstanding_after = Column(Numeric(18, 6), nullable=False)
    mode_of_payment = Column(String(140), nullable=False, server_default="Bank Transfer")
    reference_no = Column(String(140), nullable=True)
    reference_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, server_default="submitted")
    docstatus = Column(Integer, nullable=False, server_default="1")
    source_ref = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    payload = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
