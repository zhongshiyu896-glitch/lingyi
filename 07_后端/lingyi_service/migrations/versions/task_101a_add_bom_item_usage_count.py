"""Add usage count to style and sample material BOM items.

Revision ID: task_101a_add_bom_item_usage_count
Revises: task_100a_extend_master_data_sample_stage
Create Date: 2026-06-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_101a_add_bom_item_usage_count"
down_revision = "task_100a_extend_master_data_sample_stage"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLES = ("ly_apparel_bom_item", "ly_sample_material_bom_item")


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
    for table_name in _TABLES:
        if not _table_exists(bind, schema, table_name) or _column_exists(bind, schema, table_name, "usage_count"):
            continue
        column = sa.Column("usage_count", sa.Numeric(18, 6), nullable=False, server_default="1")
        if _is_sqlite(bind):
            with op.batch_alter_table(table_name, schema=schema) as batch_op:
                batch_op.add_column(column)
            continue
        op.add_column(table_name, column, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name in reversed(_TABLES):
        if not _table_exists(bind, schema, table_name) or not _column_exists(bind, schema, table_name, "usage_count"):
            continue
        if _is_sqlite(bind):
            with op.batch_alter_table(table_name, schema=schema) as batch_op:
                batch_op.drop_column("usage_count")
            continue
        op.drop_column(table_name, "usage_count", schema=schema)
