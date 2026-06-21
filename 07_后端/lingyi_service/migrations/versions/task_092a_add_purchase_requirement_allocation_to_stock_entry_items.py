"""TASK-092A add purchase requirement allocation to warehouse draft items.

Revision ID: task_092a_add_purchase_requirement_allocation_to_stock_entry_items
Revises: task_091a_add_bom_dimensions_to_material_requirements
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_092a_add_purchase_requirement_allocation_to_stock_entry_items"
down_revision = "task_091a_add_bom_dimensions_to_material_requirements"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_warehouse_stock_entry_draft_item"
_COLUMN_NAME = "purchase_requirement_id"
_INDEX_NAME = "idx_ly_whse_stock_entry_item_requirement"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(table_name, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME):
        return
    if not _column_exists(bind, schema, _TABLE_NAME, _COLUMN_NAME):
        if _is_sqlite(bind):
            with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
                batch_op.add_column(sa.Column(_COLUMN_NAME, sa.BigInteger(), nullable=True))
        else:
            op.add_column(_TABLE_NAME, sa.Column(_COLUMN_NAME, sa.BigInteger(), nullable=True), schema=schema)
    if not _index_exists(bind, schema, _TABLE_NAME, _INDEX_NAME):
        op.create_index(_INDEX_NAME, _TABLE_NAME, [_COLUMN_NAME], schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME):
        return
    if _index_exists(bind, schema, _TABLE_NAME, _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME, schema=schema)
    if not _column_exists(bind, schema, _TABLE_NAME, _COLUMN_NAME):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
            batch_op.drop_column(_COLUMN_NAME)
    else:
        op.drop_column(_TABLE_NAME, _COLUMN_NAME, schema=schema)
