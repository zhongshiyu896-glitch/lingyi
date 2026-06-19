"""Migration coverage for style and sample material BOM persistence."""

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

from migrations.versions import task_071a_create_material_bom_write_tables as migration_071a


class MaterialBomMigrationTest(unittest.TestCase):
    """Validate TASK-071A creates BOM write ledgers and sample BOM tables."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        Table("ly_apparel_bom", metadata, Column("id", Integer, primary_key=True))
        Table(
            "ly_apparel_bom_item",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("bom_id", Integer, nullable=False),
        )
        Table("ly_sample_order", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_071a.op
            migration_071a.op = operations
            try:
                migration_071a.upgrade()
            finally:
                migration_071a.op = previous_op

    def _run_downgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_071a.op
            migration_071a.op = operations
            try:
                migration_071a.downgrade()
            finally:
                migration_071a.op = previous_op

    def test_upgrade_creates_style_write_ledger_and_sample_bom_tables(self) -> None:
        self._run_upgrade()

        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        self.assertTrue(
            {
                "ly_apparel_bom_write_operation",
                "ly_sample_material_bom",
                "ly_sample_material_bom_item",
                "ly_sample_material_bom_operation",
            }.issubset(tables)
        )

        bom_item_columns = {row["name"] for row in inspector.get_columns("ly_apparel_bom_item")}
        self.assertIn("part", bom_item_columns)

        sample_bom_columns = {row["name"] for row in inspector.get_columns("ly_sample_material_bom")}
        self.assertTrue(
            {
                "company",
                "sample_order_id",
                "style_master_id",
                "item_code",
                "source_bom_id",
                "version_no",
                "status",
            }.issubset(sample_bom_columns)
        )

        sample_item_columns = {row["name"] for row in inspector.get_columns("ly_sample_material_bom_item")}
        self.assertTrue(
            {
                "bom_id",
                "source_bom_item_id",
                "material_item_code",
                "color",
                "part",
                "qty_per_piece",
                "loss_rate",
                "uom",
                "is_alternative",
                "replace_group",
            }.issubset(sample_item_columns)
        )

        sample_operation_columns = {row["name"] for row in inspector.get_columns("ly_sample_material_bom_operation")}
        self.assertTrue({"bom_id", "company", "operation", "idempotency_key", "request_hash", "response_json"}.issubset(sample_operation_columns))

        style_indexes = {row["name"]: row for row in inspector.get_indexes("ly_apparel_bom_write_operation")}
        self.assertTrue(style_indexes["uk_ly_apparel_bom_write_operation_idem"]["unique"])
        self.assertIn("idx_ly_apparel_bom_write_operation_bom", style_indexes)

        sample_indexes = {row["name"]: row for row in inspector.get_indexes("ly_sample_material_bom")}
        self.assertTrue(sample_indexes["uk_ly_sample_material_bom_order"]["unique"])
        self.assertIn("idx_ly_sample_material_bom_style", sample_indexes)

        sample_item_indexes = {row["name"]: row for row in inspector.get_indexes("ly_sample_material_bom_item")}
        self.assertIn("idx_ly_sample_material_bom_item_bom", sample_item_indexes)
        self.assertIn("idx_ly_sample_material_bom_item_material", sample_item_indexes)

        sample_operation_indexes = {row["name"]: row for row in inspector.get_indexes("ly_sample_material_bom_operation")}
        self.assertTrue(sample_operation_indexes["uk_ly_sample_material_bom_operation_idem"]["unique"])
        self.assertIn("idx_ly_sample_material_bom_operation_bom", sample_operation_indexes)

    def test_upgrade_is_idempotent_and_downgrade_removes_added_objects(self) -> None:
        self._run_upgrade()
        self._run_upgrade()
        self.assertIn("ly_sample_material_bom", set(inspect(self.engine).get_table_names()))

        self._run_downgrade()
        inspector = inspect(self.engine)
        self.assertNotIn("ly_apparel_bom_write_operation", set(inspector.get_table_names()))
        self.assertNotIn("ly_sample_material_bom", set(inspector.get_table_names()))
        self.assertNotIn("part", {row["name"] for row in inspector.get_columns("ly_apparel_bom_item")})

    def test_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_071a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)
