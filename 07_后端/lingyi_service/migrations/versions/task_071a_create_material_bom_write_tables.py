"""TASK-071A create material BOM write and sample BOM tables.

Revision ID: task_071a_create_material_bom_write_tables
Revises: task_070a_create_production_tracking_exception
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_071a_create_material_bom_write_tables"
down_revision = "task_070a_create_production_tracking_exception"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_BOM_TABLE = "ly_apparel_bom"
_BOM_ITEM_TABLE = "ly_apparel_bom_item"
_BOM_OPERATION_TABLE = "ly_apparel_bom_write_operation"
_SAMPLE_ORDER_TABLE = "ly_sample_order"
_SAMPLE_BOM_TABLE = "ly_sample_material_bom"
_SAMPLE_BOM_ITEM_TABLE = "ly_sample_material_bom_item"
_SAMPLE_BOM_OPERATION_TABLE = "ly_sample_material_bom_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(table_name, schema=schema))


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _add_bom_item_part_column(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _BOM_ITEM_TABLE) or _column_exists(bind, schema, _BOM_ITEM_TABLE, "part"):
        return
    column = sa.Column("part", sa.String(length=100), nullable=True)
    if _is_sqlite(bind):
        with op.batch_alter_table(_BOM_ITEM_TABLE, schema=schema) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(_BOM_ITEM_TABLE, column, schema=schema)


def _drop_bom_item_part_column(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _BOM_ITEM_TABLE) or not _column_exists(bind, schema, _BOM_ITEM_TABLE, "part"):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_BOM_ITEM_TABLE, schema=schema) as batch_op:
            batch_op.drop_column("part")
        return
    op.drop_column(_BOM_ITEM_TABLE, "part", schema=schema)


def _create_style_bom_operation_table(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _BOM_TABLE) or _table_exists(bind, schema, _BOM_OPERATION_TABLE):
        return
    id_type = _id_type(bind)
    op.create_table(
        _BOM_OPERATION_TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("bom_id", id_type, nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operation IN ('style_material_bom_upsert')", name="ck_ly_apparel_bom_write_operation"),
        schema=schema,
    )
    op.create_index(
        "uk_ly_apparel_bom_write_operation_idem",
        _BOM_OPERATION_TABLE,
        ["company", "operation", "idempotency_key"],
        unique=True,
        schema=schema,
    )
    op.create_index(
        "idx_ly_apparel_bom_write_operation_bom",
        _BOM_OPERATION_TABLE,
        ["bom_id", "operation"],
        schema=schema,
    )


def _create_sample_bom_tables(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _SAMPLE_ORDER_TABLE):
        return
    id_type = _id_type(bind)
    if not _table_exists(bind, schema, _SAMPLE_BOM_TABLE):
        op.create_table(
            _SAMPLE_BOM_TABLE,
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("sample_order_id", id_type, nullable=False),
            sa.Column("style_master_id", id_type, nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("source_bom_id", id_type, nullable=True),
            sa.Column("version_no", sa.String(length=32), nullable=False, server_default="S1"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_by", sa.String(length=140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["sample_order_id"],
                [_qualified(schema, _SAMPLE_ORDER_TABLE) + ".id"],
                name="fk_ly_sample_material_bom_order",
            ),
            sa.CheckConstraint("status IN ('draft','active')", name="ck_ly_sample_material_bom_status"),
            schema=schema,
        )
    if not _table_exists(bind, schema, _SAMPLE_BOM_ITEM_TABLE):
        op.create_table(
            _SAMPLE_BOM_ITEM_TABLE,
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("bom_id", id_type, nullable=False),
            sa.Column("source_bom_item_id", id_type, nullable=True),
            sa.Column("material_item_code", sa.String(length=140), nullable=False),
            sa.Column("color", sa.String(length=64), nullable=True),
            sa.Column("part", sa.String(length=100), nullable=True),
            sa.Column("qty_per_piece", sa.Numeric(18, 6), nullable=False),
            sa.Column("loss_rate", sa.Numeric(12, 6), nullable=False, server_default="0"),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("is_alternative", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("replace_group", sa.String(length=64), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["bom_id"],
                [_qualified(schema, _SAMPLE_BOM_TABLE) + ".id"],
                name="fk_ly_sample_material_bom_item_bom",
            ),
            sa.CheckConstraint("qty_per_piece > 0", name="ck_ly_sample_material_bom_item_qty"),
            sa.CheckConstraint("loss_rate >= 0", name="ck_ly_sample_material_bom_item_loss"),
            schema=schema,
        )
    if not _table_exists(bind, schema, _SAMPLE_BOM_OPERATION_TABLE):
        op.create_table(
            _SAMPLE_BOM_OPERATION_TABLE,
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("bom_id", id_type, nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("operation", sa.String(length=32), nullable=False),
            sa.Column("idempotency_key", sa.String(length=140), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("response_json", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("operation IN ('upsert','copy_from_style')", name="ck_ly_sample_material_bom_operation"),
            schema=schema,
        )


def _create_index_if_needed(bind, schema: str | None, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _create_sample_bom_indexes(bind, schema: str | None) -> None:
    _create_index_if_needed(bind, schema, _SAMPLE_BOM_TABLE, "uk_ly_sample_material_bom_order", ["company", "sample_order_id"], unique=True)
    _create_index_if_needed(bind, schema, _SAMPLE_BOM_TABLE, "idx_ly_sample_material_bom_style", ["company", "style_master_id"])
    _create_index_if_needed(bind, schema, _SAMPLE_BOM_ITEM_TABLE, "idx_ly_sample_material_bom_item_bom", ["bom_id"])
    _create_index_if_needed(bind, schema, _SAMPLE_BOM_ITEM_TABLE, "idx_ly_sample_material_bom_item_material", ["material_item_code"])
    _create_index_if_needed(
        bind,
        schema,
        _SAMPLE_BOM_OPERATION_TABLE,
        "uk_ly_sample_material_bom_operation_idem",
        ["company", "operation", "idempotency_key"],
        unique=True,
    )
    _create_index_if_needed(
        bind,
        schema,
        _SAMPLE_BOM_OPERATION_TABLE,
        "idx_ly_sample_material_bom_operation_bom",
        ["bom_id", "operation"],
    )


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def _drop_table_if_exists(bind, schema: str | None, table_name: str) -> None:
    if _table_exists(bind, schema, table_name):
        op.drop_table(table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _add_bom_item_part_column(bind, schema)
    _create_style_bom_operation_table(bind, schema)
    _create_sample_bom_tables(bind, schema)
    _create_sample_bom_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, index_name in [
        (_SAMPLE_BOM_OPERATION_TABLE, "idx_ly_sample_material_bom_operation_bom"),
        (_SAMPLE_BOM_OPERATION_TABLE, "uk_ly_sample_material_bom_operation_idem"),
        (_SAMPLE_BOM_ITEM_TABLE, "idx_ly_sample_material_bom_item_material"),
        (_SAMPLE_BOM_ITEM_TABLE, "idx_ly_sample_material_bom_item_bom"),
        (_SAMPLE_BOM_TABLE, "idx_ly_sample_material_bom_style"),
        (_SAMPLE_BOM_TABLE, "uk_ly_sample_material_bom_order"),
        (_BOM_OPERATION_TABLE, "idx_ly_apparel_bom_write_operation_bom"),
        (_BOM_OPERATION_TABLE, "uk_ly_apparel_bom_write_operation_idem"),
    ]:
        _drop_index_if_exists(bind, schema, table_name, index_name)
    _drop_table_if_exists(bind, schema, _SAMPLE_BOM_OPERATION_TABLE)
    _drop_table_if_exists(bind, schema, _SAMPLE_BOM_ITEM_TABLE)
    _drop_table_if_exists(bind, schema, _SAMPLE_BOM_TABLE)
    _drop_table_if_exists(bind, schema, _BOM_OPERATION_TABLE)
    _drop_bom_item_part_column(bind, schema)
