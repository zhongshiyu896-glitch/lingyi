"""TASK-090A create factory packing registration table.

Revision ID: task_090a_create_factory_packing
Revises: task_089a_extend_sales_order_submit_idempotency
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_090a_create_factory_packing"
down_revision = "task_089a_extend_sales_order_submit_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_factory_packing"
_PLAN_TABLE = "ly_production_plan"


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


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


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
    if not _table_exists(bind, schema, _PLAN_TABLE) or _table_exists(bind, schema, _TABLE):
        return
    _ensure_schema(bind)
    id_type = _id_type(bind)
    op.create_table(
        _TABLE,
        sa.Column("id", id_type, autoincrement=True),
        sa.Column("packing_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("plan_id", id_type, nullable=False),
        sa.Column("plan_no", sa.String(length=64), nullable=False),
        sa.Column("sales_order", sa.String(length=140), nullable=False),
        sa.Column("sales_order_item", sa.String(length=140), nullable=False),
        sa.Column("customer", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("inbound_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("outbound_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("carton_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("box_spec", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("source_ref", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("remark", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_factory_packing"),
        sa.ForeignKeyConstraint(["plan_id"], [_qualified(schema, _PLAN_TABLE) + ".id"], name="fk_ly_factory_packing_plan"),
        sa.CheckConstraint("inbound_qty >= 0", name="ck_ly_factory_packing_inbound_qty_nonnegative"),
        sa.CheckConstraint("outbound_qty >= 0", name="ck_ly_factory_packing_outbound_qty_nonnegative"),
        sa.CheckConstraint("carton_qty >= 0", name="ck_ly_factory_packing_carton_qty_nonnegative"),
        sa.CheckConstraint("status IN ('active','cancelled')", name="ck_ly_factory_packing_status"),
        schema=schema,
    )
    _create_index_if_missing(bind, schema, "uk_ly_factory_packing_no", ["company", "packing_no"], unique=True)
    _create_index_if_missing(bind, schema, "uk_ly_factory_packing_idem", ["company", "idempotency_key"], unique=True)
    _create_index_if_missing(bind, schema, "idx_ly_factory_packing_plan", ["plan_id", "status"])
    _create_index_if_missing(bind, schema, "idx_ly_factory_packing_order_item", ["company", "sales_order", "item_code", "status"])


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    for index_name in [
        "idx_ly_factory_packing_order_item",
        "idx_ly_factory_packing_plan",
        "uk_ly_factory_packing_idem",
        "uk_ly_factory_packing_no",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    op.drop_table(_TABLE, schema=schema)
