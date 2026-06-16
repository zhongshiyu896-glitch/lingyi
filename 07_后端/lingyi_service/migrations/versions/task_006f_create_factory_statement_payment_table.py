"""TASK-006F create factory statement payment table.

Revision ID: task_006f_create_factory_statement_payment_table
Revises: task_060b_create_sales_payment_entry_table
Create Date: 2026-06-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006f_create_factory_statement_payment_table"
down_revision = "task_060b_create_sales_payment_entry_table"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_factory_statement_payment"


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


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("payment_entry", sa.String(length=140), nullable=False),
        sa.Column("statement_id", sa.BigInteger(), nullable=False),
        sa.Column("statement_no", sa.String(length=64), nullable=False),
        sa.Column("supplier", sa.String(length=140), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("outstanding_before", sa.Numeric(18, 6), nullable=False),
        sa.Column("outstanding_after", sa.Numeric(18, 6), nullable=False),
        sa.Column("mode_of_payment", sa.String(length=140), nullable=False, server_default="Bank Transfer"),
        sa.Column("reference_no", sa.String(length=140), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("docstatus", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_ref", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("scenario_tag", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('submitted','cancelled')", name="ck_ly_factory_statement_payment_status"),
        sa.CheckConstraint("paid_amount > 0", name="ck_ly_factory_statement_payment_amount_positive"),
        sa.CheckConstraint("allocated_amount > 0", name="ck_ly_factory_statement_payment_allocated_positive"),
        sa.CheckConstraint("outstanding_before >= 0", name="ck_ly_factory_statement_payment_before_nonnegative"),
        sa.CheckConstraint("outstanding_after >= 0", name="ck_ly_factory_statement_payment_after_nonnegative"),
        schema=schema,
    )


def _create_indexes(bind, schema: str | None) -> None:
    indexes = [
        ("uk_ly_factory_statement_payment_company_no", ["company", "payment_entry"], True),
        ("uk_ly_factory_statement_payment_company_idem", ["company", "idempotency_key"], True),
        ("uk_ly_factory_statement_payment_company_source", ["company", "source_ref"], True),
        ("idx_ly_factory_statement_payment_statement", ["company", "statement_id"], False),
        ("idx_ly_factory_statement_payment_supplier", ["company", "supplier"], False),
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
    _ensure_schema(bind)
    _create_table(bind, schema)
    _create_indexes(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for index_name in [
        "idx_ly_factory_statement_payment_supplier",
        "idx_ly_factory_statement_payment_statement",
        "uk_ly_factory_statement_payment_company_source",
        "uk_ly_factory_statement_payment_company_idem",
        "uk_ly_factory_statement_payment_company_no",
    ]:
        _drop_index_if_exists(bind, schema, index_name)
    if _table_exists(bind, schema, _TABLE):
        op.drop_table(_TABLE, schema=schema)
