"""TASK-066C create production plan operation idempotency table.

Revision ID: task_066c_create_production_plan_operation
Revises: task_066b_add_sample_style_master_link
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_066c_create_production_plan_operation"
down_revision = "task_066b_add_sample_style_master_link"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_plan_operation"
_PLAN_TABLE = "ly_production_plan"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _PLAN_TABLE) or _table_exists(bind, schema, _TABLE):
        return
    _ensure_schema(bind)
    id_type = sa.Integer() if _is_sqlite(bind) else sa.BigInteger()
    op.create_table(
        _TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("plan_id", id_type, nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["plan_id"], [_qualified(schema, _PLAN_TABLE) + ".id"], name="fk_ly_production_plan_operation_plan"),
        schema=schema,
    )
    op.create_index(
        "uk_ly_production_plan_operation_idem",
        _TABLE,
        ["company", "operation", "idempotency_key"],
        unique=True,
        schema=schema,
    )
    op.create_index(
        "idx_ly_production_plan_operation_plan",
        _TABLE,
        ["plan_id", "operation"],
        schema=schema,
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    op.drop_index("idx_ly_production_plan_operation_plan", table_name=_TABLE, schema=schema)
    op.drop_index("uk_ly_production_plan_operation_idem", table_name=_TABLE, schema=schema)
    op.drop_table(_TABLE, schema=schema)
