"""TASK-003B wage rate resource scope

Revision ID: task_003b_wage_rate_resource_scope
Revises: task_003_create_workshop_tables
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_003b_wage_rate_resource_scope"
down_revision = "task_003_create_workshop_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add company/is_global scope columns and indexes for wage rate resource permission."""
    op.add_column(
        "ly_operation_wage_rate",
        sa.Column("company", sa.String(length=140), nullable=True),
        schema="ly_schema",
    )
    op.add_column(
        "ly_operation_wage_rate",
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="ly_schema",
    )
    op.execute("UPDATE ly_schema.ly_operation_wage_rate SET is_global = true WHERE item_code IS NULL")

    op.create_index(
        "idx_ly_operation_wage_rate_company_item_process",
        "ly_operation_wage_rate",
        ["company", "item_code", "process_name"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_company_status",
        "ly_operation_wage_rate",
        ["company", "status"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_global",
        "ly_operation_wage_rate",
        ["is_global", "status"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Revert wage rate resource scope columns and indexes."""
    op.drop_index(
        "idx_ly_operation_wage_rate_global",
        table_name="ly_operation_wage_rate",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ly_operation_wage_rate_company_status",
        table_name="ly_operation_wage_rate",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ly_operation_wage_rate_company_item_process",
        table_name="ly_operation_wage_rate",
        schema="ly_schema",
    )

    op.drop_column("ly_operation_wage_rate", "is_global", schema="ly_schema")
    op.drop_column("ly_operation_wage_rate", "company", schema="ly_schema")
