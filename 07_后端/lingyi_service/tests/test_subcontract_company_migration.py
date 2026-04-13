"""Company backfill migration tests for subcontract module (TASK-002C)."""

from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_codes import SUBCONTRACT_COMPANY_AMBIGUOUS
from app.core.error_codes import SUBCONTRACT_COMPANY_UNRESOLVED
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceUnavailableError
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.services.subcontract_migration_service import SubcontractMigrationService
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.subcontract_service import SubcontractService
from migrations.versions import task_002c_subcontract_company_and_schema as migration_002c
from migrations.versions import task_002f_inspection_detail_and_idempotency as migration_002f


class SubcontractAlembicMigrationChainTest(unittest.TestCase):
    """Validate TASK-002C migration can bootstrap subcontract schema from empty DB."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def _run_task_002c_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_002c.op
            migration_002c.op = operations
            try:
                migration_002c.upgrade()
            finally:
                migration_002c.op = previous_op

    def _run_task_002f_upgrade(self) -> None:
        with self.engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_002f.op
            migration_002f.op = operations
            try:
                migration_002f.upgrade()
            finally:
                migration_002f.op = previous_op

    def _run_head_upgrade(self) -> None:
        self._run_task_002c_upgrade()
        self._run_task_002f_upgrade()

    def test_alembic_migration_chain_creates_subcontract_base_tables_from_empty_database(self) -> None:
        self._run_head_upgrade()
        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        self.assertIn("ly_subcontract_order", tables)
        self.assertIn("ly_subcontract_material", tables)
        self.assertIn("ly_subcontract_receipt", tables)
        self.assertIn("ly_subcontract_status_log", tables)

    def test_alembic_migration_chain_adds_task_002c_company_columns_from_empty_database(self) -> None:
        self._run_head_upgrade()
        inspector = inspect(self.engine)
        order_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_order")}
        self.assertIn("company", order_columns)
        self.assertIn("resource_scope_status", order_columns)
        self.assertIn("scope_error_code", order_columns)

        material_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_material")}
        receipt_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_receipt")}
        status_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_status_log")}
        self.assertIn("company", material_columns)
        self.assertIn("company", receipt_columns)
        self.assertIn("company", status_columns)

    def test_task_002c_migration_does_not_depend_on_metadata_create_all(self) -> None:
        source = Path(migration_002c.__file__).read_text(encoding="utf-8")
        self.assertNotIn("metadata.create_all", source)

    def test_task_002c_migration_is_idempotent_when_tables_already_exist(self) -> None:
        self._run_task_002c_upgrade()
        self._run_task_002c_upgrade()
        inspector = inspect(self.engine)
        order_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_order")}
        self.assertIn("company", order_columns)

    def test_task_002f_migration_adds_inspection_columns_to_existing_task_002c_database(self) -> None:
        self._run_task_002c_upgrade()
        self._run_task_002f_upgrade()
        inspector = inspect(self.engine)
        columns = {row["name"] for row in inspector.get_columns("ly_subcontract_inspection")}
        self.assertIn("inspection_no", columns)
        self.assertIn("receipt_batch_no", columns)
        self.assertIn("deduction_amount_per_piece", columns)
        self.assertIn("idempotency_key", columns)
        self.assertIn("payload_hash", columns)
        index_names = {row["name"] for row in inspector.get_indexes("ly_subcontract_inspection")}
        self.assertIn("idx_ly_subcontract_inspection_batch", index_names)
        self.assertIn("uk_ly_subcontract_inspection_idempotency", index_names)

    def test_alembic_upgrade_head_from_empty_database_includes_inspection_columns(self) -> None:
        self._run_head_upgrade()
        inspector = inspect(self.engine)
        columns = {row["name"] for row in inspector.get_columns("ly_subcontract_inspection")}
        self.assertIn("inspection_no", columns)
        self.assertIn("receipt_batch_no", columns)
        self.assertIn("inspected_by", columns)
        self.assertIn("inspected_at", columns)
        self.assertIn("remark", columns)


class SubcontractCompanyMigrationTest(unittest.TestCase):
    """Verify TASK-002C local company backfill semantics."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        BomBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyApparelBom).delete()
            session.commit()
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-SC-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

    def test_backfill_company_from_unique_candidate_success(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=1,
                        subcontract_no="SC-001",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=2,
                        subcontract_no="SC-002",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("80"),
                        status="draft",
                    ),
                ]
            )
            session.commit()

            service = SubcontractService(session=session)
            report = service.backfill_company_scope(dry_run=False, operator="tester")
            session.commit()

            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 1).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.company, "COMP-A")
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertIsNone(row.scope_error_code)
            self.assertEqual(report.total_scanned, 1)
            self.assertEqual(report.backfilled_count, 1)

    def test_backfill_company_ambiguous_fails_closed(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=10,
                        subcontract_no="SC-010",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=11,
                        subcontract_no="SC-011",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=12,
                        subcontract_no="SC-012",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-B",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            report = service.backfill_company_scope(dry_run=False, operator="tester")
            session.commit()

            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 10).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "blocked_scope")
            self.assertEqual(row.scope_error_code, SUBCONTRACT_COMPANY_AMBIGUOUS)
            self.assertEqual(report.ambiguous_count, 1)
            self.assertEqual(report.blocked_count, 1)

    def test_backfill_company_unresolved_fails_closed(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=20,
                    subcontract_no="SC-020",
                    supplier="SUP-Z",
                    item_code="ITEM-Z",
                    company=None,
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("20"),
                    status="draft",
                )
            )
            session.commit()
            with patch.object(ERPNextJobCardAdapter, "get_item", return_value=None):
                service = SubcontractService(session=session)
                report = service.backfill_company_scope(dry_run=False, operator="tester")
                session.commit()

            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 20).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "blocked_scope")
            self.assertEqual(row.scope_error_code, SUBCONTRACT_COMPANY_UNRESOLVED)
            self.assertEqual(report.unresolved_count, 1)

    def test_backfill_erpnext_item_unavailable_fails_closed(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=30,
                    subcontract_no="SC-030",
                    supplier="SUP-Z",
                    item_code="ITEM-Z",
                    company=None,
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("20"),
                    status="draft",
                )
            )
            session.commit()
            service = SubcontractService(session=session)
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("erpnext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_company_scope(dry_run=False, operator="tester")
            session.rollback()
            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 30).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertIsNone(row.scope_error_code)

    def test_backfill_dry_run_is_read_only_even_if_caller_commits(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=40,
                        subcontract_no="SC-040",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=41,
                        subcontract_no="SC-041",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("80"),
                        status="draft",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            report = service.backfill_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)
            session.commit()
            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 40).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertEqual(report.backfilled_count, 1)

    def test_child_rows_company_derived_from_order_company(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=50,
                        subcontract_no="SC-050",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=51,
                        subcontract_no="SC-051",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("80"),
                        status="draft",
                    ),
                    LySubcontractMaterial(
                        id=500,
                        subcontract_id=50,
                        company=None,
                        material_item_code="MAT-A",
                        required_qty=Decimal("10"),
                        issued_qty=Decimal("10"),
                        stock_entry_name="N/A",
                    ),
                    LySubcontractReceipt(
                        id=501,
                        subcontract_id=50,
                        company=None,
                        received_qty=Decimal("10"),
                        inspected_qty=Decimal("10"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("10"),
                        inspect_status="pending",
                    ),
                    LySubcontractStatusLog(
                        id=502,
                        subcontract_id=50,
                        company=None,
                        from_status="draft",
                        to_status="draft",
                        operator="seed",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            service.backfill_company_scope(dry_run=False, operator="tester")
            session.commit()

            material = session.query(LySubcontractMaterial).filter(LySubcontractMaterial.id == 500).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id == 501).first()
            status_log = session.query(LySubcontractStatusLog).filter(LySubcontractStatusLog.id == 502).first()
            self.assertIsNotNone(material)
            self.assertIsNotNone(receipt)
            self.assertIsNotNone(status_log)
            self.assertEqual(material.company, "COMP-A")
            self.assertEqual(receipt.company, "COMP-A")
            self.assertEqual(status_log.company, "COMP-A")

    def test_backfill_child_update_write_failed_rolls_back_dirty_session(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=60,
                        subcontract_no="SC-060",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=61,
                        subcontract_no="SC-061",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("90"),
                        status="draft",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            with patch.object(
                SubcontractMigrationService,
                "_propagate_company_to_children",
                side_effect=DatabaseWriteFailed(),
            ):
                with self.assertRaises(DatabaseWriteFailed):
                    service.backfill_company_scope(dry_run=False, operator="tester")

            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

            session.commit()
            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 60).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertIsNone(row.scope_error_code)

    def test_backfill_flush_write_failed_rolls_back_dirty_session(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=70,
                        subcontract_no="SC-070",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=71,
                        subcontract_no="SC-071",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("85"),
                        status="draft",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            with patch.object(session, "flush", side_effect=SQLAlchemyError("flush failed")):
                with self.assertRaises(DatabaseWriteFailed):
                    service.backfill_company_scope(dry_run=False, operator="tester")

            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

            session.commit()
            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 70).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertIsNone(row.scope_error_code)

    def test_backfill_write_failed_caller_commit_does_not_persist_partial_changes(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LySubcontractOrder(
                        id=80,
                        subcontract_no="SC-080",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company=None,
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="draft",
                    ),
                    LySubcontractOrder(
                        id=81,
                        subcontract_no="SC-081",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("60"),
                        status="draft",
                    ),
                ]
            )
            session.commit()
            service = SubcontractService(session=session)
            with patch.object(
                SubcontractMigrationService,
                "_propagate_company_to_children",
                side_effect=DatabaseWriteFailed(),
            ):
                with self.assertRaises(DatabaseWriteFailed):
                    service.backfill_company_scope(dry_run=False, operator="tester")

            session.commit()
            row = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 80).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.company)
            self.assertEqual(row.resource_scope_status, "ready")
            self.assertIsNone(row.scope_error_code)


if __name__ == "__main__":
    unittest.main()
