"""TASK-060A create delivery invoice table.

Revision ID: task_060a_create_delivery_invoice_table
Revises: task_050c_create_warehouse_inventory_count
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_060a_create_delivery_invoice_table"
down_revision = "task_050c_create_warehouse_inventory_count"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_delivery_invoice"


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


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("delivery_note", sa.String(length=140), nullable=False),
        sa.Column("sales_invoice", sa.String(length=140), nullable=False),
        sa.Column("sales_order", sa.String(length=140), nullable=False),
        sa.Column("customer", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("warehouse", sa.String(length=140), nullable=False),
        sa.Column("delivered_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom", sa.String(length=32), nullable=False, server_default="Nos"),
        sa.Column("rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("grand_total", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("outstanding_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("docstatus", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_ref", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("scenario_tag", sa.String(length=64), nullable=True),
        sa.Column("warehouse_draft_id", sa.BigInteger(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "status IN ('submitted','partly_paid','paid','cancelled')",
            name="ck_ly_delivery_invoice_status",
        ),
        sa.CheckConstraint("delivered_qty > 0", name="ck_ly_delivery_invoice_qty_positive"),
        sa.CheckConstraint("grand_total >= 0", name="ck_ly_delivery_invoice_grand_total_nonnegative"),
        sa.CheckConstraint("paid_amount >= 0", name="ck_ly_delivery_invoice_paid_nonnegative"),
        sa.CheckConstraint("outstanding_amount >= 0", name="ck_ly_delivery_invoice_outstanding_nonnegative"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        ("uk_ly_delivery_invoice_company_dn", ["company", "delivery_note"], True),
        ("uk_ly_delivery_invoice_company_si", ["company", "sales_invoice"], True),
        ("uk_ly_delivery_invoice_company_idem", ["company", "idempotency_key"], True),
        ("uk_ly_delivery_invoice_company_source", ["company", "source_ref"], True),
        ("idx_ly_delivery_invoice_order", ["company", "sales_order"], False),
        ("idx_ly_delivery_invoice_customer", ["company", "customer"], False),
    ]
    for index_name, columns, unique in indexes:
        if not _index_exists(bind, schema, _TABLE, index_name):
            op.create_index(index_name, _TABLE, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, index_name: str) -> None:
    if _table_exists(bind, schema, _TABLE) and _index_exists(bind, schema, _TABLE, index_name):
        op.drop_index(index_name, table_name=_TABLE, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for index_name in [
        "idx_ly_delivery_invoice_customer",
        "idx_ly_delivery_invoice_order",
        "uk_ly_delivery_invoice_company_source",
        "uk_ly_delivery_invoice_company_idem",
        "uk_ly_delivery_invoice_company_si",
        "uk_ly_delivery_invoice_company_dn",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    if _table_exists(bind, schema, _TABLE):
        op.drop_table(_TABLE, schema=schema)
