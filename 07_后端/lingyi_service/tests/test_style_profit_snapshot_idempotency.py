"""Idempotency tests for style profit snapshot service (TASK-005D)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.services.style_profit_service import STYLE_PROFIT_IDEMPOTENCY_CONFLICT
from app.services.style_profit_service import StyleProfitService


class StyleProfitSnapshotIdempotencyTest(unittest.TestCase):
    """Validate replay/冲突 behavior by company + idempotency_key + request_hash."""

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

    def _request(self, *, idempotency_key: str = "idem-500d-1") -> StyleProfitSnapshotCreateRequest:
        return StyleProfitSnapshotCreateRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-500",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            include_provisional_subcontract=False,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key=idempotency_key,
            sales_invoice_rows=[
                {
                    "name": "SINV-500",
                    "line_id": "SINV-500-1",
                    "company": "COMP-A",
                    "sales_order": "SO-500",
                    "item_code": "STYLE-A",
                    "qty": "5",
                    "rate": "40",
                    "amount": "200",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            sales_order_rows=[],
            bom_material_rows=[{"item_code": "MAT-A", "required_qty": "2", "item_price": "5"}],
            bom_operation_rows=[],
            stock_ledger_rows=[
                {
                    "name": "SLE-500",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-500",
                    "company": "COMP-A",
                    "sales_order": "SO-500",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-40",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            workshop_ticket_rows=[],
            subcontract_rows=[],
            allowed_material_item_codes=["MAT-A"],
        )

    def test_same_company_key_and_hash_replays_same_snapshot_without_new_rows(self) -> None:
        request = self._request(idempotency_key="idem-replay")
        with self.SessionLocal() as session:
            first = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot_count_1 = session.query(LyStyleProfitSnapshot).count()
            detail_count_1 = session.query(LyStyleProfitDetail).count()
            source_count_1 = session.query(LyStyleProfitSourceMap).count()

            replay = self.service.create_snapshot(session=session, request=request, operator="u2")
            snapshot_count_2 = session.query(LyStyleProfitSnapshot).count()
            detail_count_2 = session.query(LyStyleProfitDetail).count()
            source_count_2 = session.query(LyStyleProfitSourceMap).count()

            self.assertEqual(first.snapshot_id, replay.snapshot_id)
            self.assertEqual(first.snapshot_no, replay.snapshot_no)
            self.assertTrue(replay.idempotent_replay)
            self.assertEqual(snapshot_count_1, snapshot_count_2)
            self.assertEqual(detail_count_1, detail_count_2)
            self.assertEqual(source_count_1, source_count_2)

    def test_same_company_key_different_hash_returns_conflict_and_no_new_rows(self) -> None:
        with self.SessionLocal() as session:
            first_request = self._request(idempotency_key="idem-conflict")
            first = self.service.create_snapshot(session=session, request=first_request, operator="u1")
            snapshot_count_1 = session.query(LyStyleProfitSnapshot).count()
            detail_count_1 = session.query(LyStyleProfitDetail).count()
            source_count_1 = session.query(LyStyleProfitSourceMap).count()

            second_request = self._request(idempotency_key="idem-conflict")
            second_request.to_date = date(2026, 5, 1)
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=second_request, operator="u2")

            self.assertEqual(ctx.exception.code, STYLE_PROFIT_IDEMPOTENCY_CONFLICT)
            self.assertEqual(snapshot_count_1, session.query(LyStyleProfitSnapshot).count())
            self.assertEqual(detail_count_1, session.query(LyStyleProfitDetail).count())
            self.assertEqual(source_count_1, session.query(LyStyleProfitSourceMap).count())
            latest = session.query(LyStyleProfitSnapshot).one()
            self.assertEqual(int(latest.id), first.snapshot_id)

    def test_request_hash_is_independent_of_operator_replay(self) -> None:
        request = self._request(idempotency_key="idem-operator")
        with self.SessionLocal() as session:
            first = self.service.create_snapshot(session=session, request=request, operator="operator-a")
            replay = self.service.create_snapshot(session=session, request=request, operator="operator-b")
            self.assertEqual(first.request_hash, replay.request_hash)
            self.assertTrue(replay.idempotent_replay)

    def test_same_header_but_different_source_amount_returns_conflict(self) -> None:
        with self.SessionLocal() as session:
            request = self._request(idempotency_key="idem-source-diff")
            first = self.service.create_snapshot(session=session, request=request, operator="u1")
            snapshot_count = session.query(LyStyleProfitSnapshot).count()
            detail_count = session.query(LyStyleProfitDetail).count()
            source_count = session.query(LyStyleProfitSourceMap).count()

            changed = self._request(idempotency_key="idem-source-diff")
            changed.sales_invoice_rows[0]["amount"] = "201"
            with self.assertRaises(BusinessException) as ctx:
                self.service.create_snapshot(session=session, request=changed, operator="u2")

            self.assertEqual(ctx.exception.code, STYLE_PROFIT_IDEMPOTENCY_CONFLICT)
            self.assertEqual(session.query(LyStyleProfitSnapshot).count(), snapshot_count)
            self.assertEqual(session.query(LyStyleProfitDetail).count(), detail_count)
            self.assertEqual(session.query(LyStyleProfitSourceMap).count(), source_count)
            replayed = session.query(LyStyleProfitSnapshot).one()
            self.assertEqual(int(replayed.id), first.snapshot_id)

    def test_conflict_does_not_create_second_snapshot_no(self) -> None:
        with self.SessionLocal() as session:
            request = self._request(idempotency_key="idem-no-second")
            first = self.service.create_snapshot(session=session, request=request, operator="u1")
            request_2 = self._request(idempotency_key="idem-no-second")
            request_2.revenue_mode = "estimated_only"

            with self.assertRaises(BusinessException):
                self.service.create_snapshot(session=session, request=request_2, operator="u1")

            snapshots = session.query(LyStyleProfitSnapshot).all()
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0].snapshot_no, first.snapshot_no)
            self.assertEqual(snapshots[0].revenue_amount, Decimal("200"))
