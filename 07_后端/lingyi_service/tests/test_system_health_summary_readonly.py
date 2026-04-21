"""System health summary readonly baseline tests (TASK-080D)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import SYSTEM_DIAGNOSTIC
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.system_management import get_db_session as system_management_db_dep


class SystemHealthSummaryReadonlyApiTest(unittest.TestCase):
    """Validate system health summary readonly contract and boundaries."""

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
        app.dependency_overrides[system_management_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(system_management_db_dep, None)
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
            "X-LY-Dev-User": "system.health.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_health_summary_requires_system_read_and_diagnostic(self) -> None:
        only_system_read = self.client.get(
            "/api/system/health/summary",
            headers=self._headers_with_roles("system:read"),
        )
        self.assertEqual(only_system_read.status_code, 403)

        only_health_read = self.client.get(
            "/api/system/health/summary",
            headers=self._headers_with_roles("system:diagnostic"),
        )
        self.assertEqual(only_health_read.status_code, 403)

        both_actions = self.client.get(
            "/api/system/health/summary",
            headers=self._headers_with_roles("system:read,system:diagnostic"),
        )
        self.assertEqual(both_actions.status_code, 200, both_actions.text)

    def test_system_manager_can_access_health_summary(self) -> None:
        response = self.client.get(
            "/api/system/health/summary",
            headers=self._headers_with_roles("System Manager"),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_other_module_actions_cannot_replace_system_actions(self) -> None:
        for role in (
            "permission:read",
            "dashboard:read",
            "report:diagnostic",
            "warehouse:diagnostic",
            "inventory:read",
        ):
            response = self.client.get(
                "/api/system/health/summary",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_health_summary_response_contract_and_safety(self) -> None:
        response = self.client.get(
            "/api/system/health/summary",
            headers=self._headers_with_roles("system:read,system:diagnostic"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        payload = response.json()["data"]
        items = payload["items"]
        self.assertGreaterEqual(len(items), 4)
        self.assertEqual(payload["total"], len(items))
        self.assertIn("generated_at", payload)

        required_checks = {
            "permission_source",
            "system_router_mapping",
            "ui_route_present",
            "readonly_contract",
        }
        self.assertTrue(required_checks.issubset({item["check_name"] for item in items}))

        expected_item_fields = {
            "module",
            "status",
            "check_name",
            "check_result",
            "generated_at",
        }
        for item in items:
            self.assertEqual(set(item.keys()), expected_item_fields)
            self.assertEqual(item["module"], "system")
            self.assertIn(item["status"], {"ok", "warn", "blocked"})

        blocked_fields = {
            "token",
            "authorization",
            "cookie",
            "password",
            "secret",
            "dsn",
            "database_url",
            "raw headers",
            "raw payload",
        }
        lowered = json.dumps(payload, ensure_ascii=False).lower()
        for field in blocked_fields:
            self.assertNotIn(field, lowered)

    def test_main_route_mapping_for_health_summary(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/system/health/summary",
            "raw_path": b"/api/system/health/summary",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "system")
        self.assertEqual(action, SYSTEM_DIAGNOSTIC)
        self.assertEqual(resource_type, "SystemHealthSummary")
        self.assertIsNone(resource_id)

    def test_system_management_files_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/system_management.py"),
            Path("app/services/system_health_summary_service.py"),
            Path("app/schemas/system_management.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        lowered = combined.lower()

        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "requests.",
            "httpx.",
            "/api/resource",
            "session.add(",
            "session.delete(",
            "session.commit(",
            "session.rollback(",
            ".query(",
            "select(",
            "execute(",
            "outbox",
            "worker",
            "run-once",
            "internal",
            "cache_refresh",
            "platform_manage",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, lowered)

    def test_task_080b_and_task_080c_not_regressed(self) -> None:
        config_response = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(config_response.status_code, 200, config_response.text)
        self.assertGreaterEqual(config_response.json()["data"]["total"], 6)

        dictionary_response = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(dictionary_response.status_code, 200, dictionary_response.text)
        self.assertGreaterEqual(dictionary_response.json()["data"]["total"], 6)


if __name__ == "__main__":
    unittest.main()
