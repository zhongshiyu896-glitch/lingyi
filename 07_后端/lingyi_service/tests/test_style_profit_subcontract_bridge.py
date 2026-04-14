"""Subcontract bridge behavior tests for style-profit snapshot service (TASK-005F2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.services.style_profit_service import StyleProfitService


class StyleProfitSubcontractBridgeTest(unittest.TestCase):
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
            session.query(LyStyleProfitSnapshot).delete()
            session.commit()

    def _request(
        self,
        *,
        idempotency_key: str,
        include_provisional_subcontract: bool = False,
        subcontract_rows: list[dict[str, object]] | None = None,
    ) -> StyleProfitSnapshotCreateRequest:
        return StyleProfitSnapshotCreateRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-200",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            include_provisional_subcontract=include_provisional_subcontract,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key=idempotency_key,
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
            sales_order_rows=[],
            bom_material_rows=[{"item_code": "MAT-A", "required_qty": "4", "item_price": "5"}],
            bom_operation_rows=[{"operation": "Sew", "bom_operation_rate": "2", "planned_qty": "10"}],
            stock_ledger_rows=[],
            purchase_receipt_rows=[],
            workshop_ticket_rows=[],
            subcontract_rows=subcontract_rows or [],
            allowed_material_item_codes=["MAT-A"],
            work_order="WO-200",
        )

    def test_ready_subcontract_with_inspection_bridge_is_included(self) -> None:
        request = self._request(
            idempotency_key="idem-sub-bridge-inspection",
            subcontract_rows=[
                {
                    "statement_no": "SETT-200",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "work_order": "WO-200",
                    "bridge_source": "subcontract_inspection",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "settlement_locked_net_amount": "31",
                }
            ],
        )

        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(snapshot.actual_subcontract_cost, Decimal("31"))
            mapped_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-200",
                    LyStyleProfitSourceMap.mapping_status == "mapped",
                )
                .one()
            )
            self.assertEqual(mapped_source.raw_ref.get("bridge_source"), "subcontract_inspection")

    def test_ready_subcontract_with_order_bridge_fallback_is_included(self) -> None:
        request = self._request(
            idempotency_key="idem-sub-bridge-order",
            subcontract_rows=[
                {
                    "statement_no": "SETT-ORDER-200",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "work_order": "WO-200",
                    "bridge_source": "subcontract_order",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "settlement_locked_net_amount": "12.5",
                }
            ],
        )
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(snapshot.actual_subcontract_cost, Decimal("12.5"))
            mapped_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-ORDER-200",
                    LyStyleProfitSourceMap.mapping_status == "mapped",
                )
                .one()
            )
            self.assertEqual(mapped_source.raw_ref.get("bridge_source"), "subcontract_order")

    def test_unresolved_subcontract_scope_is_not_included_and_persisted(self) -> None:
        request = self._request(
            idempotency_key="idem-sub-unresolved",
            subcontract_rows=[
                {
                    "inspection_no": "INSP-UNRESOLVED",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "bridge_source": "subcontract_inspection",
                    "profit_scope_status": "unresolved",
                    "profit_scope_error_code": "SUBCONTRACT_SCOPE_UNTRUSTED",
                    "inspected_at": "2026-04-15T10:00:00",
                    "settlement_locked_net_amount": "31",
                }
            ],
        )
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(snapshot.actual_subcontract_cost, Decimal("0"))
            self.assertEqual(snapshot.snapshot_status, "incomplete")
            unresolved_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "INSP-UNRESOLVED",
                    LyStyleProfitSourceMap.mapping_status == "unresolved",
                )
                .one()
            )
            self.assertEqual(unresolved_source.unresolved_reason, "SUBCONTRACT_SCOPE_UNTRUSTED")
            self.assertFalse(bool(unresolved_source.include_in_profit))

    def test_subcontract_cross_sales_order_not_counted(self) -> None:
        request = self._request(
            idempotency_key="idem-sub-wrong-order",
            subcontract_rows=[
                {
                    "statement_no": "SETT-WRONG-ORDER",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-999",
                    "work_order": "WO-200",
                    "bridge_source": "subcontract_inspection",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "settlement_locked_net_amount": "31",
                }
            ],
        )
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()
            self.assertEqual(snapshot.actual_subcontract_cost, Decimal("0"))
            excluded_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "SETT-WRONG-ORDER",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                )
                .one()
            )
            self.assertEqual(excluded_source.unresolved_reason, "SUBCONTRACT_SCOPE_UNTRUSTED")

    def test_unsettled_subcontract_respects_include_provisional_flag(self) -> None:
        request_true = self._request(
            idempotency_key="idem-sub-prov-true",
            include_provisional_subcontract=True,
            subcontract_rows=[
                {
                    "inspection_no": "INSP-PROV-TRUE",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "work_order": "WO-200",
                    "bridge_source": "subcontract_inspection",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "provisional_inspection_net_amount": "19",
                    "settlement_status": "unsettled",
                }
            ],
        )
        request_false = self._request(
            idempotency_key="idem-sub-prov-false",
            include_provisional_subcontract=False,
            subcontract_rows=[
                {
                    "inspection_no": "INSP-PROV-FALSE",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-200",
                    "work_order": "WO-200",
                    "bridge_source": "subcontract_inspection",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "provisional_inspection_net_amount": "19",
                    "settlement_status": "unsettled",
                }
            ],
        )
        with self.SessionLocal() as session:
            true_result = self.service.create_snapshot(session=session, request=request_true, operator="u1")
            false_result = self.service.create_snapshot(session=session, request=request_false, operator="u1")
            row_true = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == true_result.snapshot_id).one()
            row_false = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == false_result.snapshot_id).one()
            self.assertEqual(row_true.actual_subcontract_cost, Decimal("19"))
            self.assertEqual(row_false.actual_subcontract_cost, Decimal("0"))
            excluded_source = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.snapshot_id == false_result.snapshot_id,
                    LyStyleProfitSourceMap.source_name == "INSP-PROV-FALSE",
                    LyStyleProfitSourceMap.mapping_status == "excluded",
                )
                .one()
            )
            self.assertEqual(excluded_source.unresolved_reason, "SUBCONTRACT_UNSETTLED_EXCLUDED")


if __name__ == "__main__":
    unittest.main()
