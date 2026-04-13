"""TASK-002H1 settlement append-only idempotency operation table.

Revision ID: task_002h1_subcontract_settlement_operation_idempotency
Revises: task_002h_subcontract_settlement_export
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_002h1_subcontract_settlement_operation_idempotency"
down_revision = "task_002h_subcontract_settlement_export"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_INSPECTION_TABLE = "ly_subcontract_inspection"
_OPERATION_TABLE = "ly_subcontract_settlement_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


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


def _ensure_inspection_key_length(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _INSPECTION_TABLE):
        return
    if not _column_exists(bind, schema, _INSPECTION_TABLE, "settlement_request_id"):
        return

    # SQLite does not enforce VARCHAR length and cannot alter column length directly.
    if _is_sqlite(bind):
        return

    op.alter_column(
        _INSPECTION_TABLE,
        "settlement_request_id",
        type_=sa.String(length=128),
        existing_nullable=True,
        schema=schema,
    )


def _create_operation_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _OPERATION_TABLE):
        return

    op.create_table(
        _OPERATION_TABLE,
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("operation_type", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("statement_id", sa.BigInteger(), nullable=True),
        sa.Column("statement_no", sa.String(length=64), nullable=True),
        sa.Column("inspection_ids_json", sa.JSON(), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column("affected_inspection_ids_json", sa.JSON(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("operator", sa.String(length=140), nullable=False),
        sa.Column("request_id", sa.String(length=140), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("operation_type", "idempotency_key", name="uk_ly_subcontract_settlement_operation_idem"),
        schema=schema,
    )


def _ensure_operation_columns(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _OPERATION_TABLE):
        return

    columns: list[tuple[str, sa.Column]] = [
        ("operation_type", sa.Column("operation_type", sa.String(length=16), nullable=False)),
        ("idempotency_key", sa.Column("idempotency_key", sa.String(length=128), nullable=False)),
        ("request_hash", sa.Column("request_hash", sa.String(length=64), nullable=False)),
        ("statement_id", sa.Column("statement_id", sa.BigInteger(), nullable=True)),
        ("statement_no", sa.Column("statement_no", sa.String(length=64), nullable=True)),
        ("inspection_ids_json", sa.Column("inspection_ids_json", sa.JSON(), nullable=False)),
        ("result_status", sa.Column("result_status", sa.String(length=32), nullable=False)),
        ("affected_inspection_ids_json", sa.Column("affected_inspection_ids_json", sa.JSON(), nullable=False)),
        ("response_json", sa.Column("response_json", sa.JSON(), nullable=True)),
        ("operator", sa.Column("operator", sa.String(length=140), nullable=False)),
        ("request_id", sa.Column("request_id", sa.String(length=140), nullable=True)),
        (
            "created_at",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ),
    ]

    for column_name, column in columns:
        if not _column_exists(bind, schema, _OPERATION_TABLE, column_name):
            op.add_column(_OPERATION_TABLE, column, schema=schema)


def _ensure_operation_indexes(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _OPERATION_TABLE):
        return

    if not _index_exists(bind, schema, _OPERATION_TABLE, "uk_ly_subcontract_settlement_operation_idem"):
        op.create_index(
            "uk_ly_subcontract_settlement_operation_idem",
            _OPERATION_TABLE,
            ["operation_type", "idempotency_key"],
            unique=True,
            schema=schema,
        )

    if not _index_exists(bind, schema, _OPERATION_TABLE, "idx_ly_subcontract_settlement_operation_statement"):
        op.create_index(
            "idx_ly_subcontract_settlement_operation_statement",
            _OPERATION_TABLE,
            ["statement_id", "statement_no", "operation_type"],
            schema=schema,
        )

    if not _index_exists(bind, schema, _OPERATION_TABLE, "idx_ly_subcontract_settlement_operation_created"):
        op.create_index(
            "idx_ly_subcontract_settlement_operation_created",
            _OPERATION_TABLE,
            ["created_at"],
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    _ensure_schema(bind)
    _ensure_inspection_key_length(bind, schema)
    _create_operation_table(bind, schema)
    _ensure_operation_columns(bind, schema)
    _ensure_operation_indexes(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
