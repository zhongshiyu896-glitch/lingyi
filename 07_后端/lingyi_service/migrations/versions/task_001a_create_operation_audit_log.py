"""TASK-001A create operation audit log

Revision ID: task_001a_create_operation_audit_log
Revises: task_001_create_bom_tables
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_001a_create_operation_audit_log"
down_revision = "task_001_create_bom_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sensitive operation audit log table."""
    op.create_table(
        "ly_operation_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=140), nullable=False),
        sa.Column("operator_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=True),
        sa.Column("resource_no", sa.String(length=140), nullable=True),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_operation_audit_log"),
        sa.CheckConstraint("result IN ('success', 'failed')", name="ck_ly_operation_audit_log_result"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_audit_module_action",
        "ly_operation_audit_log",
        ["module", "action"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_audit_operator_time",
        "ly_operation_audit_log",
        ["operator", "created_at"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_audit_resource",
        "ly_operation_audit_log",
        ["resource_type", "resource_id"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_audit_request_id",
        "ly_operation_audit_log",
        ["request_id"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Drop sensitive operation audit log table."""
    op.drop_index("idx_ly_operation_audit_request_id", table_name="ly_operation_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_operation_audit_resource", table_name="ly_operation_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_operation_audit_operator_time", table_name="ly_operation_audit_log", schema="ly_schema")
    op.drop_index("idx_ly_operation_audit_module_action", table_name="ly_operation_audit_log", schema="ly_schema")
    op.drop_table("ly_operation_audit_log", schema="ly_schema")
