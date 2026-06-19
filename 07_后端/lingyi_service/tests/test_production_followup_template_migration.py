"""Migration tests for production follow-up template tables."""

from __future__ import annotations

import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


migration_072a = importlib.import_module("migrations.versions.task_072a_create_production_followup_template")


def _run_upgrade(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        previous = migration_072a.op
        migration_072a.op = operations
        try:
            migration_072a.upgrade()
        finally:
            migration_072a.op = previous


def _run_downgrade(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        previous = migration_072a.op
        migration_072a.op = operations
        try:
            migration_072a.downgrade()
        finally:
            migration_072a.op = previous


def _table_names(engine: sa.Engine) -> set[str]:
    with engine.connect() as connection:
        return set(sa.inspect(connection).get_table_names())


def _index_names(engine: sa.Engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        return {str(index["name"]) for index in sa.inspect(connection).get_indexes(table_name)}


def test_upgrade_creates_followup_template_tables_and_indexes() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        tables = _table_names(engine)
        assert "ly_production_followup_template" in tables
        assert "ly_production_followup_template_operation" in tables
        assert "uk_ly_production_followup_template_no" in _index_names(engine, "ly_production_followup_template")
        assert "idx_ly_production_followup_template_status" in _index_names(engine, "ly_production_followup_template")
        assert "idx_ly_production_followup_template_item" in _index_names(engine, "ly_production_followup_template")
        assert "uk_ly_production_followup_template_operation_idem" in _index_names(
            engine,
            "ly_production_followup_template_operation",
        )
    finally:
        engine.dispose()


def test_upgrade_is_idempotent_and_downgrade_removes_tables() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        _run_upgrade(engine)
        assert "ly_production_followup_template" in _table_names(engine)
        _run_downgrade(engine)
        assert "ly_production_followup_template" not in _table_names(engine)
        assert "ly_production_followup_template_operation" not in _table_names(engine)
    finally:
        engine.dispose()


def test_migration_does_not_depend_on_orm_metadata_create_all() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        assert _table_names(engine) == set()
        _run_upgrade(engine)
        assert "ly_production_followup_template" in _table_names(engine)
    finally:
        engine.dispose()
