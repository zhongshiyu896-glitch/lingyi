"""Migration tests for production quote tables."""

from __future__ import annotations

import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


migration_004a = importlib.import_module("migrations.versions.task_004a_create_production_tables")
migration_073a = importlib.import_module("migrations.versions.task_073a_create_production_quote")
migration_076a = importlib.import_module("migrations.versions.task_076a_extend_production_quote_convert")
migration_078a = importlib.import_module("migrations.versions.task_078a_extend_production_quote_operations")
migration_104a = importlib.import_module("migrations.versions.task_104a_extend_production_quote_order_level")


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
    _run_migration(engine, migration_004a, "upgrade")
    _run_migration(engine, migration_073a, "upgrade")
    _run_migration(engine, migration_076a, "upgrade")
    _run_migration(engine, migration_078a, "upgrade")
    _run_migration(engine, migration_104a, "upgrade")


def _run_downgrade(engine: sa.Engine) -> None:
    _run_migration(engine, migration_104a, "downgrade")
    _run_migration(engine, migration_078a, "downgrade")
    _run_migration(engine, migration_076a, "downgrade")
    _run_migration(engine, migration_073a, "downgrade")


def _table_names(engine: sa.Engine) -> set[str]:
    with engine.connect() as connection:
        return set(sa.inspect(connection).get_table_names())


def _index_names(engine: sa.Engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        return {str(index["name"]) for index in sa.inspect(connection).get_indexes(table_name)}


def test_upgrade_creates_quote_tables_and_indexes() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        tables = _table_names(engine)
        assert "ly_production_quote" in tables
        assert "ly_production_quote_operation" in tables
        assert "uk_ly_production_quote_no" in _index_names(engine, "ly_production_quote")
        assert "idx_ly_production_quote_plan" in _index_names(engine, "ly_production_quote")
        assert "idx_ly_production_quote_sales_order" in _index_names(engine, "ly_production_quote")
        assert "uk_ly_production_quote_operation_idem" in _index_names(engine, "ly_production_quote_operation")
        with engine.connect() as connection:
            quote_columns = {column["name"] for column in sa.inspect(connection).get_columns("ly_production_quote")}
        assert {"sales_order_id", "quote_unit_price", "other_fee", "quote_items_json"}.issubset(quote_columns)
    finally:
        engine.dispose()


def test_order_level_quote_migration_extends_sales_order_when_table_exists() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_migration(engine, migration_004a, "upgrade")
        _run_migration(engine, migration_073a, "upgrade")
        _run_migration(engine, migration_076a, "upgrade")
        _run_migration(engine, migration_078a, "upgrade")
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    CREATE TABLE ly_sales_order (
                        id INTEGER PRIMARY KEY,
                        sales_order_no VARCHAR(140) NOT NULL,
                        company VARCHAR(140) NOT NULL,
                        quote_status VARCHAR(32) DEFAULT '未核价'
                    )
                    """
                )
            )
        _run_migration(engine, migration_104a, "upgrade")
        with engine.connect() as connection:
            order_columns = {column["name"] for column in sa.inspect(connection).get_columns("ly_sales_order")}
        assert {"quote_unit_price", "quote_material_cost", "quote_labor_cost", "quote_total_cost"}.issubset(order_columns)
    finally:
        engine.dispose()


def test_upgrade_allows_quote_action_operation_ledger_rows() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        with engine.begin() as connection:
            for operation in ("convert", "copy", "void", "confirm", "update"):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO ly_production_quote_operation (
                            quote_id, company, operation, idempotency_key, request_hash, response_json, created_by
                        ) VALUES (
                            NULL, 'COMP-Q', :operation, :idempotency_key, :request_hash, '{}', 'tester'
                        )
                        """
                    ),
                    {
                        "operation": operation,
                        "idempotency_key": f"IDEM-{operation.upper()}",
                        "request_hash": f"HASH-{operation.upper()}",
                    },
                )
        with engine.connect() as connection:
            rows = connection.execute(sa.text("SELECT operation FROM ly_production_quote_operation ORDER BY operation")).fetchall()
        assert [row[0] for row in rows] == ["confirm", "convert", "copy", "update", "void"]
    finally:
        engine.dispose()


def test_upgrade_is_idempotent_and_downgrade_removes_quote_tables() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        _run_upgrade(engine)
        _run_migration(engine, migration_073a, "upgrade")
        _run_migration(engine, migration_076a, "upgrade")
        _run_migration(engine, migration_078a, "upgrade")
        _run_migration(engine, migration_104a, "upgrade")
        assert "ly_production_quote" in _table_names(engine)
        _run_downgrade(engine)
        assert "ly_production_quote" not in _table_names(engine)
        assert "ly_production_quote_operation" not in _table_names(engine)
    finally:
        engine.dispose()
