"""TASK-003D create workshop outbox

Revision ID: task_003d_create_workshop_outbox
Revises: task_003b_wage_rate_resource_scope
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_003d_create_workshop_outbox"
down_revision = "task_003b_wage_rate_resource_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workshop job-card sync outbox and enrich sync-log fields."""
    op.create_table(
        "ys_workshop_job_card_sync_outbox",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("event_key", sa.String(length=140), nullable=False),
        sa.Column("job_card", sa.String(length=140), nullable=False),
        sa.Column("work_order", sa.String(length=140), nullable=True),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("company", sa.String(length=140), nullable=False),
        sa.Column("local_completed_qty", sa.Numeric(18, 6), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_by", sa.String(length=140), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_job_card_sync_outbox"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed', 'dead')",
            name="ck_ys_workshop_job_card_sync_outbox_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_ys_workshop_job_card_sync_outbox_attempts"),
        sa.CheckConstraint("max_attempts > 0", name="ck_ys_workshop_job_card_sync_outbox_max_attempts"),
        schema="ly_schema",
    )
    op.create_index(
        "uk_ys_workshop_job_card_sync_outbox_event_key",
        "ys_workshop_job_card_sync_outbox",
        ["event_key"],
        schema="ly_schema",
        unique=True,
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_outbox_status_retry",
        "ys_workshop_job_card_sync_outbox",
        ["status", "next_retry_at"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_outbox_job_card",
        "ys_workshop_job_card_sync_outbox",
        ["job_card"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_outbox_company_item",
        "ys_workshop_job_card_sync_outbox",
        ["company", "item_code"],
        schema="ly_schema",
    )

    op.add_column(
        "ys_workshop_job_card_sync_log",
        sa.Column("outbox_id", sa.BigInteger(), nullable=True),
        schema="ly_schema",
    )
    op.add_column(
        "ys_workshop_job_card_sync_log",
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_log_outbox_id",
        "ys_workshop_job_card_sync_log",
        ["outbox_id"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Drop workshop outbox and rollback sync-log fields."""
    op.drop_index(
        "idx_ys_workshop_job_card_sync_log_outbox_id",
        table_name="ys_workshop_job_card_sync_log",
        schema="ly_schema",
    )
    op.drop_column("ys_workshop_job_card_sync_log", "attempt_no", schema="ly_schema")
    op.drop_column("ys_workshop_job_card_sync_log", "outbox_id", schema="ly_schema")

    op.drop_index(
        "idx_ys_workshop_job_card_sync_outbox_company_item",
        table_name="ys_workshop_job_card_sync_outbox",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ys_workshop_job_card_sync_outbox_job_card",
        table_name="ys_workshop_job_card_sync_outbox",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ys_workshop_job_card_sync_outbox_status_retry",
        table_name="ys_workshop_job_card_sync_outbox",
        schema="ly_schema",
    )
    op.drop_index(
        "uk_ys_workshop_job_card_sync_outbox_event_key",
        table_name="ys_workshop_job_card_sync_outbox",
        schema="ly_schema",
    )
    op.drop_table("ys_workshop_job_card_sync_outbox", schema="ly_schema")
