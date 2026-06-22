"""TASK-096A add purchase requirement context to warehouse draft items.

Revision ID: task_096a_add_purchase_requirement_context_to_stock_entry_items
Revises: task_095a_extend_apparel_bom_write_operations
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_096a_add_purchase_requirement_context_to_stock_entry_items"
down_revision = "task_095a_extend_apparel_bom_write_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_warehouse_stock_entry_draft_item"
_COLUMNS = (
    ("sales_order_item", sa.String(length=140)),
    ("bom_color", sa.String(length=100)),
    ("bom_size", sa.String(length=100)),
    ("bom_part", sa.String(length=100)),
)


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    return any(str(column.get("name")) == column_name for column in sa.inspect(bind).get_columns(table_name, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME):
        return
    for column_name, column_type in _COLUMNS:
        if _column_exists(bind, schema, _TABLE_NAME, column_name):
            continue
        column = sa.Column(column_name, column_type, nullable=True)
        if _is_sqlite(bind):
            with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
                batch_op.add_column(column)
        else:
            op.add_column(_TABLE_NAME, column, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME):
        return
    for column_name, _column_type in reversed(_COLUMNS):
        if not _column_exists(bind, schema, _TABLE_NAME, column_name):
            continue
        if _is_sqlite(bind):
            with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
                batch_op.drop_column(column_name)
        else:
            op.drop_column(_TABLE_NAME, column_name, schema=schema)
