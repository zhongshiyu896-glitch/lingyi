"""Readonly report health diagnostic tests for TASK-060D."""

from __future__ import annotations

import json
import os
import unittest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import REPORT_DIAGNOSTIC
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.report import get_db_session as report_db_dep


class ReportDiagnosticApiTest(unittest.TestCase):
    """Validate report diagnostic readonly contract and permission boundary."""

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
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[report_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(report_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "report.diagnostic.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_report_diagnostic_requires_report_diagnostic_permission(self) -> None:
        for role in ("report:read", "report:export", "dashboard:read", "quality:read", "sales_inventory:read"):
            response = self.client.get(
                "/api/reports/diagnostic",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_report_diagnostic_success_and_fields(self) -> None:
        response = self.client.get(
            "/api/reports/diagnostic",
            headers=self._headers_with_roles("report:diagnostic"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["module"], "report")
        self.assertIn(data["status"], {"ok", "error"})
        self.assertIsInstance(data["catalog_count"], int)
        self.assertIsInstance(data["catalog_keys"], list)
        self.assertIsInstance(data["supported_source_modules"], list)
        self.assertIsInstance(data["supported_report_types"], list)
        self.assertIsInstance(data["registered_actions"], list)
        self.assertIsInstance(data["checks"], list)
        self.assertIsInstance(data["export_enabled"], bool)
        self.assertIsInstance(data["generated_at"], str)
        self.assertIn("report:read", data["registered_actions"])
        self.assertIn("report:export", data["registered_actions"])
        self.assertIn("report:diagnostic", data["registered_actions"])

    def test_report_diagnostic_response_has_no_sensitive_tokens(self) -> None:
        response = self.client.get(
            "/api/reports/diagnostic",
            headers=self._headers_with_roles("report:diagnostic"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        lowered = json.dumps(response.json()["data"], ensure_ascii=False).lower()
        blocked = ("token", "cookie", "secret", "password", "authorization", "dsn", "database_url")
        for key in blocked:
            self.assertNotIn(key, lowered)

    def test_main_route_mapping_for_report_diagnostic(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/reports/diagnostic",
            "raw_path": b"/api/reports/diagnostic",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "report")
        self.assertEqual(action, REPORT_DIAGNOSTIC)
        self.assertEqual(resource_type, "ReportDiagnostic")
        self.assertIsNone(resource_id)


if __name__ == "__main__":
    unittest.main()
