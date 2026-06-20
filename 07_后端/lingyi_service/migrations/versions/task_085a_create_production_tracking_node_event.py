"""TASK-085A create production tracking node event table.

Revision ID: task_085a_create_production_tracking_node_event
Revises: task_084a_add_sample_material_bom_item_size
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_085a_create_production_tracking_node_event"
down_revision = "task_084a_add_sample_material_bom_item_size"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_tracking_node_event"
_PLAN_TABLE = "ly_production_plan"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


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


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        ("uk_ly_production_tracking_node_event_no", ["event_no"], True),
        ("idx_ly_production_tracking_node_event_plan_node", ["plan_id", "node_key", "created_at"], False),
        ("idx_ly_production_tracking_node_event_company_status", ["company", "node_key", "status"], False),
    ]
    for index_name, columns, unique in indexes:
        if not _index_exists(bind, schema, _TABLE, index_name):
            op.create_index(index_name, _TABLE, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, index_name: str) -> None:
    if _table_exists(bind, schema, _TABLE) and _index_exists(bind, schema, _TABLE, index_name):
        op.drop_index(index_name, table_name=_TABLE, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _PLAN_TABLE) or _table_exists(bind, schema, _TABLE):
        return
    _ensure_schema(bind)
    id_type = _id_type(bind)
    op.create_table(
        _TABLE,
        sa.Column("id", id_type, autoincrement=True),
        sa.Column("event_no", sa.String(length=64), nullable=False),
        sa.Column("plan_id", id_type, nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("plan_no", sa.String(length=64), nullable=False),
        sa.Column("sales_order", sa.String(length=140), nullable=False),
        sa.Column("sales_order_item", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("node_key", sa.String(length=64), nullable=False),
        sa.Column("node_name", sa.String(length=140), nullable=False),
        sa.Column("owner", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remark", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="production_tracking_node"),
        sa.Column("source_ref", sa.String(length=140), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_production_tracking_node_event"),
        sa.ForeignKeyConstraint(["plan_id"], [_qualified(schema, _PLAN_TABLE) + ".id"], name="fk_ly_production_tracking_node_event_plan"),
        sa.CheckConstraint("status IN ('pending','in_progress','done','blocked')", name="ck_ly_production_tracking_node_event_status"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ly_production_tracking_node_event_progress"),
        schema=schema,
    )
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    for index_name in [
        "idx_ly_production_tracking_node_event_company_status",
        "idx_ly_production_tracking_node_event_plan_node",
        "uk_ly_production_tracking_node_event_no",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    op.drop_table(_TABLE, schema=schema)
