"""SQLAlchemy models for warehouse stock-entry and inventory-count baselines."""

from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.sql import func

from app.models.quality import Base
from app.models.quality import IDType


class LyWarehouseStockEntryDraft(Base):
    """Warehouse stock-entry draft header."""

    __tablename__ = "ly_warehouse_stock_entry_draft"
    __table_args__ = (
        Index("uk_ly_whse_stock_entry_draft_event_key", "event_key", unique=True),
        Index("uk_ly_whse_stock_entry_draft_company_idempotency", "company", "idempotency_key", unique=True),
        Index(
            "uk_ly_whse_stock_entry_draft_company_source",
            "company",
            "source_type",
            "source_id",
            "status",
            unique=True,
        ),
        Index("idx_ly_whse_stock_entry_draft_company_status", "company", "status"),
        CheckConstraint(
            "status IN ('draft','pending_outbox','cancelled')",
            name="ck_ly_whse_stock_entry_draft_status",
        ),
        CheckConstraint(
            "purpose IN ('Material Issue','Material Receipt','Material Transfer')",
            name="ck_ly_whse_stock_entry_draft_purpose",
        ),
        {"schema": "ly_schema", "comment": "仓库 Stock Entry 草稿主表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    purpose = Column(String(64), nullable=False)
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(140), nullable=False)
    source_warehouse = Column(String(140), nullable=True)
    target_warehouse = Column(String(140), nullable=True)
    status = Column(String(32), nullable=False, server_default="draft")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(255), nullable=True)
    idempotency_key = Column(String(140), nullable=False)
    event_key = Column(String(140), nullable=False)


class LyWarehouseStockEntryDraftItem(Base):
    """Warehouse stock-entry draft item rows."""

    __tablename__ = "ly_warehouse_stock_entry_draft_item"
    __table_args__ = (
        Index("idx_ly_whse_stock_entry_item_draft", "draft_id"),
        Index("idx_ly_whse_stock_entry_item_company_item", "company", "item_code"),
        CheckConstraint("qty > 0", name="ck_ly_whse_stock_entry_item_qty_positive"),
        {"schema": "ly_schema", "comment": "仓库 Stock Entry 草稿明细表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    draft_id = Column(IDType, ForeignKey("ly_schema.ly_warehouse_stock_entry_draft.id"), nullable=False)
    company = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    qty = Column(Numeric(18, 6), nullable=False)
    uom = Column(String(32), nullable=False)
    batch_no = Column(String(140), nullable=True)
    serial_no = Column(String(500), nullable=True)
    source_warehouse = Column(String(140), nullable=True)
    target_warehouse = Column(String(140), nullable=True)


class LyWarehouseStockEntryOutboxEvent(Base):
    """Warehouse stock-entry draft outbox events."""

    __tablename__ = "ly_warehouse_stock_entry_outbox_event"
    __table_args__ = (
        Index("uk_ly_whse_stock_entry_outbox_event_key", "event_key", unique=True),
        Index("idx_ly_whse_stock_entry_outbox_draft", "draft_id"),
        Index("idx_ly_whse_stock_entry_outbox_status", "status", "retry_count", "id"),
        CheckConstraint(
            "status IN ('in_pending','processing','succeeded','failed','dead','cancelled')",
            name="ck_ly_whse_stock_entry_outbox_status",
        ),
        CheckConstraint("retry_count >= 0", name="ck_ly_whse_stock_entry_outbox_retry_count_nonnegative"),
        {"schema": "ly_schema", "comment": "仓库 Stock Entry 草稿 Outbox"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    draft_id = Column(IDType, ForeignKey("ly_schema.ly_warehouse_stock_entry_draft.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    event_key = Column(String(140), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, server_default="in_pending")
    retry_count = Column(Integer, nullable=False, server_default="0")
    external_ref = Column(String(140), nullable=True)
    error_message = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class LyWarehouseInventoryCount(Base):
    """Warehouse inventory-count header."""

    __tablename__ = "ly_warehouse_inventory_count"
    __table_args__ = (
        Index("uk_ly_whse_inv_count_company_count_no", "company", "count_no", unique=True),
        Index("idx_ly_whse_inv_count_company_warehouse", "company", "warehouse"),
        Index("idx_ly_whse_inv_count_status_date", "status", "count_date", "id"),
        CheckConstraint(
            "status IN ('draft','counted','variance_review','confirmed','cancelled')",
            name="ck_ly_whse_inv_count_status",
        ),
        {"schema": "ly_schema", "comment": "仓库库存盘点主表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    company = Column(String(140), nullable=False)
    warehouse = Column(String(140), nullable=False)
    status = Column(String(32), nullable=False, server_default="draft")
    count_no = Column(String(140), nullable=False)
    count_date = Column(Date, nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    submitted_by = Column(String(140), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(140), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(255), nullable=True)
    remark = Column(String(500), nullable=True)


class LyWarehouseInventoryCountItem(Base):
    """Warehouse inventory-count line rows."""

    __tablename__ = "ly_warehouse_inventory_count_item"
    __table_args__ = (
        Index("idx_ly_whse_inv_count_item_count_id", "count_id"),
        Index("idx_ly_whse_inv_count_item_company_wh_item", "company", "warehouse", "item_code"),
        CheckConstraint("system_qty >= 0", name="ck_ly_whse_inv_count_item_system_qty_nonnegative"),
        CheckConstraint("counted_qty >= 0", name="ck_ly_whse_inv_count_item_counted_qty_nonnegative"),
        CheckConstraint(
            "review_status IN ('pending','accepted','rejected')",
            name="ck_ly_whse_inv_count_item_review_status",
        ),
        {"schema": "ly_schema", "comment": "仓库库存盘点明细表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    count_id = Column(IDType, ForeignKey("ly_schema.ly_warehouse_inventory_count.id"), nullable=False)
    company = Column(String(140), nullable=False)
    warehouse = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    batch_no = Column(String(140), nullable=True)
    serial_no = Column(String(500), nullable=True)
    system_qty = Column(Numeric(18, 6), nullable=False)
    counted_qty = Column(Numeric(18, 6), nullable=False)
    variance_qty = Column(Numeric(18, 6), nullable=False)
    variance_reason = Column(String(255), nullable=True)
    review_status = Column(String(32), nullable=False, server_default="pending")
