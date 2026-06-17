"""TASK-064A create sample-order tracking events.

Revision ID: task_064a_create_sample_tracking_events
Revises: task_063e_extend_sample_flow_idempotency_operations
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_064a_create_sample_tracking_events"
down_revision = "task_063e_extend_sample_flow_idempotency_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_EVENT_TABLE = "ly_sample_tracking_event"
_ORDER_TABLE = "ly_sample_order"
_TEMPLATE_TABLE = "ly_sample_tracking_template"
_NODE_TABLE = "ly_sample_tracking_node"
_IDEM_TABLE = "ly_sample_idempotency"
_ENTITY_CONSTRAINT = "ck_ly_sample_idem_entity"
_OPERATION_CONSTRAINT = "ck_ly_sample_idem_operation"
_ENTITIES = "('order','template','node','tracking_event')"
_OPERATIONS = "('create','update','submit','start_patterning','start_fitting','seal','reverse','convert','deactivate','create_node','delete_node','create_tracking_event')"


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


def _check_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    for constraint in inspector.get_check_constraints(table_name, schema=schema):
        if str(constraint.get("name")) == constraint_name:
            return True
    return False


def _sqlite_constraint_sql(bind) -> str:
    row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name"),
        {"table_name": _IDEM_TABLE},
    ).fetchone()
    return str(row[0]) if row else ""


def _create_event_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _EVENT_TABLE):
        return
    op.create_table(
        _EVENT_TABLE,
        sa.Column("id", _id_type(bind), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("sample_order_id", _id_type(bind), sa.ForeignKey(_fk_target(bind, _ORDER_TABLE, "id")), nullable=False),
        sa.Column("template_id", _id_type(bind), sa.ForeignKey(_fk_target(bind, _TEMPLATE_TABLE, "id")), nullable=True),
        sa.Column("node_id", _id_type(bind), sa.ForeignKey(_fk_target(bind, _NODE_TABLE, "id")), nullable=True),
        sa.Column("node_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("stage", sa.String(length=140), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor", sa.String(length=140), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ly_sample_event_progress"),
        sa.CheckConstraint(
            "result IN ('pending','in_progress','done','blocked','rework')",
            name="ck_ly_sample_event_result",
        ),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        (_EVENT_TABLE, "idx_ly_sample_event_order", ["company", "sample_order_id", "happened_at"], False),
        (_EVENT_TABLE, "idx_ly_sample_event_node", ["node_id"], False),
    ]
    for table_name, index_name, columns, unique in indexes:
        if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _sqlite_rebuild_idempotency(bind) -> None:
    if not _table_exists(bind, None, _IDEM_TABLE):
        return
    current_sql = _sqlite_constraint_sql(bind)
    if "'tracking_event'" in current_sql and "'create_tracking_event'" in current_sql:
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
            CONSTRAINT {_ENTITY_CONSTRAINT} CHECK (entity_type IN {_ENTITIES}),
            CONSTRAINT {_OPERATION_CONSTRAINT} CHECK (operation IN {_OPERATIONS})
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
    op.drop_table(_IDEM_TABLE)
    op.rename_table("ly_sample_idempotency_new", _IDEM_TABLE)
    if not _index_exists(bind, None, _IDEM_TABLE, "uk_ly_sample_idem_key"):
        op.create_index("uk_ly_sample_idem_key", _IDEM_TABLE, ["entity_type", "company", "idempotency_key"], unique=True)
    op.execute("PRAGMA foreign_keys=on")


def _extend_idempotency_constraints(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _IDEM_TABLE):
        return
    if _is_sqlite(bind):
        _sqlite_rebuild_idempotency(bind)
        return
    if _check_exists(bind, schema, _IDEM_TABLE, _ENTITY_CONSTRAINT):
        op.drop_constraint(_ENTITY_CONSTRAINT, _IDEM_TABLE, schema=schema, type_="check")
    if _check_exists(bind, schema, _IDEM_TABLE, _OPERATION_CONSTRAINT):
        op.drop_constraint(_OPERATION_CONSTRAINT, _IDEM_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_ENTITY_CONSTRAINT, _IDEM_TABLE, f"entity_type IN {_ENTITIES}", schema=schema)
    op.create_check_constraint(_OPERATION_CONSTRAINT, _IDEM_TABLE, f"operation IN {_OPERATIONS}", schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _create_event_table(bind, schema)
    _create_indexes(bind, schema)
    _extend_idempotency_constraints(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade for sample events."""
