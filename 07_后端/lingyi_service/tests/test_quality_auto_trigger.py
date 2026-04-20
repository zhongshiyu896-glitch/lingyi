"""Tests for Purchase Receipt auto-triggered quality draft creation (TASK-030G)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.models.quality import Base as QualityBase
from app.models.quality import LyQualityInspection
from app.models.quality_outbox import LyQualityOutbox
from app.services.quality_purchase_receipt_listener import handle_purchase_receipt_event
from app.services.quality_service import QualitySourceValidationSnapshot


class _FakeSourceValidator:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def validate_for_payload(self, **kwargs):  # noqa: ANN003
        self.calls += 1
        if self.fail:
            raise BusinessException(code="QUALITY_SOURCE_UNAVAILABLE")
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": kwargs["company"]}, "item": {"name": kwargs["item_code"]}},
            source={"name": kwargs.get("source_id")},
        )


class QualityAutoTriggerTest(unittest.TestCase):
    """Validate automatic draft creation and idempotency constraints."""

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
        QualityBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyQualityOutbox).delete()
            session.query(LyQualityInspection).delete()
            session.commit()

    @staticmethod
    def _event(**overrides):
        payload = {
            "event_type": "purchase_receipt_submitted",
            "purchase_receipt_id": "PR-0001",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "warehouse": "WH-A",
            "posting_date": "2026-04-20",
            "items": [
                {"item_code": "ITEM-A", "qty": "6", "warehouse": "WH-A", "item_name": "A"},
                {"item_code": "ITEM-B", "qty": "4", "warehouse": "WH-A", "item_name": "B"},
            ],
            "event_id": "evt-pr-1",
        }
        payload.update(overrides)
        return payload

    def _seed_inspection(self, *, status: str) -> int:
        with self.SessionLocal() as session:
            row = LyQualityInspection(
                inspection_no=f"QI-SEED-{status}",
                company="COMP-A",
                source_type="incoming_material",
                source_id="PR-0001",
                item_code="ITEM-A",
                supplier="SUP-A",
                warehouse="WH-A",
                inspection_date=date(2026, 4, 20),
                inspected_qty=Decimal("10"),
                accepted_qty=Decimal("10"),
                rejected_qty=Decimal("0"),
                defect_qty=Decimal("0"),
                defect_rate=Decimal("0"),
                rejected_rate=Decimal("0"),
                result="pass",
                status=status,
                created_by="seed",
                updated_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def test_auto_trigger_creates_draft_quality_inspection(self) -> None:
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            detail = handle_purchase_receipt_event(
                session,
                self._event(),
                actor="quality.listener",
                source_validator=validator,
            )
            session.commit()

        self.assertEqual(detail.status, "draft")
        self.assertEqual(detail.source_type, "incoming_material")
        self.assertEqual(detail.source_id, "PR-0001")
        self.assertEqual(detail.company, "COMP-A")
        self.assertEqual(detail.supplier, "SUP-A")
        self.assertEqual(detail.warehouse, "WH-A")
        self.assertEqual(detail.inspected_qty, Decimal("10"))
        self.assertEqual(detail.accepted_qty, Decimal("10"))
        self.assertEqual(detail.rejected_qty, Decimal("0"))
        self.assertEqual(detail.defect_qty, Decimal("0"))
        self.assertEqual(len(detail.items), 2)
        self.assertEqual(validator.calls, 1)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 1)
            self.assertEqual(session.query(LyQualityOutbox).count(), 0)

    def test_duplicate_event_is_idempotent(self) -> None:
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            first = handle_purchase_receipt_event(session, self._event(), source_validator=validator)
            second = handle_purchase_receipt_event(session, self._event(), source_validator=validator)
            session.commit()
        self.assertEqual(first.id, second.id)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 1)

    def test_existing_confirmed_record_reused(self) -> None:
        seeded_id = self._seed_inspection(status="confirmed")
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            detail = handle_purchase_receipt_event(session, self._event(), source_validator=validator)
        self.assertEqual(detail.id, seeded_id)
        self.assertEqual(detail.status, "confirmed")

    def test_existing_cancelled_record_fails_closed(self) -> None:
        self._seed_inspection(status="cancelled")
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                handle_purchase_receipt_event(session, self._event(), source_validator=validator)
        self.assertEqual(ctx.exception.code, "QUALITY_INVALID_STATUS")

    def test_missing_required_fields_fail_closed(self) -> None:
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                handle_purchase_receipt_event(
                    session,
                    self._event(supplier=None),
                    source_validator=validator,
                )
        self.assertEqual(ctx.exception.code, "QUALITY_INVALID_SOURCE")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)

    def test_invalid_qty_fails_closed(self) -> None:
        validator = _FakeSourceValidator()
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                handle_purchase_receipt_event(
                    session,
                    self._event(items=[{"item_code": "ITEM-A", "qty": "0"}]),
                    source_validator=validator,
                )
        self.assertEqual(ctx.exception.code, "QUALITY_INVALID_QTY")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)

    def test_source_validation_failure_does_not_create_draft(self) -> None:
        validator = _FakeSourceValidator(fail=True)
        with self.SessionLocal() as session:
            with self.assertRaises(BusinessException) as ctx:
                handle_purchase_receipt_event(session, self._event(), source_validator=validator)
        self.assertEqual(ctx.exception.code, "QUALITY_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)


if __name__ == "__main__":
    unittest.main()
