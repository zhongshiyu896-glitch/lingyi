"""DEPLOY-2 create FastAPI admin login account table.

Revision ID: task_098a_create_auth_admin_user
Revises: task_097a_add_bom_context_to_stock_ledger_entries
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "task_098a_create_auth_admin_user"
down_revision = "task_097a_add_bom_context_to_stock_ledger_entries"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_auth_admin_user"
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
        sa.Column("username", sa.String(140), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("roles", _json_type(bind), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("is_service_account", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ly_auth_admin_user"),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_ly_auth_admin_user_status"),
        schema=schema,
    )
    op.create_index("uk_ly_auth_admin_user_username", _TABLE, ["username"], unique=True, schema=schema)
    op.create_index("idx_ly_auth_admin_user_status", _TABLE, ["status"], schema=schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, _TABLE, schema):
        return
    op.drop_index("idx_ly_auth_admin_user_status", table_name=_TABLE, schema=schema)
    op.drop_index("uk_ly_auth_admin_user_username", table_name=_TABLE, schema=schema)
    op.drop_table(_TABLE, schema=schema)
