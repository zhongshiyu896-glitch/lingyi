"""TASK-006B1 add active-scope uniqueness and drop inspection global uniqueness.

Revision ID: task_006b1_factory_statement_active_scope_constraints
Revises: task_006b_create_factory_statement_tables
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006b1_factory_statement_active_scope_constraints"
down_revision = "task_006b_create_factory_statement_tables"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _drop_legacy_item_inspection_unique_indexes(bind, schema: str | None, table_name: str) -> None:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        columns = list(index.get("column_names") or [])
        is_unique = bool(index.get("unique"))
        if columns == ["inspection_id"] and is_unique:
            name = str(index.get("name") or "").strip()
            if name:
                op.drop_index(name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    item_table = "ly_factory_statement_item"
    statement_table = "ly_factory_statement"
    if not _table_exists(bind, schema, statement_table) or not _table_exists(bind, schema, item_table):
        return

    _drop_legacy_item_inspection_unique_indexes(bind, schema, item_table)

    if not _index_exists(bind, schema, item_table, "idx_ly_factory_statement_item_inspection"):
        op.create_index(
            "idx_ly_factory_statement_item_inspection",
            item_table,
            ["inspection_id"],
            schema=schema,
        )

    if not _index_exists(bind, schema, statement_table, "uk_ly_factory_statement_active_scope"):
        op.create_index(
            "uk_ly_factory_statement_active_scope",
            statement_table,
            ["company", "supplier", "from_date", "to_date", "request_hash"],
            unique=True,
            schema=schema,
            postgresql_where=sa.text("statement_status <> 'cancelled'"),
            sqlite_where=sa.text("statement_status <> 'cancelled'"),
        )


def downgrade() -> None:
    """No destructive downgrade in hardening migration."""
    return
