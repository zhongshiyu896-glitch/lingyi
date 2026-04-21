"""System dictionary catalog readonly baseline tests (TASK-080C)."""

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
from app.core.permissions import SYSTEM_DICTIONARY_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.system_management import get_db_session as system_management_db_dep


class SystemDictionaryCatalogReadonlyApiTest(unittest.TestCase):
    """Validate system dictionary catalog readonly contract and boundaries."""

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
            "X-LY-Dev-User": "system.dictionary.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_dictionary_requires_both_system_and_dictionary_actions(self) -> None:
        only_system_read = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("system:read"),
        )
        self.assertEqual(only_system_read.status_code, 403)

        only_dictionary_read = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("system:dictionary_read"),
        )
        self.assertEqual(only_dictionary_read.status_code, 403)

        both_actions = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(both_actions.status_code, 200, both_actions.text)

    def test_system_manager_can_access_dictionary_catalog(self) -> None:
        response = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("System Manager"),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_other_module_actions_cannot_replace_system_dictionary_actions(self) -> None:
        for role in (
            "permission:read",
            "dashboard:read",
            "report:read",
            "warehouse:read",
            "inventory:read",
        ):
            response = self.client.get(
                "/api/system/dictionaries/catalog",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_dictionary_response_contract_and_minimum_entries(self) -> None:
        response = self.client.get(
            "/api/system/dictionaries/catalog",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        payload = response.json()["data"]
        items = payload["items"]
        self.assertGreaterEqual(len(items), 6)
        self.assertEqual(payload["total"], len(items))

        dict_types = {item["dict_type"] for item in items}
        self.assertGreaterEqual(len(dict_types), 3)

        sources = {item["source"] for item in items}
        self.assertGreaterEqual(len(sources), 2)

        statuses = {item["status"] for item in items}
        self.assertIn("active", statuses)
        self.assertIn("inactive", statuses)

        expected_fields = {
            "dict_type",
            "dict_code",
            "dict_name",
            "status",
            "source",
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

    def test_filters_and_invalid_status(self) -> None:
        by_type = self.client.get(
            "/api/system/dictionaries/catalog?dict_type=currency",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(by_type.status_code, 200, by_type.text)
        by_type_items = by_type.json()["data"]["items"]
        self.assertGreaterEqual(len(by_type_items), 1)
        self.assertTrue(all(item["dict_type"] == "currency" for item in by_type_items))

        by_status = self.client.get(
            "/api/system/dictionaries/catalog?status=inactive",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(by_status.status_code, 200, by_status.text)
        by_status_items = by_status.json()["data"]["items"]
        self.assertGreaterEqual(len(by_status_items), 1)
        self.assertTrue(all(item["status"] == "inactive" for item in by_status_items))

        by_source = self.client.get(
            "/api/system/dictionaries/catalog?source=policy_registry",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(by_source.status_code, 200, by_source.text)
        by_source_items = by_source.json()["data"]["items"]
        self.assertGreaterEqual(len(by_source_items), 1)
        self.assertTrue(all(item["source"] == "policy_registry" for item in by_source_items))

        unknown = self.client.get(
            "/api/system/dictionaries/catalog?dict_type=unknown_type",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(unknown.status_code, 200, unknown.text)
        self.assertEqual(unknown.json()["data"]["items"], [])
        self.assertEqual(unknown.json()["data"]["total"], 0)

        invalid_status = self.client.get(
            "/api/system/dictionaries/catalog?status=unknown",
            headers=self._headers_with_roles("system:read,system:dictionary_read"),
        )
        self.assertEqual(invalid_status.status_code, 400)
        self.assertEqual(invalid_status.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_main_route_mapping_for_system_dictionaries_catalog(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/system/dictionaries/catalog",
            "raw_path": b"/api/system/dictionaries/catalog",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "system")
        self.assertEqual(action, SYSTEM_DICTIONARY_READ)
        self.assertEqual(resource_type, "SystemDictionaryCatalog")
        self.assertIsNone(resource_id)

    def test_no_write_route_registered(self) -> None:
        routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/system")]
        self.assertTrue(routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_system_dictionary_files_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/system_management.py"),
            Path("app/services/system_dictionary_catalog_service.py"),
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

    def test_task_080b_config_catalog_not_regressed(self) -> None:
        response = self.client.get(
            "/api/system/configs/catalog",
            headers=self._headers_with_roles("system:read,system:config_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertGreaterEqual(payload["total"], 6)
        self.assertIn("config_key", payload["items"][0])


if __name__ == "__main__":
    unittest.main()
