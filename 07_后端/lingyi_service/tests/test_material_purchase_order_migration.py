"""Migration coverage for FastAPI-native material purchase order tables."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_064b_create_material_purchase_order_tables as migration_064b


class MaterialPurchaseOrderMigrationTest(unittest.TestCase):
    """Validate TASK-064B bootstraps purchase order tables without metadata create_all."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_064b.op
            migration_064b.op = operations
            try:
                migration_064b.upgrade()
            finally:
                migration_064b.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_064b.op
            migration_064b.op = operations
            try:
                migration_064b.downgrade()
            finally:
                migration_064b.op = previous_op

    def test_upgrade_creates_purchase_order_tables_columns_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        self.assertTrue(
            {
                "ly_material_purchase_order",
                "ly_material_purchase_order_item",
                "ly_material_purchase_idempotency",
            }.issubset(tables)
        )

        order_columns = {row["name"] for row in inspector.get_columns("ly_material_purchase_order")}
        self.assertTrue(
            {
                "company",
                "purchase_no",
                "supplier_name",
                "status",
                "total_qty",
                "received_qty",
                "total_amount",
                "currency",
                "created_by",
            }.issubset(order_columns)
        )

        item_columns = {row["name"] for row in inspector.get_columns("ly_material_purchase_order_item")}
        self.assertTrue(
            {
                "order_id",
                "company",
                "material_item_code",
                "qty",
                "received_qty",
                "uom",
                "unit_price",
                "amount",
                "warehouse",
            }.issubset(item_columns)
        )

        idem_columns = {row["name"] for row in inspector.get_columns("ly_material_purchase_idempotency")}
        self.assertTrue(
            {
                "company",
                "idempotency_key",
                "operation",
                "request_hash",
                "record_id",
                "response_data",
                "created_by",
            }.issubset(idem_columns)
        )

        order_indexes = {row["name"] for row in inspector.get_indexes("ly_material_purchase_order")}
        self.assertIn("uk_ly_material_purchase_order_company_no", order_indexes)
        self.assertIn("idx_ly_material_purchase_order_supplier_status", order_indexes)

        item_indexes = {row["name"] for row in inspector.get_indexes("ly_material_purchase_order_item")}
        self.assertIn("idx_ly_material_purchase_order_item_order", item_indexes)
        self.assertIn("idx_ly_material_purchase_order_item_material", item_indexes)

        idem_indexes = {row["name"] for row in inspector.get_indexes("ly_material_purchase_idempotency")}
        self.assertIn("uk_ly_material_purchase_idem_company_key", idem_indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_tables(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_material_purchase_order", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        tables_after_downgrade = set(inspect(self.engine).get_table_names())
        self.assertNotIn("ly_material_purchase_order", tables_after_downgrade)
        self.assertNotIn("ly_material_purchase_order_item", tables_after_downgrade)
        self.assertNotIn("ly_material_purchase_idempotency", tables_after_downgrade)

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_064b.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
