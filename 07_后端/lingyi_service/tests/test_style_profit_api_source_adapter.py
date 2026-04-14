"""Tests for ERPNextStyleProfitAdapter local-source behavior (TASK-005F)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_codes import STYLE_PROFIT_BOM_REQUIRED
from app.core.exceptions import BusinessException
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import YsWorkshopTicket
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest
from app.services.erpnext_style_profit_adapter import ERPNextStyleProfitAdapter


class ERPNextStyleProfitAdapterTest(unittest.TestCase):
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
        WorkshopBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        # Subcontract models use a dedicated declarative metadata and hold FK to ly_apparel_bom.
        # Mirror BOM table into subcontract metadata so FK resolution works in isolated test DB.
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.selector = StyleProfitSnapshotSelectorRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-001",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            include_provisional_subcontract=False,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key="idem-adapter-001",
            work_order="WO-001",
        )
        with self.SessionLocal() as session:
            session.query(YsWorkshopTicket).delete()
            session.query(LyProductionJobCardLink).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyBomOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.commit()

    def test_load_active_default_bom_rows_success(self) -> None:
        with self.SessionLocal() as session:
            bom = LyApparelBom(
                id=1,
                bom_no="BOM-001",
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
                LyApparelBomItem(
                    id=1,
                    bom_id=int(bom.id),
                    material_item_code="MAT-A",
                    qty_per_piece=Decimal("1.2"),
                    loss_rate=Decimal("0.05"),
                    uom="PCS",
                )
            )
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=int(bom.id),
                    process_name="CUT",
                    sequence_no=1,
                    is_subcontract=False,
                    wage_rate=Decimal("2"),
                )
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            materials, operations, allowed = adapter.load_active_default_bom_rows(
                company="COMP-A",
                item_code="STYLE-A",
                planned_qty=Decimal("10"),
            )

        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0]["material_item_code"], "MAT-A")
        self.assertEqual(materials[0]["bom_required_qty_with_loss"], "12.6")
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["operation"], "CUT")
        self.assertEqual(allowed, ["MAT-A"])

    def test_load_active_default_bom_rows_missing_raises_error(self) -> None:
        with self.SessionLocal() as session:
            adapter = ERPNextStyleProfitAdapter(session=session)
            with self.assertRaises(BusinessException) as ctx:
                adapter.load_active_default_bom_rows(
                    company="COMP-A",
                    item_code="STYLE-A",
                    planned_qty=Decimal("10"),
                )

        self.assertEqual(ctx.exception.code, STYLE_PROFIT_BOM_REQUIRED)

    def test_load_workshop_ticket_rows_with_trusted_scope(self) -> None:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                plan_no="PLAN-001",
                company="COMP-A",
                sales_order="SO-001",
                sales_order_item="SO-001-1",
                customer="CUST-1",
                item_code="STYLE-A",
                bom_id=1,
                bom_version="V1",
                planned_qty=Decimal("10"),
                status="planned",
                idempotency_key="plan-idem-1",
                request_hash="plan-hash-1",
                created_by="tester",
            )
            session.add(plan)
            session.flush()

            session.add(
                LyProductionJobCardLink(
                    plan_id=int(plan.id),
                    work_order="WO-001",
                    job_card="JC-001",
                    company="COMP-A",
                    item_code="STYLE-A",
                    operation="CUT",
                    operation_sequence=1,
                    expected_qty=Decimal("10"),
                    completed_qty=Decimal("5"),
                )
            )
            session.add(
                YsWorkshopTicket(
                    ticket_no="TK-001",
                    ticket_key="TK-KEY-001",
                    job_card="JC-001",
                    work_order="WO-001",
                    bom_id=1,
                    item_code="STYLE-A",
                    employee="EMP-1",
                    process_name="CUT",
                    color=None,
                    size=None,
                    operation_type="register",
                    qty=Decimal("8"),
                    unit_wage=Decimal("1.5"),
                    wage_amount=Decimal("12"),
                    work_date=date(2026, 4, 8),
                    source="manual",
                    source_ref=None,
                    created_by="tester",
                )
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            rows = adapter.load_workshop_ticket_rows(self.selector)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "COMP-A")
        self.assertEqual(rows[0]["item_code"], "STYLE-A")
        self.assertEqual(rows[0]["sales_order"], "SO-001")
        self.assertEqual(rows[0]["register_qty"], "8")
        self.assertEqual(rows[0]["reversal_qty"], "0")

    def test_load_stock_ledger_rows_keeps_missing_status_fields_without_defaults(self) -> None:
        with self.SessionLocal() as session:
            adapter = ERPNextStyleProfitAdapter(session=session)
            adapter.base_url = "https://fake.local"

            def _fake_request_json(**kwargs):
                _ = kwargs
                return {
                    "data": [
                        {
                            "name": "SLE-001",
                            "voucher_type": "Stock Entry",
                            "voucher_no": "STE-001",
                            "item_code": "MAT-A",
                            "company": "COMP-A",
                            "stock_value_difference": "-10",
                        }
                    ]
                }

            adapter._request_json = _fake_request_json  # type: ignore[method-assign]
            rows = adapter.load_stock_ledger_rows(
                self.selector,
                allowed_material_item_codes=["MAT-A"],
            )

        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["docstatus"])
        self.assertIsNone(rows[0]["status"])
        self.assertIsNone(rows[0]["is_cancelled"])

    def test_load_subcontract_rows_returns_candidates_instead_of_silent_empty(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SUB-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="submitted",
                settlement_status="unsettled",
            )
            session.add(order)
            session.flush()
            session.add(
                LySubcontractInspection(
                    id=1,
                    subcontract_id=int(order.id),
                    company="COMP-A",
                    inspection_no="INSP-001",
                    item_code="STYLE-A",
                    inspected_at=datetime(2026, 4, 10, 10, 0, 0),
                    inspected_qty=Decimal("10"),
                    accepted_qty=Decimal("10"),
                    net_amount=Decimal("18"),
                    settlement_status="unsettled",
                    status="submitted",
                )
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            rows = adapter.load_subcontract_rows(self.selector)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subcontract_order"], "SUB-001")
        self.assertEqual(rows[0]["item_code"], "STYLE-A")
        self.assertEqual(rows[0]["company"], "COMP-A")
        self.assertEqual(rows[0]["inspected_at"], "2026-04-10T10:00:00")

    def test_load_subcontract_rows_uses_inspected_at_not_created_at_for_period(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SUB-002",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="submitted",
                settlement_status="unsettled",
                sales_order="SO-001",
                work_order="WO-001",
                profit_scope_status="ready",
            )
            session.add(order)
            session.flush()
            session.add_all(
                [
                    LySubcontractInspection(
                        id=1,
                        subcontract_id=int(order.id),
                        company="COMP-A",
                        inspection_no="INSP-OUT",
                        item_code="STYLE-A",
                        sales_order="SO-001",
                        work_order="WO-001",
                        inspected_at=datetime(2026, 3, 20, 9, 0, 0),
                        created_at=datetime(2026, 4, 12, 10, 0, 0),
                        net_amount=Decimal("8"),
                        settlement_status="unsettled",
                        status="submitted",
                        profit_scope_status="ready",
                    ),
                    LySubcontractInspection(
                        id=2,
                        subcontract_id=int(order.id),
                        company="COMP-A",
                        inspection_no="INSP-IN",
                        item_code="STYLE-A",
                        sales_order="SO-001",
                        work_order="WO-001",
                        inspected_at=datetime(2026, 4, 12, 9, 0, 0),
                        created_at=datetime(2026, 3, 20, 10, 0, 0),
                        net_amount=Decimal("9"),
                        settlement_status="unsettled",
                        status="submitted",
                        profit_scope_status="ready",
                    ),
                ]
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            rows = adapter.load_subcontract_rows(self.selector)

        self.assertEqual([row["inspection_no"] for row in rows], ["INSP-IN"])

    def test_load_subcontract_rows_marks_missing_inspected_at_as_unresolved(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SUB-003",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="submitted",
                settlement_status="unsettled",
                sales_order="SO-001",
                work_order="WO-001",
                profit_scope_status="ready",
            )
            session.add(order)
            session.flush()
            session.add(
                LySubcontractInspection(
                    id=1,
                    subcontract_id=int(order.id),
                    company="COMP-A",
                    inspection_no="INSP-MISS-TIME",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=None,
                    net_amount=Decimal("9"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                )
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            rows = adapter.load_subcontract_rows(self.selector)

        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["inspected_at"])
        self.assertEqual(rows[0]["profit_scope_status"], "unresolved")
        self.assertEqual(rows[0]["profit_scope_error_code"], "SUBCONTRACT_INSPECTED_AT_REQUIRED")

    def test_load_subcontract_rows_filters_work_order_in_database_scope(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SUB-WO-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="submitted",
                settlement_status="unsettled",
                sales_order="SO-001",
                profit_scope_status="ready",
            )
            session.add(order)
            session.flush()
            session.add_all(
                [
                    LySubcontractInspection(
                        id=1,
                        subcontract_id=int(order.id),
                        company="COMP-A",
                        inspection_no="INSP-WO-1",
                        item_code="STYLE-A",
                        sales_order="SO-001",
                        work_order="WO-001",
                        inspected_at=datetime(2026, 4, 10, 10, 0, 0),
                        net_amount=Decimal("9"),
                        settlement_status="unsettled",
                        status="submitted",
                        profit_scope_status="ready",
                    ),
                    LySubcontractInspection(
                        id=2,
                        subcontract_id=int(order.id),
                        company="COMP-A",
                        inspection_no="INSP-WO-2",
                        item_code="STYLE-A",
                        sales_order="SO-001",
                        work_order="WO-002",
                        inspected_at=datetime(2026, 4, 10, 11, 0, 0),
                        net_amount=Decimal("9"),
                        settlement_status="unsettled",
                        status="submitted",
                        profit_scope_status="ready",
                    ),
                ]
            )
            session.commit()

            adapter = ERPNextStyleProfitAdapter(session=session)
            rows = adapter.load_subcontract_rows(self.selector)

        self.assertEqual([row["inspection_no"] for row in rows], ["INSP-WO-1"])
        self.assertEqual(rows[0]["work_order"], "WO-001")

    def test_load_subcontract_rows_missing_inspected_at_uses_diagnostic_limit(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SUB-DIAG-001",
                supplier="SUP-A",
                item_code="STYLE-A",
                company="COMP-A",
                bom_id=1,
                process_name="OUT",
                planned_qty=Decimal("10"),
                subcontract_rate=Decimal("3"),
                status="submitted",
                settlement_status="unsettled",
                sales_order="SO-001",
                work_order="WO-001",
                profit_scope_status="ready",
            )
            session.add(order)
            session.flush()
            for idx in range(1, 5):
                session.add(
                    LySubcontractInspection(
                        id=idx,
                        subcontract_id=int(order.id),
                        company="COMP-A",
                        inspection_no=f"INSP-DIAG-{idx}",
                        item_code="STYLE-A",
                        sales_order="SO-001",
                        work_order="WO-001",
                        inspected_at=None,
                        net_amount=Decimal("9"),
                        settlement_status="unsettled",
                        status="submitted",
                        profit_scope_status="ready",
                    )
                )
            session.commit()

            with patch.dict(os.environ, {"STYLE_PROFIT_SUBCONTRACT_DIAGNOSTIC_LIMIT": "2"}, clear=False):
                adapter = ERPNextStyleProfitAdapter(session=session)
                rows = adapter.load_subcontract_rows(self.selector)

        self.assertEqual(len(rows), 3)
        aggregate_rows = [row for row in rows if row.get("bridge_source") == "diagnostic_aggregate"]
        self.assertEqual(len(aggregate_rows), 1)
        aggregate = aggregate_rows[0]
        self.assertEqual(aggregate.get("profit_scope_error_code"), "SUBCONTRACT_INSPECTED_AT_REQUIRED")
        self.assertEqual(aggregate.get("diagnostic_total_missing_inspected_at"), "4")
        self.assertEqual(aggregate.get("diagnostic_truncated_count"), "2")


if __name__ == "__main__":
    unittest.main()
