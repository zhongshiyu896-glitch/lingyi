"""TASK-069B add production material snapshot unit.

Revision ID: task_069b_add_production_material_uom
Revises: task_069a_create_foundation_template_tables
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_069b_add_production_material_uom"
down_revision = "task_069a_create_foundation_template_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_plan_material"
_COLUMN = "uom"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return _TABLE in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == _COLUMN for column in inspector.get_columns(_TABLE, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema) or _column_exists(bind, schema):
        return
    column = sa.Column(_COLUMN, sa.String(length=32), nullable=False, server_default="米")
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(_TABLE, column, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema) or not _column_exists(bind, schema):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            batch_op.drop_column(_COLUMN)
        return
    op.drop_column(_TABLE, _COLUMN, schema=schema)
