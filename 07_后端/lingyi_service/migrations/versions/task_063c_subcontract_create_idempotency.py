"""TASK-063C add subcontract create idempotency fields.

Revision ID: task_063c_subcontract_create_idempotency
Revises: task_063b_create_material_purchase_requirements
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_063c_subcontract_create_idempotency"
down_revision = "task_063b_create_material_purchase_requirements"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_subcontract_order"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return _TABLE in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(_TABLE, schema=schema):
        if str(column.get("name")) == column_name:
            return True
    return False


def _index_exists(bind, schema: str | None, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(_TABLE, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return

    columns = [
        ("source_ref", sa.Column("source_ref", sa.String(length=140), nullable=True)),
        ("idempotency_key", sa.Column("idempotency_key", sa.String(length=128), nullable=True)),
        ("request_hash", sa.Column("request_hash", sa.String(length=64), nullable=True)),
    ]
    for column_name, column in columns:
        if not _column_exists(bind, schema, column_name):
            op.add_column(_TABLE, column, schema=schema)

    if not _index_exists(bind, schema, "uk_ly_subcontract_company_idem"):
        op.create_index(
            "uk_ly_subcontract_company_idem",
            _TABLE,
            ["company", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, "uk_ly_subcontract_company_source"):
        op.create_index(
            "uk_ly_subcontract_company_source",
            _TABLE,
            ["company", "source_ref"],
            unique=True,
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    for index_name in ["uk_ly_subcontract_company_source", "uk_ly_subcontract_company_idem"]:
        if _index_exists(bind, schema, index_name):
            op.drop_index(index_name, table_name=_TABLE, schema=schema)
    for column_name in ["request_hash", "idempotency_key", "source_ref"]:
        if _column_exists(bind, schema, column_name):
            op.drop_column(_TABLE, column_name, schema=schema)
