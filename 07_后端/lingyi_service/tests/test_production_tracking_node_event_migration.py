"""Migration coverage for production tracking node events."""

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

from migrations.versions import task_085a_create_production_tracking_node_event as migration_085a


class ProductionTrackingNodeEventMigrationTest(unittest.TestCase):
    """Validate TASK-085A creates the tracking node event fact table."""

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
            previous_op = migration_085a.op
            migration_085a.op = operations
            try:
                migration_085a.upgrade()
            finally:
                migration_085a.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_085a.op
            migration_085a.op = operations
            try:
                migration_085a.downgrade()
            finally:
                migration_085a.op = previous_op

    def test_upgrade_creates_event_table_columns_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        self.assertIn("ly_production_tracking_node_event", set(inspector.get_table_names()))

        columns = {row["name"] for row in inspector.get_columns("ly_production_tracking_node_event")}
        self.assertTrue(
            {
                "id",
                "event_no",
                "plan_id",
                "company",
                "plan_no",
                "sales_order",
                "sales_order_item",
                "item_code",
                "node_key",
                "node_name",
                "owner",
                "status",
                "progress",
                "remark",
                "source_type",
                "source_ref",
                "idempotency_key",
                "request_id",
                "created_by",
                "created_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ly_production_tracking_node_event")}
        self.assertTrue(indexes["uk_ly_production_tracking_node_event_no"]["unique"])
        self.assertIn("idx_ly_production_tracking_node_event_plan_node", indexes)
        self.assertIn("idx_ly_production_tracking_node_event_company_status", indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_table(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_production_tracking_node_event", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        self.assertNotIn("ly_production_tracking_node_event", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_085a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
