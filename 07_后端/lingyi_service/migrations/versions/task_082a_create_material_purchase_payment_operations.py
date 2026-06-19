"""TASK-082A create material purchase payment operation table.

Revision ID: task_082a_create_material_purchase_payment_operations
Revises: task_081a_create_sales_payment_operations
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_082a_create_material_purchase_payment_operations"
down_revision = "task_081a_create_sales_payment_operations"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_PAYMENT_TABLE = "ly_material_purchase_payment"
_OPERATION_TABLE = "ly_material_purchase_payment_operation"


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
    if _table_exists(bind, schema, _OPERATION_TABLE) or not _table_exists(bind, schema, _PAYMENT_TABLE):
        return
    id_type = _id_type(bind)
    op.create_table(
        _OPERATION_TABLE,
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("purchase_invoice", sa.String(length=140), nullable=False),
        sa.Column("payment_id", id_type, nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column("result_user", sa.String(length=140), nullable=False),
        sa.Column("result_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            [_qualified(schema, _PAYMENT_TABLE) + ".id"],
            name="fk_ly_material_purchase_payment_op_payment",
        ),
        sa.CheckConstraint(
            "operation_type IN ('cancel_purchase_payment')",
            name="ck_ly_material_purchase_payment_op_type",
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
        "uk_ly_material_purchase_payment_op_idem",
        ["company", "operation_type", "idempotency_key"],
        unique=True,
    )
    _create_index_if_needed(
        bind,
        schema,
        "idx_ly_material_purchase_payment_op_payment",
        ["payment_id", "operation_type", "created_at"],
    )
    _create_index_if_needed(
        bind,
        schema,
        "idx_ly_material_purchase_payment_op_invoice",
        ["company", "purchase_invoice", "operation_type", "created_at"],
    )


def downgrade() -> None:
    """Additive migration; avoid destructive downgrade in local long-running DBs."""
