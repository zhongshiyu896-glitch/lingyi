"""SQLAlchemy models for workshop ticket module (TASK-003)."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class YsWorkshopTicket(Base):
    """车间工票明细事实表。"""

    __tablename__ = "ys_workshop_ticket"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ys_workshop_ticket"),
        Index("uk_ys_workshop_ticket_no", "ticket_no", unique=True),
        Index(
            "uk_ys_workshop_ticket_idempotent",
            "ticket_key",
            "process_name",
            "color",
            "size",
            "operation_type",
            "work_date",
            unique=True,
        ),
        Index("idx_ys_workshop_ticket_employee_date", "employee", "work_date"),
        Index("idx_ys_workshop_ticket_job_card", "job_card"),
        Index("idx_ys_workshop_ticket_item_process", "item_code", "process_name"),
        Index("idx_ys_workshop_ticket_sync_status", "sync_status"),
        CheckConstraint("operation_type IN ('register', 'reversal')", name="ck_ys_workshop_ticket_operation_type"),
        CheckConstraint("qty > 0", name="ck_ys_workshop_ticket_qty"),
        CheckConstraint("unit_wage >= 0", name="ck_ys_workshop_ticket_unit_wage"),
        {"schema": "ly_schema", "comment": "车间工票明细事实表"},
    )

    id = Column(IDType, autoincrement=True)
    ticket_no = Column(String(64), nullable=False)
    ticket_key = Column(String(128), nullable=False)
    job_card = Column(String(140), nullable=False)
    work_order = Column(String(140), nullable=True)
    bom_id = Column(BigInteger, nullable=True)
    item_code = Column(String(140), nullable=False)
    employee = Column(String(140), nullable=False)
    process_name = Column(String(100), nullable=False)
    color = Column(String(64), nullable=True)
    size = Column(String(64), nullable=True)
    operation_type = Column(String(16), nullable=False)
    qty = Column(Numeric(18, 6), nullable=False)
    unit_wage = Column(Numeric(18, 6), nullable=False)
    wage_amount = Column(Numeric(18, 6), nullable=False)
    work_date = Column(Date, nullable=False)
    source = Column(String(32), nullable=False)
    source_ref = Column(String(140), nullable=True)
    original_ticket_id = Column(BigInteger, nullable=True)
    sync_status = Column(String(32), nullable=False, server_default="pending")
    sync_error_code = Column(String(64), nullable=True)
    sync_error_message = Column(String(255), nullable=True)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class YsWorkshopDailyWage(Base):
    """员工日薪汇总表。"""

    __tablename__ = "ys_workshop_daily_wage"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ys_workshop_daily_wage"),
        Index(
            "uk_ys_workshop_daily_wage_emp_date_process_item",
            "employee",
            "work_date",
            "process_name",
            "item_code",
            unique=True,
        ),
        Index("idx_ys_workshop_daily_wage_work_date", "work_date"),
        Index("idx_ys_workshop_daily_wage_employee", "employee"),
        {"schema": "ly_schema", "comment": "员工日薪汇总表"},
    )

    id = Column(IDType, autoincrement=True)
    employee = Column(String(140), nullable=False)
    work_date = Column(Date, nullable=False)
    process_name = Column(String(100), nullable=False)
    item_code = Column(String(140), nullable=True)
    register_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    reversal_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    net_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    wage_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    last_ticket_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyOperationWageRate(Base):
    """工价档案。"""

    __tablename__ = "ly_operation_wage_rate"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_operation_wage_rate"),
        Index("idx_ly_operation_wage_rate_item_process", "item_code", "process_name"),
        Index("idx_ly_operation_wage_rate_effective", "effective_from", "effective_to"),
        Index("idx_ly_operation_wage_rate_company_item_process", "company", "item_code", "process_name"),
        Index("idx_ly_operation_wage_rate_company_status", "company", "status"),
        Index("idx_ly_operation_wage_rate_global", "is_global", "status"),
        CheckConstraint("wage_rate >= 0", name="ck_ly_operation_wage_rate"),
        {"schema": "ly_schema", "comment": "工价档案"},
    )

    id = Column(IDType, autoincrement=True)
    item_code = Column(String(140), nullable=True)
    company = Column(String(140), nullable=True)
    is_global = Column(Boolean, nullable=False, server_default="false")
    process_name = Column(String(100), nullable=False)
    wage_rate = Column(Numeric(18, 6), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, server_default="active")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyOperationWageRateCompanyBackfillLog(Base):
    """历史工价 company 补数日志。"""

    __tablename__ = "ly_operation_wage_rate_company_backfill_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_operation_wage_rate_company_backfill_log"),
        Index("idx_ly_operation_wage_rate_backfill_wage_rate", "wage_rate_id"),
        Index("idx_ly_operation_wage_rate_backfill_result", "result"),
        Index(
            "uk_ly_operation_wage_rate_backfill_once",
            "wage_rate_id",
            "result",
            "new_company",
            "reason",
            unique=True,
        ),
        {"schema": "ly_schema", "comment": "历史工价 company 补数日志"},
    )

    id = Column(IDType, autoincrement=True)
    wage_rate_id = Column(BigInteger, nullable=False)
    item_code = Column(String(140), nullable=False)
    old_company = Column(String(140), nullable=True)
    new_company = Column(String(140), nullable=True)
    result = Column(String(32), nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class YsWorkshopJobCardSyncOutbox(Base):
    """Job Card 同步 outbox 最终待办状态。"""

    __tablename__ = "ys_workshop_job_card_sync_outbox"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ys_workshop_job_card_sync_outbox"),
        Index("uk_ys_workshop_job_card_sync_outbox_event_key", "event_key", unique=True),
        Index("idx_ys_workshop_job_card_sync_outbox_status_retry", "status", "next_retry_at"),
        Index("idx_ys_workshop_job_card_sync_outbox_job_card", "job_card"),
        Index("idx_ys_workshop_job_card_sync_outbox_company_item", "company", "item_code"),
        Index(
            "idx_ys_workshop_job_card_sync_outbox_scope_status_retry",
            "company",
            "item_code",
            "status",
            "next_retry_at",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed', 'dead')",
            name="ck_ys_workshop_job_card_sync_outbox_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_ys_workshop_job_card_sync_outbox_attempts"),
        CheckConstraint("max_attempts > 0", name="ck_ys_workshop_job_card_sync_outbox_max_attempts"),
        {"schema": "ly_schema", "comment": "Job Card 同步 outbox"},
    )

    id = Column(IDType, autoincrement=True)
    event_key = Column(String(140), nullable=False)
    job_card = Column(String(140), nullable=False)
    work_order = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)
    company = Column(String(140), nullable=False)
    local_completed_qty = Column(Numeric(18, 6), nullable=False)
    source_type = Column(String(32), nullable=False)
    source_ids = Column(JSONType, nullable=False)
    status = Column(String(32), nullable=False, server_default="pending")
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="5")
    next_retry_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by = Column(String(140), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class YsWorkshopOutboxAccessDenial(Base):
    """Per-principal outbox denial throttle and dedupe state."""

    __tablename__ = "ys_workshop_outbox_access_denial"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ys_workshop_outbox_access_denial"),
        Index(
            "uk_ys_workshop_outbox_access_denial_outbox_principal_reason_scope",
            "outbox_id",
            "principal",
            "reason_code",
            "scope_hash",
            unique=True,
        ),
        Index("idx_ys_workshop_outbox_access_denial_next_audit_at", "next_audit_at"),
        {"schema": "ly_schema", "comment": "Outbox 资源拒绝诊断去重与节流记录"},
    )

    id = Column(IDType, autoincrement=True)
    outbox_id = Column(BigInteger, nullable=False)
    principal = Column(String(140), nullable=False)
    reason_code = Column(String(64), nullable=False)
    scope_hash = Column(String(64), nullable=False)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_audit_at = Column(DateTime(timezone=True), nullable=True)
    next_audit_at = Column(DateTime(timezone=True), nullable=True)
    seen_count = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class YsWorkshopJobCardSyncLog(Base):
    """Job Card 同步日志。"""

    __tablename__ = "ys_workshop_job_card_sync_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ys_workshop_job_card_sync_log"),
        Index("idx_ys_workshop_job_card_sync_log_outbox_id", "outbox_id"),
        Index("idx_ys_workshop_job_card_sync_log_job_card", "job_card"),
        Index("idx_ys_workshop_job_card_sync_log_status", "erpnext_status"),
        Index("idx_ys_workshop_job_card_sync_log_created_at", "created_at"),
        {"schema": "ly_schema", "comment": "Job Card 同步日志"},
    )

    id = Column(IDType, autoincrement=True)
    outbox_id = Column(BigInteger, nullable=True)
    attempt_no = Column(Integer, nullable=False, server_default="1")
    job_card = Column(String(140), nullable=False)
    sync_type = Column(String(32), nullable=False)
    local_completed_qty = Column(Numeric(18, 6), nullable=False)
    erpnext_status = Column(String(32), nullable=False)
    erpnext_response = Column(JSONType, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
