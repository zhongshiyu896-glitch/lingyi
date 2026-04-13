"""TASK-003 create workshop tables

Revision ID: task_003_create_workshop_tables
Revises: task_001e_create_security_audit_log
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_003_create_workshop_tables"
down_revision = "task_001e_create_security_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workshop ticket related tables."""
    op.execute("CREATE SCHEMA IF NOT EXISTS ly_schema")

    op.create_table(
        "ys_workshop_ticket",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("ticket_no", sa.String(length=64), nullable=False),
        sa.Column("ticket_key", sa.String(length=128), nullable=False),
        sa.Column("job_card", sa.String(length=140), nullable=False),
        sa.Column("work_order", sa.String(length=140), nullable=True),
        sa.Column("bom_id", sa.BigInteger(), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("employee", sa.String(length=140), nullable=False),
        sa.Column("process_name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("operation_type", sa.String(length=16), nullable=False),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_wage", sa.Numeric(18, 6), nullable=False),
        sa.Column("wage_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=140), nullable=True),
        sa.Column("original_ticket_id", sa.BigInteger(), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("sync_error_code", sa.String(length=64), nullable=True),
        sa.Column("sync_error_message", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_ticket"),
        sa.CheckConstraint("operation_type IN ('register', 'reversal')", name="ck_ys_workshop_ticket_operation_type"),
        sa.CheckConstraint("qty > 0", name="ck_ys_workshop_ticket_qty"),
        sa.CheckConstraint("unit_wage >= 0", name="ck_ys_workshop_ticket_unit_wage"),
        schema="ly_schema",
    )
    op.create_index("uk_ys_workshop_ticket_no", "ys_workshop_ticket", ["ticket_no"], schema="ly_schema", unique=True)
    op.create_index(
        "uk_ys_workshop_ticket_idempotent",
        "ys_workshop_ticket",
        ["ticket_key", "process_name", "color", "size", "operation_type", "work_date"],
        schema="ly_schema",
        unique=True,
    )
    op.create_index(
        "idx_ys_workshop_ticket_employee_date",
        "ys_workshop_ticket",
        ["employee", "work_date"],
        schema="ly_schema",
    )
    op.create_index("idx_ys_workshop_ticket_job_card", "ys_workshop_ticket", ["job_card"], schema="ly_schema")
    op.create_index(
        "idx_ys_workshop_ticket_item_process",
        "ys_workshop_ticket",
        ["item_code", "process_name"],
        schema="ly_schema",
    )
    op.create_index("idx_ys_workshop_ticket_sync_status", "ys_workshop_ticket", ["sync_status"], schema="ly_schema")

    op.create_table(
        "ys_workshop_daily_wage",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("employee", sa.String(length=140), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("process_name", sa.String(length=100), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=True),
        sa.Column("register_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("reversal_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("net_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("wage_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("last_ticket_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_daily_wage"),
        schema="ly_schema",
    )
    op.create_index(
        "uk_ys_workshop_daily_wage_emp_date_process_item",
        "ys_workshop_daily_wage",
        ["employee", "work_date", "process_name", "item_code"],
        schema="ly_schema",
        unique=True,
    )
    op.create_index("idx_ys_workshop_daily_wage_work_date", "ys_workshop_daily_wage", ["work_date"], schema="ly_schema")
    op.create_index("idx_ys_workshop_daily_wage_employee", "ys_workshop_daily_wage", ["employee"], schema="ly_schema")

    op.create_table(
        "ly_operation_wage_rate",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("item_code", sa.String(length=140), nullable=True),
        sa.Column("process_name", sa.String(length=100), nullable=False),
        sa.Column("wage_rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_operation_wage_rate"),
        sa.CheckConstraint("wage_rate >= 0", name="ck_ly_operation_wage_rate"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_item_process",
        "ly_operation_wage_rate",
        ["item_code", "process_name"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_effective",
        "ly_operation_wage_rate",
        ["effective_from", "effective_to"],
        schema="ly_schema",
    )

    op.create_table(
        "ys_workshop_job_card_sync_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("job_card", sa.String(length=140), nullable=False),
        sa.Column("sync_type", sa.String(length=32), nullable=False),
        sa.Column("local_completed_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("erpnext_status", sa.String(length=32), nullable=False),
        sa.Column("erpnext_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_job_card_sync_log"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_log_job_card",
        "ys_workshop_job_card_sync_log",
        ["job_card"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_log_status",
        "ys_workshop_job_card_sync_log",
        ["erpnext_status"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_log_created_at",
        "ys_workshop_job_card_sync_log",
        ["created_at"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Drop workshop ticket related tables."""
    op.drop_index(
        "idx_ys_workshop_job_card_sync_log_created_at",
        table_name="ys_workshop_job_card_sync_log",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ys_workshop_job_card_sync_log_status",
        table_name="ys_workshop_job_card_sync_log",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ys_workshop_job_card_sync_log_job_card",
        table_name="ys_workshop_job_card_sync_log",
        schema="ly_schema",
    )
    op.drop_table("ys_workshop_job_card_sync_log", schema="ly_schema")

    op.drop_index("idx_ly_operation_wage_rate_effective", table_name="ly_operation_wage_rate", schema="ly_schema")
    op.drop_index("idx_ly_operation_wage_rate_item_process", table_name="ly_operation_wage_rate", schema="ly_schema")
    op.drop_table("ly_operation_wage_rate", schema="ly_schema")

    op.drop_index("idx_ys_workshop_daily_wage_employee", table_name="ys_workshop_daily_wage", schema="ly_schema")
    op.drop_index("idx_ys_workshop_daily_wage_work_date", table_name="ys_workshop_daily_wage", schema="ly_schema")
    op.drop_index(
        "uk_ys_workshop_daily_wage_emp_date_process_item",
        table_name="ys_workshop_daily_wage",
        schema="ly_schema",
    )
    op.drop_table("ys_workshop_daily_wage", schema="ly_schema")

    op.drop_index("idx_ys_workshop_ticket_sync_status", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_index("idx_ys_workshop_ticket_item_process", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_index("idx_ys_workshop_ticket_job_card", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_index("idx_ys_workshop_ticket_employee_date", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_index("uk_ys_workshop_ticket_idempotent", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_index("uk_ys_workshop_ticket_no", table_name="ys_workshop_ticket", schema="ly_schema")
    op.drop_table("ys_workshop_ticket", schema="ly_schema")
