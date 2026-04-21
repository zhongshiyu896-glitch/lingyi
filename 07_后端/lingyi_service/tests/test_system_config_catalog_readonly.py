"""System config catalog readonly baseline tests (TASK-080B)."""

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
from app.core.permissions import SYSTEM_CONFIG_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.system_management import get_db_session as system_management_db_dep


class SystemConfigCatalogReadonlyApiTest(unittest.TestCase):
    """Validate system config catalog readonly contract and boundaries."""

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
            "X-LY-Dev-User": "system.catalog.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_catalog_requires_both_system_read_actions(self) -> None:
        only_system_read = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:read"),
        )
        self.assertEqual(only_system_read.status_code, 403)

        only_config_read = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:config_read"),
        )
        self.assertEqual(only_config_read.status_code, 403)

        both_actions = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(both_actions.status_code, 200, both_actions.text)

    def test_system_manager_can_access_catalog(self) -> None:
        response = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("System Manager"),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_other_module_actions_cannot_replace_system_actions(self) -> None:
        for role in ("permission:read", "dashboard:read", "report:read", "warehouse:read", "inventory:read"):
            response = self.client.get(
                "/api/system/configs/catalog",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_catalog_response_contract_and_minimum_entries(self) -> None:
        response = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        payload = response.json()["data"]
        items = payload["items"]
        self.assertGreaterEqual(len(items), 6)
        self.assertEqual(payload["total"], len(items))

        groups = {item["config_group"] for item in items}
        self.assertTrue({"ui", "security", "audit", "integration"}.issubset(groups))

        sources = {item["source"] for item in items}
        self.assertGreaterEqual(len(sources), 2)
        self.assertTrue(any(item["is_sensitive"] for item in items))

        expected_fields = {
            "module",
            "config_key",
            "config_group",
            "description",
            "source",
            "is_sensitive",
            "updated_at",
        }
        for item in items:
            self.assertEqual(set(item.keys()), expected_fields)

        blocked_fields = {
            "value",
            "raw_value",
            "secret_value",
            "password",
            "token",
            "authorization",
            "cookie",
            "dsn",
            "database_url",
        }
        lowered = json.dumps(payload, ensure_ascii=False).lower()
        for field in blocked_fields:
            self.assertNotIn(field, lowered)

    def test_filters_work_and_unknown_value_returns_empty(self) -> None:
        response = self.client.get(
            "/api/system/configs/catalog?module=system&config_group=security",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["data"]["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(all(item["module"] == "system" for item in items))
        self.assertTrue(all(item["config_group"] == "security" for item in items))

        env_response = self.client.get(
            "/api/system/configs/catalog?source=env_registry",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(env_response.status_code, 200, env_response.text)
        env_items = env_response.json()["data"]["items"]
        self.assertGreaterEqual(len(env_items), 1)
        self.assertTrue(all(item["source"] == "env_registry" for item in env_items))

        unknown = self.client.get(
            "/api/system/configs/catalog?source=unknown_source",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(unknown.status_code, 200, unknown.text)
        self.assertEqual(unknown.json()["data"]["items"], [])
        self.assertEqual(unknown.json()["data"]["total"], 0)

    def test_is_sensitive_filter_and_invalid_value(self) -> None:
        sensitive = self.client.get(
            "/api/system/configs/catalog?is_sensitive=true",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(sensitive.status_code, 200, sensitive.text)
        sensitive_items = sensitive.json()["data"]["items"]
        self.assertGreaterEqual(len(sensitive_items), 1)
        self.assertTrue(all(item["is_sensitive"] is True for item in sensitive_items))

        non_sensitive = self.client.get(
            "/api/system/configs/catalog?is_sensitive=false",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(non_sensitive.status_code, 200, non_sensitive.text)
        non_sensitive_items = non_sensitive.json()["data"]["items"]
        self.assertGreaterEqual(len(non_sensitive_items), 1)
        self.assertTrue(all(item["is_sensitive"] is False for item in non_sensitive_items))

        invalid = self.client.get(
            "/api/system/configs/catalog?is_sensitive=invalid",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_no_write_route_registered(self) -> None:
        routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/system")]
        self.assertTrue(routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_main_route_mapping_for_system_configs_catalog(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/system/configs/catalog",
            "raw_path": b"/api/system/configs/catalog",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "system")
        self.assertEqual(action, SYSTEM_CONFIG_READ)
        self.assertEqual(resource_type, "SystemConfigCatalog")
        self.assertIsNone(resource_id)

    def test_system_files_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/system_management.py"),
            Path("app/services/system_config_catalog_service.py"),
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
            "erpnext",
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
            "diagnostic",
            "cache_refresh",
            "platform_manage",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, lowered)


if __name__ == "__main__":
    unittest.main()
