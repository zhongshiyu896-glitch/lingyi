"""create small-factory production notice table

Revision ID: task_106a_create_production_notice
Revises: task_105a_add_production_start_factory_fields
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "task_106a_create_production_notice"
down_revision = "task_105a_add_production_start_factory_fields"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_notice"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(str(index.get("name")) == index_name for index in sa.inspect(bind).get_indexes(table_name, schema=schema))


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if schema is not None:
        op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    if _table_exists(bind, schema, _TABLE):
        return

    op.create_table(
        _TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("notice_no", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("sales_order_id", _id_type(bind), nullable=True),
        sa.Column("sales_order", sa.String(length=140), nullable=False),
        sa.Column("customer", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("factory_name", sa.String(length=140), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("order_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("style_image_url", sa.Text(), nullable=True),
        sa.Column("workmanship_template_id", _id_type(bind), nullable=True),
        sa.Column("size_template_id", _id_type(bind), nullable=True),
        sa.Column("color_size_matrix", sa.JSON(), nullable=False),
        sa.Column("workmanship_snapshot", sa.JSON(), nullable=False),
        sa.Column("size_chart_snapshot", sa.JSON(), nullable=False),
        sa.Column("cutting_plan", sa.JSON(), nullable=False),
        sa.Column("process_text", sa.Text(), nullable=True),
        sa.Column("packaging_text", sa.Text(), nullable=True),
        sa.Column("label_text", sa.Text(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("order_qty >= 0", name="ck_ly_production_notice_order_qty_nonnegative"),
        sa.CheckConstraint("status IN ('draft','confirmed','sent')", name="ck_ly_production_notice_status"),
        schema=schema,
    )
    op.create_index("uk_ly_production_notice_no", _TABLE, ["company", "notice_no"], unique=True, schema=schema)
    op.create_index("uk_ly_production_notice_sales_order", _TABLE, ["company", "sales_order"], unique=True, schema=schema)
    op.create_index("idx_ly_production_notice_status", _TABLE, ["company", "status"], schema=schema)
    op.create_index("idx_ly_production_notice_item", _TABLE, ["company", "item_code"], schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for index_name in [
        "idx_ly_production_notice_item",
        "idx_ly_production_notice_status",
        "uk_ly_production_notice_sales_order",
        "uk_ly_production_notice_no",
    ]:
        _drop_index_if_exists(bind, schema, _TABLE, index_name)
    if _table_exists(bind, schema, _TABLE):
        op.drop_table(_TABLE, schema=schema)
