"""Batch import exception boundary tests for TASK-003C."""

from __future__ import annotations

from datetime import date
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.schemas.workshop import WorkshopTicketData
from app.services.audit_service import AuditService
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.permission_service import PermissionService
from app.services.workshop_service import WorkshopResourceContext
from app.services.workshop_service import WorkshopService


class WorkshopBatchExceptionTest(unittest.TestCase):
    """Validate system-level vs row-level error boundary for batch API."""

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
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "batch.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _row(ticket_key: str, qty: str = "10") -> dict:
        return {
            "operation_type": "register",
            "ticket_key": ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": qty,
            "work_date": "2026-04-12",
            "source": "import",
        }

    @staticmethod
    def _ctx(item_code: str = "ITEM-A", company: str = "COMP-A") -> WorkshopResourceContext:
        return WorkshopResourceContext(
            job_card="JC-001",
            work_order="WO-001",
            item_code=item_code,
            company=company,
        )

    @staticmethod
    def _ok_ticket(ticket_key: str = "OK-001") -> WorkshopTicketData:
        return WorkshopTicketData(
            ticket_no=f"TICKET-{ticket_key}",
            ticket_id=1,
            unit_wage="0.500000",
            wage_amount="5.000000",
            sync_status="synced",
        )

    @staticmethod
    def _assert_not_partial_payload(response_json: dict) -> None:
        data = response_json.get("data") or {}
        assert "success_count" not in data
        assert "failed_count" not in data

    def test_database_write_failed_returns_500_not_failed_items(self) -> None:
        with patch.object(WorkshopService, "resolve_job_card_resource", return_value=self._ctx()), patch.object(
            WorkshopService,
            "process_batch_row",
            side_effect=DatabaseWriteFailed(),
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("DB-ERR-001")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["code"], "DATABASE_WRITE_FAILED")
        self._assert_not_partial_payload(payload)

    def test_permission_source_unavailable_returns_503_not_failed_items(self) -> None:
        with patch.object(
            PermissionService,
            "get_workshop_user_permissions",
            side_effect=HTTPException(
                status_code=503,
                detail={"code": "PERMISSION_SOURCE_UNAVAILABLE", "message": "权限来源暂时不可用", "data": {}},
            ),
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("PERM-ERR-001")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(payload["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self._assert_not_partial_payload(payload)

    def test_audit_write_failed_returns_500_not_failed_items(self) -> None:
        with patch.object(WorkshopService, "resolve_job_card_resource", return_value=self._ctx()), patch.object(
            WorkshopService,
            "process_batch_row",
            return_value=self._ok_ticket("AUDIT-OK"),
        ), patch.object(
            AuditService,
            "record_success",
            side_effect=AuditWriteFailed(),
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("AUDIT-ERR-001")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["code"], "AUDIT_WRITE_FAILED")
        self._assert_not_partial_payload(payload)

    def test_unknown_error_returns_500_not_failed_items(self) -> None:
        with patch.object(WorkshopService, "resolve_job_card_resource", return_value=self._ctx()), patch.object(
            WorkshopService,
            "process_batch_row",
            side_effect=RuntimeError("boom"),
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("RUNTIME-ERR-001")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["code"], "WORKSHOP_INTERNAL_ERROR")
        self._assert_not_partial_payload(payload)

    def test_row_business_error_can_enter_failed_items(self) -> None:
        with patch.object(WorkshopService, "resolve_job_card_resource", return_value=self._ctx()), patch.object(
            WorkshopService,
            "process_batch_row",
            side_effect=[
                BusinessException(code="WORKSHOP_INVALID_QTY", message="数量必须大于 0"),
                self._ok_ticket("ROW-OK-002"),
            ],
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("ROW-BAD-001", qty="0"), self._row("ROW-OK-002", qty="10")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["success_count"], 1)
        self.assertEqual(payload["data"]["failed_count"], 1)
        self.assertEqual(payload["data"]["failed_items"][0]["code"], "WORKSHOP_INVALID_QTY")

    def test_row_resource_forbidden_can_enter_failed_items_and_write_security_audit(self) -> None:
        with patch.object(
            PermissionService,
            "get_workshop_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(
            WorkshopService,
            "resolve_job_card_resource",
            side_effect=[self._ctx(item_code="ITEM-A"), self._ctx(item_code="ITEM-B")],
        ), patch.object(
            WorkshopService,
            "process_batch_row",
            return_value=self._ok_ticket("ROW-OK-002"),
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={"tickets": [self._row("ROW-DENY-001"), self._row("ROW-OK-002")]},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["success_count"], 1)
        self.assertEqual(payload["data"]["failed_count"], 1)
        self.assertEqual(payload["data"]["failed_items"][0]["code"], "AUTH_FORBIDDEN")

        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_batch")


if __name__ == "__main__":
    unittest.main()
