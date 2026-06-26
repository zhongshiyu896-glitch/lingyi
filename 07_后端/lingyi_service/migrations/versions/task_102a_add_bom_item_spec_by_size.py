"""Add size-specific specification field to style/sample BOM items."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_102a_add_bom_item_spec_by_size"
down_revision = "task_101a_add_bom_item_usage_count"
branch_labels = None
depends_on = None

_TABLES = ("ly_apparel_bom_item", "ly_sample_material_bom_item")


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _schema() -> str | None:
    return None if _is_sqlite() else "ly_schema"


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {row["name"] for row in inspector.get_columns(table_name, schema=_schema())}


def upgrade() -> None:
    for table_name in _TABLES:
        if not _has_column(table_name, "spec_by_size"):
            op.add_column(table_name, sa.Column("spec_by_size", sa.JSON(), nullable=True), schema=_schema())


def downgrade() -> None:
    for table_name in _TABLES:
        if _has_column(table_name, "spec_by_size"):
            op.drop_column(table_name, "spec_by_size", schema=_schema())
