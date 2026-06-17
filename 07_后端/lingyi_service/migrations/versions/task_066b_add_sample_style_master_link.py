"""TASK-066B add sample order style master link.

Revision ID: task_066b_add_sample_style_master_link
Revises: task_066a_extend_style_dictionary_color_size
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_066b_add_sample_style_master_link"
down_revision = "task_066a_extend_style_dictionary_color_size"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_sample_order"
_STYLE_TABLE = "ly_style_master"
_COLUMN_NAME = "style_master_id"
_INDEX_NAME = "idx_ly_sample_order_style_master"


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
    if schema is None:
        return table_name
    return f"{schema}.{table_name}"


def _add_column(bind, schema: str | None) -> None:
    if _column_exists(bind, schema, _ORDER_TABLE, _COLUMN_NAME):
        return
    column = sa.Column(_COLUMN_NAME, sa.Integer() if _is_sqlite(bind) else sa.BigInteger(), nullable=True)
    if _is_sqlite(bind):
        with op.batch_alter_table(_ORDER_TABLE, schema=schema) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(_ORDER_TABLE, column, schema=schema)


def _backfill(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _STYLE_TABLE):
        return
    order_table = _qualified(schema, _ORDER_TABLE)
    style_table = _qualified(schema, _STYLE_TABLE)
    if _is_sqlite(bind):
        op.execute(
            sa.text(
                f"""
                UPDATE {order_table}
                SET style_master_id = (
                    SELECT sm.id
                    FROM {style_table} sm
                    WHERE sm.company = {order_table}.company
                      AND sm.ys_style_no = {order_table}.style_no
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
            UPDATE {order_table} sample_order
            SET style_master_id = style_master.id
            FROM {style_table} style_master
            WHERE sample_order.style_master_id IS NULL
              AND style_master.company = sample_order.company
              AND style_master.ys_style_no = sample_order.style_no
              AND style_master.ys_style_status = 'enabled'
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _ORDER_TABLE):
        return
    _add_column(bind, schema)
    _backfill(bind, schema)
    if not _index_exists(bind, schema, _ORDER_TABLE, _INDEX_NAME):
        op.create_index(_INDEX_NAME, _ORDER_TABLE, ["company", _COLUMN_NAME], unique=False, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _ORDER_TABLE):
        return
    if _index_exists(bind, schema, _ORDER_TABLE, _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name=_ORDER_TABLE, schema=schema)
    if _column_exists(bind, schema, _ORDER_TABLE, _COLUMN_NAME):
        if _is_sqlite(bind):
            with op.batch_alter_table(_ORDER_TABLE, schema=schema) as batch_op:
                batch_op.drop_column(_COLUMN_NAME)
            return
        op.drop_column(_ORDER_TABLE, _COLUMN_NAME, schema=schema)
