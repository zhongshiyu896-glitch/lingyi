"""TASK-030E create quality disposition table.

Revision ID: task_030e_create_quality_disposition
Revises: task_030d_create_quality_outbox
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_030e_create_quality_disposition"
down_revision = "task_030d_create_quality_outbox"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_INSPECTION_TABLE = "ly_quality_inspection"
_DISPOSITION_TABLE = "ly_quality_disposition"


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

    if not _table_exists(bind, schema, _DISPOSITION_TABLE):
        op.create_table(
            _DISPOSITION_TABLE,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("inspection_id", sa.BigInteger(), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("reason", sa.String(length=200), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=140), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("operator", sa.String(length=140), nullable=False),
            sa.Column("operated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("action IN ('release','rework')", name="ck_ly_quality_disposition_action"),
            sa.CheckConstraint("qty >= 0", name="ck_ly_quality_disposition_qty_nonnegative"),
            sa.ForeignKeyConstraint(
                ["inspection_id"],
                [_qualified_table(schema, _INSPECTION_TABLE) + ".id"],
                name="fk_ly_quality_disposition_inspection",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, _DISPOSITION_TABLE, "uk_ly_quality_disposition_action"):
        op.create_index(
            "uk_ly_quality_disposition_action",
            _DISPOSITION_TABLE,
            ["inspection_id", "action"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _DISPOSITION_TABLE, "uk_ly_quality_disposition_idempotency"):
        op.create_index(
            "uk_ly_quality_disposition_idempotency",
            _DISPOSITION_TABLE,
            ["inspection_id", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _DISPOSITION_TABLE, "idx_ly_quality_disposition_company_time"):
        op.create_index(
            "idx_ly_quality_disposition_company_time",
            _DISPOSITION_TABLE,
            ["company", "operated_at"],
            schema=schema,
        )


def downgrade() -> None:
    """No destructive downgrade in TASK-030E migration."""
    return
