"""Report catalog CSV export security baseline tests (TASK-060C)."""

from __future__ import annotations

import csv
from io import StringIO
import os
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import REPORT_EXPORT
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.report import get_db_session as report_db_dep
from app.schemas.report import ReportCatalogItemData
from app.schemas.report import ReportCatalogListData
from app.schemas.report import ReportCatalogRequestedScope


def _csv_rows(content: bytes) -> list[list[str]]:
    return list(csv.reader(StringIO(content.decode("utf-8"))))


class ReportCatalogExportApiTest(unittest.TestCase):
    """Validate report catalog export permission and CSV safety rules."""

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
            "X-LY-Dev-User": "report.export.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_export_requires_report_export_permission(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/export",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_other_module_roles_cannot_replace_report_export(self) -> None:
        for role in ("dashboard:read", "quality:read", "sales_inventory:read", "warehouse:read", "inventory:read"):
            response = self.client.get(
                "/api/reports/catalog/export",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_export_contains_task_019_required_report_keys(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/export",
            headers=self._headers_with_roles("report:export"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(
            rows[0],
            [
                "report_key",
                "name",
                "source_modules",
                "report_type",
                "required_filters",
                "optional_filters",
                "metric_summary",
                "permission_action",
                "status",
            ],
        )
        keys = {row[0] for row in rows[1:]}
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

    def test_export_filter_by_source_module_and_report_type(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/export?source_module=quality&report_type=readonly",
            headers=self._headers_with_roles("report:export"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "quality_statistics")

    def test_invalid_source_module_or_report_type_returns_400(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/export?source_module=unknown_mod",
            headers=self._headers_with_roles("report:export"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

        response = self.client.get(
            "/api/reports/catalog/export?report_type=writeable",
            headers=self._headers_with_roles("report:export"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_csv_formula_injection_values_are_escaped(self) -> None:
        payload = ReportCatalogListData(
            items=[
                ReportCatalogItemData(
                    report_key="=cmd|'/C calc'!A0",
                    name="+SUM(1,2)",
                    source_modules=["-10"],
                    report_type="readonly",
                    required_filters=['@HYPERLINK("http://evil")'],
                    optional_filters=[],
                    metric_summary=[],
                    permission_action="report:export",
                    status="designed",
                )
            ],
            requested_scope=ReportCatalogRequestedScope(company=None, source_module=None, report_type=None),
        )
        with patch("app.routers.report.ReportCatalogService.list_catalog", return_value=payload):
            response = self.client.get(
                "/api/reports/catalog/export",
                headers=self._headers_with_roles("report:export"),
            )
        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(rows[1][0], "'=cmd|'/C calc'!A0")
        self.assertEqual(rows[1][1], "'+SUM(1,2)")
        self.assertEqual(rows[1][2], "'-10")
        self.assertEqual(rows[1][4], "'@HYPERLINK(\"http://evil\")")

    def test_content_disposition_uses_safe_fixed_prefix(self) -> None:
        response = self.client.get(
            "/api/reports/catalog/export?company=UNSAFE_COMPANY&source_module=quality&report_type=readonly",
            headers=self._headers_with_roles("report:export"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        content_type = response.headers.get("content-type", "")
        disposition = response.headers.get("content-disposition", "")
        self.assertTrue(content_type.startswith("text/csv"))
        self.assertIn("attachment;", disposition)
        self.assertIn("report_catalog_export_", disposition)
        self.assertNotIn("UNSAFE_COMPANY", disposition)
        self.assertNotIn("quality", disposition)
        self.assertNotIn("readonly", disposition)

    def test_main_route_mapping_for_catalog_export(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/reports/catalog/export",
            "raw_path": b"/api/reports/catalog/export",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "report")
        self.assertEqual(action, REPORT_EXPORT)
        self.assertEqual(resource_type, "ReportCatalogExport")
        self.assertIsNone(resource_id)


if __name__ == "__main__":
    unittest.main()
