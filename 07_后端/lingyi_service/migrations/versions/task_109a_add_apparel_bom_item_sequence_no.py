"""Add sequence number to apparel BOM material items."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "task_109a_add_apparel_bom_item_sequence_no"
down_revision = "task_108a_add_style_gallery_wash_label_type"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE_NAME = "ly_apparel_bom_item"
_INDEX_NAME = "idx_ly_apparel_bom_item_sequence"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    return _TABLE_NAME in sa.inspect(bind).get_table_names(schema=schema)


def _column_exists(bind, schema: str | None, column_name: str) -> bool:
    return column_name in {row["name"] for row in sa.inspect(bind).get_columns(_TABLE_NAME, schema=schema)}


def _index_exists(bind, schema: str | None, index_name: str) -> bool:
    return index_name in {row["name"] for row in sa.inspect(bind).get_indexes(_TABLE_NAME, schema=schema)}


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema(bind)
    if not _table_exists(bind, schema):
        return
    if not _column_exists(bind, schema, "sequence_no"):
        column = sa.Column("sequence_no", sa.BigInteger(), nullable=False, server_default="10")
        if _is_sqlite(bind):
            with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
                batch_op.add_column(column)
        else:
            op.add_column(_TABLE_NAME, column, schema=schema)
    if not _index_exists(bind, schema, _INDEX_NAME):
        op.create_index(_INDEX_NAME, _TABLE_NAME, ["bom_id", "sequence_no", "id"], schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema(bind)
    if not _table_exists(bind, schema):
        return
    if _index_exists(bind, schema, _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME, schema=schema)
    if _column_exists(bind, schema, "sequence_no"):
        if _is_sqlite(bind):
            with op.batch_alter_table(_TABLE_NAME, schema=schema) as batch_op:
                batch_op.drop_column("sequence_no")
        else:
            op.drop_column(_TABLE_NAME, "sequence_no", schema=schema)
