"""TASK-001 create bom tables

Revision ID: task_001_create_bom_tables
Revises:
Create Date: 2026-04-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_001_create_bom_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create BOM related tables in ly_schema."""
    op.execute("CREATE SCHEMA IF NOT EXISTS ly_schema")

    op.create_table(
        "ly_apparel_bom",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("bom_no", sa.String(length=64), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("version_no", sa.String(length=32), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=140), nullable=False, server_default="system"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=140), nullable=False, server_default="system"),
        sa.PrimaryKeyConstraint("id", name="pk_ly_apparel_bom"),
        schema="ly_schema",
    )
    op.create_index("uk_ly_apparel_bom_bom_no", "ly_apparel_bom", ["bom_no"], schema="ly_schema", unique=True)
    op.create_index(
        "idx_ly_apparel_bom_item_default",
        "ly_apparel_bom",
        ["item_code", "is_default"],
        schema="ly_schema",
    )
    op.create_index("idx_ly_apparel_bom_status", "ly_apparel_bom", ["status"], schema="ly_schema")
    op.create_index(
        "uk_ly_apparel_bom_one_active_default",
        "ly_apparel_bom",
        ["item_code"],
        unique=True,
        schema="ly_schema",
        postgresql_where=sa.text("is_default = true AND status = 'active'"),
    )

    op.create_table(
        "ly_apparel_bom_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("bom_id", sa.BigInteger(), nullable=False),
        sa.Column("material_item_code", sa.String(length=140), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("qty_per_piece", sa.Numeric(18, 6), nullable=False),
        sa.Column("loss_rate", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(length=32), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ly_apparel_bom_item"),
        sa.ForeignKeyConstraint(["bom_id"], ["ly_schema.ly_apparel_bom.id"], name="fk_ly_apparel_bom_item_bom_id"),
        schema="ly_schema",
    )
    op.create_index("idx_ly_apparel_bom_item_bom_id", "ly_apparel_bom_item", ["bom_id"], schema="ly_schema")
    op.create_index(
        "idx_ly_apparel_bom_item_material",
        "ly_apparel_bom_item",
        ["material_item_code"],
        schema="ly_schema",
    )

    op.create_table(
        "ly_bom_operation",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("bom_id", sa.BigInteger(), nullable=False),
        sa.Column("process_name", sa.String(length=100), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("is_subcontract", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("wage_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("subcontract_cost_per_piece", sa.Numeric(18, 6), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ly_bom_operation"),
        sa.ForeignKeyConstraint(["bom_id"], ["ly_schema.ly_apparel_bom.id"], name="fk_ly_bom_operation_bom_id"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_bom_operation_bom_process",
        "ly_bom_operation",
        ["bom_id", "process_name"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_bom_operation_subcontract",
        "ly_bom_operation",
        ["is_subcontract"],
        schema="ly_schema",
    )


def downgrade() -> None:
    """Drop BOM related tables."""
    op.drop_index("idx_ly_bom_operation_subcontract", table_name="ly_bom_operation", schema="ly_schema")
    op.drop_index("idx_ly_bom_operation_bom_process", table_name="ly_bom_operation", schema="ly_schema")
    op.drop_table("ly_bom_operation", schema="ly_schema")

    op.drop_index("idx_ly_apparel_bom_item_material", table_name="ly_apparel_bom_item", schema="ly_schema")
    op.drop_index("idx_ly_apparel_bom_item_bom_id", table_name="ly_apparel_bom_item", schema="ly_schema")
    op.drop_table("ly_apparel_bom_item", schema="ly_schema")

    op.drop_index("idx_ly_apparel_bom_status", table_name="ly_apparel_bom", schema="ly_schema")
    op.drop_index("idx_ly_apparel_bom_item_default", table_name="ly_apparel_bom", schema="ly_schema")
    op.drop_index("uk_ly_apparel_bom_one_active_default", table_name="ly_apparel_bom", schema="ly_schema")
    op.drop_index("uk_ly_apparel_bom_bom_no", table_name="ly_apparel_bom", schema="ly_schema")
    op.drop_table("ly_apparel_bom", schema="ly_schema")
