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
        CheckConstraint("operation IN ('style_material_bom_upsert')", name="ck_ly_apparel_bom_write_operation"),
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
