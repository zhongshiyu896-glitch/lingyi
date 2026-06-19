"""Migration tests for production follow-up template node tables."""

from __future__ import annotations

import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


migration_072a = importlib.import_module("migrations.versions.task_072a_create_production_followup_template")
migration_074a = importlib.import_module("migrations.versions.task_074a_create_production_followup_template_nodes")


def _run_migration(engine: sa.Engine, migration, direction: str) -> None:
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        previous = migration.op
        migration.op = operations
        try:
            getattr(migration, direction)()
        finally:
            migration.op = previous


def _run_upgrade(engine: sa.Engine) -> None:
    _run_migration(engine, migration_072a, "upgrade")
    _run_migration(engine, migration_074a, "upgrade")


def _run_downgrade(engine: sa.Engine) -> None:
    _run_migration(engine, migration_074a, "downgrade")
    _run_migration(engine, migration_072a, "downgrade")


def _table_names(engine: sa.Engine) -> set[str]:
    with engine.connect() as connection:
        return set(sa.inspect(connection).get_table_names())


def _index_names(engine: sa.Engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        return {str(index["name"]) for index in sa.inspect(connection).get_indexes(table_name)}


def test_upgrade_creates_followup_template_node_tables_and_indexes() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        tables = _table_names(engine)
        assert "ly_production_followup_template_node" in tables
        assert "ly_production_followup_template_node_operation" in tables
        assert "idx_ly_production_followup_template_node_template" in _index_names(engine, "ly_production_followup_template_node")
        assert "idx_ly_production_followup_template_node_company" in _index_names(engine, "ly_production_followup_template_node")
        assert "uk_ly_production_followup_template_node_operation_idem" in _index_names(
            engine,
            "ly_production_followup_template_node_operation",
        )
    finally:
        engine.dispose()


def test_upgrade_is_idempotent_and_downgrade_removes_node_tables() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        _run_upgrade(engine)
        assert "ly_production_followup_template_node" in _table_names(engine)
        _run_downgrade(engine)
        tables = _table_names(engine)
        assert "ly_production_followup_template_node" not in tables
        assert "ly_production_followup_template_node_operation" not in tables
    finally:
        engine.dispose()
