"""SQLAlchemy models for factory statement module (TASK-006B)."""

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
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyFactoryStatement(Base):
    """加工厂对账单主表（本地草稿）。"""

    __tablename__ = "ly_factory_statement"
    __table_args__ = (
        Index("uk_ly_factory_statement_no", "statement_no", unique=True),
        Index(
            "uk_ly_factory_statement_active_scope",
            "company",
            "supplier",
            "from_date",
            "to_date",
            "request_hash",
            unique=True,
            postgresql_where=text("statement_status <> 'cancelled'"),
            sqlite_where=text("statement_status <> 'cancelled'"),
        ),
        Index(
            "uk_ly_factory_statement_company_idempotency",
            "company",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "idx_ly_factory_statement_company_supplier_status_created",
            "company",
            "supplier",
            "statement_status",
            "created_at",
        ),
        CheckConstraint(
            "statement_status IN ('draft','confirmed','cancelled','payable_draft_created')",
            name="ck_ly_factory_statement_status",
        ),
        {"schema": "ly_schema", "comment": "加工厂对账单主表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    statement_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    supplier = Column(String(140), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    source_type = Column(String(64), nullable=False, default="subcontract_inspection")
    source_count = Column(Integer, nullable=False, default=0)

    inspected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    gross_amount = Column(Numeric(18, 6), nullable=False, default=0)
    deduction_amount = Column(Numeric(18, 6), nullable=False, default=0)
    net_amount = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_rate = Column(Numeric(10, 6), nullable=False, default=0)

    statement_status = Column(String(32), nullable=False, default="draft")
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)

    created_by = Column(String(140), nullable=False)
    confirmed_by = Column(String(140), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyFactoryStatementItem(Base):
    """加工厂对账单明细快照（来源于验货事实）。"""

    __tablename__ = "ly_factory_statement_item"
    __table_args__ = (
        Index("idx_ly_factory_statement_item_statement", "statement_id", "line_no"),
        Index("idx_ly_factory_statement_item_inspection", "inspection_id"),
        Index(
            "idx_ly_factory_statement_item_company_supplier_time",
            "company",
            "supplier",
            "inspected_at",
        ),
        {"schema": "ly_schema", "comment": "加工厂对账单明细快照"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    statement_id = Column(IDType, ForeignKey("ly_schema.ly_factory_statement.id"), nullable=False)
    line_no = Column(Integer, nullable=False)

    inspection_id = Column(BigInteger, nullable=False)
    inspection_no = Column(String(64), nullable=True)
    subcontract_id = Column(BigInteger, nullable=False)
    subcontract_no = Column(String(64), nullable=False)

    company = Column(String(140), nullable=False)
    supplier = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=True)
    inspected_at = Column(DateTime(timezone=True), nullable=True)

    inspected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    subcontract_rate = Column(Numeric(18, 6), nullable=False, default=0)
    gross_amount = Column(Numeric(18, 6), nullable=False, default=0)
    deduction_amount = Column(Numeric(18, 6), nullable=False, default=0)
    net_amount = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_rate = Column(Numeric(10, 6), nullable=False, default=0)

    source_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyFactoryStatementLog(Base):
    """加工厂对账单状态日志。"""

    __tablename__ = "ly_factory_statement_log"
    __table_args__ = (
        Index("idx_ly_factory_statement_log_statement_time", "statement_id", "operated_at"),
        Index("idx_ly_factory_statement_log_company_statement", "company", "statement_id", "operated_at"),
        {"schema": "ly_schema", "comment": "加工厂对账单状态日志"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    statement_id = Column(IDType, ForeignKey("ly_schema.ly_factory_statement.id"), nullable=False)
    company = Column(String(140), nullable=False)
    supplier = Column(String(140), nullable=False)
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    operator = Column(String(140), nullable=False)
    request_id = Column(String(64), nullable=True)
    remark = Column(String(200), nullable=True)
    operated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyFactoryStatementOperation(Base):
    """加工厂对账单操作幂等记录（confirm/cancel）。"""

    __tablename__ = "ly_factory_statement_operation"
    __table_args__ = (
        Index(
            "uk_ly_factory_statement_operation_idempotency",
            "company",
            "statement_id",
            "operation_type",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "idx_ly_factory_statement_operation_statement_time",
            "statement_id",
            "created_at",
        ),
        CheckConstraint(
            "operation_type IN ('confirm','cancel')",
            name="ck_ly_factory_statement_operation_type",
        ),
        {"schema": "ly_schema", "comment": "加工厂对账单操作幂等记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    statement_id = Column(IDType, ForeignKey("ly_schema.ly_factory_statement.id"), nullable=False)
    operation_type = Column(String(32), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    result_status = Column(String(32), nullable=False)
    result_user = Column(String(140), nullable=False)
    result_at = Column(DateTime(timezone=True), nullable=False)
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyFactoryStatementPayableOutbox(Base):
    """加工厂对账单应付草稿 outbox。"""

    __tablename__ = "ly_factory_statement_payable_outbox"
    __table_args__ = (
        Index("uk_ly_factory_statement_payable_event_key", "event_key", unique=True),
        Index(
            "uk_ly_factory_statement_payable_idem",
            "company",
            "statement_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "uk_ly_factory_statement_payable_one_active",
            "statement_id",
            unique=True,
            postgresql_where=text("status IN ('pending','processing','succeeded')"),
            sqlite_where=text("status IN ('pending','processing','succeeded')"),
        ),
        Index("idx_ly_factory_statement_payable_due", "status", "next_retry_at", "id"),
        Index("idx_ly_factory_statement_payable_statement", "statement_id", "status", "id"),
        CheckConstraint(
            "status IN ('pending','processing','succeeded','failed','dead')",
            name="ck_ly_factory_statement_payable_outbox_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_ly_factory_statement_payable_outbox_attempts",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_ly_factory_statement_payable_outbox_max_attempts",
        ),
        {"schema": "ly_schema", "comment": "加工厂对账单应付草稿 outbox"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    statement_id = Column(IDType, ForeignKey("ly_schema.ly_factory_statement.id"), nullable=False)
    statement_no = Column(String(64), nullable=False)
    supplier = Column(String(140), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    event_key = Column(String(140), nullable=False)
    payload_json = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)

    status = Column(String(32), nullable=False, server_default="pending")
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="5")
    next_retry_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by = Column(String(140), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    erpnext_purchase_invoice = Column(String(140), nullable=True)
    erpnext_docstatus = Column(Integer, nullable=True)
    erpnext_status = Column(String(64), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)

    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
