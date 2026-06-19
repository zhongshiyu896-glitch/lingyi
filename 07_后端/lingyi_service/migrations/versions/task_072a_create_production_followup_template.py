"""TASK-072A create production follow-up template tables.

Revision ID: task_072a_create_production_followup_template
Revises: task_071a_create_material_bom_write_tables
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_072a_create_production_followup_template"
down_revision = "task_071a_create_material_bom_write_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TEMPLATE_TABLE = "ly_production_followup_template"
_OPERATION_TABLE = "ly_production_followup_template_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _json_type(bind):
    return sa.JSON()


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


def _create_index_if_missing(bind, schema: str | None, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    id_type = _id_type(bind)

    if not _table_exists(bind, schema, _TEMPLATE_TABLE):
        op.create_table(
            _TEMPLATE_TABLE,
            sa.Column("id", id_type, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("template_no", sa.String(length=140), nullable=False),
            sa.Column("template_name", sa.String(length=255), nullable=False),
            sa.Column("template_type", sa.String(length=140), nullable=False, server_default="基础跟进"),
            sa.Column("trigger_node", sa.String(length=140), nullable=False, server_default="制单草稿"),
            sa.Column("followup_role", sa.String(length=140), nullable=False, server_default="业务跟单"),
            sa.Column("followup_frequency", sa.String(length=64), nullable=False, server_default="每日"),
            sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
            sa.Column("item_code", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="enabled"),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_by", sa.String(length=140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_followup_template"),
            sa.CheckConstraint("status IN ('enabled','disabled')", name="ck_ly_production_followup_template_status"),
            sa.CheckConstraint("sla_hours >= 0", name="ck_ly_production_followup_template_sla_hours"),
            schema=schema,
        )
    _create_index_if_missing(bind, schema, _TEMPLATE_TABLE, "uk_ly_production_followup_template_no", ["company", "template_no"], unique=True)
    _create_index_if_missing(bind, schema, _TEMPLATE_TABLE, "idx_ly_production_followup_template_status", ["company", "status"])
    _create_index_if_missing(bind, schema, _TEMPLATE_TABLE, "idx_ly_production_followup_template_item", ["company", "item_code"])

    if not _table_exists(bind, schema, _OPERATION_TABLE):
        op.create_table(
            _OPERATION_TABLE,
            sa.Column("id", id_type, autoincrement=True),
            sa.Column("template_id", id_type, nullable=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("operation", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("response_json", _json_type(bind), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_followup_template_operation"),
            sa.ForeignKeyConstraint(
                ["template_id"],
                [_qualified(schema, _TEMPLATE_TABLE) + ".id"],
                name="fk_ly_production_followup_template_operation_template",
            ),
            sa.CheckConstraint(
                "operation IN ('create','update','copy','deactivate')",
                name="ck_ly_production_followup_template_operation",
            ),
            schema=schema,
        )
    _create_index_if_missing(
        bind,
        schema,
        _OPERATION_TABLE,
        "uk_ly_production_followup_template_operation_idem",
        ["company", "operation", "idempotency_key"],
        unique=True,
    )
    _create_index_if_missing(
        bind,
        schema,
        _OPERATION_TABLE,
        "idx_ly_production_followup_template_operation_template",
        ["template_id", "operation"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _OPERATION_TABLE):
        _drop_index_if_exists(bind, schema, _OPERATION_TABLE, "idx_ly_production_followup_template_operation_template")
        _drop_index_if_exists(bind, schema, _OPERATION_TABLE, "uk_ly_production_followup_template_operation_idem")
        op.drop_table(_OPERATION_TABLE, schema=schema)
    if _table_exists(bind, schema, _TEMPLATE_TABLE):
        _drop_index_if_exists(bind, schema, _TEMPLATE_TABLE, "idx_ly_production_followup_template_item")
        _drop_index_if_exists(bind, schema, _TEMPLATE_TABLE, "idx_ly_production_followup_template_status")
        _drop_index_if_exists(bind, schema, _TEMPLATE_TABLE, "uk_ly_production_followup_template_no")
        op.drop_table(_TEMPLATE_TABLE, schema=schema)
