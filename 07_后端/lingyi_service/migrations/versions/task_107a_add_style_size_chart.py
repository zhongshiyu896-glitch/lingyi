"""Add style-specific size chart JSON field.

Revision ID: task_107a_add_style_size_chart
Revises: task_106a_create_production_notice
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "task_107a_add_style_size_chart"
down_revision = "task_106a_create_production_notice"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_style_master"


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
    if not _table_exists(bind, schema, _TABLE) or _column_exists(bind, schema, _TABLE, "size_chart"):
        return
    op.add_column(
        _TABLE,
        sa.Column("size_chart", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        schema=schema,
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _TABLE) and _column_exists(bind, schema, _TABLE, "size_chart"):
        op.drop_column(_TABLE, "size_chart", schema=schema)
