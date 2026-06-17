"""TASK-065A add BOM company and style master link.

Revision ID: task_065a_add_bom_company_style_master_link
Revises: task_064b_create_material_purchase_order_tables
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_065a_add_bom_company_style_master_link"
down_revision = "task_064b_create_material_purchase_order_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_BOM_TABLE = "ly_apparel_bom"
_STYLE_TABLE = "ly_style_master"
_DEFAULT_COMPANY = "默认公司"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified(bind, table_name: str) -> str:
    if _is_sqlite(bind):
        return table_name
    return f"{_SCHEMA_NAME}.{table_name}"


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(table_name, schema=schema))


def _drop_index_if_exists(bind, schema: str | None, index_name: str) -> None:
    if _table_exists(bind, schema, _BOM_TABLE) and _index_exists(bind, schema, _BOM_TABLE, index_name):
        op.drop_index(index_name, table_name=_BOM_TABLE, schema=schema)


def _create_indexes(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _BOM_TABLE):
        return
    if not _index_exists(bind, schema, _BOM_TABLE, "idx_ly_apparel_bom_item_default"):
        op.create_index(
            "idx_ly_apparel_bom_item_default",
            _BOM_TABLE,
            ["company", "item_code", "is_default"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _BOM_TABLE, "idx_ly_apparel_bom_style_master"):
        op.create_index("idx_ly_apparel_bom_style_master", _BOM_TABLE, ["style_master_id"], schema=schema)
    if not _index_exists(bind, schema, _BOM_TABLE, "uk_ly_apparel_bom_one_active_default"):
        if _is_sqlite(bind):
            op.create_index(
                "uk_ly_apparel_bom_one_active_default",
                _BOM_TABLE,
                ["company", "item_code"],
                unique=True,
                schema=schema,
                sqlite_where=sa.text("is_default = 1 AND status = 'active'"),
            )
        else:
            op.create_index(
                "uk_ly_apparel_bom_one_active_default",
                _BOM_TABLE,
                ["company", "item_code"],
                unique=True,
                schema=schema,
                postgresql_where=sa.text("is_default = true AND status = 'active'"),
            )


def _backfill_company_and_style(bind) -> None:
    if not _table_exists(bind, _schema_of(bind), _STYLE_TABLE):
        bind.execute(
            sa.text(
                f"UPDATE {_qualified(bind, _BOM_TABLE)} "
                "SET company = COALESCE(NULLIF(company, ''), :default_company)"
            ),
            {"default_company": _DEFAULT_COMPANY},
        )
        return

    bom_table = _qualified(bind, _BOM_TABLE)
    style_table = _qualified(bind, _STYLE_TABLE)
    bind.execute(
        sa.text(
            f"""
            UPDATE {bom_table} AS b
            SET company = COALESCE(
                NULLIF(company, ''),
                (
                    SELECT sm.company
                    FROM {style_table} sm
                    WHERE sm.ys_style_no = b.item_code
                      AND sm.ys_style_status = 'enabled'
                    ORDER BY sm.id
                    LIMIT 1
                ),
                :default_company
            )
            """
        ),
        {"default_company": _DEFAULT_COMPANY},
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE {bom_table} AS b
            SET style_master_id = (
                SELECT sm.id
                FROM {style_table} sm
                WHERE sm.company = b.company
                  AND sm.ys_style_no = b.item_code
                  AND sm.ys_style_status = 'enabled'
                ORDER BY sm.id
                LIMIT 1
            )
            WHERE style_master_id IS NULL
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _BOM_TABLE):
        return

    if not _column_exists(bind, schema, _BOM_TABLE, "company"):
        op.add_column(
            _BOM_TABLE,
            sa.Column("company", sa.String(length=140), nullable=False, server_default=_DEFAULT_COMPANY),
            schema=schema,
        )
    if not _column_exists(bind, schema, _BOM_TABLE, "style_master_id"):
        op.add_column(_BOM_TABLE, sa.Column("style_master_id", _id_type(bind), nullable=True), schema=schema)

    _backfill_company_and_style(bind)
    _drop_index_if_exists(bind, schema, "uk_ly_apparel_bom_one_active_default")
    _drop_index_if_exists(bind, schema, "idx_ly_apparel_bom_item_default")
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _BOM_TABLE):
        return

    _drop_index_if_exists(bind, schema, "uk_ly_apparel_bom_one_active_default")
    _drop_index_if_exists(bind, schema, "idx_ly_apparel_bom_item_default")
    _drop_index_if_exists(bind, schema, "idx_ly_apparel_bom_style_master")
    op.create_index("idx_ly_apparel_bom_item_default", _BOM_TABLE, ["item_code", "is_default"], schema=schema)
    if _is_sqlite(bind):
        op.create_index(
            "uk_ly_apparel_bom_one_active_default",
            _BOM_TABLE,
            ["item_code"],
            unique=True,
            schema=schema,
            sqlite_where=sa.text("is_default = 1 AND status = 'active'"),
        )
    else:
        op.create_index(
            "uk_ly_apparel_bom_one_active_default",
            _BOM_TABLE,
            ["item_code"],
            unique=True,
            schema=schema,
            postgresql_where=sa.text("is_default = true AND status = 'active'"),
        )
    if _column_exists(bind, schema, _BOM_TABLE, "style_master_id"):
        op.drop_column(_BOM_TABLE, "style_master_id", schema=schema)
    if _column_exists(bind, schema, _BOM_TABLE, "company"):
        op.drop_column(_BOM_TABLE, "company", schema=schema)
