"""Allow wash label images in style gallery.

Revision ID: task_108a_add_style_gallery_wash_label_type
Revises: task_107a_add_style_size_chart
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "task_108a_add_style_gallery_wash_label_type"
down_revision = "task_107a_add_style_size_chart"
branch_labels = None
depends_on = None

_SCHEMA_NAME = "ly_schema"
_TABLE = "ly_style_gallery"
_CONSTRAINT = "ck_ly_style_gallery_type"
_OLD_CHECK = "image_type IN ('main','detail','color','process','other')"
_NEW_CHECK = "image_type IN ('main','detail','color','process','wash_label','other')"


def _is_sqlite(bind) -> bool:
    return bind.dialect.name == "sqlite"


def _schema_of(bind) -> str | None:
    return None if _is_sqlite(bind) else _SCHEMA_NAME


def _table_exists(bind, schema: str | None) -> bool:
    return _TABLE in sa.inspect(bind).get_table_names(schema=schema)


def _constraint_exists(bind, schema: str | None) -> bool:
    return any(
        str(constraint.get("name")) == _CONSTRAINT
        for constraint in sa.inspect(bind).get_check_constraints(_TABLE, schema=schema)
    )


def _replace_gallery_type_constraint(expression: str) -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if not _table_exists(bind, schema):
        return
    if _is_sqlite(bind):
        with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
            try:
                batch_op.drop_constraint(_CONSTRAINT, type_="check")
            except ValueError:
                pass
            batch_op.create_check_constraint(_CONSTRAINT, expression)
        return
    if _constraint_exists(bind, schema):
        op.drop_constraint(_CONSTRAINT, _TABLE, schema=schema, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, expression, schema=schema)


def upgrade() -> None:
    _replace_gallery_type_constraint(_NEW_CHECK)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema_of(bind)
    if _table_exists(bind, schema):
        qualified = _TABLE if schema is None else f"{schema}.{_TABLE}"
        op.execute(sa.text(f"UPDATE {qualified} SET image_type = 'other' WHERE image_type = 'wash_label'"))
    _replace_gallery_type_constraint(_OLD_CHECK)
