"""TASK-067A add sales order item style master link.

Revision ID: task_067a_add_sales_order_item_style_master_link
Revises: task_066c_create_production_plan_operation
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_067a_add_sales_order_item_style_master_link"
down_revision = "task_066c_create_production_plan_operation"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ITEM_TABLE = "ly_sales_order_item"
_STYLE_TABLE = "ly_style_master"
_COLUMN_NAME = "style_master_id"
_INDEX_NAME = "idx_ly_sales_order_item_style_master"


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


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _add_column(bind, schema: str | None) -> None:
    if _column_exists(bind, schema, _ITEM_TABLE, _COLUMN_NAME):
        return
    column = sa.Column(_COLUMN_NAME, _id_type(bind), nullable=True)
    if _is_sqlite(bind):
        with op.batch_alter_table(_ITEM_TABLE, schema=schema) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(_ITEM_TABLE, column, schema=schema)


def _backfill(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _STYLE_TABLE):
        return
    item_table = _qualified(schema, _ITEM_TABLE)
    style_table = _qualified(schema, _STYLE_TABLE)
    if _is_sqlite(bind):
        op.execute(
            sa.text(
                f"""
                UPDATE {item_table}
                SET style_master_id = (
                    SELECT sm.id
                    FROM {style_table} sm
                    WHERE sm.company = {item_table}.company
                      AND sm.ys_style_no = {item_table}.item_code
                      AND sm.ys_style_status = 'enabled'
                    ORDER BY sm.id
                    LIMIT 1
                )
                WHERE style_master_id IS NULL
                """
            )
        )
        return
    op.execute(
        sa.text(
            f"""
            UPDATE {item_table} sales_item
            SET style_master_id = style_master.id
            FROM {style_table} style_master
            WHERE sales_item.style_master_id IS NULL
              AND style_master.company = sales_item.company
              AND style_master.ys_style_no = sales_item.item_code
              AND style_master.ys_style_status = 'enabled'
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _ITEM_TABLE):
        return
    _add_column(bind, schema)
    _backfill(bind, schema)
    if not _index_exists(bind, schema, _ITEM_TABLE, _INDEX_NAME):
        op.create_index(_INDEX_NAME, _ITEM_TABLE, ["company", _COLUMN_NAME], unique=False, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _ITEM_TABLE):
        return
    if _index_exists(bind, schema, _ITEM_TABLE, _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name=_ITEM_TABLE, schema=schema)
    if _column_exists(bind, schema, _ITEM_TABLE, _COLUMN_NAME):
        if _is_sqlite(bind):
            with op.batch_alter_table(_ITEM_TABLE, schema=schema) as batch_op:
                batch_op.drop_column(_COLUMN_NAME)
            return
        op.drop_column(_ITEM_TABLE, _COLUMN_NAME, schema=schema)
