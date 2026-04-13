"""TASK-001E create security audit log table

Revision ID: task_001e_create_security_audit_log
Revises: task_001a_create_operation_audit_log
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_001e_create_security_audit_log"
down_revision = "task_001a_create_operation_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create security audit log table."""
    op.create_table(
        "ly_security_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=140), nullable=True),
        sa.Column("resource_no", sa.String(length=140), nullable=True),
        sa.Column("user_id", sa.String(length=140), nullable=True),
        sa.Column("user_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("permission_source", sa.String(length=32), nullable=True),
        sa.Column("deny_reason", sa.String(length=255), nullable=False),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_security_audit_log"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_created_at",
        "ly_security_audit_log",
        ["created_at"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_user_id",
        "ly_security_audit_log",
        ["user_id"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_event_type",
        "ly_security_audit_log",
        ["event_type"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_module_action",
        "ly_security_audit_log",
        ["module", "action"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_resource",
        "ly_security_audit_log",
        ["resource_type", "resource_id"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_security_audit_log_request_id",
        "ly_security_audit_log",
        ["request_id"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Drop security audit log table."""
    op.drop_index("idx_ly_security_audit_log_request_id", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_security_audit_log_resource", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_security_audit_log_module_action", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_security_audit_log_event_type", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_security_audit_log_user_id", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_security_audit_log_created_at", table_name="ly_security_audit_log", schema="ly_schema")
    op.drop_table("ly_security_audit_log", schema="ly_schema")

