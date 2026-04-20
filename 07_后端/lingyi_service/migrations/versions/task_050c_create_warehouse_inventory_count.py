"""TASK-050C create warehouse inventory-count tables.

Revision ID: task_050c_create_warehouse_inventory_count
Revises: task_050b_create_warehouse_stock_entry_outbox
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_050c_create_warehouse_inventory_count"
down_revision = "task_050b_create_warehouse_stock_entry_outbox"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_COUNT_TABLE = "ly_warehouse_inventory_count"
_ITEM_TABLE = "ly_warehouse_inventory_count_item"


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


def _create_count_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _COUNT_TABLE):
        return
    op.create_table(
        _COUNT_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("warehouse", sa.String(length=140), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("count_no", sa.String(length=140), nullable=False),
        sa.Column("count_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_by", sa.String(length=140), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=140), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','counted','variance_review','confirmed','cancelled')",
            name="ck_ly_whse_inv_count_status",
        ),
        schema=schema,
    )


def _create_item_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ITEM_TABLE):
        return
    op.create_table(
        _ITEM_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("count_id", sa.BigInteger(), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("warehouse", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("batch_no", sa.String(length=140), nullable=True),
        sa.Column("serial_no", sa.String(length=500), nullable=True),
        sa.Column("system_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("counted_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_reason", sa.String(length=255), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.ForeignKeyConstraint(
            ["count_id"],
            [_qualified_table(schema, _COUNT_TABLE) + ".id"],
            name="fk_ly_whse_inv_count_item_count",
        ),
        sa.CheckConstraint("system_qty >= 0", name="ck_ly_whse_inv_count_item_system_qty_nonnegative"),
        sa.CheckConstraint("counted_qty >= 0", name="ck_ly_whse_inv_count_item_counted_qty_nonnegative"),
        sa.CheckConstraint(
            "review_status IN ('pending','accepted','rejected')",
            name="ck_ly_whse_inv_count_item_review_status",
        ),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    if not _index_exists(bind, schema, _COUNT_TABLE, "uk_ly_whse_inv_count_company_count_no"):
        op.create_index(
            "uk_ly_whse_inv_count_company_count_no",
            _COUNT_TABLE,
            ["company", "count_no"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, _COUNT_TABLE, "idx_ly_whse_inv_count_company_warehouse"):
        op.create_index(
            "idx_ly_whse_inv_count_company_warehouse",
            _COUNT_TABLE,
            ["company", "warehouse"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _COUNT_TABLE, "idx_ly_whse_inv_count_status_date"):
        op.create_index(
            "idx_ly_whse_inv_count_status_date",
            _COUNT_TABLE,
            ["status", "count_date", "id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_inv_count_item_count_id"):
        op.create_index(
            "idx_ly_whse_inv_count_item_count_id",
            _ITEM_TABLE,
            ["count_id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_inv_count_item_company_wh_item"):
        op.create_index(
            "idx_ly_whse_inv_count_item_company_wh_item",
            _ITEM_TABLE,
            ["company", "warehouse", "item_code"],
            schema=schema,
        )


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_count_table(bind, schema)
    _create_item_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _drop_index_if_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_inv_count_item_company_wh_item")
    _drop_index_if_exists(bind, schema, _ITEM_TABLE, "idx_ly_whse_inv_count_item_count_id")
    _drop_index_if_exists(bind, schema, _COUNT_TABLE, "idx_ly_whse_inv_count_status_date")
    _drop_index_if_exists(bind, schema, _COUNT_TABLE, "idx_ly_whse_inv_count_company_warehouse")
    _drop_index_if_exists(bind, schema, _COUNT_TABLE, "uk_ly_whse_inv_count_company_count_no")
    if _table_exists(bind, schema, _ITEM_TABLE):
        op.drop_table(_ITEM_TABLE, schema=schema)
    if _table_exists(bind, schema, _COUNT_TABLE):
        op.drop_table(_COUNT_TABLE, schema=schema)
