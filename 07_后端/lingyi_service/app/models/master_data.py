"""SQLAlchemy models for FastAPI-native master data records."""

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


class LyMasterDataRecord(Base):
    """FastAPI-native master data for current frontend pages."""

    __tablename__ = "ly_master_data_record"
    __table_args__ = (
        Index("uk_ly_master_data_entity_company_code", "entity_type", "company", "code", unique=True),
        Index("idx_ly_master_data_entity_company_status", "entity_type", "company", "status"),
        Index("idx_ly_master_data_entity_name", "entity_type", "name"),
        CheckConstraint(
            "entity_type IN ('customer','supplier','factory','warehouse','material','sample_type','sample_stage','common_address','trade_term','invoice_type','cost_type','size_sort','distribution_channel','bank_account')",
            name="ck_ly_master_data_entity_type",
        ),
        CheckConstraint("status IN ('active','inactive')", name="ck_ly_master_data_status"),
        {"schema": "ly_schema", "comment": "FastAPI 原生主数据记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    entity_type = Column(String(32), nullable=False)
    company = Column(String(140), nullable=False)
    code = Column(String(140), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(16), nullable=False, server_default="active")
    payload = Column(JSONType, nullable=False, default=dict)
    version = Column(Integer, nullable=False, server_default="1")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String(140), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deactivated_by = Column(String(140), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    deactivate_reason = Column(Text, nullable=True)


class LyMasterDataIdempotency(Base):
    """Idempotency ledger for master data mutations."""

    __tablename__ = "ly_master_data_idempotency"
    __table_args__ = (
        Index("uk_ly_master_data_idem_key", "entity_type", "company", "idempotency_key", unique=True),
        Index("idx_ly_master_data_idem_record", "record_id"),
        CheckConstraint(
            "operation IN ('create','update','deactivate')",
            name="ck_ly_master_data_idem_operation",
        ),
        {"schema": "ly_schema", "comment": "FastAPI 原生主数据写入幂等记录"},
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
