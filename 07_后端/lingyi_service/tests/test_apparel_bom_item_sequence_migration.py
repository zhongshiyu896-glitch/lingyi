"""Migration coverage for BOM item sequence sorting."""

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

from migrations.versions import task_109a_add_apparel_bom_item_sequence_no as migration_109a


class ApparelBomItemSequenceMigrationTest(unittest.TestCase):
    """Validate TASK-109A adds explicit material BOM item ordering."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table(
            "ly_apparel_bom_item",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("bom_id", Integer, nullable=False),
        )
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_migration(self, direction: str) -> None:
        with self.engine.begin() as connection:
            context = MigrationContext.configure(connection)
            operations = Operations(context)
            previous_op = migration_109a.op
            migration_109a.op = operations
            try:
                getattr(migration_109a, direction)()
            finally:
                migration_109a.op = previous_op

    def _columns(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_columns("ly_apparel_bom_item")}

    def _indexes(self) -> set[str]:
        return {row["name"] for row in inspect(self.engine).get_indexes("ly_apparel_bom_item")}

    def test_upgrade_adds_sequence_column_and_index_idempotently(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("upgrade")

        self.assertIn("sequence_no", self._columns())
        self.assertIn("idx_ly_apparel_bom_item_sequence", self._indexes())

    def test_downgrade_removes_sequence_column_and_index(self) -> None:
        self._run_migration("upgrade")
        self._run_migration("downgrade")

        self.assertNotIn("sequence_no", self._columns())
        self.assertNotIn("idx_ly_apparel_bom_item_sequence", self._indexes())
