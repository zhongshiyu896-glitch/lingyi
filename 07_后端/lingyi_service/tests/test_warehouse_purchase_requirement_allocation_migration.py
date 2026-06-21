"""Migration coverage for purchase requirement allocation on stock entries."""

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

from migrations.versions import task_092a_add_purchase_requirement_allocation_to_stock_entry_items as migration_092a


class WarehousePurchaseRequirementAllocationMigrationTest(unittest.TestCase):
    """Validate TASK-092A durably adds purchase requirement allocation to draft items."""

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
            previous_op = migration_092a.op
            migration_092a.op = operations
            try:
                getattr(migration_092a, direction)()
            finally:
                migration_092a.op = previous_op

    def _columns(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns("ly_warehouse_stock_entry_draft_item")}

    def _indexes(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_indexes("ly_warehouse_stock_entry_draft_item")}

    def test_upgrade_adds_purchase_requirement_column_and_index_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        self.assertIn("purchase_requirement_id", self._columns())
        self.assertIn("idx_ly_whse_stock_entry_item_requirement", self._indexes())

    def test_downgrade_removes_purchase_requirement_column_and_index(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        self.assertNotIn("purchase_requirement_id", self._columns())
        self.assertNotIn("idx_ly_whse_stock_entry_item_requirement", self._indexes())

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_092a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
