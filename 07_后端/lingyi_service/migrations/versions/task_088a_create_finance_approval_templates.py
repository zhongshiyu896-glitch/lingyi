"""TASK-088A create finance approval template tables.

Revision ID: task_088a_create_finance_approval_templates
Revises: task_087a_extend_factory_statement_payment_approval_status
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_088a_create_finance_approval_templates"
down_revision = "task_087a_extend_factory_statement_payment_approval_status"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TEMPLATE_TABLE = "ly_finance_approval_template"
_NODE_TABLE = "ly_finance_approval_template_node"
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, table_name: str, schema: str | None) -> bool:
    return table_name in sa.inspect(bind).get_table_names(schema=schema)


def _fk_target(schema: str | None, table_name: str, column: str) -> str:
    prefix = "" if schema is None else f"{schema}."
    return f"{prefix}{table_name}.{column}"


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, _TEMPLATE_TABLE, schema):
        op.create_table(
            _TEMPLATE_TABLE,
            sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
            sa.Column("company", sa.String(140), nullable=False),
            sa.Column("template_code", sa.String(140), nullable=False),
            sa.Column("template_name", sa.String(255), nullable=False),
            sa.Column("source_type", sa.String(64), nullable=False),
            sa.Column("min_amount", sa.Numeric(18, 6), server_default="0", nullable=False),
            sa.Column("max_amount", sa.Numeric(18, 6), nullable=True),
            sa.Column("status", sa.String(16), server_default="active", nullable=False),
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
            sa.Column("remark", sa.String(500), nullable=True),
            sa.Column("created_by", sa.String(140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_by", sa.String(140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_ly_finance_approval_template"),
            sa.UniqueConstraint("company", "template_code", name="uk_ly_finance_approval_template_code"),
            sa.CheckConstraint(
                "source_type IN ('purchase_invoice','purchase_payment','factory_statement_payment')",
                name="ck_ly_finance_approval_template_source_type",
            ),
            sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_finance_approval_template_status"),
            sa.CheckConstraint("min_amount >= 0", name="ck_ly_finance_approval_template_min_amount"),
            sa.CheckConstraint(
                "max_amount IS NULL OR max_amount >= min_amount",
                name="ck_ly_finance_approval_template_amount_range",
            ),
            schema=schema,
        )
        op.create_index(
            "idx_ly_finance_approval_template_source",
            _TEMPLATE_TABLE,
            ["company", "source_type", "status"],
            schema=schema,
        )

    if not _table_exists(bind, _NODE_TABLE, schema):
        op.create_table(
            _NODE_TABLE,
            sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
            sa.Column("company", sa.String(140), nullable=False),
            sa.Column("template_id", ID_TYPE, nullable=False),
            sa.Column("sequence_no", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(140), nullable=False),
            sa.Column("approver_role", sa.String(140), nullable=False),
            sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("decision_type", sa.String(64), server_default="approve_or_reject", nullable=False),
            sa.Column("status", sa.String(16), server_default="active", nullable=False),
            sa.Column("created_by", sa.String(140), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_by", sa.String(140), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["template_id"], [_fk_target(schema, _TEMPLATE_TABLE, "id")]),
            sa.PrimaryKeyConstraint("id", name="pk_ly_finance_approval_template_node"),
            sa.UniqueConstraint("template_id", "sequence_no", name="uk_ly_finance_approval_template_node_seq"),
            sa.CheckConstraint("status IN ('active','inactive')", name="ck_ly_finance_approval_template_node_status"),
            sa.CheckConstraint("sequence_no >= 0", name="ck_ly_finance_approval_template_node_sequence"),
            schema=schema,
        )
        op.create_index(
            "idx_ly_finance_approval_template_node_template",
            _NODE_TABLE,
            ["template_id", "status", "sequence_no"],
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, _NODE_TABLE, schema):
        op.drop_index("idx_ly_finance_approval_template_node_template", table_name=_NODE_TABLE, schema=schema)
        op.drop_table(_NODE_TABLE, schema=schema)
    if _table_exists(bind, _TEMPLATE_TABLE, schema):
        op.drop_index("idx_ly_finance_approval_template_source", table_name=_TEMPLATE_TABLE, schema=schema)
        op.drop_table(_TEMPLATE_TABLE, schema=schema)
