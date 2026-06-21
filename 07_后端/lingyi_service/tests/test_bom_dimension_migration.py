"""Migration coverage for BOM dimensions on material demand rows."""

from __future__ import annotations

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

from migrations.versions import task_091a_add_bom_dimensions_to_material_requirements as migration_091a


class BomDimensionMigrationTest(unittest.TestCase):
    """Validate TASK-091A adds BOM color, size, and part columns durably."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_production_plan_material", metadata, Column("id", Integer, primary_key=True))
        Table("ly_material_purchase_requirement", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_migration(self, direction: str) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_091a.op
            migration_091a.op = operations
            try:
                getattr(migration_091a, direction)()
            finally:
                migration_091a.op = previous_op

    def _columns(self, table_name: str) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns(table_name)}

    def test_upgrade_adds_bom_dimension_columns_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        expected = {"bom_color", "bom_size", "bom_part"}
        self.assertTrue(expected.issubset(self._columns("ly_production_plan_material")))
        self.assertTrue(expected.issubset(self._columns("ly_material_purchase_requirement")))

    def test_downgrade_removes_bom_dimension_columns(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        removed = {"bom_color", "bom_size", "bom_part"}
        self.assertTrue(self._columns("ly_production_plan_material").isdisjoint(removed))
        self.assertTrue(self._columns("ly_material_purchase_requirement").isdisjoint(removed))
