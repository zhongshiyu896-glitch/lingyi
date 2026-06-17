"""TASK-061B create production tracking reconcile tables.

Revision ID: task_061b_create_production_tracking_reconcile
Revises: task_061a_create_material_purchase_invoice_payment
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_061b_create_production_tracking_reconcile"
down_revision = "task_061a_create_material_purchase_invoice_payment"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_BATCH_TABLE = "ly_production_tracking_reconcile_batch"
_RECONCILE_TABLE = "ly_production_tracking_reconcile"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type():
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


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
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_batch_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _BATCH_TABLE):
        return
    op.create_table(
        _BATCH_TABLE,
        sa.Column("id", _id_type(), autoincrement=True),
        sa.Column("batch_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmatched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_production_tracking_reconcile_batch"),
        schema=schema,
    )


def _create_reconcile_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _RECONCILE_TABLE):
        return
    op.create_table(
        _RECONCILE_TABLE,
        sa.Column("id", _id_type(), autoincrement=True),
        sa.Column("reconcile_no", sa.String(length=64), nullable=False),
        sa.Column("batch_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("sample_order_id", sa.BigInteger(), nullable=False),
        sa.Column("sample_no", sa.String(length=140), nullable=False),
        sa.Column("style_no", sa.String(length=140), nullable=False),
        sa.Column("style_name", sa.String(length=255), nullable=False),
        sa.Column("image_tone", sa.String(length=32), nullable=False, server_default="gray"),
        sa.Column("customer", sa.String(length=255), nullable=False),
        sa.Column("sample_type", sa.String(length=32), nullable=False),
        sa.Column("sealed_date", sa.Date(), nullable=True),
        sa.Column("sales_order", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("sales_order_id", sa.BigInteger(), nullable=True),
        sa.Column("sales_order_item_id", sa.BigInteger(), nullable=True),
        sa.Column("sample_qty", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("order_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("sample_price", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("diff_status", sa.String(length=32), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "diff_status IN ('matched','unmatched','quantity_diff','price_diff','late_order')",
            name="ck_ly_production_tracking_reconcile_diff_status",
        ),
        sa.CheckConstraint("sample_qty >= 0", name="ck_ly_production_tracking_reconcile_sample_qty_nonnegative"),
        sa.CheckConstraint("order_qty >= 0", name="ck_ly_production_tracking_reconcile_order_qty_nonnegative"),
        sa.CheckConstraint("sample_price >= 0", name="ck_ly_production_tracking_reconcile_sample_price_nonnegative"),
        sa.CheckConstraint("unit_price >= 0", name="ck_ly_production_tracking_reconcile_unit_price_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_ly_production_tracking_reconcile"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_BATCH_TABLE, "uk_ly_production_tracking_reconcile_batch_no", ["batch_no"], True),
        (_BATCH_TABLE, "uk_ly_production_tracking_reconcile_batch_idem", ["company", "idempotency_key"], True),
        (_BATCH_TABLE, "idx_ly_production_tracking_reconcile_batch_company_time", ["company", "created_at"], False),
        (_RECONCILE_TABLE, "uk_ly_production_tracking_reconcile_no", ["reconcile_no"], True),
        (_RECONCILE_TABLE, "uk_ly_production_tracking_reconcile_sample", ["company", "sample_no"], True),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_company_status", ["company", "diff_status"], False),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_customer", ["company", "customer"], False),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_sales_order", ["company", "sales_order"], False),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_batch", ["batch_no"], False),
    ]
    for table_name, index_name, columns, unique in indexes:
        if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_batch_table(bind, schema)
    _create_reconcile_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, index_name in [
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_batch"),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_sales_order"),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_customer"),
        (_RECONCILE_TABLE, "idx_ly_production_tracking_reconcile_company_status"),
        (_RECONCILE_TABLE, "uk_ly_production_tracking_reconcile_sample"),
        (_RECONCILE_TABLE, "uk_ly_production_tracking_reconcile_no"),
        (_BATCH_TABLE, "idx_ly_production_tracking_reconcile_batch_company_time"),
        (_BATCH_TABLE, "uk_ly_production_tracking_reconcile_batch_idem"),
        (_BATCH_TABLE, "uk_ly_production_tracking_reconcile_batch_no"),
    ]:
        _drop_index_if_exists(bind, schema, table_name, index_name)
    if _table_exists(bind, schema, _RECONCILE_TABLE):
        op.drop_table(_RECONCILE_TABLE, schema=schema)
    if _table_exists(bind, schema, _BATCH_TABLE):
        op.drop_table(_BATCH_TABLE, schema=schema)
