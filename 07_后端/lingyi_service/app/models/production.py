"""SQLAlchemy models for production planning module (TASK-004A)."""

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
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyProductionPlan(Base):
    """生产计划主表。"""

    __tablename__ = "ly_production_plan"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_plan"),
        Index("uk_ly_production_plan_no", "plan_no", unique=True),
        Index("uk_ly_production_plan_company_idempotency", "company", "idempotency_key", unique=True),
        Index("idx_ly_production_plan_company_status", "company", "status"),
        Index("idx_ly_production_plan_so_item", "sales_order", "sales_order_item"),
        Index("idx_ly_production_plan_item_status", "item_code", "status"),
        {"schema": "ly_schema", "comment": "生产计划主表"},
    )

    id = Column(IDType, autoincrement=True)
    plan_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    sales_order = Column(String(140), nullable=False)
    sales_order_item = Column(String(140), nullable=False)
    customer = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)
    bom_id = Column(BigInteger, nullable=False)
    bom_version = Column(String(64), nullable=True)
    planned_qty = Column(Numeric(18, 6), nullable=False)
    planned_start_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, server_default="planned")
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionPlanMaterial(Base):
    """生产计划物料检查快照。"""

    __tablename__ = "ly_production_plan_material"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_plan_material"),
        Index("idx_ly_production_plan_material_plan", "plan_id"),
        Index("idx_ly_production_plan_material_item", "material_item_code"),
        {"schema": "ly_schema", "comment": "生产计划物料检查快照"},
    )

    id = Column(IDType, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    bom_item_id = Column(BigInteger, nullable=True)
    material_item_code = Column(String(140), nullable=False)
    warehouse = Column(String(140), nullable=False)
    qty_per_piece = Column(Numeric(18, 6), nullable=False)
    loss_rate = Column(Numeric(12, 6), nullable=False, server_default="0")
    required_qty = Column(Numeric(18, 6), nullable=False)
    available_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    shortage_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    checked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionWorkOrderLink(Base):
    """生产计划与 ERPNext Work Order 映射。"""

    __tablename__ = "ly_production_work_order_link"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_work_order_link"),
        Index("uk_ly_production_work_order_link_work_order", "work_order", unique=True),
        Index("uk_ly_production_work_order_link_plan", "plan_id", unique=True),
        Index("idx_ly_production_work_order_link_plan", "plan_id"),
        Index("idx_ly_production_work_order_sync_status", "sync_status"),
        {"schema": "ly_schema", "comment": "生产计划 Work Order 映射"},
    )

    id = Column(IDType, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    work_order = Column(String(140), nullable=False)
    erpnext_docstatus = Column(Integer, nullable=True)
    erpnext_status = Column(String(64), nullable=True)
    sync_status = Column(String(32), nullable=False, server_default="pending")
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionWorkOrderOutbox(Base):
    """Work Order 创建 outbox。"""

    __tablename__ = "ly_production_work_order_outbox"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_work_order_outbox"),
        Index("uk_ly_production_work_order_outbox_event_key", "event_key", unique=True),
        Index("idx_ly_production_work_order_outbox_due", "action", "status", "next_retry_at", "id"),
        Index("idx_ly_production_work_order_outbox_scope", "company", "item_code", "status", "next_retry_at"),
        Index("idx_ly_production_work_order_outbox_work_order", "erpnext_work_order"),
        Index("idx_ly_production_work_order_outbox_lease", "status", "next_retry_at", "lease_until"),
        CheckConstraint("status IN ('pending','processing','succeeded','failed','dead')", name="ck_ly_production_work_order_outbox_status"),
        CheckConstraint("attempts >= 0", name="ck_ly_production_work_order_outbox_attempts"),
        CheckConstraint("max_attempts > 0", name="ck_ly_production_work_order_outbox_max_attempts"),
        {"schema": "ly_schema", "comment": "生产计划 Work Order outbox"},
    )

    id = Column(IDType, autoincrement=True)
    event_key = Column(String(140), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    company = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    action = Column(String(32), nullable=False, server_default="create_work_order")
    idempotency_key = Column(String(128), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    payload_json = Column(JSONType, nullable=False)
    status = Column(String(32), nullable=False, server_default="pending")
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="5")
    next_retry_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by = Column(String(140), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    erpnext_work_order = Column(String(140), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionJobCardLink(Base):
    """ERPNext Job Card 本地映射。"""

    __tablename__ = "ly_production_job_card_link"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_job_card_link"),
        Index("uk_ly_production_job_card_link_job_card", "job_card", unique=True),
        Index("idx_ly_production_job_card_link_plan", "plan_id"),
        Index("idx_ly_production_job_card_link_work_order", "work_order"),
        Index("idx_ly_production_job_card_company_item", "company", "item_code"),
        {"schema": "ly_schema", "comment": "生产计划 Job Card 本地映射"},
    )

    id = Column(IDType, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    work_order = Column(String(140), nullable=False)
    job_card = Column(String(140), nullable=False)
    company = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    operation = Column(String(140), nullable=True)
    operation_sequence = Column(Integer, nullable=True)
    expected_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    completed_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    erpnext_status = Column(String(64), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionStatusLog(Base):
    """生产计划状态流转日志。"""

    __tablename__ = "ly_production_status_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_status_log"),
        Index("idx_ly_production_status_log_plan_time", "plan_id", "operated_at"),
        {"schema": "ly_schema", "comment": "生产计划状态流转日志"},
    )

    id = Column(IDType, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    operator = Column(String(140), nullable=False)
    operated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request_id = Column(String(64), nullable=True)
