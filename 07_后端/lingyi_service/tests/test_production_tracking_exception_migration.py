"""Migration coverage for production tracking exceptions."""

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

from migrations.versions import task_070a_create_production_tracking_exception as migration_070a


class ProductionTrackingExceptionMigrationTest(unittest.TestCase):
    """Validate TASK-070A creates the tracking exception fact table."""

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
            previous_op = migration_070a.op
            migration_070a.op = operations
            try:
                migration_070a.upgrade()
            finally:
                migration_070a.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_070a.op
            migration_070a.op = operations
            try:
                migration_070a.downgrade()
            finally:
                migration_070a.op = previous_op

    def test_upgrade_creates_exception_table_columns_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        self.assertIn("ly_production_tracking_exception", set(inspector.get_table_names()))

        columns = {row["name"] for row in inspector.get_columns("ly_production_tracking_exception")}
        self.assertTrue(
            {
                "id",
                "exception_no",
                "plan_id",
                "company",
                "plan_no",
                "sales_order",
                "sales_order_item",
                "item_code",
                "exception_type",
                "severity",
                "status",
                "description",
                "owner",
                "created_by",
                "created_at",
                "updated_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ly_production_tracking_exception")}
        self.assertTrue(indexes["uk_ly_production_tracking_exception_no"]["unique"])
        self.assertIn("idx_ly_production_tracking_exception_plan", indexes)
        self.assertIn("idx_ly_production_tracking_exception_company_status", indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_table(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_production_tracking_exception", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        self.assertNotIn("ly_production_tracking_exception", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_070a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
