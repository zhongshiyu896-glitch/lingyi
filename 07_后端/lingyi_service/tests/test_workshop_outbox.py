"""Workshop outbox transaction-boundary tests (TASK-003D)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.routers.workshop as workshop_router
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.audit_service import AuditService
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.workshop_outbox_service import WorkshopOutboxService


class WorkshopOutboxBoundaryTest(unittest.TestCase):
    """Ensure ERPNext update never runs before local commit/audit success."""

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
        WorkshopBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=1,
                    item_code="ITEM-A",
                    company="COMP-A",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.5",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[workshop_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(YsWorkshopJobCardSyncOutbox).delete()
            session.query(YsWorkshopTicket).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "outbox.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _job_card() -> JobCardInfo:
        return JobCardInfo(
            name="JC-001",
            operation="sew",
            status="Open",
            work_order=None,
            item_code="ITEM-A",
            company="COMP-A",
        )

    @staticmethod
    def _employee() -> EmployeeInfo:
        return EmployeeInfo(name="EMP-001", status="Active", disabled=False)

    @staticmethod
    def _payload(ticket_key: str) -> dict:
        return {
            "ticket_key": ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": "10",
            "work_date": "2026-04-12",
            "source": "manual",
            "source_ref": "REF",
        }

    @staticmethod
    def _long_job_card(length: int) -> str:
        return "J" * length

    @staticmethod
    def _legacy_event_key(
        *,
        job_card: str,
        local_completed_qty: Decimal,
        source_type: str,
        source_ids: list[int],
    ) -> str:
        ids = sorted({int(v) for v in source_ids})
        raw = {
            "job_card": job_card,
            "local_completed_qty": str(local_completed_qty),
            "source_type": source_type,
            "source_ids": ids,
        }
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return f"{job_card}:{digest}"[:140]

    def test_event_key_138_char_job_card_different_source_ids_no_collision(self) -> None:
        job_card = self._long_job_card(138)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[2],
        )
        self.assertNotEqual(key1, key2)
        self.assertLessEqual(len(key1), 140)
        self.assertLessEqual(len(key2), 140)
        self.assertTrue(key1.startswith("wjc:"))
        self.assertNotIn(job_card, key1)

    def test_event_key_139_char_job_card_different_qty_no_collision(self) -> None:
        job_card = self._long_job_card(139)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("11"),
            source_type="ticket_register",
            source_ids=[1],
        )
        self.assertNotEqual(key1, key2)
        self.assertLessEqual(len(key1), 140)
        self.assertLessEqual(len(key2), 140)

    def test_event_key_140_char_job_card_different_source_type_no_collision(self) -> None:
        job_card = self._long_job_card(140)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_reversal",
            source_ids=[1],
        )
        self.assertNotEqual(key1, key2)
        self.assertLessEqual(len(key1), 140)
        self.assertLessEqual(len(key2), 140)

    def test_event_key_200_char_job_card_different_source_ids_no_collision(self) -> None:
        job_card = self._long_job_card(200)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_batch",
            source_ids=[1, 2],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_batch",
            source_ids=[1, 3],
        )
        self.assertNotEqual(key1, key2)
        self.assertLessEqual(len(key1), 140)
        self.assertLessEqual(len(key2), 140)

    def test_event_key_source_ids_order_stable(self) -> None:
        job_card = self._long_job_card(40)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_batch",
            source_ids=[3, 1, 2],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_batch",
            source_ids=[1, 2, 3],
        )
        self.assertEqual(key1, key2)

    def test_event_key_decimal_semantics_stable(self) -> None:
        job_card = self._long_job_card(40)
        key1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("1"),
            source_type="ticket_register",
            source_ids=[1],
        )
        key2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("1.0"),
            source_type="ticket_register",
            source_ids=[1],
        )
        key3 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("1.000000"),
            source_type="ticket_register",
            source_ids=[1],
        )
        self.assertEqual(key1, key2)
        self.assertEqual(key2, key3)

    def test_legacy_truncation_collision_fixed_in_new_event_key(self) -> None:
        job_card = self._long_job_card(140)
        legacy_1 = self._legacy_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        legacy_2 = self._legacy_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("11"),
            source_type="ticket_reversal",
            source_ids=[2],
        )
        self.assertEqual(legacy_1, legacy_2)

        new_1 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        new_2 = WorkshopOutboxService.build_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("11"),
            source_type="ticket_reversal",
            source_ids=[2],
        )
        self.assertNotEqual(new_1, new_2)

    def test_same_business_event_dedupes_to_single_outbox_row(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopOutboxService(session=session)
            row_1 = service.enqueue(
                job_card="JC-DEDUPE-001",
                work_order=None,
                item_code="ITEM-A",
                company="COMP-A",
                local_completed_qty=Decimal("10"),
                source_type="ticket_batch",
                source_ids=[1, 2, 3],
                request_id="rid-1",
                created_by="tester",
            )
            row_2 = service.enqueue(
                job_card="JC-DEDUPE-001",
                work_order=None,
                item_code="ITEM-A",
                company="COMP-A",
                local_completed_qty=Decimal("10.000000"),
                source_type="ticket_batch",
                source_ids=[3, 1, 2],
                request_id="rid-2",
                created_by="tester",
            )
            session.commit()

            self.assertEqual(row_1.id, row_2.id)
            rows = (
                session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.job_card == "JC-DEDUPE-001")
                .all()
            )
            self.assertEqual(len(rows), 1)

    def test_legacy_pending_outbox_is_compatible_without_duplicate_insert(self) -> None:
        job_card = self._long_job_card(140)
        legacy_key = self._legacy_event_key(
            job_card=job_card,
            local_completed_qty=Decimal("10"),
            source_type="ticket_register",
            source_ids=[1],
        )
        with self.SessionLocal() as session:
            legacy_row = YsWorkshopJobCardSyncOutbox(
                event_key=legacy_key,
                job_card=job_card,
                work_order=None,
                item_code="ITEM-A",
                company="COMP-A",
                local_completed_qty=Decimal("10"),
                source_type="ticket_register",
                source_ids=[1],
                status="pending",
                attempts=0,
                max_attempts=5,
                next_retry_at=datetime.utcnow(),
                locked_by=None,
                locked_at=None,
                last_error_code=None,
                last_error_message=None,
                request_id="rid-legacy",
                created_by="legacy.seed",
                updated_at=datetime.utcnow(),
            )
            session.add(legacy_row)
            session.flush()

            service = WorkshopOutboxService(session=session)
            row = service.enqueue(
                job_card=job_card,
                work_order=None,
                item_code="ITEM-A",
                company="COMP-A",
                local_completed_qty=Decimal("10.000000"),
                source_type="ticket_register",
                source_ids=[1],
                request_id="rid-new",
                created_by="tester",
            )
            session.commit()

            self.assertEqual(row.id, legacy_row.id)
            rows = (
                session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.job_card == job_card)
                .all()
            )
            self.assertEqual(len(rows), 1)

    def test_commit_failed_does_not_call_erp_and_rolls_back_outbox(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            workshop_router,
            "_commit_or_raise_write_error",
            side_effect=DatabaseWriteFailed(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as update_mock:
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._payload("OUTBOX-COMMIT-FAIL-001"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")
        self.assertEqual(update_mock.call_count, 0)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(YsWorkshopTicket).count(), 0)
            self.assertEqual(session.query(YsWorkshopJobCardSyncOutbox).count(), 0)

    def test_audit_failed_does_not_call_erp_and_rolls_back_outbox(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            AuditService,
            "record_success",
            side_effect=AuditWriteFailed(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as update_mock:
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._payload("OUTBOX-AUDIT-FAIL-001"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        self.assertEqual(update_mock.call_count, 0)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(YsWorkshopTicket).count(), 0)
            self.assertEqual(session.query(YsWorkshopJobCardSyncOutbox).count(), 0)


if __name__ == "__main__":
    unittest.main()
