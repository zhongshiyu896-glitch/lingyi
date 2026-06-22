"""Migration coverage for material requirement BOM dimension unique key."""

from __future__ import annotations

import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from migrations.versions import task_063b_create_material_purchase_requirements as migration_063b
from migrations.versions import task_091a_add_bom_dimensions_to_material_requirements as migration_091a
from migrations.versions import task_094a_fix_material_purchase_requirement_unique_key as migration_094a


class MaterialPurchaseRequirementUniqueKeyMigrationTest(unittest.TestCase):
    """Validate TASK-094A keeps requirement uniqueness aligned with BOM dimensions."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run(self, migration, action: str = "upgrade") -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration.op
            migration.op = operations
            try:
                getattr(migration, action)()
            finally:
                migration.op = previous_op

    def _bootstrap_to_091a(self) -> None:
        self._run(migration_063b)
        self._run(migration_091a)

    def _bootstrap_to_094a(self) -> None:
        self._bootstrap_to_091a()
        self._run(migration_094a)

    def _insert_requirement(
        self,
        *,
        requirement_no: str,
        bom_item_id: int | None = None,
        bom_color: str | None = None,
        bom_size: str | None = None,
        bom_part: str | None = None,
        material_item_code: str = "MAT-ZIP",
        warehouse: str = "MAIN-WH",
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ly_material_purchase_requirement (
                        company,
                        requirement_no,
                        source_type,
                        source_id,
                        source_no,
                        plan_id,
                        bom_item_id,
                        bom_color,
                        bom_size,
                        bom_part,
                        material_item_code,
                        material_name,
                        warehouse,
                        required_qty,
                        available_qty,
                        net_required_qty,
                        purchased_qty,
                        received_qty,
                        uom,
                        unit_price,
                        status,
                        payload,
                        created_by
                    )
                    VALUES (
                        '默认公司',
                        :requirement_no,
                        'production_plan',
                        '9602',
                        'PP-9602',
                        9602,
                        :bom_item_id,
                        :bom_color,
                        :bom_size,
                        :bom_part,
                        :material_item_code,
                        :material_item_code,
                        :warehouse,
                        10,
                        0,
                        10,
                        0,
                        0,
                        '米',
                        0,
                        'pending',
                        '{}',
                        'migration-test'
                    )
                    """
                ),
                {
                    "requirement_no": requirement_no,
                    "bom_item_id": bom_item_id,
                    "bom_color": bom_color,
                    "bom_size": bom_size,
                    "bom_part": bom_part,
                    "material_item_code": material_item_code,
                    "warehouse": warehouse,
                },
            )

    def _index_names(self) -> set[str]:
        with self.engine.connect() as conn:
            return {
                str(row[1])
                for row in conn.execute(text("PRAGMA index_list('ly_material_purchase_requirement')")).fetchall()
            }

    def test_upgrade_replaces_legacy_constraint_with_bom_dimension_index(self) -> None:
        self._bootstrap_to_094a()

        constraints = inspect(self.engine).get_unique_constraints("ly_material_purchase_requirement")
        self.assertNotIn("uk_ly_material_purchase_req_source_material", {row["name"] for row in constraints})
        self.assertIn("uk_ly_material_purchase_req_source_material", self._index_names())

        self._insert_requirement(requirement_no="REQ-DIM-001", bom_item_id=6001, bom_color="黑", bom_size="M", bom_part="门襟")
        self._insert_requirement(requirement_no="REQ-DIM-002", bom_item_id=6001, bom_color="黑", bom_size="M", bom_part="袖口")
        with self.assertRaises(IntegrityError):
            self._insert_requirement(requirement_no="REQ-DIM-003", bom_item_id=6001, bom_color="黑", bom_size="M", bom_part="袖口")

    def test_upgrade_normalizes_null_dimensions_before_enforcing_uniqueness(self) -> None:
        self._bootstrap_to_094a()

        self._insert_requirement(requirement_no="REQ-NULL-DIM-001")
        with self.assertRaises(IntegrityError):
            self._insert_requirement(requirement_no="REQ-NULL-DIM-002")

    def test_upgrade_refuses_existing_duplicate_bom_dimension_rows(self) -> None:
        self._bootstrap_to_091a()
        self._insert_requirement(requirement_no="REQ-DUP-001")
        self._insert_requirement(requirement_no="REQ-DUP-002")

        with self.assertRaisesRegex(RuntimeError, "BOM dimension key.*duplicate rows exist"):
            self._run(migration_094a)

    def test_downgrade_refuses_rows_that_legacy_key_would_merge(self) -> None:
        self._bootstrap_to_094a()
        self._insert_requirement(requirement_no="REQ-LEGACY-001", bom_item_id=7001, bom_color="黑", bom_size="M", bom_part="门襟")
        self._insert_requirement(requirement_no="REQ-LEGACY-002", bom_item_id=7001, bom_color="黑", bom_size="M", bom_part="袖口")

        with self.assertRaisesRegex(RuntimeError, "legacy key.*duplicate rows exist"):
            self._run(migration_094a, "downgrade")


if __name__ == "__main__":
    unittest.main()
