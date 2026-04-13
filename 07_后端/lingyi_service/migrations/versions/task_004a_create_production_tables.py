"""TASK-004A production plan baseline and Work Order outbox tables.

Revision ID: task_004a_create_production_tables
Revises: task_002h1_subcontract_settlement_operation_idempotency
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_004a_create_production_tables"
down_revision = "task_002h1_subcontract_settlement_operation_idempotency"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified_table(schema: str | None, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name, schema=schema):
        if str(column.get("name")) == column_name:
            return True
    return False


def _ensure_schema(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _json_type(bind):
    if _is_sqlite(bind):
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _create_tables(bind, schema: str | None) -> None:
    plan_table = "ly_production_plan"
    material_table = "ly_production_plan_material"
    link_table = "ly_production_work_order_link"
    outbox_table = "ly_production_work_order_outbox"
    job_card_table = "ly_production_job_card_link"
    status_log_table = "ly_production_status_log"

    if not _table_exists(bind, schema, plan_table):
        op.create_table(
            plan_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("plan_no", sa.String(length=64), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("sales_order", sa.String(length=140), nullable=False),
            sa.Column("sales_order_item", sa.String(length=140), nullable=False),
            sa.Column("customer", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("bom_id", sa.BigInteger(), nullable=False),
            sa.Column("bom_version", sa.String(length=64), nullable=True),
            sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("planned_start_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_plan"),
            schema=schema,
        )

    if not _index_exists(bind, schema, plan_table, "uk_ly_production_plan_no"):
        op.create_index("uk_ly_production_plan_no", plan_table, ["plan_no"], unique=True, schema=schema)
    if not _index_exists(bind, schema, plan_table, "uk_ly_production_plan_company_idempotency"):
        op.create_index(
            "uk_ly_production_plan_company_idempotency",
            plan_table,
            ["company", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, plan_table, "idx_ly_production_plan_company_status"):
        op.create_index("idx_ly_production_plan_company_status", plan_table, ["company", "status"], schema=schema)
    if not _index_exists(bind, schema, plan_table, "idx_ly_production_plan_so_item"):
        op.create_index("idx_ly_production_plan_so_item", plan_table, ["sales_order", "sales_order_item"], schema=schema)
    if not _index_exists(bind, schema, plan_table, "idx_ly_production_plan_item_status"):
        op.create_index("idx_ly_production_plan_item_status", plan_table, ["item_code", "status"], schema=schema)
    if not _column_exists(bind, schema, plan_table, "planned_start_date"):
        op.add_column(
            plan_table,
            sa.Column("planned_start_date", sa.Date(), nullable=True),
            schema=schema,
        )

    if not _table_exists(bind, schema, material_table):
        op.create_table(
            material_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("bom_item_id", sa.BigInteger(), nullable=True),
            sa.Column("material_item_code", sa.String(length=140), nullable=False),
            sa.Column("warehouse", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("qty_per_piece", sa.Numeric(18, 6), nullable=False),
            sa.Column("loss_rate", sa.Numeric(12, 6), nullable=False, server_default="0"),
            sa.Column("required_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("available_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("shortage_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["plan_id"], [_qualified_table(schema, plan_table) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_plan_material"),
            schema=schema,
        )

    if not _index_exists(bind, schema, material_table, "idx_ly_production_plan_material_plan"):
        op.create_index("idx_ly_production_plan_material_plan", material_table, ["plan_id"], schema=schema)
    if not _index_exists(bind, schema, material_table, "idx_ly_production_plan_material_item"):
        op.create_index("idx_ly_production_plan_material_item", material_table, ["material_item_code"], schema=schema)
    if not _column_exists(bind, schema, material_table, "warehouse"):
        op.add_column(
            material_table,
            sa.Column("warehouse", sa.String(length=140), nullable=False, server_default=""),
            schema=schema,
        )
    if not _column_exists(bind, schema, material_table, "checked_at"):
        op.add_column(
            material_table,
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=schema,
        )

    if not _table_exists(bind, schema, link_table):
        op.create_table(
            link_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("work_order", sa.String(length=140), nullable=False),
            sa.Column("erpnext_docstatus", sa.Integer(), nullable=True),
            sa.Column("erpnext_status", sa.String(length=64), nullable=True),
            sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(length=140), nullable=False, server_default="system"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["plan_id"], [_qualified_table(schema, plan_table) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_work_order_link"),
            schema=schema,
        )

    if not _index_exists(bind, schema, link_table, "uk_ly_production_work_order_link_work_order"):
        op.create_index("uk_ly_production_work_order_link_work_order", link_table, ["work_order"], unique=True, schema=schema)
    if not _column_exists(bind, schema, link_table, "last_synced_at"):
        op.add_column(
            link_table,
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            schema=schema,
        )
    if not _column_exists(bind, schema, link_table, "created_by"):
        op.add_column(
            link_table,
            sa.Column("created_by", sa.String(length=140), nullable=False, server_default="system"),
            schema=schema,
        )
    duplicate_plan_links = bind.execute(
        sa.text(
            f"""
            SELECT plan_id
            FROM {_qualified_table(schema, link_table)}
            GROUP BY plan_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).fetchone()
    if duplicate_plan_links is not None:
        raise RuntimeError("migration blocked: duplicate ly_production_work_order_link.plan_id found before unique index")
    if not _index_exists(bind, schema, link_table, "uk_ly_production_work_order_link_plan"):
        op.create_index("uk_ly_production_work_order_link_plan", link_table, ["plan_id"], unique=True, schema=schema)
    if not _index_exists(bind, schema, link_table, "idx_ly_production_work_order_link_plan"):
        op.create_index("idx_ly_production_work_order_link_plan", link_table, ["plan_id"], schema=schema)
    if not _index_exists(bind, schema, link_table, "idx_ly_production_work_order_sync_status"):
        op.create_index("idx_ly_production_work_order_sync_status", link_table, ["sync_status"], schema=schema)

    if not _table_exists(bind, schema, outbox_table):
        op.create_table(
            outbox_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("event_key", sa.String(length=140), nullable=False),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False, server_default="create_work_order"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=True),
            sa.Column("payload_json", _json_type(bind), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("locked_by", sa.String(length=140), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("erpnext_work_order", sa.String(length=140), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("last_error_message", sa.String(length=255), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["plan_id"], [_qualified_table(schema, plan_table) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_work_order_outbox"),
            sa.CheckConstraint("status IN ('pending','processing','succeeded','failed','dead')", name="ck_ly_production_work_order_outbox_status"),
            sa.CheckConstraint("attempts >= 0", name="ck_ly_production_work_order_outbox_attempts"),
            sa.CheckConstraint("max_attempts > 0", name="ck_ly_production_work_order_outbox_max_attempts"),
            schema=schema,
        )

    if not _index_exists(bind, schema, outbox_table, "uk_ly_production_work_order_outbox_event_key"):
        op.create_index("uk_ly_production_work_order_outbox_event_key", outbox_table, ["event_key"], unique=True, schema=schema)
    if not _index_exists(bind, schema, outbox_table, "idx_ly_production_work_order_outbox_due"):
        op.create_index(
            "idx_ly_production_work_order_outbox_due",
            outbox_table,
            ["action", "status", "next_retry_at", "id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, outbox_table, "idx_ly_production_work_order_outbox_scope"):
        op.create_index(
            "idx_ly_production_work_order_outbox_scope",
            outbox_table,
            ["company", "item_code", "status", "next_retry_at"],
            schema=schema,
        )
    if not _index_exists(bind, schema, outbox_table, "idx_ly_production_work_order_outbox_work_order"):
        op.create_index(
            "idx_ly_production_work_order_outbox_work_order",
            outbox_table,
            ["erpnext_work_order"],
            schema=schema,
        )
    if not _column_exists(bind, schema, outbox_table, "payload_hash"):
        op.add_column(
            outbox_table,
            sa.Column("payload_hash", sa.String(length=64), nullable=True),
            schema=schema,
        )
    if not _column_exists(bind, schema, outbox_table, "lease_until"):
        op.add_column(
            outbox_table,
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            schema=schema,
        )
    if not _index_exists(bind, schema, outbox_table, "idx_ly_production_work_order_outbox_lease"):
        op.create_index(
            "idx_ly_production_work_order_outbox_lease",
            outbox_table,
            ["status", "next_retry_at", "lease_until"],
            schema=schema,
        )

    if not _table_exists(bind, schema, job_card_table):
        op.create_table(
            job_card_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("work_order", sa.String(length=140), nullable=False),
            sa.Column("job_card", sa.String(length=140), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("item_code", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("operation", sa.String(length=140), nullable=True),
            sa.Column("operation_sequence", sa.Integer(), nullable=True),
            sa.Column("expected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("completed_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("erpnext_status", sa.String(length=64), nullable=True),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["plan_id"], [_qualified_table(schema, plan_table) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_job_card_link"),
            schema=schema,
        )

    if not _index_exists(bind, schema, job_card_table, "uk_ly_production_job_card_link_job_card"):
        op.create_index("uk_ly_production_job_card_link_job_card", job_card_table, ["job_card"], unique=True, schema=schema)
    if not _column_exists(bind, schema, job_card_table, "company"):
        op.add_column(
            job_card_table,
            sa.Column("company", sa.String(length=140), nullable=False, server_default=""),
            schema=schema,
        )
    if not _column_exists(bind, schema, job_card_table, "item_code"):
        op.add_column(
            job_card_table,
            sa.Column("item_code", sa.String(length=140), nullable=False, server_default=""),
            schema=schema,
        )
    if not _column_exists(bind, schema, job_card_table, "operation_sequence"):
        op.add_column(
            job_card_table,
            sa.Column("operation_sequence", sa.Integer(), nullable=True),
            schema=schema,
        )
    if not _column_exists(bind, schema, job_card_table, "synced_at"):
        op.add_column(
            job_card_table,
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            schema=schema,
        )
    if not _index_exists(bind, schema, job_card_table, "idx_ly_production_job_card_link_plan"):
        op.create_index("idx_ly_production_job_card_link_plan", job_card_table, ["plan_id"], schema=schema)
    if not _index_exists(bind, schema, job_card_table, "idx_ly_production_job_card_link_work_order"):
        op.create_index("idx_ly_production_job_card_link_work_order", job_card_table, ["work_order"], schema=schema)
    if not _index_exists(bind, schema, job_card_table, "idx_ly_production_job_card_company_item"):
        op.create_index(
            "idx_ly_production_job_card_company_item",
            job_card_table,
            ["company", "item_code"],
            schema=schema,
        )

    if not _table_exists(bind, schema, status_log_table):
        op.create_table(
            status_log_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("from_status", sa.String(length=32), nullable=False),
            sa.Column("to_status", sa.String(length=32), nullable=False),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("operator", sa.String(length=140), nullable=False),
            sa.Column("operated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(["plan_id"], [_qualified_table(schema, plan_table) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_status_log"),
            schema=schema,
        )

    if not _index_exists(bind, schema, status_log_table, "idx_ly_production_status_log_plan_time"):
        op.create_index(
            "idx_ly_production_status_log_plan_time",
            status_log_table,
            ["plan_id", "operated_at"],
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_tables(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
