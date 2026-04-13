"""TASK-003I outbox denial throttle and security-audit dedupe

Revision ID: task_003i_outbox_denial_throttle
Revises: task_003d_create_workshop_outbox
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_003i_outbox_denial_throttle"
down_revision = "task_003d_create_workshop_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create denial dedupe table and add security-audit dedupe key."""
    op.create_table(
        "ys_workshop_outbox_access_denial",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("outbox_id", sa.BigInteger(), nullable=False),
        sa.Column("principal", sa.String(length=140), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_audit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_audit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seen_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ys_workshop_outbox_access_denial"),
        schema="ly_schema",
    )
    op.create_index(
        "uk_ys_workshop_outbox_access_denial_outbox_principal_reason_scope",
        "ys_workshop_outbox_access_denial",
        ["outbox_id", "principal", "reason_code", "scope_hash"],
        unique=True,
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_outbox_access_denial_next_audit_at",
        "ys_workshop_outbox_access_denial",
        ["next_audit_at"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ys_workshop_job_card_sync_outbox_scope_status_retry",
        "ys_workshop_job_card_sync_outbox",
        ["company", "item_code", "status", "next_retry_at"],
        schema="ly_schema",
    )

    op.add_column(
        "ly_security_audit_log",
        sa.Column("dedupe_key", sa.String(length=64), nullable=True),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_dedupe_key_created_at",
        "ly_security_audit_log",
        ["dedupe_key", "created_at"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Rollback TASK-003I schema changes."""
    op.drop_index(
        "idx_ly_security_audit_log_dedupe_key_created_at",
        table_name="ly_security_audit_log",
        schema="ly_schema",
    )
    op.drop_column("ly_security_audit_log", "dedupe_key", schema="ly_schema")

    op.drop_index(
        "idx_ys_workshop_job_card_sync_outbox_scope_status_retry",
        table_name="ys_workshop_job_card_sync_outbox",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ys_workshop_outbox_access_denial_next_audit_at",
        table_name="ys_workshop_outbox_access_denial",
        schema="ly_schema",
    )
    op.drop_index(
        "uk_ys_workshop_outbox_access_denial_outbox_principal_reason_scope",
        table_name="ys_workshop_outbox_access_denial",
        schema="ly_schema",
    )
    op.drop_table("ys_workshop_outbox_access_denial", schema="ly_schema")
