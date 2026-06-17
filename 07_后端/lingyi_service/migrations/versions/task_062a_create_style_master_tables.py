"""TASK-062A create style master tables.

Revision ID: task_062a_create_style_master_tables
Revises: task_061b_create_production_tracking_reconcile
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_062a_create_style_master_tables"
down_revision = "task_061b_create_production_tracking_reconcile"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_STYLE_TABLE = "ly_style_master"
_DICT_TABLE = "ly_style_dictionary"
_IDEM_TABLE = "ly_style_master_idempotency"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _json_type(bind):
    if _is_sqlite(bind):
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


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
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_style_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _STYLE_TABLE):
        return
    op.create_table(
        _STYLE_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("ys_style_no", sa.String(length=140), nullable=False),
        sa.Column("ys_style_name_cn", sa.String(length=255), nullable=False),
        sa.Column("ys_season", sa.String(length=140), nullable=False),
        sa.Column("ys_year", sa.String(length=32), nullable=False),
        sa.Column("ys_brand", sa.String(length=140), nullable=False),
        sa.Column("ys_style_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("colors", _json_type(bind), nullable=False),
        sa.Column("sizes", _json_type(bind), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("disabled_by", sa.String(length=140), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disable_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("ys_style_status IN ('draft','enabled','disabled')", name="ck_ly_style_master_status"),
        schema=schema,
    )


def _create_dictionary_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _DICT_TABLE):
        return
    op.create_table(
        _DICT_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("dict_type", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=140), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deactivated_by", sa.String(length=140), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivate_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("dict_type IN ('season','year','brand')", name="ck_ly_style_dictionary_type"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_style_dictionary_status"),
        schema=schema,
    )


def _create_idempotency_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _IDEM_TABLE):
        return
    op.create_table(
        _IDEM_TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("entity_type IN ('style','dictionary')", name="ck_ly_style_master_idem_entity"),
        sa.CheckConstraint(
            "operation IN ('create','update','deactivate')",
            name="ck_ly_style_master_idem_operation",
        ),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_STYLE_TABLE, "uk_ly_style_master_company_no", ["company", "ys_style_no"], True),
        (_STYLE_TABLE, "idx_ly_style_master_company_status", ["company", "ys_style_status"], False),
        (_STYLE_TABLE, "idx_ly_style_master_lookup", ["company", "ys_brand", "ys_year", "ys_season"], False),
        (_DICT_TABLE, "uk_ly_style_dictionary_company_code", ["dict_type", "company", "code"], True),
        (_DICT_TABLE, "idx_ly_style_dictionary_company_type_status", ["company", "dict_type", "status"], False),
        (_IDEM_TABLE, "uk_ly_style_master_idem_key", ["entity_type", "company", "idempotency_key"], True),
        (_IDEM_TABLE, "idx_ly_style_master_idem_record", ["entity_type", "record_id"], False),
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
    _create_style_table(bind, schema)
    _create_dictionary_table(bind, schema)
    _create_idempotency_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, index_name in [
        (_IDEM_TABLE, "idx_ly_style_master_idem_record"),
        (_IDEM_TABLE, "uk_ly_style_master_idem_key"),
        (_DICT_TABLE, "idx_ly_style_dictionary_company_type_status"),
        (_DICT_TABLE, "uk_ly_style_dictionary_company_code"),
        (_STYLE_TABLE, "idx_ly_style_master_lookup"),
        (_STYLE_TABLE, "idx_ly_style_master_company_status"),
        (_STYLE_TABLE, "uk_ly_style_master_company_no"),
    ]:
        _drop_index_if_exists(bind, schema, table_name, index_name)
    for table_name in [_IDEM_TABLE, _DICT_TABLE, _STYLE_TABLE]:
        if _table_exists(bind, schema, table_name):
            op.drop_table(table_name, schema=schema)
