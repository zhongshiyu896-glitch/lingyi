"""Calculation rule tests for style profit snapshot service (TASK-005D)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.services.style_profit_service import StyleProfitService


class StyleProfitSnapshotCalculationTest(unittest.TestCase):
    """Validate revenue and cost formulas in immutable snapshot service."""

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
        StyleProfitBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.service = StyleProfitService()
        with self.SessionLocal() as session:
            session.query(LyStyleProfitSourceMap).delete()
            session.query(LyStyleProfitDetail).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.commit()

    def _request(self, *, revenue_mode: str = "actual_first", include_provisional: bool = False) -> StyleProfitSnapshotCreateRequest:
        return StyleProfitSnapshotCreateRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-200",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode=revenue_mode,
            include_provisional_subcontract=include_provisional,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key=f"idem-{revenue_mode}-{int(include_provisional)}",
            sales_invoice_rows=[
                {
                    "name": "SINV-200",
                    "line_id": "SINV-200-1",
                    "company": "COMP-A",
                    "sales_order": "SO-200",
                    "item_code": "STYLE-A",
                    "qty": "10",
                    "rate": "20",
                    "amount": "200",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            sales_order_rows=[
                {
                    "name": "SO-200",
                    "line_id": "SO-200-1",
                    "company": "COMP-A",
                    "sales_order": "SO-200",
                    "item_code": "STYLE-A",
                    "qty": "10",
                    "rate": "18",
                    "amount": "180",
                    "docstatus": 1,
                    "status": "To Deliver and Bill",
                }
            ],
            bom_material_rows=[{"item_code": "MAT-A", "required_qty": "4", "item_price": "5"}],
            bom_operation_rows=[{"operation": "Sew", "bom_operation_rate": "2", "planned_qty": "10"}],
            stock_ledger_rows=[
                {
                    "name": "SLE-200",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-200",
                    "company": "COMP-A",
                    "sales_order": "SO-200",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-90.5",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            purchase_receipt_rows=[
                {
                    "name": "PRE-200",
                    "voucher_type": "Purchase Receipt",
                    "voucher_no": "PRE-200",
                    "company": "COMP-A",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-999",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            workshop_ticket_rows=[
                {
                    "ticket_no": "T-200",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "status": "submitted",
                    "register_qty": "9",
                    "reversal_qty": "3",
                    "wage_rate_snapshot": "4",
                }
            ],
            subcontract_rows=[
                {
                    "statement_no": "SETT-200",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "settlement_locked_net_amount": "31",
                    "provisional_inspection_net_amount": "12",
                }
            ],
            allowed_material_item_codes=["MAT-A"],
        )

    def test_actual_first_prefers_sales_invoice(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(revenue_mode="actual_first"), operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_status, "actual")
            self.assertEqual(row.actual_revenue_amount, Decimal("200"))
            self.assertEqual(row.estimated_revenue_amount, Decimal("0"))
            self.assertEqual(row.revenue_amount, Decimal("200"))

    def test_actual_first_falls_back_to_sales_order_without_invoice(self) -> None:
        request = self._request(revenue_mode="actual_first")
        request.sales_invoice_rows = []
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_status, "estimated")
            self.assertEqual(row.estimated_revenue_amount, Decimal("180"))
            self.assertEqual(row.revenue_amount, Decimal("180"))

    def test_actual_only_without_invoice_is_incomplete_with_unresolved(self) -> None:
        request = self._request(revenue_mode="actual_only")
        request.sales_invoice_rows = []
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_amount, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreaterEqual(row.unresolved_count, 1)
            unresolved_revenue_detail = (
                session.query(LyStyleProfitDetail)
                .filter(
                    LyStyleProfitDetail.snapshot_id == result.snapshot_id,
                    LyStyleProfitDetail.cost_type == "unresolved",
                    LyStyleProfitDetail.source_type == "Sales Invoice",
                )
                .count()
            )
            self.assertGreaterEqual(unresolved_revenue_detail, 1)
            unresolved_revenue_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Sales Invoice",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                )
                .count()
            )
            self.assertGreaterEqual(unresolved_revenue_source, 1)

    def test_draft_cancelled_unknown_revenue_rows_not_included(self) -> None:
        request = self._request(revenue_mode="actual_first")
        request.sales_invoice_rows = [
            {"name": "SINV-DRAFT", "line_id": "1", "docstatus": 0, "status": "Draft", "item_code": "STYLE-A"},
            {"name": "SINV-CAN", "line_id": "2", "docstatus": 2, "status": "Cancelled", "item_code": "STYLE-A"},
            {"name": "SINV-UNK", "line_id": "3", "status": "Unknown", "item_code": "STYLE-A"},
        ]
        request.sales_order_rows = []
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_amount, Decimal("0"))
            self.assertEqual(row.revenue_status, "unresolved")
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            unresolved_revenue_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.source_doctype == "Revenue Source",
                )
                .count()
            )
            self.assertGreaterEqual(unresolved_revenue_source, 1)

    def test_actual_material_uses_abs_stock_value_difference_and_purchase_receipt_not_counted(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(), operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_material_cost, Decimal("90.5"))
            pr_included = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Purchase Receipt",
                    LyStyleProfitSourceMap.include_in_profit.is_(True),
                )
                .count()
            )
            self.assertEqual(pr_included, 0)

    def test_workshop_cost_uses_register_minus_reversal_times_wage_snapshot(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(), operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("24"))

    def test_workshop_company_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-COMP-MISMATCH",
                "company": "COMP-B",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-company-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-COMP-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "company_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_workshop_item_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-ITEM-MISMATCH",
                "company": "COMP-A",
                "item_code": "STYLE-B",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-item-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-ITEM-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "item_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_workshop_sales_order_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-ORDER-MISMATCH",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-999",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-order-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-ORDER-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "sales_order_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_workshop_missing_sales_order_without_bridge_is_unresolved(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-NO-SCOPE-BRIDGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-scope-unresolved"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-NO-SCOPE-BRIDGE",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.unresolved_reason == "unable_to_link_profit_scope",
                )
                .count(),
                1,
            )

    def test_workshop_missing_company_even_with_sales_order_is_unresolved(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-MISS-COMPANY",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-missing-company"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-MISS-COMPANY",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "company_scope_missing",
                )
                .count(),
                1,
            )

    def test_workshop_missing_item_even_with_sales_order_is_unresolved(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-MISS-ITEM",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-missing-item"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-MISS-ITEM",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "item_scope_missing",
                )
                .count(),
                1,
            )

    def test_workshop_missing_sales_order_with_work_order_bridge_is_unresolved_without_verified_bridge(self) -> None:
        request = self._request()
        request.work_order = "WO-200"
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-WO-BRIDGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "work_order": "WO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.idempotency_key = "idem-workshop-workorder-bridge"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "T-WO-BRIDGE",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "unable_to_link_profit_scope",
                )
                .count(),
                1,
            )

    def test_subcontract_prefers_settlement_locked_amount(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(include_provisional=True), operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("31"))

    def test_subcontract_company_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "statement_no": "SETT-COMP-MISMATCH",
                "company": "COMP-B",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-company-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-COMP-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "company_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_subcontract_item_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "statement_no": "SETT-ITEM-MISMATCH",
                "company": "COMP-A",
                "item_code": "STYLE-B",
                "sales_order": "SO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-item-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-ITEM-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "item_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_subcontract_sales_order_mismatch_is_excluded_and_not_counted(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "statement_no": "SETT-ORDER-MISMATCH",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-999",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-order-mismatch"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-ORDER-MISMATCH",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                    LyStyleProfitSourceMap.unresolved_reason == "sales_order_scope_mismatch",
                )
                .count(),
                1,
            )

    def test_subcontract_missing_sales_order_without_bridge_is_unresolved(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "inspection_no": "INSP-NO-SCOPE-BRIDGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "provisional_inspection_net_amount": "12",
            }
        ]
        request.idempotency_key = "idem-subcontract-scope-unresolved"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "INSP-NO-SCOPE-BRIDGE",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.unresolved_reason == "unable_to_link_profit_scope",
                )
                .count(),
                1,
            )

    def test_subcontract_missing_company_even_with_sales_order_is_unresolved(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "statement_no": "SETT-MISS-COMPANY",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-missing-company"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-MISS-COMPANY",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "company_scope_missing",
                )
                .count(),
                1,
            )

    def test_subcontract_missing_item_even_with_sales_order_is_unresolved(self) -> None:
        request = self._request(include_provisional=True)
        request.subcontract_rows = [
            {
                "statement_no": "SETT-MISS-ITEM",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-missing-item"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-MISS-ITEM",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "item_scope_missing",
                )
                .count(),
                1,
            )

    def test_subcontract_missing_sales_order_with_work_order_bridge_is_unresolved_without_verified_bridge(self) -> None:
        request = self._request(include_provisional=True)
        request.work_order = "WO-200"
        request.subcontract_rows = [
            {
                "statement_no": "SETT-WO-BRIDGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "work_order": "WO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-subcontract-workorder-bridge"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-WO-BRIDGE",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                    LyStyleProfitSourceMap.unresolved_reason == "unable_to_link_profit_scope",
                )
                .count(),
                1,
            )

    def test_wrong_scope_workshop_and_subcontract_do_not_affect_actual_total_cost(self) -> None:
        request = self._request(include_provisional=True)
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-WRONG-SCOPE",
                "company": "COMP-B",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "9",
                "reversal_qty": "3",
                "wage_rate_snapshot": "4",
            }
        ]
        request.subcontract_rows = [
            {
                "statement_no": "SETT-WRONG-SCOPE",
                "company": "COMP-A",
                "item_code": "STYLE-B",
                "sales_order": "SO-200",
                "settlement_locked_net_amount": "31",
            }
        ]
        request.idempotency_key = "idem-mixed-wrong-scope"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_workshop_cost, Decimal("0"))
            self.assertEqual(row.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(row.actual_total_cost, row.actual_material_cost)

    def test_provisional_subcontract_only_included_when_flag_true(self) -> None:
        request_true = self._request(include_provisional=True)
        request_true.subcontract_rows = [
            {
                "inspection_no": "INSP-1",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "provisional_inspection_net_amount": "19",
            }
        ]
        request_true.idempotency_key = "idem-prov-true"
        request_false = self._request(include_provisional=False)
        request_false.subcontract_rows = [
            {
                "inspection_no": "INSP-2",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "provisional_inspection_net_amount": "19",
            }
        ]
        request_false.idempotency_key = "idem-prov-false"

        with self.SessionLocal() as session:
            true_result = self.service.create_snapshot(session=session, request=request_true, operator="u1")
            false_result = self.service.create_snapshot(session=session, request=request_false, operator="u1")
            row_true = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == true_result.snapshot_id).one()
            row_false = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == false_result.snapshot_id).one()
            self.assertEqual(row_true.actual_subcontract_cost, Decimal("19"))
            self.assertEqual(row_false.actual_subcontract_cost, Decimal("0"))

    def test_overhead_fixed_zero_and_formula_values(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(), operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.allocated_overhead_amount, Decimal("0"))
            self.assertEqual(row.allocation_status, "not_enabled")
            self.assertEqual(row.actual_total_cost, Decimal("145.5"))
            self.assertEqual(row.profit_amount, Decimal("54.5"))
            self.assertEqual(row.profit_rate, Decimal("0.2725"))

    def test_profit_rate_is_none_when_revenue_is_zero(self) -> None:
        request = self._request(revenue_mode="actual_only")
        request.sales_invoice_rows = []
        request.workshop_ticket_rows = []
        request.subcontract_rows = []
        request.stock_ledger_rows = []
        request.idempotency_key = "idem-zero-rate"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_amount, Decimal("0"))
            self.assertIsNone(row.profit_rate)

    def test_source_status_unknown_is_not_included_in_profit(self) -> None:
        request = self._request()
        request.stock_ledger_rows = [
            {
                "name": "SLE-UNKNOWN",
                "voucher_type": "Stock Entry",
                "voucher_no": "STE-UNKNOWN",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "item_code": "MAT-A",
                "stock_value_difference": "-88",
                "status": "Unknown",
            }
        ]
        request.idempotency_key = "idem-unknown-status"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_material_cost, Decimal("0"))
            unknown_included = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "STE-UNKNOWN",
                    LyStyleProfitSourceMap.include_in_profit.is_(True),
                )
                .count()
            )
            self.assertEqual(unknown_included, 0)
            unresolved_unknown = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "STE-UNKNOWN",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                )
                .count()
            )
            self.assertEqual(unresolved_unknown, 1)
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)

    def test_actual_first_without_invoice_and_sales_order_persists_unresolved_revenue(self) -> None:
        request = self._request(revenue_mode="actual_first")
        request.sales_invoice_rows = []
        request.sales_order_rows = []
        request.idempotency_key = "idem-no-revenue-any-source"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_status, "unresolved")
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertGreaterEqual(
                session.query(LyStyleProfitDetail)
                .filter(
                    LyStyleProfitDetail.snapshot_id == result.snapshot_id,
                    LyStyleProfitDetail.cost_type == "unresolved",
                    LyStyleProfitDetail.source_type == "Revenue Source",
                )
                .count(),
                1,
            )

    def test_estimated_only_without_sales_order_persists_unresolved_revenue(self) -> None:
        request = self._request(revenue_mode="estimated_only")
        request.sales_order_rows = []
        request.sales_invoice_rows = []
        request.idempotency_key = "idem-estimated-only-empty"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.revenue_status, "unresolved")
            self.assertEqual(row.snapshot_status, "incomplete")
            self.assertGreater(row.unresolved_count, 0)
            self.assertGreaterEqual(
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Sales Order",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                )
                .count(),
                1,
            )

    def test_sle_missing_docstatus_is_unresolved_and_not_counted(self) -> None:
        request = self._request()
        request.stock_ledger_rows = [
            {
                "name": "SLE-MISS-DOC",
                "voucher_type": "Stock Entry",
                "voucher_no": "STE-MISS-DOC",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "item_code": "MAT-A",
                "stock_value_difference": "-88",
                "status": "Submitted",
            }
        ]
        request.idempotency_key = "idem-sle-miss-doc"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_material_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            unresolved_map = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "STE-MISS-DOC",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                )
                .count()
            )
            self.assertEqual(unresolved_map, 1)

    def test_sle_unable_to_link_scope_is_unresolved_and_not_counted(self) -> None:
        request = self._request()
        request.stock_ledger_rows = [
            {
                "name": "SLE-NO-LINK",
                "voucher_type": "Stock Entry",
                "voucher_no": "STE-NO-LINK",
                "company": "COMP-A",
                "item_code": "MAT-A",
                "stock_value_difference": "-50",
                "docstatus": 1,
                "status": "Submitted",
            }
        ]
        request.allowed_material_item_codes = []
        request.idempotency_key = "idem-sle-no-link"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(row.actual_material_cost, Decimal("0"))
            self.assertEqual(row.snapshot_status, "incomplete")
            unresolved_map = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "STE-NO-LINK",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.unresolved_reason == "unable_to_link_order_or_material_scope",
                )
                .count()
            )
            self.assertEqual(unresolved_map, 1)

    def test_standard_operation_missing_rate_is_unresolved(self) -> None:
        request = self._request()
        request.bom_operation_rows = [{"operation": "Sew", "planned_qty": "10"}]
        request.idempotency_key = "idem-op-rate-missing"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            unresolved_map = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "BOM Operation",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.unresolved_reason == "operation_rate_unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                )
                .count()
            )
            self.assertEqual(unresolved_map, 1)

    def test_workshop_missing_wage_rate_is_unresolved(self) -> None:
        request = self._request()
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-MISS-WAGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "8",
                "reversal_qty": "1",
            }
        ]
        request.idempotency_key = "idem-workshop-rate-missing"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            unresolved_map = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Workshop Ticket",
                    LyStyleProfitSourceMap.source_name == "T-MISS-WAGE",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                    LyStyleProfitSourceMap.unresolved_reason == "workshop_wage_rate_unresolved",
                    LyStyleProfitSourceMap.include_in_profit.is_(False),
                )
                .count()
            )
            self.assertEqual(unresolved_map, 1)

    def test_explicit_zero_rates_are_allowed_when_field_present(self) -> None:
        request = self._request()
        request.bom_operation_rows = [{"operation": "ZeroOp", "bom_operation_rate": "0", "planned_qty": "10"}]
        request.workshop_ticket_rows = [
            {
                "ticket_no": "T-ZERO-WAGE",
                "company": "COMP-A",
                "item_code": "STYLE-A",
                "sales_order": "SO-200",
                "status": "submitted",
                "register_qty": "10",
                "reversal_qty": "2",
                "wage_rate_snapshot": "0",
            }
        ]
        request.idempotency_key = "idem-explicit-zero-rates"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            mapped_op = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "BOM Operation",
                    LyStyleProfitSourceMap.source_name == "ZeroOp",
                    LyStyleProfitSourceMap.mapping_status == "mapped",
                    LyStyleProfitSourceMap.include_in_profit.is_(True),
                )
                .count()
            )
            mapped_workshop = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Workshop Ticket",
                    LyStyleProfitSourceMap.source_name == "T-ZERO-WAGE",
                    LyStyleProfitSourceMap.mapping_status == "mapped",
                    LyStyleProfitSourceMap.include_in_profit.is_(True),
                )
                .count()
            )
            self.assertEqual(mapped_op, 1)
            self.assertEqual(mapped_workshop, 1)

    def test_revenue_source_map_keeps_real_source_status(self) -> None:
        request = self._request(revenue_mode="actual_first")
        request.sales_invoice_rows = [
            {
                "name": "SINV-PAID",
                "line_id": "SINV-PAID-1",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "item_code": "STYLE-A",
                "qty": "10",
                "rate": "20",
                "amount": "200",
                "status": "Paid",
            }
        ]
        request.idempotency_key = "idem-revenue-status-paid"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Sales Invoice",
                    LyStyleProfitSourceMap.source_name == "SINV-PAID",
                )
                .one()
            )
            self.assertEqual(source.source_status, "paid")

    def test_sales_order_revenue_status_keeps_real_status(self) -> None:
        request = self._request(revenue_mode="estimated_only")
        request.sales_invoice_rows = []
        request.sales_order_rows = [
            {
                "name": "SO-TO-BILL",
                "line_id": "SO-TO-BILL-1",
                "company": "COMP-A",
                "sales_order": "SO-200",
                "item_code": "STYLE-A",
                "qty": "10",
                "rate": "18",
                "amount": "180",
                "status": "To Bill",
            }
        ]
        request.idempotency_key = "idem-revenue-status-so"
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_doctype == "Sales Order",
                    LyStyleProfitSourceMap.source_name == "SO-TO-BILL",
                )
                .one()
            )
            self.assertEqual(source.source_status, "to bill")
