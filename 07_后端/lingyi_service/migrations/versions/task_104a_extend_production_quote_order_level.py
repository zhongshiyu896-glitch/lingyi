"""TASK-104A extend production quote to order-level pricing.

Revision ID: task_104a_extend_production_quote_order_level
Revises: task_103a_add_production_plan_group_no
Create Date: 2026-06-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_104a_extend_production_quote_order_level"
down_revision = "task_103a_add_production_plan_group_no"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_QUOTE_TABLE = "ly_production_quote"
_QUOTE_OPERATION_TABLE = "ly_production_quote_operation"
_SALES_ORDER_TABLE = "ly_sales_order"
_QUOTE_OPERATION_CONSTRAINT = "ck_ly_production_quote_operation"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(str(column.get("name")) == column_name for column in sa.inspect(bind).get_columns(table_name, schema=schema))


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(str(index.get("name")) == index_name for index in sa.inspect(bind).get_indexes(table_name, schema=schema))


def _constraint_exists(bind, schema: str | None, table_name: str, constraint_name: str) -> bool:
    if not _table_exists(bind, schema, table_name):
        return False
    return any(
        str(constraint.get("name")) == constraint_name
        for constraint in sa.inspect(bind).get_check_constraints(table_name, schema=schema)
    )


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _json_type(bind):
    return sa.JSON()


def _add_column_if_missing(bind, schema: str | None, table_name: str, column_name: str, column: sa.Column) -> None:
    if _table_exists(bind, schema, table_name) and not _column_exists(bind, schema, table_name, column_name):
        op.add_column(table_name, column, schema=schema)


def _drop_column_if_exists(bind, schema: str | None, table_name: str, column_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _column_exists(bind, schema, table_name, column_name):
        op.drop_column(table_name, column_name, schema=schema)


def _replace_operation_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _QUOTE_OPERATION_TABLE):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_QUOTE_OPERATION_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_QUOTE_OPERATION_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_QUOTE_OPERATION_CONSTRAINT, expression)
        return
    if _constraint_exists(bind, schema, _QUOTE_OPERATION_TABLE, _QUOTE_OPERATION_CONSTRAINT):
        op.drop_constraint(_QUOTE_OPERATION_CONSTRAINT, _QUOTE_OPERATION_TABLE, schema=schema, type_="check")
    op.create_check_constraint(_QUOTE_OPERATION_CONSTRAINT, _QUOTE_OPERATION_TABLE, expression, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)

    quote_columns: list[tuple[str, sa.Column]] = [
        ("sales_order_id", sa.Column("sales_order_id", _id_type(bind), nullable=True)),
        ("quote_unit_price", sa.Column("quote_unit_price", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("other_fee", sa.Column("other_fee", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("gross_profit", sa.Column("gross_profit", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("gross_margin_rate", sa.Column("gross_margin_rate", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_items_json", sa.Column("quote_items_json", _json_type(bind), nullable=False, server_default="[]")),
    ]
    for column_name, column in quote_columns:
        _add_column_if_missing(bind, schema, _QUOTE_TABLE, column_name, column)
    if _table_exists(bind, schema, _QUOTE_TABLE) and not _index_exists(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_sales_order"):
        op.create_index(
            "idx_ly_production_quote_sales_order",
            _QUOTE_TABLE,
            ["company", "sales_order", "status"],
            schema=schema,
        )

    sales_order_columns: list[tuple[str, sa.Column]] = [
        ("quote_status", sa.Column("quote_status", sa.String(length=32), nullable=False, server_default="未核价")),
        ("quote_no", sa.Column("quote_no", sa.String(length=140), nullable=True)),
        ("quote_amount", sa.Column("quote_amount", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_unit_price", sa.Column("quote_unit_price", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_material_cost", sa.Column("quote_material_cost", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_labor_cost", sa.Column("quote_labor_cost", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_management_fee", sa.Column("quote_management_fee", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_other_fee", sa.Column("quote_other_fee", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("quote_total_cost", sa.Column("quote_total_cost", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("gross_profit", sa.Column("gross_profit", sa.Numeric(18, 6), nullable=False, server_default="0")),
        ("gross_margin_rate", sa.Column("gross_margin_rate", sa.Numeric(18, 6), nullable=False, server_default="0")),
    ]
    for column_name, column in sales_order_columns:
        _add_column_if_missing(bind, schema, _SALES_ORDER_TABLE, column_name, column)

    _replace_operation_constraint("operation IN ('create','update','convert','copy','void','confirm')")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _replace_operation_constraint("operation IN ('create','convert','copy','void')")
    if _table_exists(bind, schema, _QUOTE_TABLE) and _index_exists(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_sales_order"):
        op.drop_index("idx_ly_production_quote_sales_order", table_name=_QUOTE_TABLE, schema=schema)
    for column_name in ["quote_items_json", "gross_margin_rate", "gross_profit", "other_fee", "quote_unit_price", "sales_order_id"]:
        _drop_column_if_exists(bind, schema, _QUOTE_TABLE, column_name)
    for column_name in [
        "gross_margin_rate",
        "gross_profit",
        "quote_total_cost",
        "quote_other_fee",
        "quote_management_fee",
        "quote_labor_cost",
        "quote_material_cost",
        "quote_unit_price",
        "quote_amount",
        "quote_no",
        "quote_status",
    ]:
        _drop_column_if_exists(bind, schema, _SALES_ORDER_TABLE, column_name)
