"""TASK-093A create warehouse stock ledger entry table.

Revision ID: task_093a_create_warehouse_stock_ledger_entry
Revises: task_092a_add_purchase_requirement_allocation_to_stock_entry_items
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_093a_create_warehouse_stock_ledger_entry"
down_revision = "task_092a_add_purchase_requirement_allocation_to_stock_entry_items"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_warehouse_stock_ledger_entry"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(table_name, schema=schema))


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_index_if_missing(bind, schema: str | None, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, _TABLE) and not _index_exists(bind, schema, _TABLE, index_name):
        op.create_index(index_name, _TABLE, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, index_name: str) -> None:
    if _table_exists(bind, schema, _TABLE) and _index_exists(bind, schema, _TABLE, index_name):
        op.drop_index(index_name, table_name=_TABLE, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    id_type = _id_type(bind)
    if not _table_exists(bind, schema, _TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", id_type, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("warehouse", sa.String(length=140), nullable=False),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("uom", sa.String(length=32), nullable=True),
            sa.Column("posting_date", sa.Date(), nullable=False),
            sa.Column("sort_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_type", sa.String(length=64), nullable=False),
            sa.Column("source_id", sa.String(length=140), nullable=False),
            sa.Column("source_line_id", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("voucher_type", sa.String(length=140), nullable=False),
            sa.Column("voucher_no", sa.String(length=140), nullable=False),
            sa.Column("actual_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("valuation_rate", sa.Numeric(18, 6), nullable=True),
            sa.Column("batch_no", sa.String(length=140), nullable=True),
            sa.Column("serial_no", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("projected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_ly_whse_stock_ledger_entry"),
            sa.CheckConstraint("status IN ('active','voided')", name="ck_ly_whse_stock_ledger_status"),
            schema=schema,
        )
    _create_index_if_missing(
        bind,
        schema,
        "uk_ly_whse_stock_ledger_source",
        ["company", "source_type", "source_id", "source_line_id", "sequence"],
        unique=True,
    )
    _create_index_if_missing(
        bind,
        schema,
        "idx_ly_whse_stock_ledger_company_wh_item",
        ["company", "warehouse", "item_code", "status", "posting_date", "sort_at", "id"],
    )
    _create_index_if_missing(bind, schema, "idx_ly_whse_stock_ledger_voucher", ["voucher_type", "voucher_no"])


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    for index_name in [
        "idx_ly_whse_stock_ledger_voucher",
        "idx_ly_whse_stock_ledger_company_wh_item",
        "uk_ly_whse_stock_ledger_source",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    op.drop_table(_TABLE, schema=schema)
