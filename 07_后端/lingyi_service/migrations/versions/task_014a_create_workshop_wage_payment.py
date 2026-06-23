"""TASK-014A create workshop wage payment table.

Revision ID: task_014a_create_workshop_wage_payment
Revises: task_097a_add_bom_context_to_stock_ledger_entries
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_014a_create_workshop_wage_payment"
down_revision = "task_097a_add_bom_context_to_stock_ledger_entries"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ys_workshop_wage_payment"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    return any(str(index.get("name")) == index_name for index in sa.inspect(bind).get_indexes(table_name, schema=schema))


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_table(bind, schema: str | None) -> None:
    if _table_exists(bind, schema, _TABLE_NAME):
        return
    op.create_table(
        _TABLE_NAME,
        sa.Column("id", _id_type(bind), autoincrement=True),
        sa.Column("payment_entry", sa.String(length=140), nullable=False),
        sa.Column("employee", sa.String(length=140), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("process_name", sa.String(length=100), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=True),
        sa.Column("wage_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("outstanding_before", sa.Numeric(18, 6), nullable=False),
        sa.Column("outstanding_after", sa.Numeric(18, 6), nullable=False),
        sa.Column("mode_of_payment", sa.String(length=140), nullable=False, server_default="Bank Transfer"),
        sa.Column("reference_no", sa.String(length=140), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("source_ref", sa.String(length=140), nullable=False),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("scenario_tag", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_wage_payment"),
        sa.CheckConstraint("paid_amount > 0", name="ck_ys_workshop_wage_payment_paid_positive"),
        sa.CheckConstraint("outstanding_before >= 0", name="ck_ys_workshop_wage_payment_before_nonnegative"),
        sa.CheckConstraint("outstanding_after >= 0", name="ck_ys_workshop_wage_payment_after_nonnegative"),
        sa.CheckConstraint("status IN ('submitted','cancelled')", name="ck_ys_workshop_wage_payment_status"),
        schema=schema,
    )


def _create_index_if_needed(bind, schema: str | None, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, _TABLE_NAME) and not _index_exists(bind, schema, _TABLE_NAME, index_name):
        op.create_index(index_name, _TABLE_NAME, columns, unique=unique, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_table(bind, schema)
    _create_index_if_needed(bind, schema, "uk_ys_workshop_wage_payment_entry", ["payment_entry"], unique=True)
    _create_index_if_needed(bind, schema, "uk_ys_workshop_wage_payment_idem", ["idempotency_key"], unique=True)
    _create_index_if_needed(bind, schema, "uk_ys_workshop_wage_payment_source", ["source_ref"], unique=True)
    _create_index_if_needed(
        bind,
        schema,
        "idx_ys_workshop_wage_payment_daily",
        ["employee", "work_date", "process_name", "item_code"],
    )
    _create_index_if_needed(bind, schema, "idx_ys_workshop_wage_payment_status", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE_NAME):
        return
    for index_name in (
        "idx_ys_workshop_wage_payment_status",
        "idx_ys_workshop_wage_payment_daily",
        "uk_ys_workshop_wage_payment_source",
        "uk_ys_workshop_wage_payment_idem",
        "uk_ys_workshop_wage_payment_entry",
    ):
        if _index_exists(bind, schema, _TABLE_NAME, index_name):
            op.drop_index(index_name, table_name=_TABLE_NAME, schema=schema)
    op.drop_table(_TABLE_NAME, schema=schema)
