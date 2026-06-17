"""TASK-063E extend sample flow idempotency operations.

Revision ID: task_063e_extend_sample_flow_idempotency_operations
Revises: task_063d_inventory_count_idempotency
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_063e_extend_sample_flow_idempotency_operations"
down_revision = "task_063d_inventory_count_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_sample_idempotency"
_CONSTRAINT = "ck_ly_sample_idem_operation"
_OPERATIONS = "('create','update','submit','start_patterning','start_fitting','seal','reverse','convert','deactivate','create_node','delete_node')"
_OLD_OPERATIONS = "('create','update','submit','seal','reverse','convert','deactivate','create_node','delete_node')"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return _TABLE in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(_TABLE, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _sqlite_constraint_sql(bind) -> str:
    row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name"),
        {"table_name": _TABLE},
    ).fetchone()
    return str(row[0]) if row else ""


def _sqlite_rebuild(bind, *, operations_sql: str) -> None:
    if not _table_exists(bind, None):
        return
    current_sql = _sqlite_constraint_sql(bind)
    if operations_sql in current_sql:
        return
    op.execute("PRAGMA foreign_keys=off")
    op.execute(
        f"""
        CREATE TABLE ly_sample_idempotency_new (
            id INTEGER NOT NULL,
            entity_type VARCHAR(32) NOT NULL,
            company VARCHAR(140) NOT NULL,
            idempotency_key VARCHAR(140) NOT NULL,
            operation VARCHAR(32) NOT NULL,
            request_hash VARCHAR(64) NOT NULL,
            record_id INTEGER NOT NULL,
            created_by VARCHAR(140) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_ly_sample_idem_entity CHECK (entity_type IN ('order','template','node')),
            CONSTRAINT {_CONSTRAINT} CHECK (operation IN {operations_sql})
        )
        """
    )
    op.execute(
        """
        INSERT INTO ly_sample_idempotency_new (
            id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
        )
        SELECT id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
        FROM ly_sample_idempotency
        """
    )
    op.drop_table(_TABLE)
    op.rename_table("ly_sample_idempotency_new", _TABLE)
    if not _index_exists(bind, None, "uk_ly_sample_idem_key"):
        op.create_index("uk_ly_sample_idem_key", _TABLE, ["entity_type", "company", "idempotency_key"], unique=True)
    op.execute("PRAGMA foreign_keys=on")


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    if _is_sqlite(bind):
        _sqlite_rebuild(bind, operations_sql=_OPERATIONS)
        return
    op.drop_constraint(_CONSTRAINT, _TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, f"operation IN {_OPERATIONS}", schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    if _is_sqlite(bind):
        _sqlite_rebuild(bind, operations_sql=_OLD_OPERATIONS)
        return
    op.drop_constraint(_CONSTRAINT, _TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, f"operation IN {_OLD_OPERATIONS}", schema=schema)
