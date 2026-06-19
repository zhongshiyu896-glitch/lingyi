"""TASK-077A allow production follow-up node update and delete operations.

Revision ID: task_077a_extend_production_followup_node_operations
Revises: task_076a_extend_production_quote_convert
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_077a_extend_production_followup_node_operations"
down_revision = "task_076a_extend_production_quote_convert"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_followup_template_node_operation"
_CONSTRAINT = "ck_ly_production_followup_template_node_operation"


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
    _replace_operation_constraint("operation IN ('create_node','update_node','delete_node')")


def downgrade() -> None:
    _replace_operation_constraint("operation IN ('create_node')")
