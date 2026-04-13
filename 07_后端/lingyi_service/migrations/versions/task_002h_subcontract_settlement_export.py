"""TASK-002H subcontract settlement export fields.

Revision ID: task_002h_subcontract_settlement_export
Revises: task_002f_inspection_detail_and_idempotency
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_002h_subcontract_settlement_export"
down_revision = "task_002f_inspection_detail_and_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_subcontract_inspection"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified_table(schema: str | None, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name, schema=schema):
        if str(column.get("name")) == column_name:
            return True
    return False


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


def _add_columns(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _TABLE):
        return

    columns: list[tuple[str, sa.Column]] = [
        ("settlement_status", sa.Column("settlement_status", sa.String(length=32), nullable=False, server_default="unsettled")),
        ("statement_id", sa.Column("statement_id", sa.BigInteger(), nullable=True)),
        ("statement_no", sa.Column("statement_no", sa.String(length=64), nullable=True)),
        ("settlement_line_key", sa.Column("settlement_line_key", sa.String(length=128), nullable=True)),
        ("settlement_locked_by", sa.Column("settlement_locked_by", sa.String(length=140), nullable=True)),
        ("settlement_locked_at", sa.Column("settlement_locked_at", sa.DateTime(timezone=True), nullable=True)),
        ("settled_by", sa.Column("settled_by", sa.String(length=140), nullable=True)),
        ("settled_at", sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True)),
        ("settlement_request_id", sa.Column("settlement_request_id", sa.String(length=64), nullable=True)),
    ]

    for column_name, column in columns:
        if not _column_exists(bind, schema, _TABLE, column_name):
            op.add_column(_TABLE, column, schema=schema)


def _backfill(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _TABLE):
        return

    table = _qualified_table(schema, _TABLE)
    trim_fn = "trim" if _is_sqlite(bind) else "btrim"

    op.execute(
        f"""
        UPDATE {table}
        SET settlement_status = 'unsettled'
        WHERE settlement_status IS NULL OR {trim_fn}(settlement_status) = ''
        """
    )

    op.execute(
        f"""
        UPDATE {table}
        SET settlement_line_key = 'subcontract_inspection:' || CAST(id AS TEXT)
        WHERE (settlement_line_key IS NULL OR {trim_fn}(settlement_line_key) = '')
          AND id IS NOT NULL
        """
    )


def _ensure_indexes(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _TABLE):
        return

    if not _index_exists(bind, schema, _TABLE, "idx_ly_subcontract_inspection_settlement_status"):
        op.create_index(
            "idx_ly_subcontract_inspection_settlement_status",
            _TABLE,
            ["settlement_status", "inspected_at", "id"],
            schema=schema,
        )

    if not _index_exists(bind, schema, _TABLE, "idx_ly_subcontract_inspection_statement"):
        op.create_index(
            "idx_ly_subcontract_inspection_statement",
            _TABLE,
            ["statement_id", "settlement_status"],
            schema=schema,
        )

    if not _index_exists(bind, schema, _TABLE, "uk_ly_subcontract_inspection_settlement_line_key"):
        op.create_index(
            "uk_ly_subcontract_inspection_settlement_line_key",
            _TABLE,
            ["settlement_line_key"],
            unique=True,
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _add_columns(bind, schema)
    _backfill(bind, schema)
    _ensure_indexes(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
