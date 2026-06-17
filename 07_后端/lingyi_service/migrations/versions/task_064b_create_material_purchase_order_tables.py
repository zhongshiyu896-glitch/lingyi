"""TASK-064B create material purchase order base tables.

Revision ID: task_064b_create_material_purchase_order_tables
Revises: task_064a_create_sample_tracking_events
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_064b_create_material_purchase_order_tables"
down_revision = "task_064a_create_sample_tracking_events"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_material_purchase_order"
_ITEM_TABLE = "ly_material_purchase_order_item"
_IDEM_TABLE = "ly_material_purchase_idempotency"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _fk_target(bind, table_name: str, column_name: str) -> str:
    if _is_sqlite(bind):
        return f"{table_name}.{column_name}"
    return f"{_SCHEMA_NAME}.{table_name}.{column_name}"


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


def _create_order_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ORDER_TABLE):
        return
    op.create_table(
        _ORDER_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("purchase_no", sa.String(length=140), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("total_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=32), nullable=False, server_default="CNY"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('draft','partially_received','received','cancelled')",
            name="ck_ly_material_purchase_order_status",
        ),
        schema=schema,
    )


def _create_item_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ITEM_TABLE):
        return
    op.create_table(
        _ITEM_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("order_id", _id_type(bind), sa.ForeignKey(_fk_target(bind, _ORDER_TABLE, "id")), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("material_item_code", sa.String(length=140), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(length=32), nullable=False, server_default="米"),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("warehouse", sa.String(length=140), nullable=True),
        sa.CheckConstraint("qty > 0", name="ck_ly_material_purchase_order_item_qty_positive"),
        sa.CheckConstraint("received_qty >= 0", name="ck_ly_material_purchase_order_item_received_nonnegative"),
        schema=schema,
    )


def _create_idempotency_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _IDEM_TABLE):
        return
    op.create_table(
        _IDEM_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("record_id", _id_type(bind), nullable=False),
        sa.Column("response_data", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_ORDER_TABLE, "uk_ly_material_purchase_order_company_no", ["company", "purchase_no"], True),
        (_ORDER_TABLE, "idx_ly_material_purchase_order_supplier_status", ["company", "supplier_name", "status"], False),
        (_ITEM_TABLE, "idx_ly_material_purchase_order_item_order", ["order_id"], False),
        (_ITEM_TABLE, "idx_ly_material_purchase_order_item_material", ["company", "material_item_code"], False),
        (_IDEM_TABLE, "uk_ly_material_purchase_idem_company_key", ["company", "idempotency_key"], True),
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
    _create_order_table(bind, schema)
    _create_item_table(bind, schema)
    _create_idempotency_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, index_name in [
        (_IDEM_TABLE, "uk_ly_material_purchase_idem_company_key"),
        (_ITEM_TABLE, "idx_ly_material_purchase_order_item_material"),
        (_ITEM_TABLE, "idx_ly_material_purchase_order_item_order"),
        (_ORDER_TABLE, "idx_ly_material_purchase_order_supplier_status"),
        (_ORDER_TABLE, "uk_ly_material_purchase_order_company_no"),
    ]:
        _drop_index_if_exists(bind, schema, table_name, index_name)
    for table_name in [_IDEM_TABLE, _ITEM_TABLE, _ORDER_TABLE]:
        if _table_exists(bind, schema, table_name):
            op.drop_table(table_name, schema=schema)
