"""TASK-063A create sales order tables and style calc fields.

Revision ID: task_063a_sales_order_style_calc_fields
Revises: task_062c_extend_sample_idempotency_operations
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_063a_sales_order_style_calc_fields"
down_revision = "task_062c_extend_sample_idempotency_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_sales_order"
_ITEM_TABLE = "ly_sales_order_item"
_IDEM_TABLE = "ly_sales_order_idempotency"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type():
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _constraint_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    if _is_sqlite(bind):
        return False
    inspector = sa.inspect(bind)
    for constraint in inspector.get_check_constraints(table_name, schema=schema):
        if str(constraint.get("name")) == constraint_name:
            return True
    return False


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_order_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ORDER_TABLE):
        return
    op.create_table(
        _ORDER_TABLE,
        sa.Column("id", _id_type(), primary_key=True, autoincrement=True),
        sa.Column("sales_order_no", sa.String(length=140), nullable=False),
        sa.Column("source_order_ref", sa.String(length=140), nullable=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("customer", sa.String(length=140), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("docstatus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False, server_default="CNY"),
        sa.Column("grand_total", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("scenario_tag", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cancelled_by", sa.String(length=140), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.CheckConstraint("status IN ('draft','planned','cancelled')", name="ck_ly_sales_order_status"),
        schema=schema,
    )


def _create_item_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ITEM_TABLE):
        return
    fk_target = f"{_SCHEMA_NAME}.ly_sales_order.id" if schema else "ly_sales_order.id"
    op.create_table(
        _ITEM_TABLE,
        sa.Column("id", _id_type(), primary_key=True, autoincrement=True),
        sa.Column("sales_order_id", _id_type(), sa.ForeignKey(fk_target), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("sales_order_item", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("delivered_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("ys_material_calc_state", sa.String(length=32), nullable=False, server_default="待算料"),
        sa.Column("rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("uom", sa.String(length=32), nullable=False, server_default="Nos"),
        sa.Column("warehouse", sa.String(length=140), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.CheckConstraint("qty > 0", name="ck_ly_sales_order_item_qty_positive"),
        sa.CheckConstraint("ys_material_calc_state IN ('待算料','已算料')", name="ck_ly_sales_order_item_calc_state"),
        schema=schema,
    )


def _create_idempotency_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _IDEM_TABLE):
        return
    op.create_table(
        _IDEM_TABLE,
        sa.Column("id", _id_type(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("sales_order_id", _id_type(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operation IN ('create_draft','cancel_draft')", name="ck_ly_sales_order_idem_operation"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_ORDER_TABLE, "uk_ly_sales_order_company_no", ["company", "sales_order_no"], True),
        (_ORDER_TABLE, "idx_ly_sales_order_company_status", ["company", "status"], False),
        (_ORDER_TABLE, "idx_ly_sales_order_customer", ["customer"], False),
        (_ITEM_TABLE, "uk_ly_sales_order_item_line", ["sales_order_id", "line_no"], True),
        (_ITEM_TABLE, "idx_ly_sales_order_item_order", ["sales_order_id"], False),
        (_ITEM_TABLE, "idx_ly_sales_order_item_code", ["company", "item_code"], False),
        (_ITEM_TABLE, "idx_ly_sales_order_item_material_calc", ["company", "ys_material_calc_state"], False),
        (_IDEM_TABLE, "uk_ly_sales_order_idem", ["company", "operation", "idempotency_key"], True),
        (_IDEM_TABLE, "idx_ly_sales_order_idem_order", ["sales_order_id"], False),
    ]
    for table_name, index_name, columns, unique in indexes:
        if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _extend_existing_item_table(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _ITEM_TABLE):
        return
    if not _column_exists(bind, schema, _ITEM_TABLE, "color"):
        op.add_column(_ITEM_TABLE, sa.Column("color", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, _ITEM_TABLE, "size"):
        op.add_column(_ITEM_TABLE, sa.Column("size", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, _ITEM_TABLE, "ys_material_calc_state"):
        op.add_column(
            _ITEM_TABLE,
            sa.Column("ys_material_calc_state", sa.String(length=32), nullable=False, server_default="待算料"),
            schema=schema,
        )
    if not _is_sqlite(bind) and not _constraint_exists(bind, schema, _ITEM_TABLE, "ck_ly_sales_order_item_calc_state"):
        op.create_check_constraint(
            "ck_ly_sales_order_item_calc_state",
            _ITEM_TABLE,
            "ys_material_calc_state IN ('待算料','已算料')",
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_order_table(bind, schema)
    _create_item_table(bind, schema)
    _create_idempotency_table(bind, schema)
    _extend_existing_item_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _drop_index_if_exists(bind, schema, _ITEM_TABLE, "idx_ly_sales_order_item_material_calc")
    if _table_exists(bind, schema, _ITEM_TABLE):
        if not _is_sqlite(bind) and _constraint_exists(bind, schema, _ITEM_TABLE, "ck_ly_sales_order_item_calc_state"):
            op.drop_constraint("ck_ly_sales_order_item_calc_state", _ITEM_TABLE, schema=schema, type_="check")
        for column_name in ["ys_material_calc_state", "size", "color"]:
            if _column_exists(bind, schema, _ITEM_TABLE, column_name):
                op.drop_column(_ITEM_TABLE, column_name, schema=schema)
