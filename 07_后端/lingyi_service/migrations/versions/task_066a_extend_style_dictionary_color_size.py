"""TASK-066A extend style dictionaries to color and size.

Revision ID: task_066a_extend_style_dictionary_color_size
Revises: task_065b_extend_sales_order_update_idempotency
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_066a_extend_style_dictionary_color_size"
down_revision = "task_065b_extend_sales_order_update_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_DICT_TABLE = "ly_style_dictionary"
_CONSTRAINT = "ck_ly_style_dictionary_type"


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


def _replace_dictionary_type_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _DICT_TABLE):
        return

    if _is_sqlite(bind):
        with op.batch_alter_table(_DICT_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return

    if _constraint_exists(bind, schema, _DICT_TABLE, _CONSTRAINT):
        op.drop_constraint(_CONSTRAINT, _DICT_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _DICT_TABLE, expression, schema=schema)


def upgrade() -> None:
    _replace_dictionary_type_constraint("dict_type IN ('season','year','brand','color','size')")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _DICT_TABLE):
        qualified = _DICT_TABLE if schema is None else f"{schema}.{_DICT_TABLE}"
        op.execute(sa.text(f"DELETE FROM {qualified} WHERE dict_type IN ('color','size')"))
    _replace_dictionary_type_constraint("dict_type IN ('season','year','brand')")
