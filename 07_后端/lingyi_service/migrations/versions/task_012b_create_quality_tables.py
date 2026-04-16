"""TASK-012B create quality management tables.

Revision ID: task_012b_create_quality_tables
Revises: task_006e2_factory_statement_payable_active_scope
Create Date: 2026-04-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_012b_create_quality_tables"
down_revision = "task_006e2_factory_statement_payable_active_scope"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified_table(schema: str | None, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_inspection_table(bind, schema: str | None) -> None:
    table = "ly_quality_inspection"
    if _table_exists(bind, schema, table):
        return
    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("inspection_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("supplier", sa.String(length=140), nullable=True),
        sa.Column("warehouse", sa.String(length=140), nullable=True),
        sa.Column("work_order", sa.String(length=140), nullable=True),
        sa.Column("sales_order", sa.String(length=140), nullable=True),
        sa.Column("inspection_date", sa.Date(), nullable=False),
        sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("defect_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("defect_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("confirmed_by", sa.String(length=140), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "source_type IN ('incoming_material','subcontract_receipt','finished_goods','manual')",
            name="ck_ly_quality_inspection_source_type",
        ),
        sa.CheckConstraint("status IN ('draft','confirmed','cancelled')", name="ck_ly_quality_inspection_status"),
        sa.CheckConstraint("result IN ('pending','pass','fail','partial')", name="ck_ly_quality_inspection_result"),
        sa.CheckConstraint("inspected_qty >= 0", name="ck_ly_quality_inspection_inspected_qty_nonnegative"),
        sa.CheckConstraint("accepted_qty >= 0", name="ck_ly_quality_inspection_accepted_qty_nonnegative"),
        sa.CheckConstraint("rejected_qty >= 0", name="ck_ly_quality_inspection_rejected_qty_nonnegative"),
        sa.CheckConstraint("defect_qty >= 0", name="ck_ly_quality_inspection_defect_qty_nonnegative"),
        sa.CheckConstraint("accepted_qty + rejected_qty = inspected_qty", name="ck_ly_quality_inspection_qty_balanced"),
        sa.CheckConstraint("defect_qty <= inspected_qty", name="ck_ly_quality_inspection_defect_qty_lte_inspected"),
        schema=schema,
    )
    op.create_index("uk_ly_quality_inspection_no", table, ["inspection_no"], unique=True, schema=schema)
    op.create_index(
        "idx_ly_quality_inspection_company_status_date",
        table,
        ["company", "status", "inspection_date"],
        schema=schema,
    )
    op.create_index("idx_ly_quality_inspection_item_date", table, ["item_code", "inspection_date"], schema=schema)
    op.create_index("idx_ly_quality_inspection_supplier_date", table, ["supplier", "inspection_date"], schema=schema)
    op.create_index("idx_ly_quality_inspection_source", table, ["source_type", "source_id"], schema=schema)


def _create_item_table(bind, schema: str | None) -> None:
    table = "ly_quality_inspection_item"
    if _table_exists(bind, schema, table):
        return
    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("sample_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("defect_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            [_qualified_table(schema, "ly_quality_inspection") + ".id"],
            name="fk_ly_quality_inspection_item_inspection",
        ),
        sa.CheckConstraint("sample_qty >= 0", name="ck_ly_quality_inspection_item_sample_qty_nonnegative"),
        sa.CheckConstraint("accepted_qty >= 0", name="ck_ly_quality_inspection_item_accepted_qty_nonnegative"),
        sa.CheckConstraint("rejected_qty >= 0", name="ck_ly_quality_inspection_item_rejected_qty_nonnegative"),
        sa.CheckConstraint("defect_qty >= 0", name="ck_ly_quality_inspection_item_defect_qty_nonnegative"),
        sa.CheckConstraint("result IN ('pending','pass','fail','partial')", name="ck_ly_quality_inspection_item_result"),
        schema=schema,
    )
    op.create_index("idx_ly_quality_inspection_item_inspection", table, ["inspection_id", "line_no"], schema=schema)


def _create_defect_table(bind, schema: str | None) -> None:
    table = "ly_quality_defect"
    if _table_exists(bind, schema, table):
        return
    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=True),
        sa.Column("defect_code", sa.String(length=64), nullable=False),
        sa.Column("defect_name", sa.String(length=140), nullable=False),
        sa.Column("defect_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="minor"),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            [_qualified_table(schema, "ly_quality_inspection") + ".id"],
            name="fk_ly_quality_defect_inspection",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            [_qualified_table(schema, "ly_quality_inspection_item") + ".id"],
            name="fk_ly_quality_defect_item",
        ),
        sa.CheckConstraint("defect_qty >= 0", name="ck_ly_quality_defect_qty_nonnegative"),
        sa.CheckConstraint("severity IN ('minor','major','critical')", name="ck_ly_quality_defect_severity"),
        schema=schema,
    )
    op.create_index("idx_ly_quality_defect_inspection", table, ["inspection_id", "defect_code"], schema=schema)


def _create_log_table(bind, schema: str | None) -> None:
    table = "ly_quality_operation_log"
    if _table_exists(bind, schema, table):
        return
    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=140), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("remark", sa.String(length=200), nullable=True),
        sa.Column("operated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            [_qualified_table(schema, "ly_quality_inspection") + ".id"],
            name="fk_ly_quality_operation_log_inspection",
        ),
        sa.CheckConstraint("action IN ('create','update','confirm','cancel')", name="ck_ly_quality_operation_log_action"),
        schema=schema,
    )
    op.create_index(
        "idx_ly_quality_operation_log_inspection_time",
        table,
        ["inspection_id", "operated_at"],
        schema=schema,
    )
    op.create_index("idx_ly_quality_operation_log_company_time", table, ["company", "operated_at"], schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_inspection_table(bind, schema)
    _create_item_table(bind, schema)
    _create_defect_table(bind, schema)
    _create_log_table(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
