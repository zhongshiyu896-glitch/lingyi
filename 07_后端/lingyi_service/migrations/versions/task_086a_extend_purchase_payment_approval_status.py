"""TASK-086A extend purchase payment status for approval gating.

Revision ID: task_086a_extend_purchase_payment_approval_status
Revises: task_085a_create_production_tracking_node_event
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_086a_extend_purchase_payment_approval_status"
down_revision = "task_085a_create_production_tracking_node_event"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_PAYMENT_TABLE = "ly_material_purchase_payment"
_CONSTRAINT = "ck_ly_material_purchase_payment_status"
_NEW_CHECK = "status IN ('pending_approval','submitted','cancelled')"
_OLD_CHECK = "status IN ('submitted','cancelled')"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    return _PAYMENT_TABLE in sa.inspect(bind).get_table_names(schema=schema)


def _status_check_sql(bind, schema: str | None) -> str:
    for constraint in sa.inspect(bind).get_check_constraints(_PAYMENT_TABLE, schema=schema):
        if str(constraint.get("name")) == _CONSTRAINT:
            return str(constraint.get("sqltext") or "")
    return ""


def _replace_status_constraint(bind, schema: str | None, check_sql: str) -> None:
    if "pending_approval" in check_sql:
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_PAYMENT_TABLE, schema=schema, recreate="always") as batch_op:
            if check_sql:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(_CONSTRAINT, _NEW_CHECK)
        return
    if check_sql:
        op.drop_constraint(_CONSTRAINT, _PAYMENT_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _PAYMENT_TABLE, _NEW_CHECK, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    _replace_status_constraint(bind, schema, _status_check_sql(bind, schema))


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    check_sql = _status_check_sql(bind, schema)
    if "pending_approval" not in check_sql:
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_PAYMENT_TABLE, schema=schema, recreate="always") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(_CONSTRAINT, _OLD_CHECK)
        return
    op.drop_constraint(_CONSTRAINT, _PAYMENT_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _PAYMENT_TABLE, _OLD_CHECK, schema=schema)
