"""Service behavior tests for style profit snapshot creation (TASK-005D)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.services.style_profit_service import STYLE_PROFIT_INVALID_FORMULA_VERSION
from app.services.style_profit_service import STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY
from app.services.style_profit_service import STYLE_PROFIT_INVALID_PERIOD
from app.services.style_profit_service import STYLE_PROFIT_INVALID_REVENUE_MODE
from app.services.style_profit_service import STYLE_PROFIT_INTERNAL_ERROR
from app.services.style_profit_service import STYLE_PROFIT_SALES_ORDER_REQUIRED
from app.services.style_profit_service import StyleProfitService


class StyleProfitServiceTest(unittest.TestCase):
    """Validate service guardrails and transaction boundary."""

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

    def _request(self, *, idempotency_key: str = "idem-005d-1") -> StyleProfitSnapshotCreateRequest:
        return StyleProfitSnapshotCreateRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-100",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            include_provisional_subcontract=False,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key=idempotency_key,
            sales_invoice_rows=[
                {
                    "name": "SINV-100",
                    "line_id": "SINV-100-1",
                    "company": "COMP-A",
                    "sales_order": "SO-100",
                    "item_code": "STYLE-A",
                    "qty": "10",
                    "rate": "30",
                    "amount": "300",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            sales_order_rows=[],
            bom_material_rows=[
                {"item_code": "MAT-A", "required_qty": "5", "item_price": "4"},
            ],
            bom_operation_rows=[
                {"operation": "Cut", "bom_operation_rate": "1.5", "planned_qty": "10"},
            ],
            stock_ledger_rows=[
                {
                    "name": "SLE-100",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-100",
                    "company": "COMP-A",
                    "sales_order": "SO-100",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-80",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            workshop_ticket_rows=[
                {
                    "ticket_no": "T-100",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-100",
                    "status": "submitted",
                    "register_qty": "10",
                    "reversal_qty": "2",
                    "wage_rate_snapshot": "3",
                }
            ],
            subcontract_rows=[
                {
                    "statement_no": "SETT-100",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "sales_order": "SO-100",
                    "profit_scope_status": "ready",
                    "inspected_at": "2026-04-15T10:00:00",
                    "settlement_locked_net_amount": "20",
                }
            ],
            allowed_material_item_codes=["MAT-A"],
        )

    def test_create_snapshot_writes_rows_without_commit(self) -> None:
        with self.SessionLocal() as session:
            commit_calls = {"count": 0}

            def _commit_guard() -> None:
                commit_calls["count"] += 1
                raise AssertionError("service should not call commit")

            session.commit = _commit_guard  # type: ignore[method-assign]
            result = self.service.create_snapshot(session=session, request=self._request(), operator="tester")

            self.assertEqual(commit_calls["count"], 0)
            self.assertEqual(result.snapshot_status, "complete")
            self.assertEqual(
                session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.snapshot_no == result.snapshot_no).count(),
                1,
            )
            self.assertGreater(
                session.query(LyStyleProfitDetail).filter(LyStyleProfitDetail.snapshot_id == result.snapshot_id).count(),
                0,
            )
            self.assertGreater(
                session.query(LyStyleProfitSourceMap).filter(LyStyleProfitSourceMap.snapshot_id == result.snapshot_id).count(),
                0,
            )

    def test_invalid_period_raises_business_error(self) -> None:
        request = self._request()
        request.from_date = date(2026, 4, 30)
        request.to_date = date(2026, 4, 1)
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
        self.assertEqual(ctx.exception.code, STYLE_PROFIT_INVALID_PERIOD)

    def test_invalid_revenue_mode_raises_business_error(self) -> None:
        request = self._request()
        request.revenue_mode = "bad_mode"
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
        self.assertEqual(ctx.exception.code, STYLE_PROFIT_INVALID_REVENUE_MODE)

    def test_invalid_formula_version_raises_business_error(self) -> None:
        request = self._request()
        request.formula_version = "STYLE_PROFIT_V2"
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
        self.assertEqual(ctx.exception.code, STYLE_PROFIT_INVALID_FORMULA_VERSION)

    def test_idempotency_key_too_long_is_rejected_without_writes(self) -> None:
        request = self._request()
        request.idempotency_key = "x" * 129
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
            self.assertEqual(ctx.exception.code, STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY)
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_database_write_failure_maps_to_database_write_failed(self) -> None:
        request = self._request()
        with self.SessionLocal() as session:
            with mock.patch.object(session, "flush", side_effect=SQLAlchemyError("boom")):
                with self.assertRaises(DatabaseWriteFailed):
                    self.service.create_snapshot(session=session, request=request, operator="tester")

    def test_sales_order_none_is_rejected_without_writes(self) -> None:
        request = self._request(idempotency_key="idem-sales-order-none")
        request.sales_order = None
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
            self.assertEqual(ctx.exception.code, STYLE_PROFIT_SALES_ORDER_REQUIRED)
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_sales_order_empty_string_is_rejected_without_writes(self) -> None:
        request = self._request(idempotency_key="idem-sales-order-empty")
        request.sales_order = ""
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
            self.assertEqual(ctx.exception.code, STYLE_PROFIT_SALES_ORDER_REQUIRED)
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_sales_order_blank_string_is_rejected_without_writes(self) -> None:
        request = self._request(idempotency_key="idem-sales-order-blank")
        request.sales_order = "   "
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=request, operator="tester")
            self.assertEqual(ctx.exception.code, STYLE_PROFIT_SALES_ORDER_REQUIRED)
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_runtime_error_rolls_back_nested_writes_even_if_outer_commit(self) -> None:
        request = self._request(idempotency_key="idem-savepoint-runtime")
        with self.SessionLocal() as session:
            with mock.patch.object(self.service, "_persist_subcontract_details", side_effect=RuntimeError("boom")):
                with self.assertRaises(BusinessException) as ctx:
                    self.service.create_snapshot(session=session, request=request, operator="tester")
                self.assertEqual(ctx.exception.code, STYLE_PROFIT_INTERNAL_ERROR)
            session.commit()
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_sqlalchemy_error_rolls_back_nested_writes_even_if_outer_commit(self) -> None:
        request = self._request(idempotency_key="idem-savepoint-sqlalchemy")
        with self.SessionLocal() as session:
            with mock.patch.object(self.service, "_persist_subcontract_details", side_effect=SQLAlchemyError("boom")):
                with self.assertRaises(DatabaseWriteFailed):
                    self.service.create_snapshot(session=session, request=request, operator="tester")
            session.commit()
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), 0)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), 0)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), 0)

    def test_profit_formula_matches_snapshot_values(self) -> None:
        with self.SessionLocal() as session:
            result = self.service.create_snapshot(session=session, request=self._request(), operator="tester")
            row = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.id == result.snapshot_id).one()

            self.assertEqual(row.allocated_overhead_amount, Decimal("0"))
            self.assertEqual(row.allocation_status, "not_enabled")
            self.assertEqual(
                row.actual_total_cost,
                row.actual_material_cost + row.actual_workshop_cost + row.actual_subcontract_cost + row.allocated_overhead_amount,
            )
            self.assertEqual(row.profit_amount, row.revenue_amount - row.actual_total_cost)
