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
from sqlalchemy import Text
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
    uom = Column(String(32), nullable=False, server_default="米")
    qty_per_piece = Column(Numeric(18, 6), nullable=False)
    loss_rate = Column(Numeric(12, 6), nullable=False, server_default="0")
    required_qty = Column(Numeric(18, 6), nullable=False)
    available_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    shortage_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    checked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionPlanOperation(Base):
    """Idempotency ledger for production plan write operations."""

    __tablename__ = "ly_production_plan_operation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_plan_operation"),
        Index("uk_ly_production_plan_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_production_plan_operation_plan", "plan_id", "operation"),
        {"schema": "ly_schema", "comment": "生产计划写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    company = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
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


class LyProductionTrackingException(Base):
    """生产跟进异常登记事实。"""

    __tablename__ = "ly_production_tracking_exception"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_tracking_exception"),
        Index("uk_ly_production_tracking_exception_no", "exception_no", unique=True),
        Index("idx_ly_production_tracking_exception_plan", "plan_id", "created_at"),
        Index("idx_ly_production_tracking_exception_company_status", "company", "status", "severity"),
        CheckConstraint("severity IN ('low','medium','high','blocker')", name="ck_ly_production_tracking_exception_severity"),
        CheckConstraint("status IN ('open','processing','resolved','ignored')", name="ck_ly_production_tracking_exception_status"),
        {"schema": "ly_schema", "comment": "生产跟进异常登记事实"},
    )

    id = Column(IDType, autoincrement=True)
    exception_no = Column(String(64), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    company = Column(String(140), nullable=False)
    plan_no = Column(String(64), nullable=False)
    sales_order = Column(String(140), nullable=False)
    sales_order_item = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    exception_type = Column(String(64), nullable=False, server_default="progress")
    severity = Column(String(32), nullable=False, server_default="medium")
    status = Column(String(32), nullable=False, server_default="open")
    description = Column(String(1000), nullable=False)
    owner = Column(String(140), nullable=False, server_default="")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionFollowupTemplate(Base):
    """FastAPI-native production follow-up template used by the existing template page."""

    __tablename__ = "ly_production_followup_template"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_followup_template"),
        Index("uk_ly_production_followup_template_no", "company", "template_no", unique=True),
        Index("idx_ly_production_followup_template_status", "company", "status"),
        Index("idx_ly_production_followup_template_item", "company", "item_code"),
        CheckConstraint("status IN ('enabled','disabled')", name="ck_ly_production_followup_template_status"),
        CheckConstraint("sla_hours >= 0", name="ck_ly_production_followup_template_sla_hours"),
        {"schema": "ly_schema", "comment": "FastAPI 原生大货跟进模板"},
    )

    id = Column(IDType, autoincrement=True)
    company = Column(String(140), nullable=False)
    template_no = Column(String(140), nullable=False)
    template_name = Column(String(255), nullable=False)
    template_type = Column(String(140), nullable=False, server_default="基础跟进")
    trigger_node = Column(String(140), nullable=False, server_default="制单草稿")
    followup_role = Column(String(140), nullable=False, server_default="业务跟单")
    followup_frequency = Column(String(64), nullable=False, server_default="每日")
    sla_hours = Column(Integer, nullable=False, server_default="24")
    item_code = Column(String(140), nullable=False, server_default="")
    status = Column(String(32), nullable=False, server_default="enabled")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionFollowupTemplateNode(Base):
    """FastAPI-native production follow-up template node."""

    __tablename__ = "ly_production_followup_template_node"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_followup_template_node"),
        Index("idx_ly_production_followup_template_node_template", "template_id", "sequence_no"),
        Index("idx_ly_production_followup_template_node_company", "company", "template_id"),
        CheckConstraint("status IN ('required','optional','locked')", name="ck_ly_production_followup_template_node_status"),
        CheckConstraint("lead_time_hours >= 0", name="ck_ly_production_followup_template_node_lead_time"),
        CheckConstraint("sequence_no >= 0", name="ck_ly_production_followup_template_node_sequence"),
        {"schema": "ly_schema", "comment": "FastAPI 原生大货跟进模板节点"},
    )

    id = Column(IDType, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_followup_template.id"), nullable=False)
    company = Column(String(140), nullable=False)
    node_name = Column(String(255), nullable=False)
    owner = Column(String(140), nullable=False, server_default="")
    lead_time_hours = Column(Integer, nullable=False, server_default="0")
    status = Column(String(32), nullable=False, server_default="required")
    gate = Column(Text, nullable=False, server_default="")
    output = Column(Text, nullable=False, server_default="")
    reminder = Column(Text, nullable=False, server_default="")
    sequence_no = Column(Integer, nullable=False, server_default="10")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionFollowupTemplateOperation(Base):
    """Idempotency ledger for production follow-up template writes."""

    __tablename__ = "ly_production_followup_template_operation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_followup_template_operation"),
        Index("uk_ly_production_followup_template_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_production_followup_template_operation_template", "template_id", "operation"),
        CheckConstraint(
            "operation IN ('create','update','copy','deactivate')",
            name="ck_ly_production_followup_template_operation",
        ),
        {"schema": "ly_schema", "comment": "大货跟进模板写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_followup_template.id"), nullable=True)
    company = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionFollowupTemplateNodeOperation(Base):
    """Idempotency ledger for production follow-up template node writes."""

    __tablename__ = "ly_production_followup_template_node_operation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_followup_template_node_operation"),
        Index("uk_ly_production_followup_template_node_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_production_followup_template_node_operation_node", "node_id", "operation"),
        CheckConstraint(
            "operation IN ('create_node','update_node','delete_node')",
            name="ck_ly_production_followup_template_node_operation",
        ),
        {"schema": "ly_schema", "comment": "大货跟进模板节点写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_followup_template.id"), nullable=False)
    node_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_followup_template_node.id"), nullable=True)
    company = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionQuote(Base):
    """FastAPI-native production quote saved from the existing quote page."""

    __tablename__ = "ly_production_quote"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_quote"),
        Index("uk_ly_production_quote_no", "company", "quote_no", unique=True),
        Index("idx_ly_production_quote_plan", "plan_id", "status"),
        Index("idx_ly_production_quote_company_status", "company", "status"),
        Index("idx_ly_production_quote_item", "company", "item_code"),
        CheckConstraint("quote_qty >= 0", name="ck_ly_production_quote_qty_nonnegative"),
        CheckConstraint("material_cost >= 0", name="ck_ly_production_quote_material_nonnegative"),
        CheckConstraint("labor_cost >= 0", name="ck_ly_production_quote_labor_nonnegative"),
        CheckConstraint("management_fee >= 0", name="ck_ly_production_quote_management_nonnegative"),
        CheckConstraint("quote_amount >= 0", name="ck_ly_production_quote_amount_nonnegative"),
        CheckConstraint("status IN ('draft','pricing','quoted','converted','void')", name="ck_ly_production_quote_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生报价单"},
    )

    id = Column(IDType, autoincrement=True)
    quote_no = Column(String(140), nullable=False)
    company = Column(String(140), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_plan.id"), nullable=False)
    plan_no = Column(String(64), nullable=False)
    sales_order = Column(String(140), nullable=False)
    sales_order_item = Column(String(140), nullable=False)
    customer = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)
    quote_qty = Column(Numeric(18, 6), nullable=False)
    material_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    labor_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    management_fee = Column(Numeric(18, 6), nullable=False, server_default="0")
    quote_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    currency = Column(String(16), nullable=False, server_default="CNY")
    valid_until = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, server_default="draft")
    remark = Column(String(500), nullable=False, server_default="")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyProductionQuoteOperation(Base):
    """Idempotency ledger for production quote writes."""

    __tablename__ = "ly_production_quote_operation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_quote_operation"),
        Index("uk_ly_production_quote_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_production_quote_operation_quote", "quote_id", "operation"),
        CheckConstraint("operation IN ('create','convert','copy','void')", name="ck_ly_production_quote_operation"),
        {"schema": "ly_schema", "comment": "报价单写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True)
    quote_id = Column(BigInteger, ForeignKey("ly_schema.ly_production_quote.id"), nullable=True)
    company = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSONType, nullable=False, default=dict)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionTrackingReconcileBatch(Base):
    """样板单到大货订单对账生成批次。"""

    __tablename__ = "ly_production_tracking_reconcile_batch"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_tracking_reconcile_batch"),
        Index("uk_ly_production_tracking_reconcile_batch_no", "batch_no", unique=True),
        Index("uk_ly_production_tracking_reconcile_batch_idem", "company", "idempotency_key", unique=True),
        Index("idx_ly_production_tracking_reconcile_batch_company_time", "company", "created_at"),
        {"schema": "ly_schema", "comment": "样板单到大货订单对账生成批次"},
    )

    id = Column(IDType, autoincrement=True)
    batch_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    created_count = Column(Integer, nullable=False, server_default="0")
    updated_count = Column(Integer, nullable=False, server_default="0")
    matched_count = Column(Integer, nullable=False, server_default="0")
    unmatched_count = Column(Integer, nullable=False, server_default="0")
    response_json = Column(JSONType, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyProductionTrackingReconcile(Base):
    """样板单到大货订单对账快照。"""

    __tablename__ = "ly_production_tracking_reconcile"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_production_tracking_reconcile"),
        Index("uk_ly_production_tracking_reconcile_no", "reconcile_no", unique=True),
        Index("uk_ly_production_tracking_reconcile_sample", "company", "sample_no", unique=True),
        Index("idx_ly_production_tracking_reconcile_company_status", "company", "diff_status"),
        Index("idx_ly_production_tracking_reconcile_customer", "company", "customer"),
        Index("idx_ly_production_tracking_reconcile_sales_order", "company", "sales_order"),
        Index("idx_ly_production_tracking_reconcile_batch", "batch_no"),
        CheckConstraint(
            "diff_status IN ('matched','unmatched','quantity_diff','price_diff','late_order')",
            name="ck_ly_production_tracking_reconcile_diff_status",
        ),
        CheckConstraint("sample_qty >= 0", name="ck_ly_production_tracking_reconcile_sample_qty_nonnegative"),
        CheckConstraint("order_qty >= 0", name="ck_ly_production_tracking_reconcile_order_qty_nonnegative"),
        CheckConstraint("sample_price >= 0", name="ck_ly_production_tracking_reconcile_sample_price_nonnegative"),
        CheckConstraint("unit_price >= 0", name="ck_ly_production_tracking_reconcile_unit_price_nonnegative"),
        {"schema": "ly_schema", "comment": "样板单到大货订单对账快照"},
    )

    id = Column(IDType, autoincrement=True)
    reconcile_no = Column(String(64), nullable=False)
    batch_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    sample_order_id = Column(BigInteger, nullable=False)
    sample_no = Column(String(140), nullable=False)
    style_no = Column(String(140), nullable=False)
    style_name = Column(String(255), nullable=False)
    image_tone = Column(String(32), nullable=False, server_default="gray")
    customer = Column(String(255), nullable=False)
    sample_type = Column(String(32), nullable=False)
    sealed_date = Column(Date, nullable=True)
    sales_order = Column(String(140), nullable=False, server_default="")
    sales_order_id = Column(BigInteger, nullable=True)
    sales_order_item_id = Column(BigInteger, nullable=True)
    sample_qty = Column(Numeric(18, 6), nullable=False, server_default="1")
    order_qty = Column(Numeric(18, 6), nullable=False, server_default="0")
    sample_price = Column(Numeric(18, 6), nullable=False, server_default="0")
    unit_price = Column(Numeric(18, 6), nullable=False, server_default="0")
    diff_status = Column(String(32), nullable=False)
    remark = Column(String(500), nullable=False, server_default="")
    owner = Column(String(140), nullable=False, server_default="")
    source_hash = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
