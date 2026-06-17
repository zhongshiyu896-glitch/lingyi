"""TASK-063D add inventory-count idempotency columns.

Revision ID: task_063d_inventory_count_idempotency
Revises: task_063c_subcontract_create_idempotency
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_063d_inventory_count_idempotency"
down_revision = "task_063c_subcontract_create_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_warehouse_inventory_count"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return _TABLE_NAME in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(_TABLE_NAME, schema=schema))


def _index_exists(bind, schema: str | None, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(_TABLE_NAME, schema=schema))


def _drop_index_if_exists(bind, schema: str | None, index_name: str) -> None:
    if _table_exists(bind, schema) and _index_exists(bind, schema, index_name):
        op.drop_index(index_name, table_name=_TABLE_NAME, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return

    if not _column_exists(bind, schema, "idempotency_key"):
        op.add_column(_TABLE_NAME, sa.Column("idempotency_key", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "source_ref"):
        op.add_column(_TABLE_NAME, sa.Column("source_ref", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "request_hash"):
        op.add_column(_TABLE_NAME, sa.Column("request_hash", sa.String(length=64), nullable=True), schema=schema)

    if not _index_exists(bind, schema, "uk_ly_whse_inv_count_company_idempotency"):
        op.create_index(
            "uk_ly_whse_inv_count_company_idempotency",
            _TABLE_NAME,
            ["company", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, "uk_ly_whse_inv_count_company_source_ref"):
        op.create_index(
            "uk_ly_whse_inv_count_company_source_ref",
            _TABLE_NAME,
            ["company", "source_ref"],
            unique=True,
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    _drop_index_if_exists(bind, schema, "uk_ly_whse_inv_count_company_source_ref")
    _drop_index_if_exists(bind, schema, "uk_ly_whse_inv_count_company_idempotency")
    for column_name in ["request_hash", "source_ref", "idempotency_key"]:
        if _column_exists(bind, schema, column_name):
            op.drop_column(_TABLE_NAME, column_name, schema=schema)
