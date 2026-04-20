"""Readonly report catalog baseline tests (TASK-060B)."""

from __future__ import annotations

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
from app.core.permissions import REPORT_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.report import get_db_session as report_db_dep


class ReportCatalogReadonlyApiTest(unittest.TestCase):
    """Validate report catalog contract, permissions and readonly boundaries."""

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
            "X-LY-Dev-User": "report.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_report_read_can_access_catalog(self) -> None:
        response = self.client.get(
            "/api/reports/catalog?company=COMP-A",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertGreaterEqual(len(payload["items"]), 7)
        self.assertEqual(payload["requested_scope"]["company"], "COMP-A")

    def test_module_read_actions_cannot_replace_report_read(self) -> None:
        for role in ("dashboard:read", "quality:read", "sales_inventory:read", "warehouse:read", "inventory:read"):
            response = self.client.get(
                "/api/reports/catalog",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_catalog_contains_task_019_required_report_keys(self) -> None:
        response = self.client.get(
            "/api/reports/catalog",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        keys = {item["report_key"] for item in response.json()["data"]["items"]}
        expected = {
            "production_progress",
            "inventory_trend",
            "style_profit_trend",
            "factory_statement_summary",
            "sales_inventory_view",
            "quality_statistics",
            "financial_summary",
        }
        self.assertTrue(expected.issubset(keys))

    def test_source_module_and_report_type_filters_work(self) -> None:
        response = self.client.get(
            "/api/reports/catalog?source_module=quality&report_type=readonly",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["report_key"], "quality_statistics")

    def test_invalid_source_module_returns_400(self) -> None:
        response = self.client.get(
            "/api/reports/catalog?source_module=unknown_mod",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_invalid_report_type_returns_400(self) -> None:
        response = self.client.get(
            "/api/reports/catalog?report_type=writeable",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_catalog_detail_found(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/inventory_trend?company=COMP-A",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["data"]["item"]
        self.assertEqual(item["report_key"], "inventory_trend")
        self.assertEqual(response.json()["data"]["requested_scope"]["company"], "COMP-A")

    def test_catalog_detail_not_found_returns_404(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/not_exists",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "REPORT_NOT_FOUND")

    def test_no_write_route_registered(self) -> None:
        report_routes = [
            route
            for route in app.routes
            if str(getattr(route, "path", "")).startswith("/api/reports/catalog")
        ]
        self.assertTrue(report_routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in report_routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_main_route_mapping_for_reports_catalog(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/reports/catalog",
            "raw_path": b"/api/reports/catalog",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "report")
        self.assertEqual(action, REPORT_READ)
        self.assertEqual(resource_type, "ReportCatalog")
        self.assertIsNone(resource_id)

        detail_scope = dict(scope)
        detail_scope["path"] = "/api/reports/catalog/inventory_trend"
        detail_scope["raw_path"] = b"/api/reports/catalog/inventory_trend"
        detail_request = Request(detail_scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(detail_request)
        self.assertEqual(module, "report")
        self.assertEqual(action, REPORT_READ)
        self.assertEqual(resource_type, "ReportCatalog")
        self.assertEqual(resource_id, "inventory_trend")

    def test_report_files_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/report.py"),
            Path("app/services/report_catalog_service.py"),
            Path("app/schemas/report.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "requests.",
            "httpx.",
            "/api/resource",
            "outbox",
            "worker",
            "run-once",
            "internal",
            "diagnostic",
            "cache_refresh",
            "recalculate",
            "generate",
            "sync",
            "submit",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)


if __name__ == "__main__":
    unittest.main()
