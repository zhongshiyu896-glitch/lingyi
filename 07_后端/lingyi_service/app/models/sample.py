"""SQLAlchemy models for FastAPI-native sample workflow."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.audit import IDType

Base = declarative_base()


class LySampleOrder(Base):
    """Sample order header used by existing sample pages."""

    __tablename__ = "ly_sample_order"
    __table_args__ = (
        Index("uk_ly_sample_order_company_no", "company", "sample_no", unique=True),
        Index("idx_ly_sample_order_status", "company", "status"),
        Index("idx_ly_sample_order_style", "company", "style_no"),
        Index("idx_ly_sample_order_style_master", "company", "style_master_id"),
        CheckConstraint(
            "status IN ('draft','pending','patterning','fitting','sealed','reversed','converted')",
            name="ck_ly_sample_order_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ly_sample_order_progress"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样板单"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    sample_no = Column(String(140), nullable=False)
    style_no = Column(String(140), nullable=False)
    style_name = Column(String(255), nullable=False)
    style_master_id = Column(IDType, nullable=True)
    customer = Column(String(255), nullable=False)
    factory = Column(String(255), nullable=False)
    sample_type = Column(String(32), nullable=False)
    stage = Column(String(140), nullable=False, default="建档")
    progress = Column(Integer, nullable=False, default=0)
    pattern_maker = Column(String(140), nullable=False, default="")
    sample_maker = Column(String(140), nullable=False, default="")
    due_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    image_tone = Column(String(32), nullable=False, default="blue")
    owner_note = Column(Text, nullable=False, default="")
    bulk_handoff_no = Column(String(140), nullable=True)
    bulk_handoff_status = Column(String(64), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    submitted_by = Column(String(140), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reversed_by = Column(String(140), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reverse_reason = Column(Text, nullable=True)
    converted_by = Column(String(140), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)


class LySampleTrackingTemplate(Base):
    """Sample tracking template for existing template page."""

    __tablename__ = "ly_sample_tracking_template"
    __table_args__ = (
        Index("uk_ly_sample_template_company_code", "company", "template_code", unique=True),
        Index("idx_ly_sample_template_status", "company", "status"),
        CheckConstraint("status IN ('enabled','disabled')", name="ck_ly_sample_template_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样衣跟进模板"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    template_code = Column(String(140), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(140), nullable=False)
    group_name = Column(String(140), nullable=False)
    status = Column(String(32), nullable=False, default="enabled")
    owner = Column(String(140), nullable=False, default="")
    version_no = Column(String(64), nullable=False, default="V1")
    summary = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    nodes = relationship(
        "LySampleTrackingNode",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="LySampleTrackingNode.sequence_no.asc()",
    )


class LySampleTrackingNode(Base):
    """Sample tracking template node."""

    __tablename__ = "ly_sample_tracking_node"
    __table_args__ = (
        Index("idx_ly_sample_node_template", "template_id", "sequence_no"),
        CheckConstraint("status IN ('required','optional','locked')", name="ck_ly_sample_node_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样衣跟进节点"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    template_id = Column(IDType, ForeignKey("ly_schema.ly_sample_tracking_template.id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(140), nullable=False)
    lead_time = Column(String(64), nullable=False, default="")
    status = Column(String(32), nullable=False, default="required")
    gate = Column(Text, nullable=False, default="")
    output = Column(Text, nullable=False, default="")
    reminder = Column(Text, nullable=False, default="")
    sequence_no = Column(Integer, nullable=False, default=10)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    template = relationship("LySampleTrackingTemplate", back_populates="nodes")


class LySampleTrackingEvent(Base):
    """Sample-order instance tracking event."""

    __tablename__ = "ly_sample_tracking_event"
    __table_args__ = (
        Index("idx_ly_sample_event_order", "company", "sample_order_id", "happened_at"),
        Index("idx_ly_sample_event_node", "node_id"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ly_sample_event_progress"),
        CheckConstraint(
            "result IN ('pending','in_progress','done','blocked','rework')",
            name="ck_ly_sample_event_result",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生样板单实例跟进事件"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    sample_order_id = Column(IDType, ForeignKey("ly_schema.ly_sample_order.id"), nullable=False)
    template_id = Column(IDType, ForeignKey("ly_schema.ly_sample_tracking_template.id"), nullable=True)
    node_id = Column(IDType, ForeignKey("ly_schema.ly_sample_tracking_node.id"), nullable=True)
    node_name = Column(String(255), nullable=False, default="")
    stage = Column(String(140), nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    result = Column(String(32), nullable=False, default="in_progress")
    remark = Column(Text, nullable=False, default="")
    actor = Column(String(140), nullable=False)
    happened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySampleMaterialBom(Base):
    """Sample-specific material BOM snapshot."""

    __tablename__ = "ly_sample_material_bom"
    __table_args__ = (
        Index("uk_ly_sample_material_bom_order", "company", "sample_order_id", unique=True),
        Index("idx_ly_sample_material_bom_style", "company", "style_master_id"),
        CheckConstraint("status IN ('draft','active')", name="ck_ly_sample_material_bom_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样板用料BOM"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    sample_order_id = Column(IDType, ForeignKey("ly_schema.ly_sample_order.id"), nullable=False)
    style_master_id = Column(IDType, nullable=True)
    item_code = Column(String(140), nullable=False)
    source_bom_id = Column(IDType, nullable=True)
    version_no = Column(String(32), nullable=False, default="S1")
    status = Column(String(32), nullable=False, default="draft")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    items = relationship(
        "LySampleMaterialBomItem",
        back_populates="bom",
        cascade="all, delete-orphan",
        order_by="LySampleMaterialBomItem.id.asc()",
    )


class LySampleMaterialBomItem(Base):
    """Sample-specific material BOM line."""

    __tablename__ = "ly_sample_material_bom_item"
    __table_args__ = (
        Index("idx_ly_sample_material_bom_item_bom", "bom_id"),
        Index("idx_ly_sample_material_bom_item_material", "material_item_code"),
        CheckConstraint("qty_per_piece > 0", name="ck_ly_sample_material_bom_item_qty"),
        CheckConstraint("loss_rate >= 0", name="ck_ly_sample_material_bom_item_loss"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样板用料BOM明细"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    bom_id = Column(IDType, ForeignKey("ly_schema.ly_sample_material_bom.id"), nullable=False)
    source_bom_item_id = Column(IDType, nullable=True)
    material_item_code = Column(String(140), nullable=False)
    color = Column(String(64), nullable=True)
    part = Column(String(100), nullable=True)
    qty_per_piece = Column(Numeric(18, 6), nullable=False)
    loss_rate = Column(Numeric(12, 6), nullable=False, default=0)
    uom = Column(String(32), nullable=False)
    is_alternative = Column(Integer, nullable=False, default=0)
    replace_group = Column(String(64), nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    bom = relationship("LySampleMaterialBom", back_populates="items")


class LySampleMaterialBomOperation(Base):
    """Idempotency ledger for sample material BOM writes."""

    __tablename__ = "ly_sample_material_bom_operation"
    __table_args__ = (
        Index("uk_ly_sample_material_bom_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_sample_material_bom_operation_bom", "bom_id", "operation"),
        CheckConstraint("operation IN ('upsert','copy_from_style')", name="ck_ly_sample_material_bom_operation"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样板用料BOM写操作幂等账本"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    bom_id = Column(IDType, nullable=False)
    company = Column(String(140), nullable=False)
    operation = Column(String(32), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(Text, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySampleCostLine(Base):
    """Actual sample cost lines captured on a sample order."""

    __tablename__ = "ly_sample_cost_line"
    __table_args__ = (
        Index("idx_ly_sample_cost_line_order", "company", "sample_order_id"),
        Index("idx_ly_sample_cost_line_type", "company", "cost_type"),
        CheckConstraint("qty >= 0", name="ck_ly_sample_cost_line_qty"),
        CheckConstraint("unit_price >= 0", name="ck_ly_sample_cost_line_unit_price"),
        CheckConstraint("amount >= 0", name="ck_ly_sample_cost_line_amount"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样衣成本归集明细"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    sample_order_id = Column(IDType, ForeignKey("ly_schema.ly_sample_order.id"), nullable=False)
    cost_type = Column(String(64), nullable=False)
    description = Column(String(255), nullable=False, default="")
    qty = Column(Numeric(18, 6), nullable=False, default=0)
    unit_price = Column(Numeric(18, 6), nullable=False, default=0)
    amount = Column(Numeric(18, 6), nullable=False, default=0)
    occurred_date = Column(Date, nullable=True)
    remark = Column(Text, nullable=True)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LySampleCostOperation(Base):
    """Idempotency ledger for sample cost writes."""

    __tablename__ = "ly_sample_cost_operation"
    __table_args__ = (
        Index("uk_ly_sample_cost_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_sample_cost_operation_order", "sample_order_id", "operation"),
        CheckConstraint("operation IN ('upsert')", name="ck_ly_sample_cost_operation"),
        {"schema": "ly_schema", "comment": "FastAPI 原生样衣成本写操作幂等账本"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    sample_order_id = Column(IDType, nullable=False)
    company = Column(String(140), nullable=False)
    operation = Column(String(32), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(Text, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySampleIdempotency(Base):
    """Idempotency ledger for sample workflow writes."""

    __tablename__ = "ly_sample_idempotency"
    __table_args__ = (
        Index("uk_ly_sample_idem_key", "entity_type", "company", "idempotency_key", unique=True),
        CheckConstraint(
            "entity_type IN ('order','template','node','tracking_event')",
            name="ck_ly_sample_idem_entity",
        ),
        CheckConstraint(
            "operation IN ('create','update','submit','start_patterning','start_fitting','seal','reverse','convert','deactivate','create_node','delete_node','create_tracking_event')",
            name="ck_ly_sample_idem_operation",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生样衣流程幂等记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    entity_type = Column(String(32), nullable=False)
    company = Column(String(140), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    operation = Column(String(32), nullable=False)
    request_hash = Column(String(64), nullable=False)
    record_id = Column(IDType, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
