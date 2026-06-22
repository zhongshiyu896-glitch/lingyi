"""TASK-094A align material purchase requirement unique key with BOM dimensions.

Revision ID: task_094a_fix_material_purchase_requirement_unique_key
Revises: task_093a_create_warehouse_stock_ledger_entry
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_094a_fix_material_purchase_requirement_unique_key"
down_revision = "task_093a_create_warehouse_stock_ledger_entry"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_material_purchase_requirement"
_UNIQUE_NAME = "uk_ly_material_purchase_req_source_material"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _constraint_exists(bind, schema: str | None, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(
        str(constraint.get("name")) == constraint_name
        for constraint in inspector.get_unique_constraints(_TABLE, schema=schema)
    )


def _qualified_table(schema: str | None) -> str:
    return f"{schema}.{_TABLE}" if schema else _TABLE


def _qualified_index(schema: str | None) -> str:
    return f"{schema}.{_UNIQUE_NAME}" if schema else _UNIQUE_NAME


def _duplicate_lookup_sql(*, include_dimensions: bool) -> str:
    dimension_columns = ""
    dimension_group = ""
    if include_dimensions:
        dimension_columns = (
            ", COALESCE(bom_color, '') AS bom_color_key"
            ", COALESCE(bom_size, '') AS bom_size_key"
            ", COALESCE(bom_part, '') AS bom_part_key"
        )
        dimension_group = ", COALESCE(bom_color, ''), COALESCE(bom_size, ''), COALESCE(bom_part, '')"
    table_name = _qualified_table(_schema_of(op.get_bind()))
    return f"""
        SELECT
            company,
            source_type,
            source_id,
            COALESCE(bom_item_id, -1) AS bom_item_id_key,
            material_item_code,
            warehouse
            {dimension_columns},
            COUNT(*) AS row_count
        FROM {table_name}
        GROUP BY
            company,
            source_type,
            source_id,
            COALESCE(bom_item_id, -1),
            material_item_code,
            warehouse
            {dimension_group}
        HAVING COUNT(*) > 1
        LIMIT 1
    """


def _require_no_duplicates(*, include_dimensions: bool) -> None:
    bind = op.get_bind()
    row = bind.execute(sa.text(_duplicate_lookup_sql(include_dimensions=include_dimensions))).mappings().first()
    if row is None:
        return
    key = ", ".join(f"{name}={value}" for name, value in row.items() if name != "row_count")
    mode = "BOM dimension key" if include_dimensions else "legacy key"
    raise RuntimeError(f"Cannot create material purchase requirement {mode}; duplicate rows exist: {key}")


def _drop_old_unique_if_exists(bind, schema: str | None) -> None:
    if not _constraint_exists(bind, schema, _UNIQUE_NAME):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            batch_op.drop_constraint(_UNIQUE_NAME, type_="unique")
        return
    op.drop_constraint(_UNIQUE_NAME, _TABLE, type_="unique", schema=schema)


def _create_old_unique_if_missing(bind, schema: str | None) -> None:
    if _constraint_exists(bind, schema, _UNIQUE_NAME):
        return
    columns = ["company", "source_type", "source_id", "bom_item_id", "material_item_code", "warehouse"]
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            batch_op.create_unique_constraint(_UNIQUE_NAME, columns)
        return
    op.create_unique_constraint(_UNIQUE_NAME, _TABLE, columns, schema=schema)


def _create_dimension_index(schema: str | None) -> None:
    table_name = _qualified_table(schema)
    index_name = _qualified_index(schema)
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
        ON {table_name} (
            company,
            source_type,
            source_id,
            COALESCE(bom_item_id, -1),
            COALESCE(bom_color, ''),
            COALESCE(bom_size, ''),
            COALESCE(bom_part, ''),
            material_item_code,
            warehouse
        )
        """
    )


def _drop_dimension_index(schema: str | None) -> None:
    op.execute(f"DROP INDEX IF EXISTS {_qualified_index(schema)}")


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    _require_no_duplicates(include_dimensions=True)
    _drop_old_unique_if_exists(bind, schema)
    _create_dimension_index(schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema, _TABLE):
        return
    _require_no_duplicates(include_dimensions=False)
    _drop_dimension_index(schema)
    _create_old_unique_if_missing(bind, schema)
