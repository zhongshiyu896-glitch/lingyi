"""TASK-095A extend apparel BOM write operation idempotency.

Revision ID: task_095a_extend_apparel_bom_write_operations
Revises: task_094a_fix_material_purchase_requirement_unique_key
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_095a_extend_apparel_bom_write_operations"
down_revision = "task_094a_fix_material_purchase_requirement_unique_key"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_apparel_bom_write_operation"
_CONSTRAINT = "ck_ly_apparel_bom_write_operation"
_OLD_OPERATIONS = "('style_material_bom_upsert')"
_NEW_OPERATIONS = "('style_material_bom_upsert','bom:create','bom:update','bom:set_default','bom:activate','bom:deactivate')"


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
    _replace_operation_constraint(f"operation IN {_NEW_OPERATIONS}")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema):
        qualified = _TABLE if schema is None else f"{schema}.{_TABLE}"
        op.execute(sa.text(f"DELETE FROM {qualified} WHERE operation <> 'style_material_bom_upsert'"))
    _replace_operation_constraint(f"operation IN {_OLD_OPERATIONS}")
