"""Migration coverage for warehouse stock ledger BOM context columns."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_097a_add_bom_context_to_stock_ledger_entries as migration_097a


class WarehouseStockLedgerContextMigrationTest(unittest.TestCase):
    """Validate TASK-097A adds contextual dimensions to durable ledger entries."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table(
            "ly_warehouse_stock_ledger_entry",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("company", String(140), nullable=False),
            Column("warehouse", String(140), nullable=False),
            Column("item_code", String(140), nullable=False),
            Column("uom", String(32), nullable=True),
            Column("posting_date", Date(), nullable=False),
            Column("sort_at", DateTime(timezone=True), nullable=False),
            Column("source_type", String(64), nullable=False),
            Column("source_id", String(140), nullable=False),
            Column("source_line_id", String(140), nullable=False),
            Column("sequence", Integer, nullable=False),
            Column("voucher_type", String(140), nullable=False),
            Column("voucher_no", String(140), nullable=False),
            Column("actual_qty", Numeric(18, 6), nullable=False),
            Column("valuation_rate", Numeric(18, 6), nullable=True),
            Column("status", String(32), nullable=False),
            Column("projected_at", DateTime(timezone=True), nullable=False),
            Column("voided_at", DateTime(timezone=True), nullable=True),
        )
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_migration(self, direction: str) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_097a.op
            migration_097a.op = operations
            try:
                getattr(migration_097a, direction)()
            finally:
                migration_097a.op = previous_op

    def _columns(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns("ly_warehouse_stock_ledger_entry")}

    def _indexes(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_indexes("ly_warehouse_stock_ledger_entry")}

    def test_upgrade_adds_context_columns_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        self.assertTrue(
            {
                "purchase_requirement_id",
                "sales_order_item",
                "bom_color",
                "bom_size",
                "bom_part",
            }.issubset(self._columns())
        )
        self.assertIn("idx_ly_whse_stock_ledger_requirement", self._indexes())

    def test_downgrade_removes_context_columns(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        self.assertFalse(
            {
                "purchase_requirement_id",
                "sales_order_item",
                "bom_color",
                "bom_size",
                "bom_part",
            }
            & self._columns()
        )
        self.assertNotIn("idx_ly_whse_stock_ledger_requirement", self._indexes())

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_097a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
