"""TASK-006E2 add active payable outbox unique scope.

Revision ID: task_006e2_factory_statement_payable_active_scope
Revises: task_006d_factory_statement_payable_outbox
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006e2_factory_statement_payable_active_scope"
down_revision = "task_006d_factory_statement_payable_outbox"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_factory_statement_payable_outbox"
_INDEX_NAME = "uk_ly_factory_statement_payable_one_active"
_ACTIVE_WHERE = "status IN ('pending','processing','succeeded')"


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


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    if not _table_exists(bind, schema, _TABLE_NAME):
        return

    if _index_exists(bind, schema, _TABLE_NAME, _INDEX_NAME):
        return

    op.create_index(
        _INDEX_NAME,
        _TABLE_NAME,
        ["statement_id"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text(_ACTIVE_WHERE),
        sqlite_where=sa.text(_ACTIVE_WHERE),
    )


def downgrade() -> None:
    """No destructive downgrade for hardening migration."""
    return
