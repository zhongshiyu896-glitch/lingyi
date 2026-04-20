"""TASK-030C add cancel_reason column to quality inspection.

Revision ID: task_030c_add_quality_cancel_reason
Revises: task_012b_create_quality_tables
Create Date: 2026-04-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_030c_add_quality_cancel_reason"
down_revision = "task_012b_create_quality_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_quality_inspection"
_COLUMN_NAME = "cancel_reason"


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


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    if not _table_exists(bind, schema, _TABLE_NAME):
        return

    if _column_exists(bind, schema, _TABLE_NAME, _COLUMN_NAME):
        return

    op.add_column(
        _TABLE_NAME,
        sa.Column(_COLUMN_NAME, sa.String(length=200), nullable=True),
        schema=schema,
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    if not _table_exists(bind, schema, _TABLE_NAME):
        return

    if not _column_exists(bind, schema, _TABLE_NAME, _COLUMN_NAME):
        return

    op.drop_column(
        _TABLE_NAME,
        _COLUMN_NAME,
        schema=schema,
    )
