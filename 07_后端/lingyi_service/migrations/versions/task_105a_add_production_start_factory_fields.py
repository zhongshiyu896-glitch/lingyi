"""add production start factory binding fields

Revision ID: task_105a_add_production_start_factory_fields
Revises: task_104a_extend_production_quote_order_level
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "task_105a_add_production_start_factory_fields"
down_revision = "task_104a_extend_production_quote_order_level"
branch_labels = None
depends_on = None

_TABLE = "ly_production_plan"


def _schema() -> str | None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return None
    return "ly_schema"


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name, schema=schema))


def _add_column_if_missing(bind, schema: str | None, column_name: str, column: sa.Column) -> None:
    if not _column_exists(bind, schema, _TABLE, column_name):
        op.add_column(_TABLE, column, schema=schema)


def _drop_column_if_exists(bind, schema: str | None, column_name: str) -> None:
    if _column_exists(bind, schema, _TABLE, column_name):
        op.drop_column(_TABLE, column_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema()
    _add_column_if_missing(bind, schema, "production_mode", sa.Column("production_mode", sa.String(length=32), nullable=True))
    _add_column_if_missing(bind, schema, "factory_id", sa.Column("factory_id", sa.String(length=140), nullable=True))
    _add_column_if_missing(bind, schema, "factory_name", sa.Column("factory_name", sa.String(length=140), nullable=True))
    _add_column_if_missing(bind, schema, "production_start_date", sa.Column("production_start_date", sa.Date(), nullable=True))
    _add_column_if_missing(bind, schema, "expected_finish_date", sa.Column("expected_finish_date", sa.Date(), nullable=True))
    _add_column_if_missing(bind, schema, "production_remark", sa.Column("production_remark", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema()
    for column_name in [
        "production_remark",
        "expected_finish_date",
        "production_start_date",
        "factory_name",
        "factory_id",
        "production_mode",
    ]:
        _drop_column_if_exists(bind, schema, column_name)
