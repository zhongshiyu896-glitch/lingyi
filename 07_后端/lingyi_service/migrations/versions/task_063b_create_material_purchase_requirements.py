"""TASK-063B create material purchase requirement pool.

Revision ID: task_063b_create_material_purchase_requirements
Revises: task_063a_sales_order_style_calc_fields
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_063b_create_material_purchase_requirements"
down_revision = "task_063a_sales_order_style_calc_fields"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_material_purchase_requirement"


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


def _create_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", _id_type(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("requirement_no", sa.String(length=140), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=140), nullable=False),
        sa.Column("source_no", sa.String(length=140), nullable=True),
        sa.Column("plan_id", _id_type(), nullable=True),
        sa.Column("bom_item_id", _id_type(), nullable=True),
        sa.Column("sales_order", sa.String(length=140), nullable=True),
        sa.Column("sales_order_item", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=True),
        sa.Column("material_item_code", sa.String(length=140), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("warehouse", sa.String(length=140), nullable=False),
        sa.Column("required_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("available_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_required_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("purchased_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(length=32), nullable=False, server_default="米"),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("purchase_order_id", _id_type(), nullable=True),
        sa.Column("purchase_order_item_id", _id_type(), nullable=True),
        sa.Column("purchase_no", sa.String(length=140), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "company",
            "source_type",
            "source_id",
            "bom_item_id",
            "material_item_code",
            "warehouse",
            name="uk_ly_material_purchase_req_source_material",
        ),
        sa.CheckConstraint("status IN ('pending','purchased','completed','cancelled')", name="ck_ly_material_purchase_req_status"),
        sa.CheckConstraint("required_qty >= 0", name="ck_ly_material_purchase_req_required_nonnegative"),
        sa.CheckConstraint("available_qty >= 0", name="ck_ly_material_purchase_req_available_nonnegative"),
        sa.CheckConstraint("net_required_qty >= 0", name="ck_ly_material_purchase_req_net_nonnegative"),
        sa.CheckConstraint("purchased_qty >= 0", name="ck_ly_material_purchase_req_purchased_nonnegative"),
        sa.CheckConstraint("received_qty >= 0", name="ck_ly_material_purchase_req_received_nonnegative"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        ("uk_ly_material_purchase_req_company_no", ["company", "requirement_no"], True),
        ("idx_ly_material_purchase_req_status", ["company", "status"], False),
        ("idx_ly_material_purchase_req_material", ["company", "material_item_code", "status"], False),
        ("idx_ly_material_purchase_req_purchase", ["company", "purchase_no"], False),
    ]
    for index_name, columns, unique in indexes:
        if _table_exists(bind, schema, _TABLE) and not _index_exists(bind, schema, _TABLE, index_name):
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
        "idx_ly_material_purchase_req_purchase",
        "idx_ly_material_purchase_req_material",
        "idx_ly_material_purchase_req_status",
        "uk_ly_material_purchase_req_company_no",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    if _table_exists(bind, schema, _TABLE):
        op.drop_table(_TABLE, schema=schema)
