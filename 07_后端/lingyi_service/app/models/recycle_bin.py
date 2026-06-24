"""Unified recycle-bin rows for recoverable deletes."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.models.audit import IDType

Base = declarative_base()
JSONType = JSON().with_variant(JSONB(), "postgresql")


class LyRecycleBinItem(Base):
    """Recoverable deletion snapshot for FastAPI-native data."""

    __tablename__ = "ly_recycle_bin_item"
    __table_args__ = (
        Index("idx_ly_recycle_bin_status_deleted", "status", "deleted_at"),
        Index("idx_ly_recycle_bin_module_entity", "module", "entity_type", "status"),
        Index("idx_ly_recycle_bin_company", "company", "status"),
        CheckConstraint("status IN ('deleted','restored')", name="ck_ly_recycle_bin_status"),
        {"schema": "ly_schema", "comment": "统一回收站：可恢复删除快照"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    module = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_path = Column(String(140), nullable=True)
    original_id = Column(IDType, nullable=False)
    company = Column(String(140), nullable=True)
    code = Column(String(140), nullable=True)
    name = Column(String(255), nullable=True)
    snapshot = Column(JSONType, nullable=False, default=dict)
    details = Column(JSONType, nullable=False, default=dict)
    status = Column(String(16), nullable=False, server_default="deleted")
    deleted_by = Column(String(140), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    restored_by = Column(String(140), nullable=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, server_default="1")
