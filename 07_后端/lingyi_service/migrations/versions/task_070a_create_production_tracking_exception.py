"""TASK-070A create production tracking exception table.

Revision ID: task_070a_create_production_tracking_exception
Revises: task_069b_add_production_material_uom
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_070a_create_production_tracking_exception"
down_revision = "task_069b_add_production_material_uom"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_production_tracking_exception"
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
        ("uk_ly_production_tracking_exception_no", ["exception_no"], True),
        ("idx_ly_production_tracking_exception_plan", ["plan_id", "created_at"], False),
        ("idx_ly_production_tracking_exception_company_status", ["company", "status", "severity"], False),
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
        sa.Column("exception_no", sa.String(length=64), nullable=False),
        sa.Column("plan_id", id_type, nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("plan_no", sa.String(length=64), nullable=False),
        sa.Column("sales_order", sa.String(length=140), nullable=False),
        sa.Column("sales_order_item", sa.String(length=140), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("exception_type", sa.String(length=64), nullable=False, server_default="progress"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("owner", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_production_tracking_exception"),
        sa.ForeignKeyConstraint(["plan_id"], [_qualified(schema, _PLAN_TABLE) + ".id"], name="fk_ly_production_tracking_exception_plan"),
        sa.CheckConstraint("severity IN ('low','medium','high','blocker')", name="ck_ly_production_tracking_exception_severity"),
        sa.CheckConstraint("status IN ('open','processing','resolved','ignored')", name="ck_ly_production_tracking_exception_status"),
        schema=schema,
    )
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    for index_name in [
        "idx_ly_production_tracking_exception_company_status",
        "idx_ly_production_tracking_exception_plan",
        "uk_ly_production_tracking_exception_no",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    op.drop_table(_TABLE, schema=schema)
