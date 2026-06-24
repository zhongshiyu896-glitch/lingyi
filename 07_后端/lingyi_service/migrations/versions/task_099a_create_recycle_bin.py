"""Create unified recycle bin table.

Revision ID: task_099a_create_recycle_bin
Revises: task_098a_create_auth_admin_user
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_099a_create_recycle_bin"
down_revision = "task_098a_create_auth_admin_user"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_recycle_bin_item"
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, table_name: str, schema: str | None) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=schema)


def _json_type(bind):
    if _is_sqlite(bind):
        return sa.JSON()
    return postgresql.JSONB()


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, _TABLE, schema):
        return

    op.create_table(
        _TABLE,
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_path", sa.String(140), nullable=True),
        sa.Column("original_id", ID_TYPE, nullable=False),
        sa.Column("company", sa.String(140), nullable=True),
        sa.Column("code", sa.String(140), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("snapshot", _json_type(bind), nullable=False),
        sa.Column("details", _json_type(bind), nullable=False),
        sa.Column("status", sa.String(16), server_default="deleted", nullable=False),
        sa.Column("deleted_by", sa.String(140), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("restored_by", sa.String(140), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ly_recycle_bin_item"),
        sa.CheckConstraint("status IN ('deleted','restored')", name="ck_ly_recycle_bin_status"),
        schema=schema,
    )
    op.create_index("idx_ly_recycle_bin_status_deleted", _TABLE, ["status", "deleted_at"], schema=schema)
    op.create_index("idx_ly_recycle_bin_module_entity", _TABLE, ["module", "entity_type", "status"], schema=schema)
    op.create_index("idx_ly_recycle_bin_company", _TABLE, ["company", "status"], schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, _TABLE, schema):
        return
    op.drop_index("idx_ly_recycle_bin_company", table_name=_TABLE, schema=schema)
    op.drop_index("idx_ly_recycle_bin_module_entity", table_name=_TABLE, schema=schema)
    op.drop_index("idx_ly_recycle_bin_status_deleted", table_name=_TABLE, schema=schema)
    op.drop_table(_TABLE, schema=schema)
