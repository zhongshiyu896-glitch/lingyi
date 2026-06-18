"""TASK-069A create foundation template tables.

Revision ID: task_069a_create_foundation_template_tables
Revises: task_068a_extend_master_data_config_entities
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_069a_create_foundation_template_tables"
down_revision = "task_068a_extend_master_data_config_entities"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TEMPLATE_TABLE = "ly_foundation_template"
_NODE_TABLE = "ly_foundation_template_node"
_IDEM_TABLE = "ly_foundation_template_idempotency"
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, table_name: str, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _fk_target(schema: str | None, table_name: str, column: str) -> str:
    prefix = "" if schema is None else f"{schema}."
    return f"{prefix}{table_name}.{column}"


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, _TEMPLATE_TABLE, schema):
        op.create_table(
            _TEMPLATE_TABLE,
            sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
            sa.Column("company", sa.String(140), server_default="默认公司", nullable=False),
            sa.Column("template_type", sa.String(32), nullable=False),
            sa.Column("template_code", sa.String(140), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("scene", sa.String(140), server_default="业务配置", nullable=False),
            sa.Column("status", sa.String(16), server_default="active", nullable=False),
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_by", sa.String(140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_by", sa.String(140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deactivated_by", sa.String(140), nullable=True),
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deactivate_reason", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_ly_foundation_template"),
            sa.CheckConstraint("template_type IN ('workmanship','size_spec')", name="ck_ly_foundation_template_type"),
            sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_foundation_template_status"),
            schema=schema,
        )
        op.create_index(
            "uk_ly_foundation_template_company_type_code",
            _TEMPLATE_TABLE,
            ["company", "template_type", "template_code"],
            unique=True,
            schema=schema,
        )
        op.create_index(
            "idx_ly_foundation_template_type_status",
            _TEMPLATE_TABLE,
            ["template_type", "status"],
            schema=schema,
        )

    if not _table_exists(bind, _NODE_TABLE, schema):
        op.create_table(
            _NODE_TABLE,
            sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
            sa.Column("template_id", ID_TYPE, nullable=False),
            sa.Column("code", sa.String(140), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("node_type", sa.String(100), nullable=False),
            sa.Column("required", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("status", sa.String(16), server_default="active", nullable=False),
            sa.Column("sort_no", sa.Integer(), server_default="10", nullable=False),
            sa.Column("owner", sa.String(140), server_default="业务", nullable=False),
            sa.Column("created_by", sa.String(140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_by", sa.String(140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["template_id"], [_fk_target(schema, _TEMPLATE_TABLE, "id")]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_foundation_template_node"),
            sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_foundation_template_node_status"),
            schema=schema,
        )
        op.create_index(
            "uk_ly_foundation_template_node_code",
            _NODE_TABLE,
            ["template_id", "code"],
            unique=True,
            schema=schema,
        )
        op.create_index(
            "idx_ly_foundation_template_node_template_sort",
            _NODE_TABLE,
            ["template_id", "sort_no"],
            schema=schema,
        )

    if not _table_exists(bind, _IDEM_TABLE, schema):
        op.create_table(
            _IDEM_TABLE,
            sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
            sa.Column("entity_type", sa.String(32), nullable=False),
            sa.Column("company", sa.String(140), nullable=False),
            sa.Column("template_type", sa.String(32), nullable=False),
            sa.Column("idempotency_key", sa.String(140), nullable=False),
            sa.Column("operation", sa.String(32), nullable=False),
            sa.Column("request_hash", sa.String(64), nullable=False),
            sa.Column("record_id", ID_TYPE, nullable=False),
            sa.Column("created_by", sa.String(140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_ly_foundation_template_idempotency"),
            sa.CheckConstraint("entity_type IN ('template','node')", name="ck_ly_foundation_template_idem_entity"),
            sa.CheckConstraint(
                "operation IN ('create','update','deactivate','create_node','update_node','deactivate_node')",
                name="ck_ly_foundation_template_idem_operation",
            ),
            schema=schema,
        )
        op.create_index(
            "uk_ly_foundation_template_idem_key",
            _IDEM_TABLE,
            ["entity_type", "company", "template_type", "idempotency_key"],
            unique=True,
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, _IDEM_TABLE, schema):
        op.drop_index("uk_ly_foundation_template_idem_key", table_name=_IDEM_TABLE, schema=schema)
        op.drop_table(_IDEM_TABLE, schema=schema)
    if _table_exists(bind, _NODE_TABLE, schema):
        op.drop_index("idx_ly_foundation_template_node_template_sort", table_name=_NODE_TABLE, schema=schema)
        op.drop_index("uk_ly_foundation_template_node_code", table_name=_NODE_TABLE, schema=schema)
        op.drop_table(_NODE_TABLE, schema=schema)
    if _table_exists(bind, _TEMPLATE_TABLE, schema):
        op.drop_index("idx_ly_foundation_template_type_status", table_name=_TEMPLATE_TABLE, schema=schema)
        op.drop_index("uk_ly_foundation_template_company_type_code", table_name=_TEMPLATE_TABLE, schema=schema)
        op.drop_table(_TEMPLATE_TABLE, schema=schema)
