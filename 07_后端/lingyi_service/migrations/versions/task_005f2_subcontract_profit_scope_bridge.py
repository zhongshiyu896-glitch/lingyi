"""TASK-005F2 subcontract profit scope bridge fields and indexes.

Revision ID: task_005f2_subcontract_profit_scope_bridge
Revises: task_005c_create_style_profit_tables
Create Date: 2026-04-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_005f2_subcontract_profit_scope_bridge"
down_revision = "task_005c_create_style_profit_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_subcontract_order"
_INSPECTION_TABLE = "ly_subcontract_inspection"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name, schema=schema):
        if str(column.get("name")) == column_name:
            return True
    return False


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


def _add_order_columns(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _ORDER_TABLE):
        return

    columns: list[tuple[str, sa.Column]] = [
        ("sales_order", sa.Column("sales_order", sa.String(length=140), nullable=True)),
        ("sales_order_item", sa.Column("sales_order_item", sa.String(length=140), nullable=True)),
        ("production_plan_id", sa.Column("production_plan_id", sa.BigInteger(), nullable=True)),
        ("work_order", sa.Column("work_order", sa.String(length=140), nullable=True)),
        ("job_card", sa.Column("job_card", sa.String(length=140), nullable=True)),
        (
            "profit_scope_status",
            sa.Column("profit_scope_status", sa.String(length=32), nullable=False, server_default="unresolved"),
        ),
        ("profit_scope_error_code", sa.Column("profit_scope_error_code", sa.String(length=64), nullable=True)),
        ("profit_scope_resolved_at", sa.Column("profit_scope_resolved_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for column_name, column in columns:
        if not _column_exists(bind, schema, _ORDER_TABLE, column_name):
            op.add_column(_ORDER_TABLE, column, schema=schema)


def _add_inspection_columns(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _INSPECTION_TABLE):
        return

    columns: list[tuple[str, sa.Column]] = [
        ("sales_order", sa.Column("sales_order", sa.String(length=140), nullable=True)),
        ("sales_order_item", sa.Column("sales_order_item", sa.String(length=140), nullable=True)),
        ("production_plan_id", sa.Column("production_plan_id", sa.BigInteger(), nullable=True)),
        ("work_order", sa.Column("work_order", sa.String(length=140), nullable=True)),
        ("job_card", sa.Column("job_card", sa.String(length=140), nullable=True)),
        (
            "profit_scope_status",
            sa.Column("profit_scope_status", sa.String(length=32), nullable=False, server_default="unresolved"),
        ),
        ("profit_scope_error_code", sa.Column("profit_scope_error_code", sa.String(length=64), nullable=True)),
        ("profit_scope_resolved_at", sa.Column("profit_scope_resolved_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for column_name, column in columns:
        if not _column_exists(bind, schema, _INSPECTION_TABLE, column_name):
            op.add_column(_INSPECTION_TABLE, column, schema=schema)


def _ensure_indexes(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ORDER_TABLE):
        if not _index_exists(bind, schema, _ORDER_TABLE, "idx_ly_subcontract_profit_scope_order"):
            op.create_index(
                "idx_ly_subcontract_profit_scope_order",
                _ORDER_TABLE,
                ["company", "item_code", "sales_order", "work_order", "profit_scope_status"],
                schema=schema,
            )
        if not _index_exists(bind, schema, _ORDER_TABLE, "idx_ly_subcontract_profit_plan"):
            op.create_index(
                "idx_ly_subcontract_profit_plan",
                _ORDER_TABLE,
                ["production_plan_id", "work_order"],
                schema=schema,
            )

    if _table_exists(bind, schema, _INSPECTION_TABLE):
        if not _index_exists(bind, schema, _INSPECTION_TABLE, "idx_ly_subcontract_inspection_profit_scope"):
            op.create_index(
                "idx_ly_subcontract_inspection_profit_scope",
                _INSPECTION_TABLE,
                ["company", "item_code", "sales_order", "work_order", "settlement_status", "inspected_at"],
                schema=schema,
            )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _add_order_columns(bind, schema)
    _add_inspection_columns(bind, schema)
    _ensure_indexes(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
