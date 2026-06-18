"""Migration coverage for production material snapshot units."""

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

from migrations.versions import task_069b_add_production_material_uom as migration_069b


class ProductionMaterialUomMigrationTest(unittest.TestCase):
    """Validate TASK-069B adds a durable uom column to material snapshots."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_production_plan_material", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_069b.op
            migration_069b.op = operations
            try:
                migration_069b.upgrade()
            finally:
                migration_069b.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_069b.op
            migration_069b.op = operations
            try:
                migration_069b.downgrade()
            finally:
                migration_069b.op = previous_op

    def test_upgrade_adds_uom_column_idempotently(self) -> None:
        self._run_upgrade()
        self._run_upgrade()

        columns = {row["name"] for row in inspect(self.engine).get_columns("ly_production_plan_material")}
        self.assertIn("uom", columns)

    def test_downgrade_removes_uom_column(self) -> None:
        self._run_upgrade()
        self._run_downgrade()

        columns = {row["name"] for row in inspect(self.engine).get_columns("ly_production_plan_material")}
        self.assertNotIn("uom", columns)
