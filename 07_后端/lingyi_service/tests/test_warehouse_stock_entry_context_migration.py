"""Migration coverage for purchase requirement context on stock-entry items."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_096a_add_purchase_requirement_context_to_stock_entry_items as migration_096a


class WarehouseStockEntryContextMigrationTest(unittest.TestCase):
    """Validate TASK-096A durably adds BOM context snapshot columns to draft items."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_warehouse_stock_entry_draft_item", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_migration(self, direction: str) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_096a.op
            migration_096a.op = operations
            try:
                getattr(migration_096a, direction)()
            finally:
                migration_096a.op = previous_op

    def _columns(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns("ly_warehouse_stock_entry_draft_item")}

    def test_upgrade_adds_context_columns_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        columns = self._columns()
        self.assertIn("sales_order_item", columns)
        self.assertIn("bom_color", columns)
        self.assertIn("bom_size", columns)
        self.assertIn("bom_part", columns)

    def test_downgrade_removes_context_columns(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        columns = self._columns()
        self.assertNotIn("sales_order_item", columns)
        self.assertNotIn("bom_color", columns)
        self.assertNotIn("bom_size", columns)
        self.assertNotIn("bom_part", columns)

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_096a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
