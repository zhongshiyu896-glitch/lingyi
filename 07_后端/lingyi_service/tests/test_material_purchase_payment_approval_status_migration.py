"""Migration coverage for purchase payment approval-gated status."""

from __future__ import annotations

import inspect as py_inspect
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

from migrations.versions import task_086a_extend_purchase_payment_approval_status as migration_086a


class MaterialPurchasePaymentApprovalStatusMigrationTest(unittest.TestCase):
    """Validate TASK-086A extends payment status without ORM create_all."""

    def setUp(self) -> None:
        self.engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
        metadata = sa.MetaData()
        sa.Table(
            "ly_material_purchase_payment",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.CheckConstraint("status IN ('submitted','cancelled')", name="ck_ly_material_purchase_payment_status"),
        )
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as connection:
            context = MigrationContext.configure(connection)
            operations = Operations(context)
            previous_op = migration_086a.op
            migration_086a.op = operations
            try:
                migration_086a.upgrade()
            finally:
                migration_086a.op = previous_op

    def test_upgrade_allows_pending_approval_status_idempotently(self) -> None:
        self._run_upgrade()
        self._run_upgrade()

        with self.engine.begin() as connection:
            connection.execute(
                sa.text("INSERT INTO ly_material_purchase_payment (id, status) VALUES (1, 'pending_approval')")
            )
            row = connection.execute(sa.text("SELECT status FROM ly_material_purchase_payment WHERE id = 1")).fetchone()
            create_sql = connection.execute(
                sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_material_purchase_payment'")
            ).scalar_one()

        self.assertEqual(row[0], "pending_approval")
        self.assertIn("'pending_approval'", str(create_sql))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = py_inspect.getsource(migration_086a)
        self.assertNotIn("metadata.create_all", source)


if __name__ == "__main__":
    unittest.main()
