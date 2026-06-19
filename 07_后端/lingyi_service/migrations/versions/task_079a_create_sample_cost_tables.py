"""TASK-079A create sample cost capture tables.

Revision ID: task_079a_create_sample_cost_tables
Revises: task_078a_extend_production_quote_operations
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_079a_create_sample_cost_tables"
down_revision = "task_078a_extend_production_quote_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_sample_order"
_COST_LINE_TABLE = "ly_sample_cost_line"
_COST_OPERATION_TABLE = "ly_sample_cost_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    return any(str(index.get("name")) == index_name for index in sa.inspect(bind).get_indexes(table_name, schema=schema))


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_cost_line_table(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _ORDER_TABLE) or _table_exists(bind, schema, _COST_LINE_TABLE):
        return
    id_type = _id_type(bind)
    op.create_table(
        _COST_LINE_TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("sample_order_id", id_type, nullable=False),
        sa.Column("cost_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("occurred_date", sa.Date(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["sample_order_id"],
            [_qualified(schema, _ORDER_TABLE) + ".id"],
            name="fk_ly_sample_cost_line_order",
        ),
        sa.CheckConstraint("qty >= 0", name="ck_ly_sample_cost_line_qty"),
        sa.CheckConstraint("unit_price >= 0", name="ck_ly_sample_cost_line_unit_price"),
        sa.CheckConstraint("amount >= 0", name="ck_ly_sample_cost_line_amount"),
        schema=schema,
    )


def _create_cost_operation_table(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _ORDER_TABLE) or _table_exists(bind, schema, _COST_OPERATION_TABLE):
        return
    id_type = _id_type(bind)
    op.create_table(
        _COST_OPERATION_TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("sample_order_id", id_type, nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operation IN ('upsert')", name="ck_ly_sample_cost_operation"),
        schema=schema,
    )


def _create_index_if_needed(bind, schema: str | None, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_cost_line_table(bind, schema)
    _create_cost_operation_table(bind, schema)
    _create_index_if_needed(bind, schema, _COST_LINE_TABLE, "idx_ly_sample_cost_line_order", ["company", "sample_order_id"])
    _create_index_if_needed(bind, schema, _COST_LINE_TABLE, "idx_ly_sample_cost_line_type", ["company", "cost_type"])
    _create_index_if_needed(
        bind,
        schema,
        _COST_OPERATION_TABLE,
        "uk_ly_sample_cost_operation_idem",
        ["company", "operation", "idempotency_key"],
        unique=True,
    )
    _create_index_if_needed(bind, schema, _COST_OPERATION_TABLE, "idx_ly_sample_cost_operation_order", ["sample_order_id", "operation"])


def downgrade() -> None:
    """Additive migration; avoid destructive downgrade in local long-running DBs."""
