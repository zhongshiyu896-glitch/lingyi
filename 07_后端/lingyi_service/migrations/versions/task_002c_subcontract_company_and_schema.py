"""TASK-002C subcontract company facts and scope schema.

Revision ID: task_002c_subcontract_company_and_schema
Revises: task_003l_wage_rate_company_backfill
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_002c_subcontract_company_and_schema"
down_revision = "task_003l_wage_rate_company_backfill"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _qualified_table(name: str, schema: str | None) -> str:
    return f"{schema}.{name}" if schema else name


def _trim_expr(bind) -> str:
    return "trim" if _is_sqlite(bind) else "btrim"


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name, schema=schema):
        if str(column.get("name")) == column_name:
            return True
    return False


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name, schema=schema):
        if str(index.get("name")) == index_name:
            return True
    return False


def _check_exists(bind, schema: str | None, table_name: str, check_name: str) -> bool:
    inspector = sa.inspect(bind)
    try:
        checks = inspector.get_check_constraints(table_name, schema=schema)
    except NotImplementedError:
        return False
    for check in checks:
        if str(check.get("name")) == check_name:
            return True
    return False


def _create_schema_if_needed(bind) -> None:
    if _is_sqlite(bind):
        return
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _ensure_subcontract_base_tables(bind, schema: str | None) -> None:
    order_table = "ly_subcontract_order"
    material_table = "ly_subcontract_material"
    receipt_table = "ly_subcontract_receipt"
    status_log_table = "ly_subcontract_status_log"

    if not _table_exists(bind, schema, order_table):
        op.create_table(
            order_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_no", sa.String(length=64), nullable=False),
            sa.Column("supplier", sa.String(length=140), nullable=False),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("bom_id", sa.BigInteger(), nullable=False),
            sa.Column("process_name", sa.String(length=100), nullable=False),
            sa.Column("planned_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("issued_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("gross_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["bom_id"], [_qualified_table("ly_apparel_bom", schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_order"),
            schema=schema,
        )

    if not _index_exists(bind, schema, order_table, "uk_subcontract_no"):
        op.create_index("uk_subcontract_no", order_table, ["subcontract_no"], unique=True, schema=schema)
    if not _index_exists(bind, schema, order_table, "idx_supplier_status"):
        op.create_index("idx_supplier_status", order_table, ["supplier", "status"], schema=schema)
    if not _index_exists(bind, schema, order_table, "idx_item_code"):
        op.create_index("idx_item_code", order_table, ["item_code"], schema=schema)

    if not _table_exists(bind, schema, material_table):
        op.create_table(
            material_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("material_item_code", sa.String(length=140), nullable=False),
            sa.Column("required_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("issued_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("stock_entry_name", sa.String(length=140), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_material"),
            schema=schema,
        )

    if not _index_exists(bind, schema, material_table, "idx_subcontract_id"):
        op.create_index("idx_subcontract_id", material_table, ["subcontract_id"], schema=schema)
    if not _index_exists(bind, schema, material_table, "idx_stock_entry"):
        op.create_index("idx_stock_entry", material_table, ["stock_entry_name"], schema=schema)

    if not _table_exists(bind, schema, receipt_table):
        op.create_table(
            receipt_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("stock_outbox_id", sa.BigInteger(), nullable=True),
            sa.Column("company", sa.String(length=140), nullable=True),
            sa.Column("receipt_batch_no", sa.String(length=64), nullable=True),
            sa.Column("receipt_warehouse", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=True),
            sa.Column("color", sa.String(length=64), nullable=True),
            sa.Column("size", sa.String(length=64), nullable=True),
            sa.Column("batch_no", sa.String(length=140), nullable=True),
            sa.Column("uom", sa.String(length=32), nullable=True),
            sa.Column("received_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("sync_error_code", sa.String(length=64), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=True),
            sa.Column("received_by", sa.String(length=140), nullable=True),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("stock_entry_name", sa.String(length=140), nullable=True),
            sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
            sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("inspect_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_receipt"),
            schema=schema,
        )

    if not _index_exists(bind, schema, receipt_table, "idx_subcontract_receipt_subcontract_id"):
        op.create_index("idx_subcontract_receipt_subcontract_id", receipt_table, ["subcontract_id"], schema=schema)
    if not _index_exists(bind, schema, receipt_table, "idx_inspect_status"):
        op.create_index("idx_inspect_status", receipt_table, ["inspect_status"], schema=schema)
    if not _index_exists(bind, schema, receipt_table, "idx_ly_subcontract_receipt_outbox"):
        op.create_index("idx_ly_subcontract_receipt_outbox", receipt_table, ["stock_outbox_id"], schema=schema)
    if not _index_exists(bind, schema, receipt_table, "idx_ly_subcontract_receipt_idempotency"):
        op.create_index(
            "idx_ly_subcontract_receipt_idempotency",
            receipt_table,
            ["subcontract_id", "idempotency_key"],
            schema=schema,
        )

    if not _table_exists(bind, schema, status_log_table):
        op.create_table(
            status_log_table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("from_status", sa.String(length=32), nullable=False),
            sa.Column("to_status", sa.String(length=32), nullable=False),
            sa.Column("operator", sa.String(length=140), nullable=False),
            sa.Column("operated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_status_log"),
            schema=schema,
        )

    if not _index_exists(bind, schema, status_log_table, "idx_subcontract_time"):
        op.create_index("idx_subcontract_time", status_log_table, ["subcontract_id", "operated_at"], schema=schema)


def _ensure_company_columns(bind, schema: str | None) -> None:
    order_table = "ly_subcontract_order"
    material_table = "ly_subcontract_material"
    receipt_table = "ly_subcontract_receipt"
    status_log_table = "ly_subcontract_status_log"

    if not _column_exists(bind, schema, order_table, "company"):
        op.add_column(order_table, sa.Column("company", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, order_table, "resource_scope_status"):
        op.add_column(
            order_table,
            sa.Column("resource_scope_status", sa.String(length=32), nullable=False, server_default="ready"),
            schema=schema,
        )
    if not _column_exists(bind, schema, order_table, "scope_error_code"):
        op.add_column(order_table, sa.Column("scope_error_code", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, order_table, "subcontract_rate"):
        op.add_column(order_table, sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "issued_qty"):
        op.add_column(order_table, sa.Column("issued_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "received_qty"):
        op.add_column(order_table, sa.Column("received_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "inspected_qty"):
        op.add_column(order_table, sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "rejected_qty"):
        op.add_column(order_table, sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "accepted_qty"):
        op.add_column(order_table, sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "gross_amount"):
        op.add_column(order_table, sa.Column("gross_amount", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "deduction_amount"):
        op.add_column(order_table, sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, order_table, "net_amount"):
        op.add_column(order_table, sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)

    if not _index_exists(bind, schema, order_table, "idx_ly_subcontract_company_status"):
        op.create_index("idx_ly_subcontract_company_status", order_table, ["company", "status"], schema=schema)
    if not _index_exists(bind, schema, order_table, "idx_ly_subcontract_company_supplier_status"):
        op.create_index(
            "idx_ly_subcontract_company_supplier_status",
            order_table,
            ["company", "supplier", "status"],
            schema=schema,
        )
    if not _index_exists(bind, schema, order_table, "idx_ly_subcontract_company_item_status"):
        op.create_index(
            "idx_ly_subcontract_company_item_status",
            order_table,
            ["company", "item_code", "status"],
            schema=schema,
        )

    if not _column_exists(bind, schema, material_table, "company"):
        op.add_column(material_table, sa.Column("company", sa.String(length=140), nullable=True), schema=schema)
    if not _index_exists(bind, schema, material_table, "idx_ly_subcontract_material_company_order"):
        op.create_index(
            "idx_ly_subcontract_material_company_order",
            material_table,
            ["company", "subcontract_id"],
            schema=schema,
        )

    if not _column_exists(bind, schema, receipt_table, "company"):
        op.add_column(receipt_table, sa.Column("company", sa.String(length=140), nullable=True), schema=schema)
    if not _index_exists(bind, schema, receipt_table, "idx_ly_subcontract_receipt_company_order"):
        op.create_index(
            "idx_ly_subcontract_receipt_company_order",
            receipt_table,
            ["company", "subcontract_id"],
            schema=schema,
        )

    if not _column_exists(bind, schema, status_log_table, "company"):
        op.add_column(status_log_table, sa.Column("company", sa.String(length=140), nullable=True), schema=schema)
    if not _index_exists(bind, schema, status_log_table, "idx_ly_subcontract_status_log_company_order"):
        op.create_index(
            "idx_ly_subcontract_status_log_company_order",
            status_log_table,
            ["company", "subcontract_id", "operated_at"],
            schema=schema,
        )


def _ensure_scope_tables(bind, schema: str | None) -> None:
    order_table = "ly_subcontract_order"

    if not _table_exists(bind, schema, "ly_subcontract_inspection"):
        op.create_table(
            "ly_subcontract_inspection",
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=True),
            sa.Column("inspection_no", sa.String(length=64), nullable=True),
            sa.Column("receipt_batch_no", sa.String(length=64), nullable=True),
            sa.Column("receipt_warehouse", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=True),
            sa.Column("inspected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("rejected_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
            sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("gross_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("deduction_amount_per_piece", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("deduction_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=True),
            sa.Column("inspected_by", sa.String(length=140), nullable=True),
            sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("remark", sa.String(length=200), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_inspection"),
            schema=schema,
        )
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "inspection_no"):
        op.add_column("ly_subcontract_inspection", sa.Column("inspection_no", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "receipt_batch_no"):
        op.add_column("ly_subcontract_inspection", sa.Column("receipt_batch_no", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "receipt_warehouse"):
        op.add_column("ly_subcontract_inspection", sa.Column("receipt_warehouse", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "item_code"):
        op.add_column("ly_subcontract_inspection", sa.Column("item_code", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "accepted_qty"):
        op.add_column("ly_subcontract_inspection", sa.Column("accepted_qty", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "rejected_rate"):
        op.add_column("ly_subcontract_inspection", sa.Column("rejected_rate", sa.Numeric(10, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "subcontract_rate"):
        op.add_column("ly_subcontract_inspection", sa.Column("subcontract_rate", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "deduction_amount_per_piece"):
        op.add_column(
            "ly_subcontract_inspection",
            sa.Column("deduction_amount_per_piece", sa.Numeric(18, 6), nullable=False, server_default="0"),
            schema=schema,
        )
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "idempotency_key"):
        op.add_column("ly_subcontract_inspection", sa.Column("idempotency_key", sa.String(length=128), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "payload_hash"):
        op.add_column("ly_subcontract_inspection", sa.Column("payload_hash", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "inspected_by"):
        op.add_column("ly_subcontract_inspection", sa.Column("inspected_by", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "inspected_at"):
        op.add_column("ly_subcontract_inspection", sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "request_id"):
        op.add_column("ly_subcontract_inspection", sa.Column("request_id", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, "ly_subcontract_inspection", "remark"):
        op.add_column("ly_subcontract_inspection", sa.Column("remark", sa.String(length=200), nullable=True), schema=schema)
    if not _index_exists(bind, schema, "ly_subcontract_inspection", "idx_ly_subcontract_inspection_company_order"):
        op.create_index(
            "idx_ly_subcontract_inspection_company_order",
            "ly_subcontract_inspection",
            ["company", "subcontract_id", "created_at"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_inspection", "idx_ly_subcontract_inspection_receipt_batch"):
        op.create_index(
            "idx_ly_subcontract_inspection_receipt_batch",
            "ly_subcontract_inspection",
            ["receipt_batch_no"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_inspection", "uk_ly_subcontract_inspection_no"):
        op.create_index(
            "uk_ly_subcontract_inspection_no",
            "ly_subcontract_inspection",
            ["company", "inspection_no"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_inspection", "uk_ly_subcontract_inspection_idempotency"):
        op.create_index(
            "uk_ly_subcontract_inspection_idempotency",
            "ly_subcontract_inspection",
            ["subcontract_id", "idempotency_key"],
            unique=True,
            schema=schema,
        )

    if not _table_exists(bind, schema, "ly_subcontract_stock_outbox"):
        op.create_table(
            "ly_subcontract_stock_outbox",
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("event_key", sa.String(length=140), nullable=True),
            sa.Column("stock_action", sa.String(length=32), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("company", sa.String(length=140), nullable=True),
            sa.Column("supplier", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=True),
            sa.Column("warehouse", sa.String(length=140), nullable=True),
            sa.Column("action", sa.String(length=32), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("locked_by", sa.String(length=140), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("stock_entry_name", sa.String(length=140), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("last_error_message", sa.String(length=255), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_stock_outbox"),
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_company_status"):
        op.create_index(
            "idx_ly_subcontract_outbox_company_status",
            "ly_subcontract_stock_outbox",
            ["company", "status", "next_retry_at"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_due"):
        op.create_index(
            "idx_ly_subcontract_outbox_due",
            "ly_subcontract_stock_outbox",
            ["stock_action", "status", "next_retry_at", "id"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_stock_entry"):
        op.create_index(
            "idx_ly_subcontract_outbox_stock_entry",
            "ly_subcontract_stock_outbox",
            ["stock_entry_name"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "uk_ly_subcontract_stock_outbox_event_key"):
        op.create_index(
            "uk_ly_subcontract_stock_outbox_event_key",
            "ly_subcontract_stock_outbox",
            ["event_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "uk_ly_subcontract_stock_outbox_idempotency"):
        op.create_index(
            "uk_ly_subcontract_stock_outbox_idempotency",
            "ly_subcontract_stock_outbox",
            ["subcontract_id", "stock_action", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_scope"):
        op.create_index(
            "idx_ly_subcontract_outbox_scope",
            "ly_subcontract_stock_outbox",
            ["company", "supplier", "item_code", "warehouse", "stock_action", "status", "next_retry_at"],
            schema=schema,
        )

    if not _table_exists(bind, schema, "ly_subcontract_stock_sync_log"):
        op.create_table(
            "ly_subcontract_stock_sync_log",
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("outbox_id", sa.BigInteger(), nullable=False),
            sa.Column("subcontract_id", sa.BigInteger(), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=True),
            sa.Column("stock_action", sa.String(length=32), nullable=True),
            sa.Column("attempt_no", sa.Integer(), nullable=True),
            sa.Column("stock_entry_name", sa.String(length=140), nullable=True),
            sa.Column("sync_status", sa.String(length=32), nullable=False),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.String(length=255), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["outbox_id"], [_qualified_table("ly_subcontract_stock_outbox", schema) + ".id"]),
            sa.ForeignKeyConstraint(["subcontract_id"], [_qualified_table(order_table, schema) + ".id"]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_subcontract_stock_sync_log"),
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_sync_log", "idx_ly_subcontract_sync_log_company_outbox"):
        op.create_index(
            "idx_ly_subcontract_sync_log_company_outbox",
            "ly_subcontract_stock_sync_log",
            ["company", "outbox_id", "created_at"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_sync_log", "idx_ly_subcontract_sync_log_outbox"):
        op.create_index(
            "idx_ly_subcontract_sync_log_outbox",
            "ly_subcontract_stock_sync_log",
            ["outbox_id", "attempt_no"],
            schema=schema,
        )
    if not _index_exists(bind, schema, "ly_subcontract_stock_sync_log", "idx_ly_subcontract_sync_log_company"):
        op.create_index(
            "idx_ly_subcontract_sync_log_company",
            "ly_subcontract_stock_sync_log",
            ["company", "created_at"],
            schema=schema,
        )


def _ensure_task_002d_fields(bind, schema: str | None) -> None:
    """Add TASK-002D issue-outbox fields to existing schema in-place."""

    material_table = "ly_subcontract_material"
    receipt_table = "ly_subcontract_receipt"
    outbox_table = "ly_subcontract_stock_outbox"
    sync_log_table = "ly_subcontract_stock_sync_log"

    if _table_exists(bind, schema, material_table):
        if not _column_exists(bind, schema, material_table, "stock_outbox_id"):
            op.add_column(material_table, sa.Column("stock_outbox_id", sa.BigInteger(), nullable=True), schema=schema)
        if not _column_exists(bind, schema, material_table, "issue_batch_no"):
            op.add_column(material_table, sa.Column("issue_batch_no", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, material_table, "sync_status"):
            op.add_column(
                material_table,
                sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
                schema=schema,
            )
        if not _index_exists(bind, schema, material_table, "idx_ly_subcontract_material_outbox"):
            op.create_index("idx_ly_subcontract_material_outbox", material_table, ["stock_outbox_id"], schema=schema)

    if _table_exists(bind, schema, receipt_table):
        if not _column_exists(bind, schema, receipt_table, "stock_outbox_id"):
            op.add_column(receipt_table, sa.Column("stock_outbox_id", sa.BigInteger(), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "receipt_batch_no"):
            op.add_column(receipt_table, sa.Column("receipt_batch_no", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "receipt_warehouse"):
            op.add_column(receipt_table, sa.Column("receipt_warehouse", sa.String(length=140), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "item_code"):
            op.add_column(receipt_table, sa.Column("item_code", sa.String(length=140), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "color"):
            op.add_column(receipt_table, sa.Column("color", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "size"):
            op.add_column(receipt_table, sa.Column("size", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "batch_no"):
            op.add_column(receipt_table, sa.Column("batch_no", sa.String(length=140), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "uom"):
            op.add_column(receipt_table, sa.Column("uom", sa.String(length=32), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "sync_status"):
            op.add_column(
                receipt_table,
                sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
                schema=schema,
            )
        if not _column_exists(bind, schema, receipt_table, "sync_error_code"):
            op.add_column(receipt_table, sa.Column("sync_error_code", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "idempotency_key"):
            op.add_column(receipt_table, sa.Column("idempotency_key", sa.String(length=128), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "payload_hash"):
            op.add_column(receipt_table, sa.Column("payload_hash", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "received_by"):
            op.add_column(receipt_table, sa.Column("received_by", sa.String(length=140), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "received_at"):
            op.add_column(receipt_table, sa.Column("received_at", sa.DateTime(timezone=True), nullable=True), schema=schema)
        if not _column_exists(bind, schema, receipt_table, "stock_entry_name"):
            op.add_column(receipt_table, sa.Column("stock_entry_name", sa.String(length=140), nullable=True), schema=schema)

        if not _index_exists(bind, schema, receipt_table, "idx_ly_subcontract_receipt_outbox"):
            op.create_index("idx_ly_subcontract_receipt_outbox", receipt_table, ["stock_outbox_id"], schema=schema)
        if not _index_exists(bind, schema, receipt_table, "idx_ly_subcontract_receipt_idempotency"):
            op.create_index(
                "idx_ly_subcontract_receipt_idempotency",
                receipt_table,
                ["subcontract_id", "idempotency_key"],
                schema=schema,
            )

    if _table_exists(bind, schema, outbox_table):
        if not _column_exists(bind, schema, outbox_table, "event_key"):
            op.add_column(outbox_table, sa.Column("event_key", sa.String(length=140), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "stock_action"):
            op.add_column(outbox_table, sa.Column("stock_action", sa.String(length=32), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "idempotency_key"):
            op.add_column(outbox_table, sa.Column("idempotency_key", sa.String(length=128), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "payload_hash"):
            op.add_column(outbox_table, sa.Column("payload_hash", sa.String(length=64), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "payload_json"):
            op.add_column(outbox_table, sa.Column("payload_json", sa.JSON(), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "lease_until"):
            op.add_column(outbox_table, sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True), schema=schema)
        if not _column_exists(bind, schema, outbox_table, "stock_entry_name"):
            op.add_column(outbox_table, sa.Column("stock_entry_name", sa.String(length=140), nullable=True), schema=schema)

        if not _index_exists(bind, schema, outbox_table, "uk_ly_subcontract_stock_outbox_event_key"):
            op.create_index(
                "uk_ly_subcontract_stock_outbox_event_key",
                outbox_table,
                ["event_key"],
                unique=True,
                schema=schema,
            )
        if not _index_exists(bind, schema, outbox_table, "uk_ly_subcontract_stock_outbox_idempotency"):
            op.create_index(
                "uk_ly_subcontract_stock_outbox_idempotency",
                outbox_table,
                ["subcontract_id", "stock_action", "idempotency_key"],
                unique=True,
                schema=schema,
            )
        if not _index_exists(bind, schema, outbox_table, "idx_ly_subcontract_outbox_due"):
            op.create_index(
                "idx_ly_subcontract_outbox_due",
                outbox_table,
                ["stock_action", "status", "next_retry_at", "id"],
                schema=schema,
            )
        if not _index_exists(bind, schema, outbox_table, "idx_ly_subcontract_outbox_stock_entry"):
            op.create_index("idx_ly_subcontract_outbox_stock_entry", outbox_table, ["stock_entry_name"], schema=schema)

    if _table_exists(bind, schema, sync_log_table):
        if not _column_exists(bind, schema, sync_log_table, "stock_action"):
            op.add_column(sync_log_table, sa.Column("stock_action", sa.String(length=32), nullable=True), schema=schema)
        if not _column_exists(bind, schema, sync_log_table, "attempt_no"):
            op.add_column(sync_log_table, sa.Column("attempt_no", sa.Integer(), nullable=True), schema=schema)
        if not _column_exists(bind, schema, sync_log_table, "stock_entry_name"):
            op.add_column(sync_log_table, sa.Column("stock_entry_name", sa.String(length=140), nullable=True), schema=schema)
        if not _index_exists(bind, schema, sync_log_table, "idx_ly_subcontract_sync_log_outbox"):
            op.create_index(
                "idx_ly_subcontract_sync_log_outbox",
                sync_log_table,
                ["outbox_id", "attempt_no"],
                schema=schema,
            )
        if not _index_exists(bind, schema, sync_log_table, "idx_ly_subcontract_sync_log_company"):
            op.create_index(
                "idx_ly_subcontract_sync_log_company",
                sync_log_table,
                ["company", "created_at"],
                schema=schema,
            )


def _ensure_order_checks(bind, schema: str | None) -> None:
    if _is_sqlite(bind):
        return
    table_name = "ly_subcontract_order"
    if not _check_exists(bind, schema, table_name, "ck_ly_subcontract_order_company_not_blank"):
        op.create_check_constraint(
            "ck_ly_subcontract_order_company_not_blank",
            table_name,
            "(company IS NULL) OR (btrim(company) <> '')",
            schema=schema,
        )
    if not _check_exists(bind, schema, table_name, "ck_ly_subcontract_order_scope_status"):
        op.create_check_constraint(
            "ck_ly_subcontract_order_scope_status",
            table_name,
            "resource_scope_status IN ('ready', 'blocked_scope')",
            schema=schema,
        )


def _backfill_existing_company_scope(bind, schema: str | None) -> None:
    trim_fn = _trim_expr(bind)
    order_table = _qualified_table("ly_subcontract_order", schema)
    material_table = _qualified_table("ly_subcontract_material", schema)
    receipt_table = _qualified_table("ly_subcontract_receipt", schema)
    status_log_table = _qualified_table("ly_subcontract_status_log", schema)

    op.execute(
        f"""
        UPDATE {order_table}
        SET resource_scope_status = CASE
            WHEN company IS NULL OR {trim_fn}(company) = '' THEN 'blocked_scope'
            ELSE 'ready'
        END,
            scope_error_code = CASE
            WHEN company IS NULL OR {trim_fn}(company) = '' THEN 'SUBCONTRACT_COMPANY_UNRESOLVED'
            ELSE NULL
        END
        """
    )

    if _is_sqlite(bind):
        op.execute(
            f"""
            UPDATE {material_table}
            SET company = (
                SELECT o.company
                FROM {order_table} AS o
                WHERE o.id = {material_table}.subcontract_id
            )
            WHERE (company IS NULL OR {trim_fn}(company) = '')
              AND EXISTS (
                  SELECT 1
                  FROM {order_table} AS o
                  WHERE o.id = {material_table}.subcontract_id
                    AND o.company IS NOT NULL
                    AND {trim_fn}(o.company) <> ''
              )
            """
        )
        op.execute(
            f"""
            UPDATE {receipt_table}
            SET company = (
                SELECT o.company
                FROM {order_table} AS o
                WHERE o.id = {receipt_table}.subcontract_id
            )
            WHERE (company IS NULL OR {trim_fn}(company) = '')
              AND EXISTS (
                  SELECT 1
                  FROM {order_table} AS o
                  WHERE o.id = {receipt_table}.subcontract_id
                    AND o.company IS NOT NULL
                    AND {trim_fn}(o.company) <> ''
              )
            """
        )
        op.execute(
            f"""
            UPDATE {status_log_table}
            SET company = (
                SELECT o.company
                FROM {order_table} AS o
                WHERE o.id = {status_log_table}.subcontract_id
            )
            WHERE (company IS NULL OR {trim_fn}(company) = '')
              AND EXISTS (
                  SELECT 1
                  FROM {order_table} AS o
                  WHERE o.id = {status_log_table}.subcontract_id
                    AND o.company IS NOT NULL
                    AND {trim_fn}(o.company) <> ''
              )
            """
        )
        return

    op.execute(
        f"""
        UPDATE {material_table} AS m
        SET company = o.company
        FROM {order_table} AS o
        WHERE m.subcontract_id = o.id
          AND (m.company IS NULL OR {trim_fn}(m.company) = '')
          AND o.company IS NOT NULL
          AND {trim_fn}(o.company) <> ''
        """
    )
    op.execute(
        f"""
        UPDATE {receipt_table} AS r
        SET company = o.company
        FROM {order_table} AS o
        WHERE r.subcontract_id = o.id
          AND (r.company IS NULL OR {trim_fn}(r.company) = '')
          AND o.company IS NOT NULL
          AND {trim_fn}(o.company) <> ''
        """
    )
    op.execute(
        f"""
        UPDATE {status_log_table} AS s
        SET company = o.company
        FROM {order_table} AS o
        WHERE s.subcontract_id = o.id
          AND (s.company IS NULL OR {trim_fn}(s.company) = '')
          AND o.company IS NOT NULL
          AND {trim_fn}(o.company) <> ''
        """
    )


def upgrade() -> None:
    """Add subcontract company facts, indexes and scope status fields.

    This migration is intentionally self-contained for empty-database bootstrap:
    when base subcontract tables are missing, it creates them first, then applies
    TASK-002C company/scope fields and skeleton scope tables.
    """
    bind = op.get_bind()
    schema = _schema_of(bind)

    _create_schema_if_needed(bind)
    _ensure_subcontract_base_tables(bind, schema)
    _ensure_company_columns(bind, schema)
    _ensure_scope_tables(bind, schema)
    _ensure_task_002d_fields(bind, schema)
    _ensure_order_checks(bind, schema)
    _backfill_existing_company_scope(bind, schema)


def downgrade() -> None:
    """Rollback TASK-002C subcontract company/schema additions."""
    bind = op.get_bind()
    schema = _schema_of(bind)

    if _table_exists(bind, schema, "ly_subcontract_order"):
        if not _is_sqlite(bind):
            if _check_exists(bind, schema, "ly_subcontract_order", "ck_ly_subcontract_order_scope_status"):
                op.drop_constraint("ck_ly_subcontract_order_scope_status", "ly_subcontract_order", schema=schema)
            if _check_exists(bind, schema, "ly_subcontract_order", "ck_ly_subcontract_order_company_not_blank"):
                op.drop_constraint(
                    "ck_ly_subcontract_order_company_not_blank",
                    "ly_subcontract_order",
                    schema=schema,
                )

    if _table_exists(bind, schema, "ly_subcontract_stock_sync_log"):
        if _index_exists(bind, schema, "ly_subcontract_stock_sync_log", "idx_ly_subcontract_sync_log_company_outbox"):
            op.drop_index(
                "idx_ly_subcontract_sync_log_company_outbox",
                table_name="ly_subcontract_stock_sync_log",
                schema=schema,
            )
        op.drop_table("ly_subcontract_stock_sync_log", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_stock_outbox"):
        if _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_scope"):
            op.drop_index(
                "idx_ly_subcontract_outbox_scope",
                table_name="ly_subcontract_stock_outbox",
                schema=schema,
            )
        if _index_exists(bind, schema, "ly_subcontract_stock_outbox", "idx_ly_subcontract_outbox_company_status"):
            op.drop_index(
                "idx_ly_subcontract_outbox_company_status",
                table_name="ly_subcontract_stock_outbox",
                schema=schema,
            )
        op.drop_table("ly_subcontract_stock_outbox", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_inspection"):
        if _index_exists(bind, schema, "ly_subcontract_inspection", "idx_ly_subcontract_inspection_company_order"):
            op.drop_index(
                "idx_ly_subcontract_inspection_company_order",
                table_name="ly_subcontract_inspection",
                schema=schema,
            )
        op.drop_table("ly_subcontract_inspection", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_status_log"):
        if _index_exists(bind, schema, "ly_subcontract_status_log", "idx_ly_subcontract_status_log_company_order"):
            op.drop_index(
                "idx_ly_subcontract_status_log_company_order",
                table_name="ly_subcontract_status_log",
                schema=schema,
            )
        if _column_exists(bind, schema, "ly_subcontract_status_log", "company"):
            op.drop_column("ly_subcontract_status_log", "company", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_receipt"):
        if _index_exists(bind, schema, "ly_subcontract_receipt", "idx_ly_subcontract_receipt_idempotency"):
            op.drop_index(
                "idx_ly_subcontract_receipt_idempotency",
                table_name="ly_subcontract_receipt",
                schema=schema,
            )
        if _index_exists(bind, schema, "ly_subcontract_receipt", "idx_ly_subcontract_receipt_outbox"):
            op.drop_index(
                "idx_ly_subcontract_receipt_outbox",
                table_name="ly_subcontract_receipt",
                schema=schema,
            )
        if _index_exists(bind, schema, "ly_subcontract_receipt", "idx_ly_subcontract_receipt_company_order"):
            op.drop_index(
                "idx_ly_subcontract_receipt_company_order",
                table_name="ly_subcontract_receipt",
                schema=schema,
            )
        for column_name in (
            "stock_entry_name",
            "received_at",
            "received_by",
            "payload_hash",
            "idempotency_key",
            "sync_error_code",
            "sync_status",
            "uom",
            "batch_no",
            "size",
            "color",
            "item_code",
            "receipt_warehouse",
            "receipt_batch_no",
            "stock_outbox_id",
        ):
            if _column_exists(bind, schema, "ly_subcontract_receipt", column_name):
                op.drop_column("ly_subcontract_receipt", column_name, schema=schema)
        if _column_exists(bind, schema, "ly_subcontract_receipt", "company"):
            op.drop_column("ly_subcontract_receipt", "company", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_material"):
        if _index_exists(bind, schema, "ly_subcontract_material", "idx_ly_subcontract_material_outbox"):
            op.drop_index(
                "idx_ly_subcontract_material_outbox",
                table_name="ly_subcontract_material",
                schema=schema,
            )
        if _column_exists(bind, schema, "ly_subcontract_material", "stock_outbox_id"):
            op.drop_column("ly_subcontract_material", "stock_outbox_id", schema=schema)
        if _column_exists(bind, schema, "ly_subcontract_material", "issue_batch_no"):
            op.drop_column("ly_subcontract_material", "issue_batch_no", schema=schema)
        if _column_exists(bind, schema, "ly_subcontract_material", "sync_status"):
            op.drop_column("ly_subcontract_material", "sync_status", schema=schema)
        if _index_exists(bind, schema, "ly_subcontract_material", "idx_ly_subcontract_material_company_order"):
            op.drop_index(
                "idx_ly_subcontract_material_company_order",
                table_name="ly_subcontract_material",
                schema=schema,
            )
        if _column_exists(bind, schema, "ly_subcontract_material", "company"):
            op.drop_column("ly_subcontract_material", "company", schema=schema)

    if _table_exists(bind, schema, "ly_subcontract_order"):
        if _index_exists(bind, schema, "ly_subcontract_order", "idx_ly_subcontract_company_item_status"):
            op.drop_index(
                "idx_ly_subcontract_company_item_status",
                table_name="ly_subcontract_order",
                schema=schema,
            )
        if _index_exists(bind, schema, "ly_subcontract_order", "idx_ly_subcontract_company_supplier_status"):
            op.drop_index(
                "idx_ly_subcontract_company_supplier_status",
                table_name="ly_subcontract_order",
                schema=schema,
            )
        if _index_exists(bind, schema, "ly_subcontract_order", "idx_ly_subcontract_company_status"):
            op.drop_index(
                "idx_ly_subcontract_company_status",
                table_name="ly_subcontract_order",
                schema=schema,
            )

        if _column_exists(bind, schema, "ly_subcontract_order", "scope_error_code"):
            op.drop_column("ly_subcontract_order", "scope_error_code", schema=schema)
        if _column_exists(bind, schema, "ly_subcontract_order", "resource_scope_status"):
            op.drop_column("ly_subcontract_order", "resource_scope_status", schema=schema)
        if _column_exists(bind, schema, "ly_subcontract_order", "company"):
            op.drop_column("ly_subcontract_order", "company", schema=schema)
