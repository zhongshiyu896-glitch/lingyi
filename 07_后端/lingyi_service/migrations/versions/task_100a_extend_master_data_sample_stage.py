"""Extend master data entity types with sample stage.

Revision ID: task_100a_extend_master_data_sample_stage
Revises: task_099a_create_recycle_bin
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_100a_extend_master_data_sample_stage"
down_revision = "task_099a_create_recycle_bin"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_master_data_record"
_CONSTRAINT = "ck_ly_master_data_entity_type"
_OLD_ENTITY_TYPES = (
    "'customer','supplier','factory','warehouse','material','sample_type',"
    "'common_address','trade_term','invoice_type','cost_type','size_sort','distribution_channel','bank_account'"
)
_NEW_ENTITY_TYPES = (
    "'customer','supplier','factory','warehouse','material','sample_type','sample_stage',"
    "'common_address','trade_term','invoice_type','cost_type','size_sort','distribution_channel','bank_account'"
)


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return _TABLE in inspector.get_table_names(schema=schema)


def _constraint_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return any(str(constraint.get("name")) == _CONSTRAINT for constraint in inspector.get_check_constraints(_TABLE, schema=schema))


def _replace_constraint(entity_types_sql: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    expression = f"entity_type IN ({entity_types_sql})"
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
    _replace_constraint(_NEW_ENTITY_TYPES)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema):
        qualified = _TABLE if schema is None else f"{schema}.{_TABLE}"
        op.execute(sa.text(f"DELETE FROM {qualified} WHERE entity_type = 'sample_stage'"))
    _replace_constraint(_OLD_ENTITY_TYPES)
