"""TASK-006D create factory statement payable outbox table.

Revision ID: task_006d_factory_statement_payable_outbox
Revises: task_006c_factory_statement_operation_table
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_006d_factory_statement_payable_outbox"
down_revision = "task_006c_factory_statement_operation_table"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


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

    statement_table = "ly_factory_statement"
    table = "ly_factory_statement_payable_outbox"
    if not _table_exists(bind, schema, statement_table):
        return

    if not _table_exists(bind, schema, table):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("statement_id", sa.BigInteger(), nullable=False),
            sa.Column("statement_no", sa.String(length=64), nullable=False),
            sa.Column("supplier", sa.String(length=140), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("event_key", sa.String(length=140), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("locked_by", sa.String(length=140), nullable=True),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("erpnext_purchase_invoice", sa.String(length=140), nullable=True),
            sa.Column("erpnext_docstatus", sa.Integer(), nullable=True),
            sa.Column("erpnext_status", sa.String(length=64), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("last_error_message", sa.String(length=255), nullable=True),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "status IN ('pending','processing','succeeded','failed','dead')",
                name="ck_ly_factory_statement_payable_outbox_status",
            ),
            sa.CheckConstraint(
                "attempts >= 0",
                name="ck_ly_factory_statement_payable_outbox_attempts",
            ),
            sa.CheckConstraint(
                "max_attempts > 0",
                name="ck_ly_factory_statement_payable_outbox_max_attempts",
            ),
            sa.ForeignKeyConstraint(
                ["statement_id"],
                [f"{schema + '.' if schema else ''}{statement_table}.id"],
                name="fk_ly_factory_statement_payable_outbox_statement",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "uk_ly_factory_statement_payable_event_key"):
        op.create_index(
            "uk_ly_factory_statement_payable_event_key",
            table,
            ["event_key"],
            unique=True,
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "uk_ly_factory_statement_payable_idem"):
        op.create_index(
            "uk_ly_factory_statement_payable_idem",
            table,
            ["company", "statement_id", "idempotency_key"],
            unique=True,
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "idx_ly_factory_statement_payable_due"):
        op.create_index(
            "idx_ly_factory_statement_payable_due",
            table,
            ["status", "next_retry_at", "id"],
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "idx_ly_factory_statement_payable_statement"):
        op.create_index(
            "idx_ly_factory_statement_payable_statement",
            table,
            ["statement_id", "status", "id"],
            schema=schema,
        )


def downgrade() -> None:
    """No destructive downgrade in hardening migration."""
    return
