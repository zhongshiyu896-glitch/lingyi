"""TASK-006C create factory statement operation idempotency table.

Revision ID: task_006c_factory_statement_operation_table
Revises: task_006b1_factory_statement_active_scope_constraints
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006c_factory_statement_operation_table"
down_revision = "task_006b1_factory_statement_active_scope_constraints"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    statement_table = "ly_factory_statement"
    operation_table = "ly_factory_statement_operation"
    if not _table_exists(bind, schema, statement_table):
        return

    if not _table_exists(bind, schema, operation_table):
        op.create_table(
            operation_table,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("statement_id", sa.BigInteger(), nullable=False),
            sa.Column("operation_type", sa.String(length=32), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("result_status", sa.String(length=32), nullable=False),
            sa.Column("result_user", sa.String(length=140), nullable=False),
            sa.Column("result_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("remark", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "operation_type IN ('confirm','cancel')",
                name="ck_ly_factory_statement_operation_type",
            ),
            sa.ForeignKeyConstraint(
                ["statement_id"],
                [f"{schema + '.' if schema else ''}{statement_table}.id"],
                name="fk_ly_factory_statement_operation_statement",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, operation_table, "uk_ly_factory_statement_operation_idempotency"):
        op.create_index(
            "uk_ly_factory_statement_operation_idempotency",
            operation_table,
            ["company", "statement_id", "operation_type", "idempotency_key"],
            unique=True,
            schema=schema,
        )

    if not _index_exists(bind, schema, operation_table, "idx_ly_factory_statement_operation_statement_time"):
        op.create_index(
            "idx_ly_factory_statement_operation_statement_time",
            operation_table,
            ["statement_id", "created_at"],
            schema=schema,
        )


def downgrade() -> None:
    """No destructive downgrade in hardening migration."""
    return
