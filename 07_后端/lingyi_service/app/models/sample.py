"""SQLAlchemy models for FastAPI-native sample workflow."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
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


class LySampleIdempotency(Base):
    """Idempotency ledger for sample workflow writes."""

    __tablename__ = "ly_sample_idempotency"
    __table_args__ = (
        Index("uk_ly_sample_idem_key", "entity_type", "company", "idempotency_key", unique=True),
        CheckConstraint(
            "entity_type IN ('order','template','node')",
            name="ck_ly_sample_idem_entity",
        ),
        CheckConstraint(
            "operation IN ('create','update','submit','start_patterning','start_fitting','seal','reverse','convert','deactivate','create_node','delete_node')",
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
