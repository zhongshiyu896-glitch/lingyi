"""SQLAlchemy model for quality Stock Entry outbox (TASK-030D)."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.sql import func

from app.models.quality import Base
from app.models.quality import IDType


class LyQualityOutbox(Base):
    """质量确认后的 ERPNext Stock Entry 异步出站事件。"""

    __tablename__ = "ly_quality_outbox"
    __table_args__ = (
        Index("uk_ly_quality_outbox_event_key", "event_key", unique=True),
        Index("uk_ly_quality_outbox_inspection_event", "inspection_id", "event_type", unique=True),
        Index("idx_ly_quality_outbox_due", "status", "next_retry_at", "id"),
        Index("idx_ly_quality_outbox_scope", "company", "status", "next_retry_at"),
        Index("idx_ly_quality_outbox_inspection", "inspection_id", "status", "id"),
        Index("idx_ly_quality_outbox_lease", "status", "next_retry_at", "locked_until"),
        CheckConstraint(
            "status IN ('pending','processing','succeeded','failed','dead')",
            name="ck_ly_quality_outbox_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_ly_quality_outbox_attempts_nonnegative"),
        CheckConstraint("max_attempts > 0", name="ck_ly_quality_outbox_max_attempts_positive"),
        {"schema": "ly_schema", "comment": "质量确认 Stock Entry outbox"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    inspection_id = Column(IDType, ForeignKey("ly_schema.ly_quality_inspection.id"), nullable=False)
    company = Column(String(140), nullable=False)
    event_type = Column(String(64), nullable=False, server_default="quality_stock_entry_sync")
    event_key = Column(String(140), nullable=False)
    payload_json = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)

    status = Column(String(32), nullable=False, server_default="pending")
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="3")
    next_retry_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    locked_by = Column(String(140), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)
    stock_entry_name = Column(String(140), nullable=True)

    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    succeeded_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    dead_at = Column(DateTime(timezone=True), nullable=True)
