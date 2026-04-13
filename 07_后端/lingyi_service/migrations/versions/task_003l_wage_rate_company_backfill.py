"""TASK-003L wage-rate company backfill and legacy scope hardening

Revision ID: task_003l_wage_rate_company_backfill
Revises: task_003i_outbox_denial_throttle
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_003l_wage_rate_company_backfill"
down_revision = "task_003i_outbox_denial_throttle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create backfill log table and close legacy null-company item rates."""
    op.create_table(
        "ly_operation_wage_rate_company_backfill_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True),
        sa.Column("wage_rate_id", sa.BigInteger(), nullable=False),
        sa.Column("item_code", sa.String(length=140), nullable=False),
        sa.Column("old_company", sa.String(length=140), nullable=True),
        sa.Column("new_company", sa.String(length=140), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ly_operation_wage_rate_company_backfill_log"),
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_backfill_wage_rate",
        "ly_operation_wage_rate_company_backfill_log",
        ["wage_rate_id"],
        schema="ly_schema",
    )
    op.create_index(
        "idx_ly_operation_wage_rate_backfill_result",
        "ly_operation_wage_rate_company_backfill_log",
        ["result"],
        schema="ly_schema",
    )
    op.create_index(
        "uk_ly_operation_wage_rate_backfill_once",
        "ly_operation_wage_rate_company_backfill_log",
        ["wage_rate_id", "result", "new_company", "reason"],
        unique=True,
        schema="ly_schema",
    )

    # 0) Normalize blank company to NULL for item-specific active legacy rows.
    op.execute(
        """
        WITH normalized AS (
            UPDATE ly_schema.ly_operation_wage_rate AS r
            SET company = NULL,
                updated_at = NOW()
            WHERE r.item_code IS NOT NULL
              AND r.status = 'active'
              AND r.company IS NOT NULL
              AND btrim(r.company) = ''
            RETURNING r.id, r.item_code
        )
        INSERT INTO ly_schema.ly_operation_wage_rate_company_backfill_log (
            wage_rate_id,
            item_code,
            old_company,
            new_company,
            result,
            reason,
            created_at
        )
        SELECT
            n.id,
            n.item_code,
            '',
            NULL,
            'normalized_blank_company',
            'normalized_blank_company',
            NOW()
        FROM normalized AS n
        WHERE NOT EXISTS (
            SELECT 1
            FROM ly_schema.ly_operation_wage_rate_company_backfill_log AS l
            WHERE l.wage_rate_id = n.id
              AND l.result = 'normalized_blank_company'
              AND l.new_company IS NULL
              AND l.reason = 'normalized_blank_company'
        );
        """
    )

    # 1) Backfill rows that can be uniquely inferred from existing scoped rates.
    op.execute(
        """
        WITH unique_company AS (
            SELECT item_code, MIN(company) AS company
            FROM ly_schema.ly_operation_wage_rate
            WHERE item_code IS NOT NULL
              AND company IS NOT NULL
              AND btrim(company) <> ''
            GROUP BY item_code
            HAVING COUNT(DISTINCT company) = 1
        ), updated AS (
            UPDATE ly_schema.ly_operation_wage_rate AS r
            SET company = u.company,
                updated_at = NOW()
            FROM unique_company AS u
            WHERE r.item_code = u.item_code
              AND r.item_code IS NOT NULL
              AND (r.company IS NULL OR btrim(r.company) = '')
              AND r.status = 'active'
            RETURNING r.id, r.item_code, u.company
        )
        INSERT INTO ly_schema.ly_operation_wage_rate_company_backfill_log (
            wage_rate_id,
            item_code,
            old_company,
            new_company,
            result,
            reason,
            created_at
        )
        SELECT
            u.id,
            u.item_code,
            NULL,
            u.company,
            'backfilled',
            'unique_company',
            NOW()
        FROM updated AS u
        WHERE NOT EXISTS (
            SELECT 1
            FROM ly_schema.ly_operation_wage_rate_company_backfill_log AS l
            WHERE l.wage_rate_id = u.id
              AND l.result = 'backfilled'
              AND l.new_company = u.company
              AND l.reason = 'unique_company'
        );
        """
    )

    # 2) Ambiguous company -> fail closed (inactive).
    op.execute(
        """
        WITH ambiguous_item AS (
            SELECT item_code
            FROM ly_schema.ly_operation_wage_rate
            WHERE item_code IS NOT NULL
              AND company IS NOT NULL
              AND btrim(company) <> ''
            GROUP BY item_code
            HAVING COUNT(DISTINCT company) > 1
        ), blocked AS (
            UPDATE ly_schema.ly_operation_wage_rate AS r
            SET status = 'inactive',
                updated_at = NOW()
            FROM ambiguous_item AS a
            WHERE r.item_code = a.item_code
              AND r.item_code IS NOT NULL
              AND (r.company IS NULL OR btrim(r.company) = '')
              AND r.status = 'active'
            RETURNING r.id, r.item_code
        )
        INSERT INTO ly_schema.ly_operation_wage_rate_company_backfill_log (
            wage_rate_id,
            item_code,
            old_company,
            new_company,
            result,
            reason,
            created_at
        )
        SELECT
            b.id,
            b.item_code,
            NULL,
            NULL,
            'blocked',
            'WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS',
            NOW()
        FROM blocked AS b
        WHERE NOT EXISTS (
            SELECT 1
            FROM ly_schema.ly_operation_wage_rate_company_backfill_log AS l
            WHERE l.wage_rate_id = b.id
              AND l.result = 'blocked'
              AND l.new_company IS NULL
              AND l.reason = 'WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS'
        );
        """
    )

    # 3) Remaining unresolved company -> fail closed (inactive).
    op.execute(
        """
        WITH unresolved AS (
            UPDATE ly_schema.ly_operation_wage_rate AS r
            SET status = 'inactive',
                updated_at = NOW()
            WHERE r.item_code IS NOT NULL
              AND (r.company IS NULL OR btrim(r.company) = '')
              AND r.status = 'active'
            RETURNING r.id, r.item_code
        )
        INSERT INTO ly_schema.ly_operation_wage_rate_company_backfill_log (
            wage_rate_id,
            item_code,
            old_company,
            new_company,
            result,
            reason,
            created_at
        )
        SELECT
            u.id,
            u.item_code,
            NULL,
            NULL,
            'blocked',
            'WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED',
            NOW()
        FROM unresolved AS u
        WHERE NOT EXISTS (
            SELECT 1
            FROM ly_schema.ly_operation_wage_rate_company_backfill_log AS l
            WHERE l.wage_rate_id = u.id
              AND l.result = 'blocked'
              AND l.new_company IS NULL
              AND l.reason = 'WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED'
        );
        """
    )


def downgrade() -> None:
    """Drop backfill log table (data updates are not reverted)."""
    op.drop_index(
        "uk_ly_operation_wage_rate_backfill_once",
        table_name="ly_operation_wage_rate_company_backfill_log",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ly_operation_wage_rate_backfill_result",
        table_name="ly_operation_wage_rate_company_backfill_log",
        schema="ly_schema",
    )
    op.drop_index(
        "idx_ly_operation_wage_rate_backfill_wage_rate",
        table_name="ly_operation_wage_rate_company_backfill_log",
        schema="ly_schema",
    )
    op.drop_table("ly_operation_wage_rate_company_backfill_log", schema="ly_schema")
