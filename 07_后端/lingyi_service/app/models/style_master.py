"""SQLAlchemy models for FastAPI-native style master data."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.models.audit import IDType

Base = declarative_base()
JSONType = JSON().with_variant(JSONB(), "postgresql")


class LyStyleMaster(Base):
    """Minimal style master used by sample, bulk order and BOM links."""

    __tablename__ = "ly_style_master"
    __table_args__ = (
        Index("uk_ly_style_master_company_no", "company", "ys_style_no", unique=True),
        Index("idx_ly_style_master_company_status", "company", "ys_style_status"),
        Index("idx_ly_style_master_lookup", "company", "ys_brand", "ys_year", "ys_season"),
        CheckConstraint("ys_style_status IN ('draft','enabled','disabled')", name="ck_ly_style_master_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生款式资料最小主档"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    ys_style_no = Column(String(140), nullable=False)
    ys_style_name_cn = Column(String(255), nullable=False)
    ys_season = Column(String(140), nullable=False)
    ys_year = Column(String(32), nullable=False)
    ys_brand = Column(String(140), nullable=False)
    ys_style_status = Column(String(32), nullable=False, server_default="draft")
    colors = Column(JSONType, nullable=False, default=list)
    sizes = Column(JSONType, nullable=False, default=list)
    version = Column(Integer, nullable=False, server_default="1")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    disabled_by = Column(String(140), nullable=True)
    disabled_at = Column(DateTime(timezone=True), nullable=True)
    disable_reason = Column(Text, nullable=True)


class LyStyleDictionary(Base):
    """Season/year/brand dictionary used by the minimal style master."""

    __tablename__ = "ly_style_dictionary"
    __table_args__ = (
        Index("uk_ly_style_dictionary_company_code", "dict_type", "company", "code", unique=True),
        Index("idx_ly_style_dictionary_company_type_status", "company", "dict_type", "status"),
        CheckConstraint("dict_type IN ('season','year','brand')", name="ck_ly_style_dictionary_type"),
        CheckConstraint("status IN ('active','inactive')", name="ck_ly_style_dictionary_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生款式季节/年份/品牌字典"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    dict_type = Column(String(32), nullable=False)
    code = Column(String(140), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(16), nullable=False, server_default="active")
    sort_no = Column(Integer, nullable=False, server_default="10")
    version = Column(Integer, nullable=False, server_default="1")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deactivated_by = Column(String(140), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivate_reason = Column(Text, nullable=True)


class LyStyleMasterIdempotency(Base):
    """Idempotency ledger for style master and dictionary writes."""

    __tablename__ = "ly_style_master_idempotency"
    __table_args__ = (
        Index("uk_ly_style_master_idem_key", "entity_type", "company", "idempotency_key", unique=True),
        Index("idx_ly_style_master_idem_record", "entity_type", "record_id"),
        CheckConstraint("entity_type IN ('style','dictionary')", name="ck_ly_style_master_idem_entity"),
        CheckConstraint(
            "operation IN ('create','update','deactivate')",
            name="ck_ly_style_master_idem_operation",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生款式主档幂等记录"},
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
