"""add production plan group number

Revision ID: task_103a_add_production_plan_group_no
Revises: task_102a_add_bom_item_spec_by_size
Create Date: 2026-06-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "task_103a_add_production_plan_group_no"
down_revision = "task_102a_add_bom_item_spec_by_size"
branch_labels = None
depends_on = None

_TABLE = "ly_production_plan"


def _schema() -> str | None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return None
    return "ly_schema"


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name, schema=schema))


def upgrade() -> None:
    schema = _schema()
    bind = op.get_bind()
    if not _column_exists(bind, schema, _TABLE, "plan_group_no"):
        op.add_column(_TABLE, sa.Column("plan_group_no", sa.String(length=64), nullable=True), schema=schema)
    if not _index_exists(bind, schema, _TABLE, "idx_ly_production_plan_group"):
        op.create_index("idx_ly_production_plan_group", _TABLE, ["plan_group_no"], schema=schema)


def downgrade() -> None:
    schema = _schema()
    bind = op.get_bind()
    if _index_exists(bind, schema, _TABLE, "idx_ly_production_plan_group"):
        op.drop_index("idx_ly_production_plan_group", table_name=_TABLE, schema=schema)
    if _column_exists(bind, schema, _TABLE, "plan_group_no"):
        op.drop_column(_TABLE, "plan_group_no", schema=schema)
