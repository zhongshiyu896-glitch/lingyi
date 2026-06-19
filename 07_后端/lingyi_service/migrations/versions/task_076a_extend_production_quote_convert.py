"""TASK-076A allow production quote convert operation.

Revision ID: task_076a_extend_production_quote_convert
Revises: task_075a_create_style_sku_matrix
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_076a_extend_production_quote_convert"
down_revision = "task_075a_create_style_sku_matrix"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_quote_operation"
_CONSTRAINT = "ck_ly_production_quote_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    return _TABLE in sa.inspect(bind).get_table_names(schema=schema)


def _constraint_exists(bind, schema: str | None) -> bool:
    return any(
        str(constraint.get("name")) == _CONSTRAINT
        for constraint in sa.inspect(bind).get_check_constraints(_TABLE, schema=schema)
    )


def _replace_operation_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return
    if _constraint_exists(bind, schema):
        op.drop_constraint(_CONSTRAINT, _TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, expression, schema=schema)


def upgrade() -> None:
    _replace_operation_constraint("operation IN ('create','convert')")


def downgrade() -> None:
    _replace_operation_constraint("operation IN ('create')")
