"""TASK-089A allow sales order draft submit idempotency.

Revision ID: task_089a_extend_sales_order_submit_idempotency
Revises: task_088a_create_finance_approval_templates
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_089a_extend_sales_order_submit_idempotency"
down_revision = "task_088a_create_finance_approval_templates"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_IDEM_TABLE = "ly_sales_order_idempotency"
_CONSTRAINT = "ck_ly_sales_order_idem_operation"


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


def _replace_operation_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _IDEM_TABLE):
        return

    if _is_sqlite(bind):
        with op.batch_alter_table(_IDEM_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return

    if _constraint_exists(bind, schema, _IDEM_TABLE, _CONSTRAINT):
        op.drop_constraint(_CONSTRAINT, _IDEM_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _IDEM_TABLE, expression, schema=schema)


def upgrade() -> None:
    _replace_operation_constraint("operation IN ('create_draft','update_draft','submit_draft','cancel_draft')")


def downgrade() -> None:
    _replace_operation_constraint("operation IN ('create_draft','update_draft','cancel_draft')")
