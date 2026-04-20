"""TASK-050B create warehouse stock-entry draft and outbox tables.

Revision ID: task_050b_create_warehouse_stock_entry_outbox
Revises: task_030d_create_quality_outbox
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_050b_create_warehouse_stock_entry_outbox"
down_revision = "task_030d_create_quality_outbox"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_DRAFT_TABLE = "ly_warehouse_stock_entry_draft"
_ITEM_TABLE = "ly_warehouse_stock_entry_draft_item"
_OUTBOX_TABLE = "ly_warehouse_stock_entry_outbox_event"


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


def _create_draft_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _DRAFT_TABLE):
        return
    op.create_table(
        _DRAFT_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=140), nullable=False),
        sa.Column("source_warehouse", sa.String(length=140), nullable=True),
        sa.Column("target_warehouse", sa.String(length=140), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("event_key", sa.String(length=140), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','pending_outbox','cancelled')",
            name="ck_ly_whse_stock_entry_draft_status",
        ),
        sa.CheckConstraint(
            "purpose IN ('Material Issue','Material Receipt','Material Transfer')",
            name="ck_ly_whse_stock_entry_draft_purpose",
        ),
        schema=schema,
    )


def _create_item_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ITEM_TABLE):
        return
    op.create_table(
        _ITEM_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("draft_id", sa.BigInteger(), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom", sa.String(length=32), nullable=False),
        sa.Column("batch_no", sa.String(length=140), nullable=True),
        sa.Column("serial_no", sa.String(length=500), nullable=True),
        sa.Column("source_warehouse", sa.String(length=140), nullable=True),
        sa.Column("target_warehouse", sa.String(length=140), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            [_qualified_table(schema, _DRAFT_TABLE) + ".id"],
            name="fk_ly_whse_stock_entry_item_draft",
        ),
        sa.CheckConstraint("qty > 0", name="ck_ly_whse_stock_entry_item_qty_positive"),
        schema=schema,
    )


def _create_outbox_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _OUTBOX_TABLE):
        return
    op.create_table(
        _OUTBOX_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("draft_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_key", sa.String(length=140), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_ref", sa.String(length=140), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            [_qualified_table(schema, _DRAFT_TABLE) + ".id"],
            name="fk_ly_whse_stock_entry_outbox_draft",
        ),
        sa.CheckConstraint(
            "status IN ('in_pending','processing','succeeded','failed','dead','cancelled')",
            name="ck_ly_whse_stock_entry_outbox_status",
        ),
        sa.CheckConstraint("retry_count >= 0", name="ck_ly_whse_stock_entry_outbox_retry_count_nonnegative"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    if not _index_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_event_key"):
        op.create_index(
            "uk_ly_whse_stock_entry_draft_event_key",
            _DRAFT_TABLE,
            ["event_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_company_idempotency"):
        op.create_index(
            "uk_ly_whse_stock_entry_draft_company_idempotency",
            _DRAFT_TABLE,
            ["company", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_company_source"):
        op.create_index(
            "uk_ly_whse_stock_entry_draft_company_source",
            _DRAFT_TABLE,
            ["company", "source_type", "source_id", "status"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _DRAFT_TABLE, "idx_ly_whse_stock_entry_draft_company_status"):
        op.create_index(
            "idx_ly_whse_stock_entry_draft_company_status",
            _DRAFT_TABLE,
            ["company", "status"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_stock_entry_item_draft"):
        op.create_index(
            "idx_ly_whse_stock_entry_item_draft",
            _ITEM_TABLE,
            ["draft_id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_stock_entry_item_company_item"):
        op.create_index(
            "idx_ly_whse_stock_entry_item_company_item",
            _ITEM_TABLE,
            ["company", "item_code"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "uk_ly_whse_stock_entry_outbox_event_key"):
        op.create_index(
            "uk_ly_whse_stock_entry_outbox_event_key",
            _OUTBOX_TABLE,
            ["event_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_whse_stock_entry_outbox_draft"):
        op.create_index(
            "idx_ly_whse_stock_entry_outbox_draft",
            _OUTBOX_TABLE,
            ["draft_id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_whse_stock_entry_outbox_status"):
        op.create_index(
            "idx_ly_whse_stock_entry_outbox_status",
            _OUTBOX_TABLE,
            ["status", "retry_count", "id"],
            schema=schema,
        )


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)

    _create_draft_table(bind, schema)
    _create_item_table(bind, schema)
    _create_outbox_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    _drop_index_if_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_whse_stock_entry_outbox_status")
    _drop_index_if_exists(bind, schema, _OUTBOX_TABLE, "idx_ly_whse_stock_entry_outbox_draft")
    _drop_index_if_exists(bind, schema, _OUTBOX_TABLE, "uk_ly_whse_stock_entry_outbox_event_key")

    _drop_index_if_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_stock_entry_item_company_item")
    _drop_index_if_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_stock_entry_item_draft")

    _drop_index_if_exists(bind, schema, _DRAFT_TABLE, "idx_ly_whse_stock_entry_draft_company_status")
    _drop_index_if_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_company_source")
    _drop_index_if_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_company_idempotency")
    _drop_index_if_exists(bind, schema, _DRAFT_TABLE, "uk_ly_whse_stock_entry_draft_event_key")

    if _table_exists(bind, schema, _OUTBOX_TABLE):
        op.drop_table(_OUTBOX_TABLE, schema=schema)
    if _table_exists(bind, schema, _ITEM_TABLE):
        op.drop_table(_ITEM_TABLE, schema=schema)
    if _table_exists(bind, schema, _DRAFT_TABLE):
        op.drop_table(_DRAFT_TABLE, schema=schema)
