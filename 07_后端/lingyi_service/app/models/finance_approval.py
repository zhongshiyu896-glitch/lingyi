"""FastAPI-native finance approval task models."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.models.quality import IDType

Base = declarative_base()


class LyFinanceApprovalTask(Base):
    """Finance approval task linked to an existing payable/payment source."""

    __tablename__ = "ly_finance_approval_task"
    __table_args__ = (
        UniqueConstraint("company", "source_type", "source_id", name="uk_ly_finance_approval_source"),
        Index("uk_ly_finance_approval_company_no", "company", "approval_no", unique=True),
        Index("uk_ly_finance_approval_company_idem", "company", "idempotency_key", unique=True),
        Index("idx_ly_finance_approval_status", "company", "status", "created_at"),
        Index("idx_ly_finance_approval_source_no", "company", "source_no"),
        CheckConstraint(
            "source_type IN ('purchase_invoice','purchase_payment','factory_statement_payment')",
            name="ck_ly_finance_approval_source_type",
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected','cancelled')",
            name="ck_ly_finance_approval_status",
        ),
        CheckConstraint("amount >= 0", name="ck_ly_finance_approval_amount_nonnegative"),
        {"schema": "ly_schema", "comment": "FastAPI 原生财务审批任务"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    approval_no = Column(String(140), nullable=False)
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(140), nullable=False)
    source_no = Column(String(140), nullable=False)
    source_status = Column(String(64), nullable=False, default="")
    partner_name = Column(String(255), nullable=False, default="")
    amount = Column(Numeric(18, 6), nullable=False, default=0)
    currency = Column(String(32), nullable=False, default="CNY")
    status = Column(String(32), nullable=False, default="pending")
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    scenario_tag = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    submitted_by = Column(String(140), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    approved_by = Column(String(140), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(String(140), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    reject_reason = Column(String(500), nullable=True)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyFinanceApprovalOperation(Base):
    """Idempotent decision ledger for finance approval tasks."""

    __tablename__ = "ly_finance_approval_operation"
    __table_args__ = (
        Index(
            "uk_ly_finance_approval_op_idem",
            "company",
            "operation_type",
            "idempotency_key",
            unique=True,
        ),
        Index("idx_ly_finance_approval_op_task", "task_id", "operation_type", "created_at"),
        CheckConstraint(
            "operation_type IN ('approve_task','reject_task')",
            name="ck_ly_finance_approval_op_type",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生财务审批操作幂等记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    task_id = Column(IDType, ForeignKey("ly_schema.ly_finance_approval_task.id"), nullable=False)
    operation_type = Column(String(64), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    result_status = Column(String(32), nullable=False)
    result_user = Column(String(140), nullable=False)
    result_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
