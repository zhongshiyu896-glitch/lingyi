"""SQLAlchemy models for subcontract module (TASK-002)."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class LySubcontractOrder(Base):
    """外发加工单。"""

    __tablename__ = "ly_subcontract_order"
    __table_args__ = (
        Index("uk_subcontract_no", "subcontract_no", unique=True),
        Index("idx_supplier_status", "supplier", "status"),
        Index("idx_item_code", "item_code"),
        Index("idx_ly_subcontract_company_status", "company", "status"),
        Index("idx_ly_subcontract_company_supplier_status", "company", "supplier", "status"),
        Index("idx_ly_subcontract_company_item_status", "company", "item_code", "status"),
        {"schema": "ly_schema", "comment": "外发加工单"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_no = Column(String(64), nullable=False)
    supplier = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=False)
    company = Column(String(140), nullable=True)
    bom_id = Column(BigInteger, ForeignKey("ly_schema.ly_apparel_bom.id"), nullable=False)
    process_name = Column(String(100), nullable=False)
    planned_qty = Column(Numeric(18, 6), nullable=False)
    subcontract_rate = Column(Numeric(18, 6), nullable=False, default=0)
    issued_qty = Column(Numeric(18, 6), nullable=False, default=0)
    received_qty = Column(Numeric(18, 6), nullable=False, default=0)
    inspected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    gross_amount = Column(Numeric(18, 6), nullable=False, default=0)
    deduction_amount = Column(Numeric(18, 6), nullable=False, default=0)
    net_amount = Column(Numeric(18, 6), nullable=False, default=0)
    status = Column(String(32), nullable=False, default="draft")
    settlement_status = Column(String(32), nullable=False, default="unsettled")
    resource_scope_status = Column(String(32), nullable=False, default="ready")
    scope_error_code = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LySubcontractMaterial(Base):
    """外发发料明细。"""

    __tablename__ = "ly_subcontract_material"
    __table_args__ = (
        Index("idx_subcontract_id", "subcontract_id"),
        Index("idx_stock_entry", "stock_entry_name"),
        Index("idx_ly_subcontract_material_outbox", "stock_outbox_id"),
        Index("idx_ly_subcontract_material_company_order", "company", "subcontract_id"),
        {"schema": "ly_schema", "comment": "外发发料明细"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    stock_outbox_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_stock_outbox.id"), nullable=True)
    company = Column(String(140), nullable=True)
    issue_batch_no = Column(String(64), nullable=True)
    material_item_code = Column(String(140), nullable=False)
    required_qty = Column(Numeric(18, 6), nullable=False)
    issued_qty = Column(Numeric(18, 6), nullable=False)
    sync_status = Column(String(32), nullable=False, default="pending")
    stock_entry_name = Column(String(140), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySubcontractReceipt(Base):
    """外发回料事实。"""

    __tablename__ = "ly_subcontract_receipt"
    __table_args__ = (
        Index("idx_subcontract_receipt_subcontract_id", "subcontract_id"),
        Index("idx_inspect_status", "inspect_status"),
        Index("idx_ly_subcontract_receipt_company_order", "company", "subcontract_id"),
        Index("idx_ly_subcontract_receipt_outbox", "stock_outbox_id"),
        Index("idx_ly_subcontract_receipt_idempotency", "subcontract_id", "idempotency_key"),
        {"schema": "ly_schema", "comment": "外发回料验货"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    stock_outbox_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_stock_outbox.id"), nullable=True)
    company = Column(String(140), nullable=True)
    receipt_batch_no = Column(String(64), nullable=True)
    receipt_warehouse = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=True)
    color = Column(String(64), nullable=True)
    size = Column(String(64), nullable=True)
    batch_no = Column(String(140), nullable=True)
    uom = Column(String(32), nullable=True)
    received_qty = Column(Numeric(18, 6), nullable=False)
    sync_status = Column(String(32), nullable=False, default="pending")
    sync_error_code = Column(String(64), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    received_by = Column(String(140), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    stock_entry_name = Column(String(140), nullable=True)
    inspected_qty = Column(Numeric(18, 6), nullable=False)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_rate = Column(Numeric(10, 6), nullable=False, default=0)
    deduction_amount = Column(Numeric(18, 6), nullable=False, default=0)
    net_amount = Column(Numeric(18, 6), nullable=False, default=0)
    inspect_status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySubcontractStatusLog(Base):
    """外发状态日志。"""

    __tablename__ = "ly_subcontract_status_log"
    __table_args__ = (
        Index("idx_subcontract_time", "subcontract_id", "operated_at"),
        Index("idx_ly_subcontract_status_log_company_order", "company", "subcontract_id", "operated_at"),
        {"schema": "ly_schema", "comment": "外发状态日志"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    company = Column(String(140), nullable=True)
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    operator = Column(String(140), nullable=False)
    operated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySubcontractInspection(Base):
    """外发验货记录。"""

    __tablename__ = "ly_subcontract_inspection"
    __table_args__ = (
        Index("idx_ly_subcontract_inspection_subcontract_id", "subcontract_id"),
        Index("idx_ly_subcontract_inspection_company_order", "company", "subcontract_id", "created_at"),
        Index("idx_ly_subcontract_inspection_receipt_batch", "receipt_batch_no"),
        Index("idx_ly_subcontract_inspection_batch", "company", "subcontract_id", "receipt_batch_no"),
        Index(
            "idx_ly_subcontract_inspection_settlement_status",
            "settlement_status",
            "inspected_at",
            "id",
        ),
        Index(
            "idx_ly_subcontract_inspection_statement",
            "statement_id",
            "settlement_status",
        ),
        UniqueConstraint("company", "inspection_no", name="uk_ly_subcontract_inspection_no"),
        UniqueConstraint("subcontract_id", "idempotency_key", name="uk_ly_subcontract_inspection_idempotency"),
        UniqueConstraint("settlement_line_key", name="uk_ly_subcontract_inspection_settlement_line_key"),
        {"schema": "ly_schema", "comment": "外发验货记录"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    company = Column(String(140), nullable=True)
    inspection_no = Column(String(64), nullable=True)
    receipt_batch_no = Column(String(64), nullable=True)
    receipt_warehouse = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=True)
    inspected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_rate = Column(Numeric(10, 6), nullable=False, default=0)
    subcontract_rate = Column(Numeric(18, 6), nullable=False, default=0)
    gross_amount = Column(Numeric(18, 6), nullable=False, default=0)
    deduction_amount_per_piece = Column(Numeric(18, 6), nullable=False, default=0)
    deduction_amount = Column(Numeric(18, 6), nullable=False, default=0)
    net_amount = Column(Numeric(18, 6), nullable=False, default=0)
    settlement_status = Column(String(32), nullable=False, default="unsettled")
    statement_id = Column(BigInteger, nullable=True)
    statement_no = Column(String(64), nullable=True)
    settlement_line_key = Column(String(128), nullable=True)
    settlement_locked_by = Column(String(140), nullable=True)
    settlement_locked_at = Column(DateTime(timezone=True), nullable=True)
    settled_by = Column(String(140), nullable=True)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    # Compatibility-only latest request marker; full idempotency history is in ly_subcontract_settlement_operation.
    settlement_request_id = Column(String(128), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    inspected_by = Column(String(140), nullable=True)
    inspected_at = Column(DateTime(timezone=True), nullable=True)
    request_id = Column(String(64), nullable=True)
    remark = Column(String(200), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LySubcontractStockOutbox(Base):
    """外发库存同步 outbox。"""

    __tablename__ = "ly_subcontract_stock_outbox"
    __table_args__ = (
        Index("uk_ly_subcontract_stock_outbox_event_key", "event_key", unique=True),
        Index(
            "uk_ly_subcontract_stock_outbox_idempotency",
            "subcontract_id",
            "stock_action",
            "idempotency_key",
            unique=True,
        ),
        Index("idx_ly_subcontract_outbox_due", "stock_action", "status", "next_retry_at", "id"),
        Index("idx_ly_subcontract_outbox_stock_entry", "stock_entry_name"),
        Index("idx_ly_subcontract_outbox_company_status", "company", "status", "next_retry_at"),
        Index(
            "idx_ly_subcontract_outbox_scope",
            "company",
            "supplier",
            "item_code",
            "warehouse",
            "stock_action",
            "status",
            "next_retry_at",
        ),
        {"schema": "ly_schema", "comment": "外发库存同步 outbox"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    event_key = Column(String(140), nullable=True)
    stock_action = Column(String(32), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    payload_hash = Column(String(64), nullable=True)
    payload_json = Column(JSON, nullable=True)
    company = Column(String(140), nullable=True)
    supplier = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=True)
    warehouse = Column(String(140), nullable=True)
    action = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    payload = Column(JSON, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    next_retry_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by = Column(String(140), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    stock_entry_name = Column(String(140), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LySubcontractSettlementOperation(Base):
    """外发结算锁定/释放幂等操作日志（append-only）。"""

    __tablename__ = "ly_subcontract_settlement_operation"
    __table_args__ = (
        UniqueConstraint("operation_type", "idempotency_key", name="uk_ly_subcontract_settlement_operation_idem"),
        Index(
            "idx_ly_subcontract_settlement_operation_statement",
            "statement_id",
            "statement_no",
            "operation_type",
        ),
        Index("idx_ly_subcontract_settlement_operation_created", "created_at"),
        {"schema": "ly_schema", "comment": "外发结算幂等操作日志"},
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    operation_type = Column(String(16), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    statement_id = Column(BigInteger, nullable=True)
    statement_no = Column(String(64), nullable=True)
    inspection_ids_json = Column(JSON, nullable=False)
    result_status = Column(String(32), nullable=False)
    affected_inspection_ids_json = Column(JSON, nullable=False)
    response_json = Column(JSON, nullable=True)
    operator = Column(String(140), nullable=False)
    request_id = Column(String(140), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySubcontractStockSyncLog(Base):
    """外发库存同步尝试日志。"""

    __tablename__ = "ly_subcontract_stock_sync_log"
    __table_args__ = (
        Index("idx_ly_subcontract_sync_log_outbox", "outbox_id", "attempt_no"),
        Index("idx_ly_subcontract_sync_log_company", "company", "created_at"),
        Index("idx_ly_subcontract_sync_log_company_outbox", "company", "outbox_id", "created_at"),
        {"schema": "ly_schema", "comment": "外发库存同步日志"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    outbox_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_stock_outbox.id"), nullable=False)
    subcontract_id = Column(BigInteger, ForeignKey("ly_schema.ly_subcontract_order.id"), nullable=False)
    company = Column(String(140), nullable=True)
    stock_action = Column(String(32), nullable=True)
    attempt_no = Column(Integer, nullable=True)
    stock_entry_name = Column(String(140), nullable=True)
    sync_status = Column(String(32), nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
