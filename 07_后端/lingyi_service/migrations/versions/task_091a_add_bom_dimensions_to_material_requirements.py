"""TASK-091A add BOM dimensions to production material requirements.

Revision ID: task_091a_add_bom_dimensions_to_material_requirements
Revises: task_090a_create_factory_packing
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_091a_add_bom_dimensions_to_material_requirements"
down_revision = "task_090a_create_factory_packing"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_COLUMNS = {
    "ly_production_plan_material": ("bom_color", "bom_size", "bom_part"),
    "ly_material_purchase_requirement": ("bom_color", "bom_size", "bom_part"),
}


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(str(column.get("name")) == column_name for column in inspector.get_columns(table_name, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, column_names in _TABLE_COLUMNS.items():
        if not _table_exists(bind, schema, table_name):
            continue
        columns = [
            sa.Column(column_name, sa.String(length=100), nullable=True)
            for column_name in column_names
            if not _column_exists(bind, schema, table_name, column_name)
        ]
        if not columns:
            continue
        if _is_sqlite(bind):
            with op.batch_alter_table(table_name, schema=schema) as batch_op:
                for column in columns:
                    batch_op.add_column(column)
            continue
        for column in columns:
            op.add_column(table_name, column, schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    for table_name, column_names in _TABLE_COLUMNS.items():
        if not _table_exists(bind, schema, table_name):
            continue
        existing_columns = [
            column_name
            for column_name in reversed(column_names)
            if _column_exists(bind, schema, table_name, column_name)
        ]
        if not existing_columns:
            continue
        if _is_sqlite(bind):
            with op.batch_alter_table(table_name, schema=schema) as batch_op:
                for column_name in existing_columns:
                    batch_op.drop_column(column_name)
            continue
        for column_name in existing_columns:
            op.drop_column(table_name, column_name, schema=schema)
