"""Tests for subcontract profit-scope bridge fields/backfill (TASK-005F2)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_codes import SUBCONTRACT_SCOPE_BLOCKED
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.schemas.subcontract import InspectRequest
from app.schemas.subcontract import SubcontractCreateRequest
from app.services.subcontract_profit_scope_backfill_service import SubcontractProfitScopeBackfillService
from app.services.subcontract_service import SubcontractService
from app.services.audit_service import AuditService
from migrations.versions import task_002c_subcontract_company_and_schema as migration_002c
from migrations.versions import task_002f_inspection_detail_and_idempotency as migration_002f
from migrations.versions import task_002h_subcontract_settlement_export as migration_002h
from migrations.versions import task_005f2_subcontract_profit_scope_bridge as migration_005f2


class SubcontractProfitScopeBridgeMigrationTest(unittest.TestCase):
    """Validate TASK-005F2 migration columns/indexes and idempotency."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _run_upgrade(engine, migration_module) -> None:
        with engine.begin() as conn:
            context = MigrationContext.configure(conn)
            operations = Operations(context)
            previous_op = migration_module.op
            migration_module.op = operations
            try:
                migration_module.upgrade()
            finally:
                migration_module.op = previous_op

    def _run_chain_to_f2(self) -> None:
        self._run_upgrade(self.engine, migration_002c)
        self._run_upgrade(self.engine, migration_002f)
        self._run_upgrade(self.engine, migration_002h)
        self._run_upgrade(self.engine, migration_005f2)

    def test_task_005f2_adds_bridge_columns_and_indexes(self) -> None:
        self._run_chain_to_f2()
        inspector = inspect(self.engine)

        order_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_order")}
        self.assertTrue(
            {
                "sales_order",
                "sales_order_item",
                "production_plan_id",
                "work_order",
                "job_card",
                "profit_scope_status",
                "profit_scope_error_code",
                "profit_scope_resolved_at",
            }.issubset(order_columns)
        )

        inspection_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_inspection")}
        self.assertTrue(
            {
                "sales_order",
                "sales_order_item",
                "production_plan_id",
                "work_order",
                "job_card",
                "profit_scope_status",
                "profit_scope_error_code",
                "profit_scope_resolved_at",
            }.issubset(inspection_columns)
        )

        order_indexes = {row["name"] for row in inspector.get_indexes("ly_subcontract_order")}
        self.assertIn("idx_ly_subcontract_profit_scope_order", order_indexes)
        self.assertIn("idx_ly_subcontract_profit_plan", order_indexes)

        inspection_indexes = {row["name"] for row in inspector.get_indexes("ly_subcontract_inspection")}
        self.assertIn("idx_ly_subcontract_inspection_profit_scope", inspection_indexes)

    def test_task_005f2_upgrade_is_idempotent(self) -> None:
        self._run_chain_to_f2()
        self._run_upgrade(self.engine, migration_005f2)
        inspector = inspect(self.engine)
        order_columns = {row["name"] for row in inspector.get_columns("ly_subcontract_order")}
        self.assertIn("profit_scope_status", order_columns)

    def test_task_005f2_profit_scope_default_is_unresolved(self) -> None:
        self._run_chain_to_f2()
        inspector = inspect(self.engine)
        order_columns = {row["name"]: row for row in inspector.get_columns("ly_subcontract_order")}
        inspection_columns = {row["name"]: row for row in inspector.get_columns("ly_subcontract_inspection")}
        self.assertIn("unresolved", str(order_columns["profit_scope_status"].get("default") or "").lower())
        self.assertIn("unresolved", str(inspection_columns["profit_scope_status"].get("default") or "").lower())


