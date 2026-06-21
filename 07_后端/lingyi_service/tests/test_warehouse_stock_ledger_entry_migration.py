"""Migration coverage for warehouse stock ledger entry facts."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_093a_create_warehouse_stock_ledger_entry as migration_093a


class WarehouseStockLedgerEntryMigrationTest(unittest.TestCase):
    """Validate TASK-093A creates the durable stock movement fact table."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_migration(self, direction: str) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_093a.op
            migration_093a.op = operations
            try:
                getattr(migration_093a, direction)()
            finally:
                migration_093a.op = previous_op

    def _tables(self) -> set[str]:
        return set(inspect(self.engine).get_table_names())

    def _columns(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns("ly_warehouse_stock_ledger_entry")}

    def _indexes(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_indexes("ly_warehouse_stock_ledger_entry")}

    def test_upgrade_creates_ledger_table_and_indexes_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        self.assertIn("ly_warehouse_stock_ledger_entry", self._tables())
        self.assertTrue(
            {
                "company",
                "warehouse",
                "item_code",
                "uom",
                "posting_date",
                "sort_at",
                "source_type",
                "source_id",
                "source_line_id",
                "sequence",
                "voucher_type",
                "voucher_no",
                "actual_qty",
                "valuation_rate",
                "status",
                "projected_at",
                "voided_at",
            }.issubset(self._columns())
        )
        self.assertTrue(
            {
                "uk_ly_whse_stock_ledger_source",
                "idx_ly_whse_stock_ledger_company_wh_item",
                "idx_ly_whse_stock_ledger_voucher",
            }.issubset(self._indexes())
        )

    def test_downgrade_removes_ledger_table(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        self.assertNotIn("ly_warehouse_stock_ledger_entry", self._tables())

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_093a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
