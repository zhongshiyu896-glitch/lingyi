"""TASK-006B create factory statement tables and indexes.

Revision ID: task_006b_create_factory_statement_tables
Revises: task_005f2_subcontract_profit_scope_bridge
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006b_create_factory_statement_tables"
down_revision = "task_005f2_subcontract_profit_scope_bridge"
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


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_statement_table(bind, schema: str | None) -> None:
    table = "ly_factory_statement"
    if _table_exists(bind, schema, table):
        return

    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("statement_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("supplier", sa.String(length=140), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="subcontract_inspection"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("gross_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("statement_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("confirmed_by", sa.String(length=140), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "statement_status IN ('draft','confirmed','cancelled','payable_draft_created')",
            name="ck_ly_factory_statement_status",
        ),
        schema=schema,
    )

    op.create_index("uk_ly_factory_statement_no", table, ["statement_no"], unique=True, schema=schema)
    op.create_index(
        "uk_ly_factory_statement_active_scope",
        table,
        ["company", "supplier", "from_date", "to_date", "request_hash"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("statement_status <> 'cancelled'"),
        sqlite_where=sa.text("statement_status <> 'cancelled'"),
    )
    op.create_index(
        "uk_ly_factory_statement_company_idempotency",
        table,
        ["company", "idempotency_key"],
        unique=True,
        schema=schema,
    )
    op.create_index(
        "idx_ly_factory_statement_company_supplier_status_created",
        table,
        ["company", "supplier", "statement_status", "created_at"],
        schema=schema,
    )


def _create_item_table(bind, schema: str | None) -> None:
    table = "ly_factory_statement_item"
    if _table_exists(bind, schema, table):
        return

    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("statement_id", sa.BigInteger(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("inspection_no", sa.String(length=64), nullable=True),
        sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
        sa.Column("subcontract_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("supplier", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("gross_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("source_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            [_qualified_table(schema, "ly_factory_statement") + ".id"],
            name="fk_ly_factory_statement_item_statement",
        ),
        schema=schema,
    )

    op.create_index("idx_ly_factory_statement_item_statement", table, ["statement_id", "line_no"], schema=schema)
    op.create_index("idx_ly_factory_statement_item_inspection", table, ["inspection_id"], schema=schema)
    op.create_index(
        "idx_ly_factory_statement_item_company_supplier_time",
        table,
        ["company", "supplier", "inspected_at"],
        schema=schema,
    )


def _create_log_table(bind, schema: str | None) -> None:
    table = "ly_factory_statement_log"
    if _table_exists(bind, schema, table):
        return

    op.create_table(
        table,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("statement_id", sa.BigInteger(), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("supplier", sa.String(length=140), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=140), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("remark", sa.String(length=200), nullable=True),
        sa.Column("operated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            [_qualified_table(schema, "ly_factory_statement") + ".id"],
            name="fk_ly_factory_statement_log_statement",
        ),
        schema=schema,
    )

    op.create_index(
        "idx_ly_factory_statement_log_statement_time",
        table,
        ["statement_id", "operated_at"],
        schema=schema,
    )
    op.create_index(
        "idx_ly_factory_statement_log_company_statement",
        table,
        ["company", "statement_id", "operated_at"],
        schema=schema,
    )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    _ensure_schema(bind)
    _create_statement_table(bind, schema)
    _create_item_table(bind, schema)
    _create_log_table(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
