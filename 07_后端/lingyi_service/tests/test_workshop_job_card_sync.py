"""Job Card outbox sync behavior tests for workshop module (TASK-003D)."""

from __future__ import annotations

from datetime import date
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
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.service_account_policy import ServiceAccountResourcePolicy
from app.services.workshop_job_card_sync_worker import WorkshopJobCardSyncWorker


class WorkshopJobCardSyncTest(unittest.TestCase):
    """Validate outbox creation and worker retry behavior."""

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
            session.query(YsWorkshopJobCardSyncLog).delete()
            session.query(YsWorkshopJobCardSyncOutbox).delete()
            session.query(YsWorkshopTicket).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "sync.user", "X-LY-Dev-Roles": role}

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
    def _service_policy() -> ServiceAccountResourcePolicy:
        return ServiceAccountResourcePolicy(
            username="svc.worker",
            allowed_companies={"COMP-A"},
            allowed_items={"ITEM-A"},
        )

    def _register_payload(self, ticket_key: str = "SYNC-TK-001") -> dict:
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

    def test_register_creates_pending_outbox_without_inline_erp_sync(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as update_mock:
            register_resp = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="SYNC-PENDING-001"),
            )

        self.assertEqual(register_resp.status_code, 200)
        payload = register_resp.json()["data"]
        self.assertEqual(payload["sync_status"], "pending")
        self.assertIsNotNone(payload.get("sync_outbox_id"))
        self.assertEqual(update_mock.call_count, 0)

        with self.SessionLocal() as session:
            ticket = session.query(YsWorkshopTicket).order_by(YsWorkshopTicket.id.desc()).first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.sync_status, "pending")
            outbox = session.query(YsWorkshopJobCardSyncOutbox).order_by(YsWorkshopJobCardSyncOutbox.id.desc()).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "pending")
            self.assertTrue(str(outbox.event_key).startswith("wjc:"))
            self.assertLessEqual(len(str(outbox.event_key)), 140)
            self.assertNotIn(str(outbox.job_card), str(outbox.event_key))

    def test_worker_success_marks_outbox_succeeded_and_ticket_synced(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            register_resp = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="SYNC-WORKER-OK-001"),
            )
        self.assertEqual(register_resp.status_code, 200)

        with self.SessionLocal() as session, patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            worker = WorkshopJobCardSyncWorker(
                session=session,
                erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
            )
            result = worker.run_once(limit=10, service_account_policy=self._service_policy())
            session.commit()

        self.assertGreaterEqual(result.processed, 1)
        self.assertGreaterEqual(result.succeeded, 1)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).order_by(YsWorkshopJobCardSyncOutbox.id.desc()).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            ticket = session.query(YsWorkshopTicket).order_by(YsWorkshopTicket.id.desc()).first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.sync_status, "synced")
            log_row = session.query(YsWorkshopJobCardSyncLog).order_by(YsWorkshopJobCardSyncLog.id.desc()).first()
            self.assertIsNotNone(log_row)
            self.assertEqual(log_row.erpnext_status, "success")
            self.assertIsNotNone(log_row.outbox_id)

    def test_worker_failure_can_retry_after_manual_sync_enqueue(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            register_resp = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="SYNC-WORKER-FAIL-001"),
            )
        self.assertEqual(register_resp.status_code, 200)

        with self.SessionLocal() as session, patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            side_effect=ERPNextServiceUnavailableError("down"),
        ):
            worker = WorkshopJobCardSyncWorker(
                session=session,
                erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
            )
            fail_result = worker.run_once(limit=10, service_account_policy=self._service_policy())
            session.commit()

        self.assertGreaterEqual(fail_result.processed, 1)
        self.assertGreaterEqual(fail_result.failed + fail_result.dead, 1)

        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()):
            retry_resp = self.client.post("/api/workshop/job-cards/JC-001/sync", headers=self._headers())
        self.assertEqual(retry_resp.status_code, 200)
        self.assertEqual(retry_resp.json()["data"]["sync_status"], "pending")
        self.assertIsNotNone(retry_resp.json()["data"].get("sync_outbox_id"))

        with self.SessionLocal() as session, patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            worker = WorkshopJobCardSyncWorker(
                session=session,
                erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
            )
            success_result = worker.run_once(limit=10, service_account_policy=self._service_policy())
            session.commit()

        self.assertGreaterEqual(success_result.processed, 1)
        self.assertGreaterEqual(success_result.succeeded, 1)
        with self.SessionLocal() as session:
            ticket = session.query(YsWorkshopTicket).order_by(YsWorkshopTicket.id.desc()).first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.sync_status, "synced")

    def test_service_account_forbidden_marks_failed_without_losing_local_ticket(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            register_resp = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="SYNC-SA-FORBIDDEN-001"),
            )
        self.assertEqual(register_resp.status_code, 200)

        with self.SessionLocal() as session, patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            side_effect=ERPNextServiceAccountForbiddenError("forbidden"),
        ):
            worker = WorkshopJobCardSyncWorker(
                session=session,
                erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
            )
            result = worker.run_once(limit=10, service_account_policy=self._service_policy())
            session.commit()

        self.assertGreaterEqual(result.processed, 1)
        self.assertGreaterEqual(result.failed + result.dead, 1)
        with self.SessionLocal() as session:
            ticket = session.query(YsWorkshopTicket).order_by(YsWorkshopTicket.id.desc()).first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.sync_status, "failed")
            outbox = session.query(YsWorkshopJobCardSyncOutbox).order_by(YsWorkshopJobCardSyncOutbox.id.desc()).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.last_error_code, "ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
