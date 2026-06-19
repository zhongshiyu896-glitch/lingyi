"""Migration coverage for quality write idempotency ledger."""

from __future__ import annotations

from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from migrations.versions import task_030f_create_quality_write_idempotency as migration_030f


class QualityWriteIdempotencyMigrationTest(unittest.TestCase):
    """Validate TASK-030F creates quality write idempotency table."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_quality_inspection", metadata, Column("id", BigInteger, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_030f.op
            migration_030f.op = operations
            try:
                migration_030f.upgrade()
            finally:
                migration_030f.op = previous_op

    def test_upgrade_creates_quality_write_idempotency_table_and_indexes(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        self.assertIn("ly_quality_write_idempotency", set(inspector.get_table_names()))

        columns = {row["name"] for row in inspector.get_columns("ly_quality_write_idempotency")}
        self.assertTrue(
            {
                "company",
                "operation",
                "idempotency_key",
                "request_hash",
                "resource_id",
                "result_json",
                "created_by",
                "created_at",
            }.issubset(columns)
        )

        indexes = {row["name"]: row for row in inspector.get_indexes("ly_quality_write_idempotency")}
        self.assertTrue(indexes["uk_ly_quality_write_idem_key"]["unique"])
        self.assertIn("idx_ly_quality_write_idem_resource", indexes)

    def test_upgrade_is_idempotent(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_quality_write_idempotency", set(inspect(self.engine).get_table_names()))

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_030f.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)


if __name__ == "__main__":
    unittest.main()

