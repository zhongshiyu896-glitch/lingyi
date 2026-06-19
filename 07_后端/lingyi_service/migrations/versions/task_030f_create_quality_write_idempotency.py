"""TASK-030F create quality write idempotency table.

Revision ID: task_030f_create_quality_write_idempotency
Revises: task_030e_create_quality_disposition
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_030f_create_quality_write_idempotency"
down_revision = "task_030e_create_quality_disposition"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_INSPECTION_TABLE = "ly_quality_inspection"
_IDEMPOTENCY_TABLE = "ly_quality_write_idempotency"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified_table(schema: str | None, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)

    if not _table_exists(bind, schema, _INSPECTION_TABLE):
        return

    if not _table_exists(bind, schema, _IDEMPOTENCY_TABLE):
        op.create_table(
            _IDEMPOTENCY_TABLE,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("operation", sa.String(length=32), nullable=False),
            sa.Column("idempotency_key", sa.String(length=140), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("resource_id", sa.BigInteger(), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "operation IN ('create','update','confirm','cancel','defects')",
                name="ck_ly_quality_write_idem_operation",
            ),
            sa.ForeignKeyConstraint(
                ["resource_id"],
                [_qualified_table(schema, _INSPECTION_TABLE) + ".id"],
                name="fk_ly_quality_write_idem_inspection",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, _IDEMPOTENCY_TABLE, "uk_ly_quality_write_idem_key"):
        op.create_index(
            "uk_ly_quality_write_idem_key",
            _IDEMPOTENCY_TABLE,
            ["company", "operation", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _IDEMPOTENCY_TABLE, "idx_ly_quality_write_idem_resource"):
        op.create_index(
            "idx_ly_quality_write_idem_resource",
            _IDEMPOTENCY_TABLE,
            ["resource_id", "operation"],
            schema=schema,
        )


def downgrade() -> None:
    """No destructive downgrade in TASK-030F migration."""
    return

