"""Migration coverage for workshop wage payments."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_014a_create_workshop_wage_payment as migration_014a


class WorkshopWagePaymentMigrationTest(unittest.TestCase):
    """Validate TASK-014A creates the durable wage payment fact table."""

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
            previous_op = migration_014a.op
            migration_014a.op = operations
            try:
                getattr(migration_014a, direction)()
            finally:
                migration_014a.op = previous_op

    def test_upgrade_creates_wage_payment_table_columns_and_indexes_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        inspector = inspect(self.engine)
        self.assertIn("ys_workshop_wage_payment", set(inspector.get_table_names()))
        columns = {row["name"] for row in inspector.get_columns("ys_workshop_wage_payment")}
        self.assertTrue(
            {
                "id",
                "payment_entry",
                "employee",
                "work_date",
                "process_name",
                "item_code",
                "wage_amount",
                "paid_amount",
                "outstanding_before",
                "outstanding_after",
                "mode_of_payment",
                "reference_no",
                "reference_date",
                "status",
                "source_ref",
                "idempotency_key",
                "request_hash",
                "scenario_tag",
                "payload",
                "created_by",
                "created_at",
                "updated_by",
                "updated_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ys_workshop_wage_payment")}
        self.assertTrue(indexes["uk_ys_workshop_wage_payment_entry"]["unique"])
        self.assertTrue(indexes["uk_ys_workshop_wage_payment_idem"]["unique"])
        self.assertTrue(indexes["uk_ys_workshop_wage_payment_source"]["unique"])
        self.assertIn("idx_ys_workshop_wage_payment_daily", indexes)
        self.assertIn("idx_ys_workshop_wage_payment_status", indexes)

    def test_downgrade_removes_wage_payment_table(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        self.assertNotIn("ys_workshop_wage_payment", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_014a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
