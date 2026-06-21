"""Migration coverage for factory packing registrations."""

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

from migrations.versions import task_090a_create_factory_packing as migration_090a


class FactoryPackingMigrationTest(unittest.TestCase):
    """Validate TASK-090A creates the FastAPI-native factory packing fact table."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_production_plan", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_090a.op
            migration_090a.op = operations
            try:
                migration_090a.upgrade()
            finally:
                migration_090a.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_090a.op
            migration_090a.op = operations
            try:
                migration_090a.downgrade()
            finally:
                migration_090a.op = previous_op

    def test_upgrade_creates_factory_packing_table_columns_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        self.assertIn("ly_factory_packing", set(inspector.get_table_names()))

        columns = {row["name"] for row in inspector.get_columns("ly_factory_packing")}
        self.assertTrue(
            {
                "id",
                "packing_no",
                "company",
                "plan_id",
                "plan_no",
                "sales_order",
                "sales_order_item",
                "customer",
                "item_code",
                "inbound_qty",
                "outbound_qty",
                "carton_qty",
                "box_spec",
                "source_ref",
                "remark",
                "status",
                "idempotency_key",
                "request_hash",
                "created_by",
                "created_at",
                "updated_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ly_factory_packing")}
        self.assertTrue(indexes["uk_ly_factory_packing_no"]["unique"])
        self.assertTrue(indexes["uk_ly_factory_packing_idem"]["unique"])
        self.assertIn("idx_ly_factory_packing_plan", indexes)
        self.assertIn("idx_ly_factory_packing_order_item", indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_table(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_factory_packing", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        self.assertNotIn("ly_factory_packing", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_090a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