class SubcontractProfitScopeBridgeServiceTest(unittest.TestCase):
    """Validate bridge resolution/snapshot copy and backfill semantics."""

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
        ProductionBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyProductionWorkOrderLink).delete()
            session.query(LyProductionPlan).delete()
            session.query(LyBomOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.commit()

            bom = LyApparelBom(
                id=1,
                bom_no="BOM-SUB-001",
                item_code="STYLE-A",
                version_no="V1",
                is_default=True,
                status="active",
                created_by="tester",
                updated_by="tester",
            )
            session.add(bom)
            session.flush()
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=1,
                    process_name="OUT",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("3"),
                    wage_rate=Decimal("3"),
                )
            )
            session.commit()

    def _seed_plan_and_work_order(
        self,
        session,
        *,
        company: str = "COMP-A",
        item_code: str = "STYLE-A",
        sales_order: str = "SO-001",
        bom_id: int = 1,
        plan_no: str = "PLAN-001",
        work_order: str = "WO-001",
    ) -> LyProductionPlan:
        plan = LyProductionPlan(
            plan_no=plan_no,
            company=company,
            sales_order=sales_order,
            sales_order_item=f"{sales_order}-1",
            customer="CUST-1",
            item_code=item_code,
            bom_id=bom_id,
            bom_version="V1",
            planned_qty=Decimal("10"),
            status="planned",
            idempotency_key=f"idem-{plan_no}",
            request_hash=f"hash-{plan_no}",
            created_by="tester",
        )
        session.add(plan)
        session.flush()
        session.add(
            LyProductionWorkOrderLink(
                plan_id=int(plan.id),
                work_order=work_order,
                erpnext_docstatus=1,
                erpnext_status="Submitted",
                sync_status="succeeded",
                created_by="tester",
            )
        )
        session.flush()
        return plan

    def test_create_order_without_bridge_defaults_unresolved(self) -> None:
        with self.SessionLocal() as session:
            service = SubcontractService(session=session)
            created = service.create_order(
                payload=SubcontractCreateRequest(
                    supplier="SUP-A",
                    item_code="STYLE-A",
                    company="COMP-A",
                    bom_id=1,
                    planned_qty=Decimal("10"),
                    process_name="OUT",
                ),
                operator="tester",
            )
            session.commit()

            row = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == created.name)
                .one()
            )
            self.assertEqual(str(row.profit_scope_status), "unresolved")
            self.assertEqual(str(row.profit_scope_error_code), "SUBCONTRACT_SCOPE_UNTRUSTED")
            self.assertIsNone(row.sales_order)
            self.assertIsNone(row.work_order)

    def test_create_order_with_valid_bridge_marks_ready(self) -> None:
        with self.SessionLocal() as session:
            plan = self._seed_plan_and_work_order(session)
            service = SubcontractService(session=session)
            created = service.create_order(
                payload=SubcontractCreateRequest(
                    supplier="SUP-A",
                    item_code="STYLE-A",
                    company="COMP-A",
                    bom_id=1,
                    planned_qty=Decimal("10"),
                    process_name="OUT",
                    sales_order="SO-001",
                    sales_order_item="SO-001-1",
                    production_plan_id=int(plan.id),
                    work_order="WO-001",
                ),
                operator="tester",
            )
            session.commit()

            row = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == created.name)
                .one()
            )
            self.assertEqual(str(row.profit_scope_status), "ready")
            self.assertIsNone(row.profit_scope_error_code)
            self.assertEqual(str(row.sales_order), "SO-001")
            self.assertEqual(str(row.work_order), "WO-001")
            self.assertEqual(int(row.production_plan_id), int(plan.id))

    def test_create_order_cross_company_plan_blocked_and_not_persisted(self) -> None:
        with self.SessionLocal() as session:
            plan = self._seed_plan_and_work_order(session, company="COMP-B", plan_no="PLAN-X", work_order="WO-X")
            service = SubcontractService(session=session)
            with self.assertRaises(BusinessException) as ctx:
                service.create_order(
                    payload=SubcontractCreateRequest(
                        supplier="SUP-A",
                        item_code="STYLE-A",
                        company="COMP-A",
                        bom_id=1,
                        planned_qty=Decimal("10"),
                        process_name="OUT",
                        production_plan_id=int(plan.id),
                    ),
                    operator="tester",
                )
            self.assertEqual(ctx.exception.code, SUBCONTRACT_SCOPE_BLOCKED)
            session.rollback()
            self.assertEqual(session.query(LySubcontractOrder).count(), 0)

    def test_inspection_copies_order_scope_snapshot_fields(self) -> None:
        with self.SessionLocal() as session:
            plan = self._seed_plan_and_work_order(session, plan_no="PLAN-I", work_order="WO-I")
            service = SubcontractService(session=session)
            created = service.create_order(
                payload=SubcontractCreateRequest(
                    supplier="SUP-A",
                    item_code="STYLE-A",
                    company="COMP-A",
                    bom_id=1,
                    planned_qty=Decimal("10"),
                    process_name="OUT",
                    sales_order="SO-001",
                    sales_order_item="SO-001-1",
                    production_plan_id=int(plan.id),
                    work_order="WO-I",
                ),
                operator="tester",
            )
            order = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == created.name)
                .one()
            )
            order.status = "waiting_inspection"
            order.settlement_status = "unsettled"
            session.add(
                LySubcontractReceipt(
                    id=1,
                    subcontract_id=int(order.id),
                    company="COMP-A",
                    receipt_batch_no="RB-001",
                    receipt_warehouse="WIP-WH",
                    item_code="STYLE-A",
                    color=None,
                    size=None,
                    batch_no=None,
                    uom="Nos",
                    received_qty=Decimal("10"),
                    sync_status="succeeded",
                    sync_error_code=None,
                    idempotency_key="idem-rb-001",
                    payload_hash="hash-rb-001",
                    received_by="tester",
                    received_at=datetime.utcnow(),
                    stock_entry_name="STE-001",
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                )
            )
            session.flush()

            service.inspect(
                order_id=int(order.id),
                payload=InspectRequest(
                    receipt_batch_no="RB-001",
                    idempotency_key="idem-inspect-001",
                    inspected_qty=Decimal("5"),
                    rejected_qty=Decimal("0"),
                    deduction_amount_per_piece=Decimal("0"),
                ),
                operator="tester",
            )
            session.commit()

            inspection = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == int(order.id))
                .order_by(LySubcontractInspection.id.desc())
                .first()
            )
            self.assertIsNotNone(inspection)
            self.assertEqual(str(inspection.sales_order), "SO-001")
            self.assertEqual(str(inspection.work_order), "WO-I")
            self.assertEqual(int(inspection.production_plan_id), int(plan.id))
            self.assertEqual(str(inspection.profit_scope_status), "ready")

    def test_backfill_dry_run_is_read_only_even_after_commit(self) -> None:
        with self.SessionLocal() as session:
            self._seed_plan_and_work_order(session, plan_no="PLAN-DRY", work_order="WO-DRY")
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SC-DRY-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="draft",
                settlement_status="unsettled",
                resource_scope_status="ready",
                sales_order=None,
                production_plan_id=None,
                work_order=None,
                profit_scope_status="unresolved",
                profit_scope_error_code="SUBCONTRACT_SCOPE_UNTRUSTED",
            )
            session.add(order)
            session.flush()
            inspection = LySubcontractInspection(
                id=1,
                subcontract_id=int(order.id),
                company="COMP-A",
                inspection_no="INSP-DRY",
                receipt_batch_no="RB-DRY",
                item_code="STYLE-A",
                inspected_qty=Decimal("1"),
                accepted_qty=Decimal("1"),
                rejected_qty=Decimal("0"),
                rejected_rate=Decimal("0"),
                subcontract_rate=Decimal("3"),
                gross_amount=Decimal("3"),
                deduction_amount_per_piece=Decimal("0"),
                deduction_amount=Decimal("0"),
                net_amount=Decimal("3"),
                settlement_status="unsettled",
                status="inspected",
                profit_scope_status="unresolved",
                profit_scope_error_code="SUBCONTRACT_SCOPE_UNTRUSTED",
            )
            session.add(inspection)
            session.commit()

            service = SubcontractProfitScopeBackfillService(session=session)
            report = service.backfill(dry_run=True, operator="tester")
            self.assertEqual(report.total_scanned, 1)
            self.assertEqual(report.updated_count, 0)
            session.commit()

            refreshed_order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == int(order.id)).one()
            refreshed_insp = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id == int(inspection.id))
                .one()
            )
            self.assertEqual(str(refreshed_order.profit_scope_status), "unresolved")
            self.assertIsNone(refreshed_order.sales_order)
            self.assertIsNone(refreshed_order.work_order)
            self.assertIsNone(refreshed_insp.sales_order)
            self.assertIsNone(refreshed_insp.work_order)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 0)

    def test_backfill_execute_sets_ready_on_unique_bridge(self) -> None:
        with self.SessionLocal() as session:
            self._seed_plan_and_work_order(session, plan_no="PLAN-EXEC", work_order="WO-EXEC")
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SC-EXEC-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="draft",
                settlement_status="unsettled",
                resource_scope_status="ready",
                sales_order=None,
                production_plan_id=None,
                work_order=None,
                profit_scope_status="unresolved",
                profit_scope_error_code="SUBCONTRACT_SCOPE_UNTRUSTED",
            )
            session.add(order)
            session.commit()

            service = SubcontractProfitScopeBackfillService(session=session)
            report = service.execute(operator="tester")
            self.assertEqual(report.total_scanned, 1)
            self.assertGreaterEqual(report.updated_count, 1)
            session.commit()

            refreshed_order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == int(order.id)).one()
            self.assertEqual(str(refreshed_order.profit_scope_status), "ready")
            self.assertEqual(str(refreshed_order.sales_order), "SO-001")
            self.assertEqual(str(refreshed_order.work_order), "WO-EXEC")
            self.assertIsNone(refreshed_order.profit_scope_error_code)
            audit_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:profit_scope_backfill",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(audit_row)
            assert audit_row is not None
            self.assertEqual(audit_row.result, "success")
            self.assertEqual(audit_row.operator, "tester")

    def test_backfill_execute_keeps_unresolved_on_ambiguous_or_untrusted(self) -> None:
        with self.SessionLocal() as session:
            self._seed_plan_and_work_order(session, plan_no="PLAN-A-1", work_order="WO-A-1")
            self._seed_plan_and_work_order(session, plan_no="PLAN-A-2", work_order="WO-A-2")

            ambiguous = LySubcontractOrder(
                id=1,
                subcontract_no="SC-AMB-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="draft",
                settlement_status="unsettled",
                resource_scope_status="ready",
                profit_scope_status="unresolved",
            )
            untrusted = LySubcontractOrder(
                id=2,
                subcontract_no="SC-UNTRUST-001",
                supplier="SUP-A",
                item_code="STYLE-X",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="draft",
                settlement_status="unsettled",
                resource_scope_status="ready",
                profit_scope_status="unresolved",
            )
            session.add_all([ambiguous, untrusted])
            session.commit()

            service = SubcontractProfitScopeBackfillService(session=session)
            report = service.backfill(dry_run=False, operator="tester")
            self.assertEqual(report.total_scanned, 2)
            session.commit()

            row_amb = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == "SC-AMB-001")
                .one()
            )
            row_untrusted = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == "SC-UNTRUST-001")
                .one()
            )
            self.assertEqual(str(row_amb.profit_scope_status), "unresolved")
            self.assertEqual(str(row_amb.profit_scope_error_code), "SUBCONTRACT_SCOPE_AMBIGUOUS")
            self.assertEqual(str(row_untrusted.profit_scope_status), "unresolved")
            self.assertEqual(str(row_untrusted.profit_scope_error_code), "SUBCONTRACT_SCOPE_UNTRUSTED")

    def test_backfill_execute_audit_failure_rolls_back_business_updates(self) -> None:
        with self.SessionLocal() as session:
            self._seed_plan_and_work_order(session, plan_no="PLAN-AUDIT-FAIL", work_order="WO-AUDIT-FAIL")
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SC-AUDIT-FAIL-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="draft",
                settlement_status="unsettled",
                resource_scope_status="ready",
                sales_order=None,
                production_plan_id=None,
                work_order=None,
                profit_scope_status="unresolved",
                profit_scope_error_code="SUBCONTRACT_SCOPE_UNTRUSTED",
            )
            session.add(order)
            session.commit()

            service = SubcontractProfitScopeBackfillService(session=session)
            with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
                with self.assertRaises(AuditWriteFailed):
                    service.execute(operator="tester")

            session.commit()
            refreshed_order = (
                session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == "SC-AUDIT-FAIL-001")
                .one()
            )
            self.assertEqual(str(refreshed_order.profit_scope_status), "unresolved")
            self.assertIsNone(refreshed_order.sales_order)
            self.assertIsNone(refreshed_order.work_order)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 0)


if __name__ == "__main__":
    unittest.main()
