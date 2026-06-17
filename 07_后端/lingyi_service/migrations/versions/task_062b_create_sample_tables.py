"""TASK-062B create sample workflow tables.

Revision ID: task_062b_create_sample_tables
Revises: task_062a_create_style_master_tables
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_062b_create_sample_tables"
down_revision = "task_062a_create_style_master_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_ORDER_TABLE = "ly_sample_order"
_TEMPLATE_TABLE = "ly_sample_tracking_template"
_NODE_TABLE = "ly_sample_tracking_node"
_IDEM_TABLE = "ly_sample_idempotency"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _fk_target(bind, table_name: str, column_name: str) -> str:
    if _is_sqlite(bind):
        return f"{table_name}.{column_name}"
    return f"{_SCHEMA_NAME}.{table_name}.{column_name}"


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


def _create_order_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _ORDER_TABLE):
        return
    op.create_table(
        _ORDER_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("sample_no", sa.String(length=140), nullable=False),
        sa.Column("style_no", sa.String(length=140), nullable=False),
        sa.Column("style_name", sa.String(length=255), nullable=False),
        sa.Column("customer", sa.String(length=255), nullable=False),
        sa.Column("factory", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sample_type", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=140), nullable=False, server_default="建档"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pattern_maker", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("sample_maker", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("image_tone", sa.String(length=32), nullable=False, server_default="blue"),
        sa.Column("owner_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("bulk_handoff_no", sa.String(length=140), nullable=True),
        sa.Column("bulk_handoff_status", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_by", sa.String(length=140), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.String(length=140), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverse_reason", sa.Text(), nullable=True),
        sa.Column("converted_by", sa.String(length=140), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','pending','patterning','fitting','sealed','reversed','converted')",
            name="ck_ly_sample_order_status",
        ),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ly_sample_order_progress"),
        schema=schema,
    )


def _create_template_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _TEMPLATE_TABLE):
        return
    op.create_table(
        _TEMPLATE_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("template_code", sa.String(length=140), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=140), nullable=False),
        sa.Column("group_name", sa.String(length=140), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="enabled"),
        sa.Column("owner", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("version_no", sa.String(length=64), nullable=False, server_default="V1"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('enabled','disabled')", name="ck_ly_sample_template_status"),
        schema=schema,
    )


def _create_node_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _NODE_TABLE):
        return
    op.create_table(
        _NODE_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("template_id", _id_type(bind), sa.ForeignKey(_fk_target(bind, _TEMPLATE_TABLE, "id")), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=140), nullable=False),
        sa.Column("lead_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="required"),
        sa.Column("gate", sa.Text(), nullable=False, server_default=""),
        sa.Column("output", sa.Text(), nullable=False, server_default=""),
        sa.Column("reminder", sa.Text(), nullable=False, server_default=""),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('required','optional','locked')", name="ck_ly_sample_node_status"),
        schema=schema,
    )


def _create_idempotency_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _IDEM_TABLE):
        return
    op.create_table(
        _IDEM_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("record_id", _id_type(bind), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("entity_type IN ('order','template','node')", name="ck_ly_sample_idem_entity"),
        sa.CheckConstraint(
            "operation IN ('create','update','submit','seal','reverse','convert','deactivate','create_node','delete_node')",
            name="ck_ly_sample_idem_operation",
        ),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_ORDER_TABLE, "uk_ly_sample_order_company_no", ["company", "sample_no"], True),
        (_ORDER_TABLE, "idx_ly_sample_order_status", ["company", "status"], False),
        (_ORDER_TABLE, "idx_ly_sample_order_style", ["company", "style_no"], False),
        (_TEMPLATE_TABLE, "uk_ly_sample_template_company_code", ["company", "template_code"], True),
        (_TEMPLATE_TABLE, "idx_ly_sample_template_status", ["company", "status"], False),
        (_NODE_TABLE, "idx_ly_sample_node_template", ["template_id", "sequence_no"], False),
        (_IDEM_TABLE, "uk_ly_sample_idem_key", ["entity_type", "company", "idempotency_key"], True),
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
    _create_order_table(bind, schema)
    _create_template_table(bind, schema)
    _create_node_table(bind, schema)
    _create_idempotency_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, index_name in [
        (_IDEM_TABLE, "uk_ly_sample_idem_key"),
        (_NODE_TABLE, "idx_ly_sample_node_template"),
        (_TEMPLATE_TABLE, "idx_ly_sample_template_status"),
        (_TEMPLATE_TABLE, "uk_ly_sample_template_company_code"),
        (_ORDER_TABLE, "idx_ly_sample_order_style"),
        (_ORDER_TABLE, "idx_ly_sample_order_status"),
        (_ORDER_TABLE, "uk_ly_sample_order_company_no"),
    ]:
        _drop_index_if_exists(bind, schema, table_name, index_name)
    for table_name in [_IDEM_TABLE, _NODE_TABLE, _TEMPLATE_TABLE, _ORDER_TABLE]:
        if _table_exists(bind, schema, table_name):
            op.drop_table(table_name, schema=schema)
