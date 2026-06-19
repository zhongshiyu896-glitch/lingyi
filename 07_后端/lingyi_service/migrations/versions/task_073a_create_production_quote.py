"""TASK-073A create production quote tables.

Revision ID: task_073a_create_production_quote
Revises: task_072a_create_production_followup_template
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_073a_create_production_quote"
down_revision = "task_072a_create_production_followup_template"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_QUOTE_TABLE = "ly_production_quote"
_OPERATION_TABLE = "ly_production_quote_operation"
_PLAN_TABLE = "ly_production_plan"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _id_type(bind):
    return sa.Integer() if _is_sqlite(bind) else sa.BigInteger()


def _json_type(bind):
    return sa.JSON()


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _index_exists(bind, schema: str | None, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(index.get("name")) == index_name for index in inspector.get_indexes(table_name, schema=schema))


def _qualified(schema: str | None, table_name: str) -> str:
    return table_name if schema is None else f"{schema}.{table_name}"


def _ensure_schema(bind) -> None:
    if not _is_sqlite(bind):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_NAME}")


def _create_index_if_missing(bind, schema: str | None, table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _table_exists(bind, schema, table_name) and not _index_exists(bind, schema, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, schema=schema)


def _drop_index_if_exists(bind, schema: str | None, table_name: str, index_name: str) -> None:
    if _table_exists(bind, schema, table_name) and _index_exists(bind, schema, table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    _ensure_schema(bind)
    id_type = _id_type(bind)

    if not _table_exists(bind, schema, _QUOTE_TABLE):
        op.create_table(
            _QUOTE_TABLE,
            sa.Column("id", id_type, autoincrement=True),
            sa.Column("quote_no", sa.String(length=140), nullable=False),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("plan_id", id_type, nullable=False),
            sa.Column("plan_no", sa.String(length=64), nullable=False),
            sa.Column("sales_order", sa.String(length=140), nullable=False),
            sa.Column("sales_order_item", sa.String(length=140), nullable=False),
            sa.Column("customer", sa.String(length=140), nullable=True),
            sa.Column("item_code", sa.String(length=140), nullable=False),
            sa.Column("quote_qty", sa.Numeric(18, 6), nullable=False),
            sa.Column("material_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("labor_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("management_fee", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("quote_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=16), nullable=False, server_default="CNY"),
            sa.Column("valid_until", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("remark", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_by", sa.String(length=140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_quote"),
            sa.ForeignKeyConstraint(
                ["plan_id"],
                [_qualified(schema, _PLAN_TABLE) + ".id"],
                name="fk_ly_production_quote_plan",
            ),
            sa.CheckConstraint("quote_qty >= 0", name="ck_ly_production_quote_qty_nonnegative"),
            sa.CheckConstraint("material_cost >= 0", name="ck_ly_production_quote_material_nonnegative"),
            sa.CheckConstraint("labor_cost >= 0", name="ck_ly_production_quote_labor_nonnegative"),
            sa.CheckConstraint("management_fee >= 0", name="ck_ly_production_quote_management_nonnegative"),
            sa.CheckConstraint("quote_amount >= 0", name="ck_ly_production_quote_amount_nonnegative"),
            sa.CheckConstraint("status IN ('draft','pricing','quoted','converted','void')", name="ck_ly_production_quote_status"),
            schema=schema,
        )
    _create_index_if_missing(bind, schema, _QUOTE_TABLE, "uk_ly_production_quote_no", ["company", "quote_no"], unique=True)
    _create_index_if_missing(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_plan", ["plan_id", "status"])
    _create_index_if_missing(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_company_status", ["company", "status"])
    _create_index_if_missing(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_item", ["company", "item_code"])

    if not _table_exists(bind, schema, _OPERATION_TABLE):
        op.create_table(
            _OPERATION_TABLE,
            sa.Column("id", id_type, autoincrement=True),
            sa.Column("quote_id", id_type, nullable=True),
            sa.Column("company", sa.String(length=140), nullable=False),
            sa.Column("operation", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("response_json", _json_type(bind), nullable=False),
            sa.Column("created_by", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_ly_production_quote_operation"),
            sa.ForeignKeyConstraint(
                ["quote_id"],
                [_qualified(schema, _QUOTE_TABLE) + ".id"],
                name="fk_ly_production_quote_operation_quote",
            ),
            sa.CheckConstraint("operation IN ('create')", name="ck_ly_production_quote_operation"),
            schema=schema,
        )
    _create_index_if_missing(
        bind,
        schema,
        _OPERATION_TABLE,
        "uk_ly_production_quote_operation_idem",
        ["company", "operation", "idempotency_key"],
        unique=True,
    )
    _create_index_if_missing(
        bind,
        schema,
        _OPERATION_TABLE,
        "idx_ly_production_quote_operation_quote",
        ["quote_id", "operation"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema, _OPERATION_TABLE):
        _drop_index_if_exists(bind, schema, _OPERATION_TABLE, "idx_ly_production_quote_operation_quote")
        _drop_index_if_exists(bind, schema, _OPERATION_TABLE, "uk_ly_production_quote_operation_idem")
        op.drop_table(_OPERATION_TABLE, schema=schema)
    if _table_exists(bind, schema, _QUOTE_TABLE):
        _drop_index_if_exists(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_item")
        _drop_index_if_exists(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_company_status")
        _drop_index_if_exists(bind, schema, _QUOTE_TABLE, "idx_ly_production_quote_plan")
        _drop_index_if_exists(bind, schema, _QUOTE_TABLE, "uk_ly_production_quote_no")
        op.drop_table(_QUOTE_TABLE, schema=schema)
