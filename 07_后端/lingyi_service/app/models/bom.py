"""SQLAlchemy models for BOM module (TASK-001)."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import text as sa_text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyApparelBom(Base):
    """BOM 主表。"""

    __tablename__ = "ly_apparel_bom"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_apparel_bom"),
        Index("uk_ly_apparel_bom_bom_no", "bom_no", unique=True),
        Index("idx_ly_apparel_bom_item_default", "company", "item_code", "is_default"),
        Index("idx_ly_apparel_bom_style_master", "style_master_id"),
        Index("idx_ly_apparel_bom_status", "status"),
        Index(
            "uk_ly_apparel_bom_one_active_default",
            "company",
            "item_code",
            unique=True,
            postgresql_where=sa_text("is_default = true AND status = 'active'"),
        ),
        {"schema": "ly_schema", "comment": "BOM主表"},
    )

    id = Column(IDType, autoincrement=True)
    bom_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False, default="默认公司", server_default="默认公司")
    style_master_id = Column(BigInteger, nullable=True)
    item_code = Column(String(140), nullable=False)
    version_no = Column(String(32), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="draft")
    effective_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String(140), nullable=False, default="system")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(140), nullable=False, default="system")

    items = relationship("LyApparelBomItem", back_populates="bom", cascade="all, delete-orphan")
    operations = relationship("LyBomOperation", back_populates="bom", cascade="all, delete-orphan")


class LyApparelBomItem(Base):
    """BOM 物料明细。"""

    __tablename__ = "ly_apparel_bom_item"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_apparel_bom_item"),
        Index("idx_ly_apparel_bom_item_bom_id", "bom_id"),
        Index("idx_ly_apparel_bom_item_material", "material_item_code"),
        {"schema": "ly_schema", "comment": "BOM物料明细"},
    )

    id = Column(IDType, autoincrement=True)
    bom_id = Column(BigInteger, ForeignKey("ly_schema.ly_apparel_bom.id"), nullable=False)
    material_item_code = Column(String(140), nullable=False)
    color = Column(String(64), nullable=True)
    part = Column(String(100), nullable=True)
    size = Column(String(64), nullable=True)
    qty_per_piece = Column(Numeric(18, 6), nullable=False)
    loss_rate = Column(Numeric(12, 6), nullable=False, default=0)
    uom = Column(String(32), nullable=False)
    remark = Column(Text, nullable=True)

    bom = relationship("LyApparelBom", back_populates="items")


class LyBomOperation(Base):
    """BOM 工序明细。"""

    __tablename__ = "ly_bom_operation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_bom_operation"),
        Index("idx_ly_bom_operation_bom_process", "bom_id", "process_name"),
        Index("idx_ly_bom_operation_subcontract", "is_subcontract"),
        {"schema": "ly_schema", "comment": "BOM工序明细"},
    )

    id = Column(IDType, autoincrement=True)
    bom_id = Column(BigInteger, ForeignKey("ly_schema.ly_apparel_bom.id"), nullable=False)
    process_name = Column(String(100), nullable=False)
    sequence_no = Column(BigInteger, nullable=False)
    is_subcontract = Column(Boolean, nullable=False, default=False)
    wage_rate = Column(Numeric(18, 6), nullable=True)
    subcontract_cost_per_piece = Column(Numeric(18, 6), nullable=True)
    remark = Column(Text, nullable=True)

    bom = relationship("LyApparelBom", back_populates="operations")


class LyApparelBomWriteOperation(Base):
    """Idempotency ledger for material BOM writes."""

    __tablename__ = "ly_apparel_bom_write_operation"
    __table_args__ = (
        Index("uk_ly_apparel_bom_write_operation_idem", "company", "operation", "idempotency_key", unique=True),
        Index("idx_ly_apparel_bom_write_operation_bom", "bom_id", "operation"),
        CheckConstraint(
            "operation IN ('style_material_bom_upsert','bom:create','bom:update','bom:set_default','bom:activate','bom:deactivate')",
            name="ck_ly_apparel_bom_write_operation",
        ),
        {"schema": "ly_schema", "comment": "款式用料BOM写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True, primary_key=True)
    bom_id = Column(BigInteger, nullable=False)
    company = Column(String(140), nullable=False)
    operation = Column(String(64), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(Text, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyFoundationTemplate(Base):
    """Foundation template header for workmanship and size spec templates."""

    __tablename__ = "ly_foundation_template"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_foundation_template"),
        Index("uk_ly_foundation_template_company_type_code", "company", "template_type", "template_code", unique=True),
        Index("idx_ly_foundation_template_type_status", "template_type", "status"),
        CheckConstraint("template_type IN ('workmanship','size_spec')", name="ck_ly_foundation_template_type"),
        CheckConstraint("status IN ('active','inactive')", name="ck_ly_foundation_template_status"),
        {"schema": "ly_schema", "comment": "基础资料模板主表"},
    )

    id = Column(IDType, autoincrement=True)
    company = Column(String(140), nullable=False, default="默认公司", server_default="默认公司")
    template_type = Column(String(32), nullable=False)
    template_code = Column(String(140), nullable=False)
    name = Column(String(255), nullable=False)
    scene = Column(String(140), nullable=False, default="业务配置", server_default="业务配置")
    status = Column(String(16), nullable=False, default="active", server_default="active")
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deactivated_by = Column(String(140), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivate_reason = Column(Text, nullable=True)

    nodes = relationship("LyFoundationTemplateNode", back_populates="template", cascade="all, delete-orphan")


class LyFoundationTemplateNode(Base):
    """Foundation template node rows."""

    __tablename__ = "ly_foundation_template_node"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_foundation_template_node"),
        Index("uk_ly_foundation_template_node_code", "template_id", "code", unique=True),
        Index("idx_ly_foundation_template_node_template_sort", "template_id", "sort_no"),
        CheckConstraint("status IN ('active','inactive')", name="ck_ly_foundation_template_node_status"),
        {"schema": "ly_schema", "comment": "基础资料模板节点"},
    )

    id = Column(IDType, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("ly_schema.ly_foundation_template.id"), nullable=False)
    code = Column(String(140), nullable=False)
    name = Column(String(255), nullable=False)
    node_type = Column(String(100), nullable=False)
    required = Column(Boolean, nullable=False, default=False, server_default="false")
    status = Column(String(16), nullable=False, default="active", server_default="active")
    sort_no = Column(Integer, nullable=False, default=10, server_default="10")
    owner = Column(String(140), nullable=False, default="业务", server_default="业务")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    template = relationship("LyFoundationTemplate", back_populates="nodes")


class LyFoundationTemplateIdempotency(Base):
    """Idempotency ledger for foundation template mutations."""

    __tablename__ = "ly_foundation_template_idempotency"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_foundation_template_idempotency"),
        Index("uk_ly_foundation_template_idem_key", "entity_type", "company", "template_type", "idempotency_key", unique=True),
        CheckConstraint("entity_type IN ('template','node')", name="ck_ly_foundation_template_idem_entity"),
        CheckConstraint(
            "operation IN ('create','update','deactivate','create_node','update_node','deactivate_node')",
            name="ck_ly_foundation_template_idem_operation",
        ),
        {"schema": "ly_schema", "comment": "基础资料模板写操作幂等账本"},
    )

    id = Column(IDType, autoincrement=True)
    entity_type = Column(String(32), nullable=False)
    company = Column(String(140), nullable=False)
    template_type = Column(String(32), nullable=False)
    idempotency_key = Column(String(140), nullable=False)
    operation = Column(String(32), nullable=False)
    request_hash = Column(String(64), nullable=False)
    record_id = Column(BigInteger, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
