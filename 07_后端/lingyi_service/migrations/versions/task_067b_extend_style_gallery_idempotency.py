"""TASK-067B extend style idempotency to gallery writes.

Revision ID: task_067b_extend_style_gallery_idempotency
Revises: task_067a_add_sales_order_item_style_master_link
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_067b_extend_style_gallery_idempotency"
down_revision = "task_067a_add_sales_order_item_style_master_link"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_style_master_idempotency"
_CONSTRAINT = "ck_ly_style_master_idem_entity"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _constraint_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(constraint.get("name")) == constraint_name for constraint in inspector.get_check_constraints(table_name, schema=schema))


def _replace_entity_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return
    if _constraint_exists(bind, schema, _TABLE, _CONSTRAINT):
        op.drop_constraint(_CONSTRAINT, _TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, expression, schema=schema)


def upgrade() -> None:
    _replace_entity_constraint("entity_type IN ('style','dictionary','gallery')")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _TABLE):
        qualified = _TABLE if schema is None else f"{schema}.{_TABLE}"
        op.execute(sa.text(f"DELETE FROM {qualified} WHERE entity_type = 'gallery'"))
    _replace_entity_constraint("entity_type IN ('style','dictionary')")
