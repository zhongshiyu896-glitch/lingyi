"""TASK-084A add size dimension to sample material BOM items.

Revision ID: task_084a_add_sample_material_bom_item_size
Revises: task_083a_create_delivery_invoice_operations
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_084a_add_sample_material_bom_item_size"
down_revision = "task_083a_create_delivery_invoice_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_sample_material_bom_item"


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
    if not _table_exists(bind, schema, _TABLE_NAME) or _column_exists(bind, schema, _TABLE_NAME, "size"):
        return
    column = sa.Column("size", sa.String(length=64), nullable=True)
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(_TABLE_NAME, column, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME) or not _column_exists(bind, schema, _TABLE_NAME, "size"):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
            batch_op.drop_column("size")
        return
    op.drop_column(_TABLE_NAME, "size", schema=schema)
