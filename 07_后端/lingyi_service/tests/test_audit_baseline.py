"""TASK-007B audit baseline coverage tests."""

from __future__ import annotations

import unittest

from fastapi import HTTPException
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.logging import REDACTED_MESSAGE
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService


class AuditBaselineTest(unittest.TestCase):
    """Validate baseline audit event catalog and sensitive-field redaction."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        AuditBase.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal

        cls._fallback_path = "/api/test/task-007b1/security-fallback"

        def _raise_security_exception() -> None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "EXTERNAL_SERVICE_UNAVAILABLE",
                    "message": "Authorization=Bearer top-secret; Cookie=sid=secret; token=abc; password=123",
                    "data": None,
                },
            )

        app.add_api_route(cls._fallback_path, _raise_security_exception, methods=["GET"])
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) != cls._fallback_path]
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _build_request() -> Request:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/test",
            "raw_path": b"/api/test",
            "query_string": b"",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        return Request(scope)

    def test_security_event_catalog_contains_task_007b_required_events(self) -> None:
        required = {
            "AUTH_UNAUTHENTICATED",
            "AUTH_FORBIDDEN",
            "RESOURCE_ACCESS_DENIED",
            "PERMISSION_SOURCE_UNAVAILABLE",
            "INTERNAL_API_FORBIDDEN",
            "REQUEST_ID_REJECTED",
            "EXTERNAL_SERVICE_UNAVAILABLE",
        }
        self.assertTrue(required.issubset(AuditService.SECURITY_EVENT_TYPES))

    def test_security_audit_fallback_codes_include_new_events(self) -> None:
        required = {
            "AUTH_UNAUTHENTICATED",
            "RESOURCE_ACCESS_DENIED",
            "EXTERNAL_SERVICE_UNAVAILABLE",
            "INTERNAL_API_FORBIDDEN",
            "REQUEST_ID_REJECTED",
            "AUTH_UNAUTHORIZED",
            "AUTH_FORBIDDEN",
            "PERMISSION_SOURCE_UNAVAILABLE",
        }
        self.assertTrue(required.issubset(main_module.SECURITY_AUDIT_CODES))

    def test_operation_event_catalog_contains_task_007b_required_events(self) -> None:
        required = {
            "create",
            "update",
            "confirm",
            "cancel",
            "export",
            "dry_run",
            "diagnostic",
            "worker_run",
            "retry",
        }
        self.assertTrue(required.issubset(AuditService.OPERATION_EVENT_TYPES))

    def test_operation_audit_snapshot_redacts_sensitive_fields(self) -> None:
        with self.SessionLocal() as session:
            audit = AuditService(session)
            audit.record_success(
                module="permission_audit",
                action="diagnostic",
                operator="auditor",
                operator_roles=["System Manager"],
                resource_type="permission_audit",
                resource_id=1,
                resource_no="PA-1",
                before_data={
                    "password": "123456",
                    "nested": {
                        "token": "secret-token",
                        "remark": "keep",
                    },
                },
                after_data={
                    "api_key": "abc",
                    "status": "ok",
                },
                context=AuditContext(request_id="REQ-1", ip_address="127.0.0.1", user_agent="pytest"),
            )
            session.commit()

            row = session.query(LyOperationAuditLog).order_by(LyOperationAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.before_data["password"], REDACTED_MESSAGE)
            self.assertEqual(row.before_data["nested"]["token"], REDACTED_MESSAGE)
            self.assertEqual(row.before_data["nested"]["remark"], "keep")
            self.assertEqual(row.after_data["api_key"], REDACTED_MESSAGE)
            self.assertEqual(row.after_data["status"], "ok")

    def test_security_audit_reason_code_and_scope_are_recorded(self) -> None:
        class _User:
            username = "audit.user"
            roles = ["System Manager"]

        with self.SessionLocal() as session:
            audit = AuditService(session)
            audit.record_security_audit(
                event_type="RESOURCE_ACCESS_DENIED",
                module="permission_audit",
                action="permission_audit:manage",
                resource_type="COMPANY",
                resource_id="COMP-A",
                resource_no="COMP-A",
                user=_User(),
                deny_reason="Authorization=Bearer abc",
                permission_source="erpnext",
                request_obj=self._build_request(),
                reason_code="RESOURCE_ACCESS_DENIED",
                resource_scope={"company": "COMP-A", "supplier": "SUP-1"},
            )
            session.commit()

            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertTrue((row.deny_reason or "").startswith("[RESOURCE_ACCESS_DENIED]"))
            self.assertNotIn("Authorization", row.deny_reason or "")
            self.assertNotIn("Bearer", row.deny_reason or "")

    def test_http_exception_fallback_records_security_audit_for_new_code(self) -> None:
        response = self.client.get(
            self._fallback_path,
            headers={
                "X-Request-ID": "REQ-FALLBACK-001",
                "Authorization": "Bearer should-not-leak",
                "Cookie": "sid=should-not-leak",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json().get("code"), "EXTERNAL_SERVICE_UNAVAILABLE")

        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()

        self.assertIsNotNone(row)
        self.assertEqual(row.event_type, "EXTERNAL_SERVICE_UNAVAILABLE")
        deny_reason = (row.deny_reason or "").lower()
        self.assertNotIn("authorization", deny_reason)
        self.assertNotIn("cookie", deny_reason)
        self.assertNotIn("token", deny_reason)
        self.assertNotIn("secret", deny_reason)
        self.assertNotIn("password", deny_reason)


if __name__ == "__main__":
    unittest.main()
