"""SQLAlchemy models for style profit report module (TASK-005C)."""

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
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyStyleProfitSnapshot(Base):
    """Style profit immutable snapshot header."""

    __tablename__ = "ly_style_profit_snapshot"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_style_profit_snapshot"),
        Index("uk_ly_style_profit_snapshot_no", "snapshot_no", unique=True),
        Index("uk_ly_style_profit_snapshot_idempotency", "company", "idempotency_key", unique=True),
        Index("idx_ly_style_profit_snapshot_company_item_order", "company", "item_code", "sales_order"),
        Index(
            "idx_ly_style_profit_snapshot_company_item_period",
            "company",
            "item_code",
            "from_date",
            "to_date",
        ),
        Index("idx_ly_style_profit_snapshot_created_at", "created_at"),
        Index("idx_ly_style_profit_snapshot_status", "snapshot_status"),
        Index("idx_ly_style_profit_snapshot_formula_version", "formula_version"),
        CheckConstraint(
            "revenue_status IN ('actual','estimated','unresolved')",
            name="ck_ly_style_profit_snapshot_revenue_status",
        ),
        CheckConstraint(
            "snapshot_status IN ('complete','incomplete','failed')",
            name="ck_ly_style_profit_snapshot_status",
        ),
        CheckConstraint(
            "allocation_status IN ('not_enabled','enabled')",
            name="ck_ly_style_profit_snapshot_allocation_status",
        ),
        CheckConstraint(
            "revenue_mode IN ('actual_first','actual_only','estimated_only')",
            name="ck_ly_style_profit_snapshot_revenue_mode",
        ),
        {"schema": "ly_schema", "comment": "款式利润快照主表"},
    )

    id = Column(IDType, autoincrement=True)
    snapshot_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    sales_order = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)

    revenue_status = Column(String(32), nullable=False, server_default="unresolved")
    estimated_revenue_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    actual_revenue_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    revenue_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    from_date = Column(Date, nullable=True)
    to_date = Column(Date, nullable=True)
    revenue_mode = Column(String(32), nullable=False, server_default="actual_first")

    standard_material_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    standard_operation_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    standard_total_cost = Column(Numeric(18, 6), nullable=False, server_default="0")

    actual_material_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    actual_workshop_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    actual_subcontract_cost = Column(Numeric(18, 6), nullable=False, server_default="0")
    allocated_overhead_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    actual_total_cost = Column(Numeric(18, 6), nullable=False, server_default="0")

    profit_amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    profit_rate = Column(Numeric(18, 6), nullable=True)

    snapshot_status = Column(String(32), nullable=False, server_default="incomplete")
    allocation_status = Column(String(32), nullable=False, server_default="not_enabled")
    formula_version = Column(String(32), nullable=False, server_default="STYLE_PROFIT_V1")
    include_provisional_subcontract = Column(Boolean, nullable=False, server_default=text("false"))
    unresolved_count = Column(Integer, nullable=False, server_default="0")

    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyStyleProfitDetail(Base):
    """Style profit snapshot detail lines."""

    __tablename__ = "ly_style_profit_detail"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_style_profit_detail"),
        Index("idx_ly_style_profit_detail_snapshot", "snapshot_id", "line_no"),
        Index("idx_ly_style_profit_detail_cost_type", "cost_type"),
        Index("idx_ly_style_profit_detail_source", "source_type", "source_name"),
        CheckConstraint(
            (
                "cost_type IN ("
                "'revenue','standard_material','standard_operation','actual_material','workshop',"
                "'subcontract','deduction','overhead','unresolved'"
                ")"
            ),
            name="ck_ly_style_profit_detail_cost_type",
        ),
        {"schema": "ly_schema", "comment": "款式利润快照明细"},
    )

    id = Column(IDType, autoincrement=True)
    snapshot_id = Column(
        BigInteger,
        ForeignKey("ly_schema.ly_style_profit_snapshot.id"),
        nullable=False,
        comment="FK to ly_style_profit_snapshot.id",
    )
    line_no = Column(Integer, nullable=False)
    cost_type = Column(String(64), nullable=False)
    source_type = Column(String(64), nullable=False)
    source_name = Column(String(140), nullable=False)
    item_code = Column(String(140), nullable=True)
    qty = Column(Numeric(18, 6), nullable=True)
    unit_rate = Column(Numeric(18, 6), nullable=True)
    amount = Column(Numeric(18, 6), nullable=False)
    formula_code = Column(String(64), nullable=True)
    is_unresolved = Column(Boolean, nullable=False, server_default=text("false"))
    unresolved_reason = Column(String(128), nullable=True)
    raw_ref = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyStyleProfitSourceMap(Base):
    """Style profit source-level mapping registry."""

    __tablename__ = "ly_style_profit_source_map"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_style_profit_source_map"),
        Index(
            "uk_ly_style_profit_source_map_snapshot_source",
            "snapshot_id",
            "source_system",
            "source_doctype",
            "source_name",
            "source_line_no",
            unique=True,
        ),
        Index("idx_ly_style_profit_source_map_snapshot_status", "snapshot_id", "mapping_status"),
        Index("idx_ly_style_profit_source_map_scope", "company", "sales_order", "style_item_code"),
        Index(
            "idx_ly_style_profit_source_map_source_lookup",
            "source_system",
            "source_doctype",
            "source_name",
        ),
        Index("idx_ly_style_profit_source_map_detail", "detail_id"),
        CheckConstraint(
            "mapping_status IN ('mapped','unresolved','excluded')",
            name="ck_ly_style_profit_source_map_status",
        ),
        CheckConstraint(
            "source_system IN ('erpnext','fastapi','manual')",
            name="ck_ly_style_profit_source_map_source_system",
        ),
        CheckConstraint(
            "source_status <> ''",
            name="ck_ly_style_profit_source_map_source_status_non_empty",
        ),
        CheckConstraint(
            "NOT include_in_profit OR mapping_status = 'mapped'",
            name="ck_ly_style_profit_source_map_include_requires_mapped",
        ),
        {"schema": "ly_schema", "comment": "款式利润来源映射表"},
    )

    id = Column(IDType, autoincrement=True)
    snapshot_id = Column(BigInteger, ForeignKey("ly_schema.ly_style_profit_snapshot.id"), nullable=False)
    detail_id = Column(BigInteger, ForeignKey("ly_schema.ly_style_profit_detail.id"), nullable=True)
    company = Column(String(140), nullable=False)
    sales_order = Column(String(140), nullable=True)
    style_item_code = Column(String(140), nullable=False)
    source_item_code = Column(String(140), nullable=True)
    production_plan_id = Column(BigInteger, nullable=True)
    work_order = Column(String(140), nullable=True)
    job_card = Column(String(140), nullable=True)
    source_system = Column(String(64), nullable=False)
    source_doctype = Column(String(140), nullable=False)
    source_status = Column(String(64), nullable=False, server_default="unknown")
    source_name = Column(String(140), nullable=False)
    source_line_no = Column(String(140), nullable=False, server_default="")
    qty = Column(Numeric(18, 6), nullable=True)
    unit_rate = Column(Numeric(18, 6), nullable=True)
    amount = Column(Numeric(18, 6), nullable=False, server_default="0")
    currency = Column(String(16), nullable=True)
    warehouse = Column(String(140), nullable=True)
    posting_date = Column(Date, nullable=True)
    raw_ref = Column(JSONType, nullable=True)
    include_in_profit = Column(Boolean, nullable=False, server_default=text("false"))
    mapping_status = Column(String(32), nullable=False, server_default="unresolved")
    unresolved_reason = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyCostAllocationRule(Base):
    """Cost allocation rule registry (reserved for future versions)."""

    __tablename__ = "ly_cost_allocation_rule"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_cost_allocation_rule"),
        Index("idx_ly_cost_allocation_rule_company_status", "company", "status"),
        CheckConstraint(
            "cost_type IN ('manufacturing_overhead','admin','other')",
            name="ck_ly_cost_allocation_rule_cost_type",
        ),
        CheckConstraint(
            "allocation_basis IN ('qty','amount','work_hour','manual')",
            name="ck_ly_cost_allocation_rule_basis",
        ),
        CheckConstraint(
            "status IN ('draft','active','disabled')",
            name="ck_ly_cost_allocation_rule_status",
        ),
        {"schema": "ly_schema", "comment": "费用分摊规则（V1 预留）"},
    )

    id = Column(IDType, autoincrement=True)
    company = Column(String(140), nullable=False)
    rule_name = Column(String(140), nullable=False)
    cost_type = Column(String(64), nullable=False)
    allocation_basis = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, server_default="disabled")
    created_by = Column(String(140), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
