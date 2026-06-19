"""TASK-083A create delivery invoice operation table.

Revision ID: task_083a_create_delivery_invoice_operations
Revises: task_082a_create_material_purchase_payment_operations
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_083a_create_delivery_invoice_operations"
down_revision = "task_082a_create_material_purchase_payment_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_INVOICE_TABLE = "ly_delivery_invoice"
_OPERATION_TABLE = "ly_delivery_invoice_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    return any(str(index.get("name")) == index_name for index in sa.inspect(bind).get_indexes(table_name, schema=schema))


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_operation_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _OPERATION_TABLE) or not _table_exists(bind, schema, _INVOICE_TABLE):
        return
    id_type = _id_type(bind)
    op.create_table(
        _OPERATION_TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("delivery_invoice_id", id_type, nullable=False),
        sa.Column("delivery_note", sa.String(length=140), nullable=False),
        sa.Column("sales_invoice", sa.String(length=140), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column("result_user", sa.String(length=140), nullable=False),
        sa.Column("result_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["delivery_invoice_id"],
            [_qualified(schema, _INVOICE_TABLE) + ".id"],
            name="fk_ly_delivery_invoice_op_invoice",
        ),
        sa.CheckConstraint(
            "operation_type IN ('cancel_delivery_invoice')",
            name="ck_ly_delivery_invoice_op_type",
        ),
        schema=schema,
    )


def _create_index_if_needed(bind, schema: str | None, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, _OPERATION_TABLE) and not _index_exists(bind, schema, _OPERATION_TABLE, index_name):
        op.create_index(index_name, _OPERATION_TABLE, columns, unique=unique, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_operation_table(bind, schema)
    _create_index_if_needed(
        bind,
        schema,
        "uk_ly_delivery_invoice_op_idem",
        ["company", "operation_type", "idempotency_key"],
        unique=True,
    )
    _create_index_if_needed(
        bind,
        schema,
        "idx_ly_delivery_invoice_op_invoice",
        ["delivery_invoice_id", "operation_type", "created_at"],
    )
    _create_index_if_needed(
        bind,
        schema,
        "idx_ly_delivery_invoice_op_sales_invoice",
        ["company", "sales_invoice", "operation_type", "created_at"],
    )


def downgrade() -> None:
    """Additive migration; avoid destructive downgrade in local long-running DBs."""
