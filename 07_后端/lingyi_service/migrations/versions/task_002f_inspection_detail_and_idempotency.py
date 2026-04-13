"""TASK-002F1 inspection detail fields and idempotency scope migration.

Revision ID: task_002f_inspection_detail_and_idempotency
Revises: task_002c_subcontract_company_and_schema
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_002f_inspection_detail_and_idempotency"
down_revision = "task_002c_subcontract_company_and_schema"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_subcontract_inspection"


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


def _ensure_schema_if_needed(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _ensure_inspection_table_columns(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _TABLE):
        return

    add_columns: list[tuple[str, sa.Column]] = [
        ("inspection_no", sa.Column("inspection_no", sa.String(length=64), nullable=True)),
        ("receipt_batch_no", sa.Column("receipt_batch_no", sa.String(length=64), nullable=True)),
        ("receipt_warehouse", sa.Column("receipt_warehouse", sa.String(length=140), nullable=True)),
        ("item_code", sa.Column("item_code", sa.String(length=140), nullable=True)),
        ("accepted_qty", sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("rejected_rate", sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0")),
        ("subcontract_rate", sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0")),
        (
            "deduction_amount_per_piece",
            sa.Column("deduction_amount_per_piece", sa.Numeric(18, 6), nullable=False, server_default="0"),
        ),
        ("idempotency_key", sa.Column("idempotency_key", sa.String(length=128), nullable=True)),
        ("payload_hash", sa.Column("payload_hash", sa.String(length=64), nullable=True)),
        ("inspected_by", sa.Column("inspected_by", sa.String(length=140), nullable=True)),
        ("inspected_at", sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True)),
        ("request_id", sa.Column("request_id", sa.String(length=64), nullable=True)),
        ("remark", sa.Column("remark", sa.String(length=200), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())),
    ]
    for column_name, column in add_columns:
        if not _column_exists(bind, schema, _TABLE, column_name):
            op.add_column(_TABLE, column, schema=schema)


def _ensure_inspection_indexes(bind, schema: str | None) -> None:
    if not _table_exists(bind, schema, _TABLE):
        return
    if not _index_exists(bind, schema, _TABLE, "idx_ly_subcontract_inspection_receipt_batch"):
        op.create_index("idx_ly_subcontract_inspection_receipt_batch", _TABLE, ["receipt_batch_no"], schema=schema)
    if not _index_exists(bind, schema, _TABLE, "idx_ly_subcontract_inspection_batch"):
        op.create_index(
            "idx_ly_subcontract_inspection_batch",
            _TABLE,
            ["company", "subcontract_id", "receipt_batch_no"],
            schema=schema,
        )
    if not _index_exists(bind, schema, _TABLE, "uk_ly_subcontract_inspection_idempotency"):
        op.create_index(
            "uk_ly_subcontract_inspection_idempotency",
            _TABLE,
            ["subcontract_id", "idempotency_key"],
            unique=True,
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema_if_needed(bind)
    _ensure_inspection_table_columns(bind, schema)
    _ensure_inspection_indexes(bind, schema)


def downgrade() -> None:
    """TASK migration is additive/idempotent; no destructive downgrade."""
    return

