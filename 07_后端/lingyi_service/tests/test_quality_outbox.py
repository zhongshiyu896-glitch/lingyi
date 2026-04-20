"""TASK-030D quality outbox service/worker baseline tests."""

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
from app.services.quality_outbox_service import QualityOutboxService
from app.services.quality_outbox_worker import QualityOutboxWorker


class _SuccessAdapter:
    def sync_stock_entry(self, *, event_key: str, payload_json: dict) -> str:  # noqa: ARG002
        return "STE-QUALITY-001"


class _RetryableFailAdapter:
    def sync_stock_entry(self, *, event_key: str, payload_json: dict) -> str:  # noqa: ARG002
        raise BusinessException(code="ERPNEXT_SERVICE_UNAVAILABLE", message="temporary unavailable")


class _NonRetryableFailAdapter:
    def sync_stock_entry(self, *, event_key: str, payload_json: dict) -> str:  # noqa: ARG002
        raise BusinessException(code="QUALITY_INVALID_SOURCE", message="payload invalid")


class QualityOutboxTest(unittest.TestCase):
    """Validate quality outbox idempotency and worker transitions."""

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

    def _seed_confirmed_inspection(self) -> int:
        with self.SessionLocal() as session:
            row = LyQualityInspection(
                inspection_no="QI-OUTBOX-001",
                company="COMP-A",
                source_type="manual",
                source_id=None,
                item_code="ITEM-A",
                supplier="SUP-A",
                warehouse="WH-A",
                inspection_date=date(2026, 4, 20),
                inspected_qty=Decimal("10"),
                accepted_qty=Decimal("8"),
                rejected_qty=Decimal("2"),
                defect_qty=Decimal("1"),
                defect_rate=Decimal("0.1"),
                rejected_rate=Decimal("0.2"),
                result="partial",
                status="confirmed",
                created_by="seed",
                updated_by="seed",
                confirmed_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def test_create_outbox_idempotent_by_inspection_event(self) -> None:
        inspection_id = self._seed_confirmed_inspection()
        with self.SessionLocal() as session:
            svc = QualityOutboxService(session=session)
            first = svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A"},
                created_by="quality.user",
            )
            second = svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A", "x": 1},
                created_by="quality.user",
            )
            session.commit()
            self.assertEqual(int(first.id), int(second.id))
            self.assertEqual(session.query(LyQualityOutbox).count(), 1)

    def test_worker_dry_run_does_not_mutate_outbox(self) -> None:
        inspection_id = self._seed_confirmed_inspection()
        with self.SessionLocal() as session:
            svc = QualityOutboxService(session=session)
            svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A"},
                created_by="quality.user",
            )
            session.commit()

        with self.SessionLocal() as session:
            worker = QualityOutboxWorker(session=session, adapter=_SuccessAdapter())
            result = worker.run_once(batch_size=10, worker_id="quality-worker:test", dry_run=True)
            self.assertTrue(result.dry_run)
            self.assertEqual(result.processed_count, 1)
            row = session.query(LyQualityOutbox).one()
            self.assertEqual(str(row.status), "pending")
            self.assertEqual(int(row.attempts), 0)

    def test_worker_success_marks_succeeded(self) -> None:
        inspection_id = self._seed_confirmed_inspection()
        with self.SessionLocal() as session:
            svc = QualityOutboxService(session=session)
            svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A"},
                created_by="quality.user",
            )
            session.commit()

        with self.SessionLocal() as session:
            worker = QualityOutboxWorker(session=session, adapter=_SuccessAdapter())
            result = worker.run_once(batch_size=10, worker_id="quality-worker:test", dry_run=False)
            self.assertFalse(result.dry_run)
            self.assertEqual(result.processed_count, 1)
            self.assertEqual(result.succeeded_count, 1)
            row = session.query(LyQualityOutbox).one()
            self.assertEqual(str(row.status), "succeeded")
            self.assertEqual(str(row.stock_entry_name), "STE-QUALITY-001")
            self.assertEqual(int(row.attempts), 1)

    def test_worker_retryable_error_keeps_failed_with_next_retry(self) -> None:
        inspection_id = self._seed_confirmed_inspection()
        with self.SessionLocal() as session:
            svc = QualityOutboxService(session=session)
            svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A"},
                created_by="quality.user",
            )
            session.commit()

        with self.SessionLocal() as session:
            worker = QualityOutboxWorker(session=session, adapter=_RetryableFailAdapter())
            result = worker.run_once(batch_size=10, worker_id="quality-worker:test", dry_run=False)
            self.assertEqual(result.processed_count, 1)
            self.assertEqual(result.failed_count, 1)
            self.assertEqual(result.dead_count, 0)
            row = session.query(LyQualityOutbox).one()
            self.assertEqual(str(row.status), "failed")
            self.assertEqual(int(row.attempts), 1)
            self.assertIsNotNone(row.next_retry_at)

    def test_worker_non_retryable_error_goes_dead(self) -> None:
        inspection_id = self._seed_confirmed_inspection()
        with self.SessionLocal() as session:
            svc = QualityOutboxService(session=session)
            svc.create_outbox(
                inspection_id=inspection_id,
                company="COMP-A",
                payload_json={"inspection_id": inspection_id, "item_code": "ITEM-A"},
                created_by="quality.user",
            )
            session.commit()

        with self.SessionLocal() as session:
            worker = QualityOutboxWorker(session=session, adapter=_NonRetryableFailAdapter())
            result = worker.run_once(batch_size=10, worker_id="quality-worker:test", dry_run=False)
            self.assertEqual(result.processed_count, 1)
            self.assertEqual(result.failed_count, 1)
            self.assertEqual(result.dead_count, 1)
            row = session.query(LyQualityOutbox).one()
            self.assertEqual(str(row.status), "dead")
            self.assertEqual(int(row.attempts), 1)
            self.assertIsNotNone(row.dead_at)


if __name__ == "__main__":
    unittest.main()

