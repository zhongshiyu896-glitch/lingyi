"""TASK-030D create quality outbox table.

Revision ID: task_030d_create_quality_outbox
Revises: task_030c_add_quality_cancel_reason
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_030d_create_quality_outbox"
down_revision = "task_030c_add_quality_cancel_reason"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_INSPECTION_TABLE = "ly_quality_inspection"
_OUTBOX_TABLE = "ly_quality_outbox"


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

    if not _table_exists(bind, schema, _OUTBOX_TABLE):
        op.create_table(
            _OUTBOX_TABLE,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("inspection_id", sa.BigInteger(), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False, server_default="quality_stock_entry_sync"),
            sa.Column("event_key", sa.String(length=140), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("locked_by", sa.String(length=140), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("last_error_message", sa.String(length=255), nullable=True),
            sa.Column("stock_entry_name", sa.String(length=140), nullable=True),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dead_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "status IN ('pending','processing','succeeded','failed','dead')",
                name="ck_ly_quality_outbox_status",
            ),
            sa.CheckConstraint(
                "attempts >= 0",
                name="ck_ly_quality_outbox_attempts_nonnegative",
            ),
            sa.CheckConstraint(
                "max_attempts > 0",
                name="ck_ly_quality_outbox_max_attempts_positive",
            ),
            sa.ForeignKeyConstraint(
                ["inspection_id"],
                [_qualified_table(schema, _INSPECTION_TABLE) + ".id"],
                name="fk_ly_quality_outbox_inspection",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, _OUTBOX_TABLE, "uk_ly_quality_outbox_event_key"):
        op.create_index(
            "uk_ly_quality_outbox_event_key",
            _OUTBOX_TABLE,
            ["event_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "uk_ly_quality_outbox_inspection_event"):
        op.create_index(
            "uk_ly_quality_outbox_inspection_event",
            _OUTBOX_TABLE,
            ["inspection_id", "event_type"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_quality_outbox_due"):
        op.create_index(
            "idx_ly_quality_outbox_due",
            _OUTBOX_TABLE,
            ["status", "next_retry_at", "id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_quality_outbox_scope"):
        op.create_index(
            "idx_ly_quality_outbox_scope",
            _OUTBOX_TABLE,
            ["company", "status", "next_retry_at"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_quality_outbox_inspection"):
        op.create_index(
            "idx_ly_quality_outbox_inspection",
            _OUTBOX_TABLE,
            ["inspection_id", "status", "id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_quality_outbox_lease"):
        op.create_index(
            "idx_ly_quality_outbox_lease",
            _OUTBOX_TABLE,
            ["status", "next_retry_at", "locked_until"],
            schema=schema,
        )


def downgrade() -> None:
    """No destructive downgrade in TASK-030D migration."""
    return
