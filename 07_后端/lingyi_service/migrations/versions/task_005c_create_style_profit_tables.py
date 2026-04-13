"""TASK-005C create style profit tables and indexes.

Revision ID: task_005c_create_style_profit_tables
Revises: task_004a_create_production_tables
Create Date: 2026-04-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_005c_create_style_profit_tables"
down_revision = "task_004a_create_production_tables"
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


def _check_constraint_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    for constraint in inspector.get_check_constraints(table_name, schema=schema):
        if str(constraint.get("name")) == constraint_name:
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


def _create_snapshot_table(bind, schema: str | None) -> None:
    table = "ly_style_profit_snapshot"
    if not _table_exists(bind, schema, table):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("snapshot_no", sa.String(length=64), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("sales_order", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("revenue_status", sa.String(length=32), nullable=False, server_default="unresolved"),
            sa.Column("estimated_revenue_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("actual_revenue_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("revenue_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("from_date", sa.Date(), nullable=True),
            sa.Column("to_date", sa.Date(), nullable=True),
            sa.Column("revenue_mode", sa.String(length=32), nullable=False, server_default="actual_first"),
            sa.Column("standard_material_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("standard_operation_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("standard_total_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("actual_material_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("actual_workshop_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("actual_subcontract_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("allocated_overhead_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("actual_total_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("profit_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("profit_rate", sa.Numeric(18, 6), nullable=True),
            sa.Column("snapshot_status", sa.String(length=32), nullable=False, server_default="incomplete"),
            sa.Column("allocation_status", sa.String(length=32), nullable=False, server_default="not_enabled"),
            sa.Column("formula_version", sa.String(length=32), nullable=False, server_default="STYLE_PROFIT_V1"),
            sa.Column("include_provisional_subcontract", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("unresolved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_style_profit_snapshot"),
            sa.CheckConstraint(
                "revenue_status IN ('actual','estimated','unresolved')",
                name="ck_ly_style_profit_snapshot_revenue_status",
            ),
            sa.CheckConstraint(
                "snapshot_status IN ('complete','incomplete','failed')",
                name="ck_ly_style_profit_snapshot_status",
            ),
            sa.CheckConstraint(
                "allocation_status IN ('not_enabled','enabled')",
                name="ck_ly_style_profit_snapshot_allocation_status",
            ),
            sa.CheckConstraint(
                "revenue_mode IN ('actual_first','actual_only','estimated_only')",
                name="ck_ly_style_profit_snapshot_revenue_mode",
            ),
            schema=schema,
        )
    if not _column_exists(bind, schema, table, "from_date"):
        op.add_column(table, sa.Column("from_date", sa.Date(), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "to_date"):
        op.add_column(table, sa.Column("to_date", sa.Date(), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "revenue_mode"):
        op.add_column(
            table,
            sa.Column("revenue_mode", sa.String(length=32), nullable=False, server_default="actual_first"),
            schema=schema,
        )
    if not _column_exists(bind, schema, table, "unresolved_count"):
        op.add_column(
            table,
            sa.Column("unresolved_count", sa.Integer(), nullable=False, server_default="0"),
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "uk_ly_style_profit_snapshot_no"):
        op.create_index("uk_ly_style_profit_snapshot_no", table, ["snapshot_no"], unique=True, schema=schema)
    if not _index_exists(bind, schema, table, "uk_ly_style_profit_snapshot_idempotency"):
        op.create_index(
            "uk_ly_style_profit_snapshot_idempotency",
            table,
            ["company", "idempotency_key"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_snapshot_company_item_order"):
        op.create_index(
            "idx_ly_style_profit_snapshot_company_item_order",
            table,
            ["company", "item_code", "sales_order"],
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_snapshot_company_item_period"):
        op.create_index(
            "idx_ly_style_profit_snapshot_company_item_period",
            table,
            ["company", "item_code", "from_date", "to_date"],
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_snapshot_created_at"):
        op.create_index("idx_ly_style_profit_snapshot_created_at", table, ["created_at"], schema=schema)
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_snapshot_status"):
        op.create_index("idx_ly_style_profit_snapshot_status", table, ["snapshot_status"], schema=schema)
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_snapshot_formula_version"):
        op.create_index("idx_ly_style_profit_snapshot_formula_version", table, ["formula_version"], schema=schema)


def _create_detail_table(bind, schema: str | None) -> None:
    table = "ly_style_profit_detail"
    snapshot_table = "ly_style_profit_snapshot"
    if not _table_exists(bind, schema, table):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("snapshot_id", sa.BigInteger(), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("cost_type", sa.String(length=64), nullable=False),
            sa.Column("source_type", sa.String(length=64), nullable=False),
            sa.Column("source_name", sa.String(length=140), nullable=False),
            sa.Column("item_code", sa.String(length=140), nullable=True),
            sa.Column("qty", sa.Numeric(18, 6), nullable=True),
            sa.Column("unit_rate", sa.Numeric(18, 6), nullable=True),
            sa.Column("amount", sa.Numeric(18, 6), nullable=False),
            sa.Column("formula_code", sa.String(length=64), nullable=True),
            sa.Column("is_unresolved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("unresolved_reason", sa.String(length=128), nullable=True),
            sa.Column("raw_ref", _json_type(bind), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_style_profit_detail"),
            sa.ForeignKeyConstraint(
                ["snapshot_id"],
                [_qualified_table(schema, snapshot_table) + ".id"],
                name="fk_style_profit_detail_snapshot_id",
            ),
            sa.CheckConstraint(
                (
                    "cost_type IN ("
                    "'revenue','standard_material','standard_operation','actual_material','workshop',"
                    "'subcontract','deduction','overhead','unresolved'"
                    ")"
                ),
                name="ck_ly_style_profit_detail_cost_type",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "idx_ly_style_profit_detail_snapshot"):
        op.create_index("idx_ly_style_profit_detail_snapshot", table, ["snapshot_id", "line_no"], schema=schema)
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_detail_cost_type"):
        op.create_index("idx_ly_style_profit_detail_cost_type", table, ["cost_type"], schema=schema)
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_detail_source"):
        op.create_index("idx_ly_style_profit_detail_source", table, ["source_type", "source_name"], schema=schema)


def _create_source_map_table(bind, schema: str | None) -> None:
    table = "ly_style_profit_source_map"
    snapshot_table = "ly_style_profit_snapshot"
    detail_table = "ly_style_profit_detail"
    if not _table_exists(bind, schema, table):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("snapshot_id", sa.BigInteger(), nullable=False),
            sa.Column("detail_id", sa.BigInteger(), nullable=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("sales_order", sa.String(length=140), nullable=True),
            sa.Column("style_item_code", sa.String(length=140), nullable=False),
            sa.Column("source_item_code", sa.String(length=140), nullable=True),
            sa.Column("production_plan_id", sa.BigInteger(), nullable=True),
            sa.Column("work_order", sa.String(length=140), nullable=True),
            sa.Column("job_card", sa.String(length=140), nullable=True),
            sa.Column("source_system", sa.String(length=64), nullable=False),
            sa.Column("source_doctype", sa.String(length=140), nullable=False),
            sa.Column("source_status", sa.String(length=64), nullable=False, server_default="unknown"),
            sa.Column("source_name", sa.String(length=140), nullable=False),
            sa.Column("source_line_no", sa.String(length=140), nullable=False, server_default=""),
            sa.Column("qty", sa.Numeric(18, 6), nullable=True),
            sa.Column("unit_rate", sa.Numeric(18, 6), nullable=True),
            sa.Column("amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=16), nullable=True),
            sa.Column("warehouse", sa.String(length=140), nullable=True),
            sa.Column("posting_date", sa.Date(), nullable=True),
            sa.Column("raw_ref", _json_type(bind), nullable=True),
            sa.Column("include_in_profit", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("mapping_status", sa.String(length=32), nullable=False, server_default="unresolved"),
            sa.Column("unresolved_reason", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_style_profit_source_map"),
            sa.ForeignKeyConstraint(
                ["snapshot_id"],
                [_qualified_table(schema, snapshot_table) + ".id"],
                name="fk_style_profit_source_map_snapshot_id",
            ),
            sa.ForeignKeyConstraint(
                ["detail_id"],
                [_qualified_table(schema, detail_table) + ".id"],
                name="fk_style_profit_source_map_detail_id",
            ),
            sa.CheckConstraint(
                "mapping_status IN ('mapped','unresolved','excluded')",
                name="ck_ly_style_profit_source_map_status",
            ),
            sa.CheckConstraint(
                "source_system IN ('erpnext','fastapi','manual')",
                name="ck_ly_style_profit_source_map_source_system",
            ),
            sa.CheckConstraint(
                "source_status <> ''",
                name="ck_ly_style_profit_source_map_source_status_non_empty",
            ),
            sa.CheckConstraint(
                "NOT include_in_profit OR mapping_status = 'mapped'",
                name="ck_ly_style_profit_source_map_include_requires_mapped",
            ),
            schema=schema,
        )
    if not _column_exists(bind, schema, table, "snapshot_id"):
        op.add_column(table, sa.Column("snapshot_id", sa.BigInteger(), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "detail_id"):
        op.add_column(table, sa.Column("detail_id", sa.BigInteger(), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "style_item_code"):
        op.add_column(table, sa.Column("style_item_code", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "source_item_code"):
        op.add_column(table, sa.Column("source_item_code", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "source_system"):
        op.add_column(table, sa.Column("source_system", sa.String(length=64), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "source_doctype"):
        op.add_column(table, sa.Column("source_doctype", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "source_status"):
        op.add_column(
            table,
            sa.Column("source_status", sa.String(length=64), nullable=False, server_default="unknown"),
            schema=schema,
        )
    if not _column_exists(bind, schema, table, "source_line_no"):
        op.add_column(table, sa.Column("source_line_no", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "qty"):
        op.add_column(table, sa.Column("qty", sa.Numeric(18, 6), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "unit_rate"):
        op.add_column(table, sa.Column("unit_rate", sa.Numeric(18, 6), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "amount"):
        op.add_column(table, sa.Column("amount", sa.Numeric(18, 6), nullable=False, server_default="0"), schema=schema)
    if not _column_exists(bind, schema, table, "currency"):
        op.add_column(table, sa.Column("currency", sa.String(length=16), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "warehouse"):
        op.add_column(table, sa.Column("warehouse", sa.String(length=140), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "posting_date"):
        op.add_column(table, sa.Column("posting_date", sa.Date(), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "raw_ref"):
        op.add_column(table, sa.Column("raw_ref", _json_type(bind), nullable=True), schema=schema)
    if not _column_exists(bind, schema, table, "include_in_profit"):
        op.add_column(
            table,
            sa.Column("include_in_profit", sa.Boolean(), nullable=False, server_default=sa.false()),
            schema=schema,
        )
    if not _column_exists(bind, schema, table, "mapping_status"):
        op.add_column(
            table,
            sa.Column("mapping_status", sa.String(length=32), nullable=False, server_default="unresolved"),
            schema=schema,
        )

    # Normalize legacy rows to satisfy non-empty / non-null source_status contract.
    op.execute(
        sa.text(
            f"UPDATE {_qualified_table(schema, table)} "  # noqa: S608
            "SET source_system = COALESCE(NULLIF(TRIM(source_system), ''), 'manual'), "  # noqa: S608
            "source_doctype = COALESCE(NULLIF(TRIM(source_doctype), ''), 'Unknown'), "  # noqa: S608
            "source_status = COALESCE(NULLIF(TRIM(source_status), ''), 'unknown'), "  # noqa: S608
            "mapping_status = COALESCE(NULLIF(TRIM(mapping_status), ''), 'unresolved'), "  # noqa: S608
            "include_in_profit = COALESCE(include_in_profit, FALSE) "  # noqa: S608
        )
    )

    if not _is_sqlite(bind):
        op.alter_column(table, "source_status", existing_type=sa.String(length=64), nullable=False, server_default="unknown", schema=schema)
        op.alter_column(table, "include_in_profit", existing_type=sa.Boolean(), nullable=False, server_default=sa.false(), schema=schema)
        op.alter_column(table, "mapping_status", existing_type=sa.String(length=32), nullable=False, server_default="unresolved", schema=schema)

    if not _check_constraint_exists(bind, schema, table, "ck_ly_style_profit_source_map_source_system"):
        op.create_check_constraint(
            "ck_ly_style_profit_source_map_source_system",
            table,
            "source_system IN ('erpnext','fastapi','manual')",
            schema=schema,
        )
    if not _check_constraint_exists(bind, schema, table, "ck_ly_style_profit_source_map_source_status_non_empty"):
        op.create_check_constraint(
            "ck_ly_style_profit_source_map_source_status_non_empty",
            table,
            "source_status <> ''",
            schema=schema,
        )
    if not _check_constraint_exists(bind, schema, table, "ck_ly_style_profit_source_map_include_requires_mapped"):
        op.create_check_constraint(
            "ck_ly_style_profit_source_map_include_requires_mapped",
            table,
            "NOT include_in_profit OR mapping_status = 'mapped'",
            schema=schema,
        )

    if _index_exists(bind, schema, table, "uk_ly_style_profit_source_map_source"):
        op.drop_index("uk_ly_style_profit_source_map_source", table_name=table, schema=schema)
    if not _index_exists(bind, schema, table, "uk_ly_style_profit_source_map_snapshot_source"):
        op.create_index(
            "uk_ly_style_profit_source_map_snapshot_source",
            table,
            ["snapshot_id", "source_system", "source_doctype", "source_name", "source_line_no"],
            unique=True,
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_source_map_scope"):
        op.create_index(
            "idx_ly_style_profit_source_map_scope",
            table,
            ["company", "sales_order", "style_item_code"],
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_source_map_snapshot_status"):
        op.create_index(
            "idx_ly_style_profit_source_map_snapshot_status",
            table,
            ["snapshot_id", "mapping_status"],
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_source_map_source_lookup"):
        op.create_index(
            "idx_ly_style_profit_source_map_source_lookup",
            table,
            ["source_system", "source_doctype", "source_name"],
            schema=schema,
        )
    if not _index_exists(bind, schema, table, "idx_ly_style_profit_source_map_detail"):
        op.create_index("idx_ly_style_profit_source_map_detail", table, ["detail_id"], schema=schema)


def _create_cost_allocation_rule_table(bind, schema: str | None) -> None:
    table = "ly_cost_allocation_rule"
    if not _table_exists(bind, schema, table):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("rule_name", sa.String(length=140), nullable=False),
            sa.Column("cost_type", sa.String(length=64), nullable=False),
            sa.Column("allocation_basis", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="disabled"),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_cost_allocation_rule"),
            sa.CheckConstraint(
                "cost_type IN ('manufacturing_overhead','admin','other')",
                name="ck_ly_cost_allocation_rule_cost_type",
            ),
            sa.CheckConstraint(
                "allocation_basis IN ('qty','amount','work_hour','manual')",
                name="ck_ly_cost_allocation_rule_basis",
            ),
            sa.CheckConstraint(
                "status IN ('draft','active','disabled')",
                name="ck_ly_cost_allocation_rule_status",
            ),
            schema=schema,
        )

    if not _index_exists(bind, schema, table, "idx_ly_cost_allocation_rule_company_status"):
        op.create_index(
            "idx_ly_cost_allocation_rule_company_status",
            table,
            ["company", "status"],
            schema=schema,
        )
    if not _is_sqlite(bind):
        op.alter_column(table, "status", server_default="disabled", schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    _create_snapshot_table(bind, schema)
    _create_detail_table(bind, schema)
    _create_source_map_table(bind, schema)
    _create_cost_allocation_rule_table(bind, schema)


def downgrade() -> None:
    """Additive migration only; no destructive downgrade."""
    return
