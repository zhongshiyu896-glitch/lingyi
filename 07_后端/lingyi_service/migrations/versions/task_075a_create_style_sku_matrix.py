"""TASK-075A create style SKU matrix.

Revision ID: task_075a_create_style_sku_matrix
Revises: task_074a_create_production_followup_template_nodes
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_075a_create_style_sku_matrix"
down_revision = "task_074a_create_production_followup_template_nodes"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_SKU_TABLE = "ly_style_sku"
_IDEM_TABLE = "ly_style_master_idempotency"
_IDEM_CONSTRAINT = "ck_ly_style_master_idem_entity"


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


def _constraint_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(
        str(constraint.get("name")) == constraint_name
        for constraint in sa.inspect(bind).get_check_constraints(table_name, schema=schema)
    )


def _create_sku_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _SKU_TABLE):
        return
    op.create_table(
        _SKU_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("style_master_id", _id_type(bind), nullable=False),
        sa.Column("ys_style_no", sa.String(length=140), nullable=False),
        sa.Column("color_code", sa.String(length=64), nullable=False),
        sa.Column("color_name", sa.String(length=140), nullable=False),
        sa.Column("size_code", sa.String(length=64), nullable=False),
        sa.Column("size_name", sa.String(length=140), nullable=False),
        sa.Column("sku_code", sa.String(length=180), nullable=False),
        sa.Column("barcode", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_style_sku_status"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        ("uk_ly_style_sku_company_style_pair", ["company", "style_master_id", "color_code", "size_code"], True),
        ("uk_ly_style_sku_company_style_sku", ["company", "style_master_id", "sku_code"], True),
        ("idx_ly_style_sku_company_style_status", ["company", "style_master_id", "status"], False),
    ]
    for index_name, columns, unique in indexes:
        if not _index_exists(bind, schema, _SKU_TABLE, index_name):
            op.create_index(index_name, _SKU_TABLE, columns, unique=unique, schema=schema)


def _replace_idempotency_entity_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _IDEM_TABLE):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_IDEM_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_IDEM_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_IDEM_CONSTRAINT, expression)
        return
    if _constraint_exists(bind, schema, _IDEM_TABLE, _IDEM_CONSTRAINT):
        op.drop_constraint(_IDEM_CONSTRAINT, _IDEM_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_IDEM_CONSTRAINT, _IDEM_TABLE, expression, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _create_sku_table(bind, schema)
    _create_indexes(bind, schema)
    _replace_idempotency_entity_constraint("entity_type IN ('style','dictionary','gallery','sku')")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _IDEM_TABLE):
        qualified = _IDEM_TABLE if schema is None else f"{schema}.{_IDEM_TABLE}"
        op.execute(sa.text(f"DELETE FROM {qualified} WHERE entity_type = 'sku'"))
    _replace_idempotency_entity_constraint("entity_type IN ('style','dictionary','gallery')")
    for index_name in [
        "idx_ly_style_sku_company_style_status",
        "uk_ly_style_sku_company_style_sku",
        "uk_ly_style_sku_company_style_pair",
    ]:
        if _index_exists(bind, schema, _SKU_TABLE, index_name):
            op.drop_index(index_name, table_name=_SKU_TABLE, schema=schema)
    if _table_exists(bind, schema, _SKU_TABLE):
        op.drop_table(_SKU_TABLE, schema=schema)
