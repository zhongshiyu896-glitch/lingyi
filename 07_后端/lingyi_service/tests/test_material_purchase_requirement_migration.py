"""Migration coverage for FastAPI-native material purchase requirement pool."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_063b_create_material_purchase_requirements as migration_063b


class MaterialPurchaseRequirementMigrationTest(unittest.TestCase):
    """Validate TASK-063B bootstraps the material requirement pool table."""

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
            previous_op = migration_063b.op
            migration_063b.op = operations
            try:
                migration_063b.upgrade()
            finally:
                migration_063b.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_063b.op
            migration_063b.op = operations
            try:
                migration_063b.downgrade()
            finally:
                migration_063b.op = previous_op

    def test_upgrade_creates_requirement_table_columns_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        self.assertIn("ly_material_purchase_requirement", set(inspector.get_table_names()))

        columns = {row["name"] for row in inspector.get_columns("ly_material_purchase_requirement")}
        self.assertTrue(
            {
                "company",
                "requirement_no",
                "source_type",
                "source_id",
                "source_no",
                "plan_id",
                "bom_item_id",
                "sales_order",
                "sales_order_item",
                "item_code",
                "material_item_code",
                "material_name",
                "supplier_name",
                "warehouse",
                "required_qty",
                "available_qty",
                "net_required_qty",
                "purchased_qty",
                "received_qty",
                "uom",
                "unit_price",
                "status",
                "purchase_order_id",
                "purchase_order_item_id",
                "purchase_no",
                "payload",
                "created_by",
                "created_at",
                "updated_by",
                "updated_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ly_material_purchase_requirement")}
        self.assertTrue(indexes["uk_ly_material_purchase_req_company_no"]["unique"])
        self.assertIn("idx_ly_material_purchase_req_status", indexes)
        self.assertIn("idx_ly_material_purchase_req_material", indexes)
        self.assertIn("idx_ly_material_purchase_req_purchase", indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_table(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_material_purchase_requirement", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        self.assertNotIn("ly_material_purchase_requirement", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_063b.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)

