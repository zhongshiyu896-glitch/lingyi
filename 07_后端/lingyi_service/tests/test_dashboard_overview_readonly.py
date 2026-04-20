"""Dashboard overview read-only baseline tests (TASK-060A)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import DASHBOARD_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.dashboard import get_db_session as dashboard_db_dep
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException


class DashboardOverviewReadonlyApiTest(unittest.TestCase):
    """Validate dashboard overview contract, permissions and readonly boundary."""

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
        app.dependency_overrides[dashboard_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(dashboard_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "dashboard.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_dashboard_read_can_access_overview(self) -> None:
        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=3,
                total_inspected_qty=Decimal("100"),
                total_accepted_qty=Decimal("95"),
                total_rejected_qty=Decimal("5"),
                total_defect_qty=Decimal("2"),
            ),
        ), patch(
            "app.services.sales_inventory_service.SalesInventoryService.get_inventory_aggregation",
            return_value=SimpleNamespace(
                items=[
                    SimpleNamespace(actual_qty=Decimal("10"), is_below_safety=True, is_below_reorder=False),
                    SimpleNamespace(actual_qty=Decimal("20"), is_below_safety=False, is_below_reorder=True),
                ]
            ),
        ), patch(
            "app.services.warehouse_service.WarehouseService.get_alerts",
            return_value=SimpleNamespace(
                items=[
                    SimpleNamespace(severity="high"),
                    SimpleNamespace(severity="medium"),
                    SimpleNamespace(severity="medium"),
                ]
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A&from_date=2026-04-01&to_date=2026-04-20",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(payload["quality"]["inspection_count"], 3)
        self.assertEqual(payload["sales_inventory"]["item_count"], 2)
        self.assertEqual(payload["sales_inventory"]["below_safety_count"], 1)
        self.assertEqual(payload["sales_inventory"]["below_reorder_count"], 1)
        self.assertEqual(payload["warehouse"]["alert_count"], 3)
        self.assertEqual(payload["warehouse"]["critical_alert_count"], 1)
        self.assertEqual(payload["warehouse"]["warning_alert_count"], 2)
        self.assertEqual([row["module"] for row in payload["source_status"]], ["quality", "sales_inventory", "warehouse"])

    def test_module_read_actions_cannot_replace_dashboard_read(self) -> None:
        for role in ("quality:read", "sales_inventory:read", "warehouse:read", "inventory:read"):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_company_missing_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_company_empty_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_invalid_date_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=COMP-A&from_date=2026/04/01",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_from_date_later_than_to_date_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=COMP-A&from_date=2026-04-21&to_date=2026-04-20",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_source_unavailable_is_fail_closed(self) -> None:
        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=1,
                total_inspected_qty=Decimal("1"),
                total_accepted_qty=Decimal("1"),
                total_rejected_qty=Decimal("0"),
                total_defect_qty=Decimal("0"),
            ),
        ), patch(
            "app.services.sales_inventory_service.SalesInventoryService.get_inventory_aggregation",
            side_effect=ERPNextAdapterException(
                error_code="EXTERNAL_SERVICE_UNAVAILABLE",
                http_status=503,
                safe_message="sales source unavailable",
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["code"], "DASHBOARD_SOURCE_UNAVAILABLE")
        self.assertEqual(body["data"]["module"], "sales_inventory")

    def test_no_write_route_registered(self) -> None:
        dashboard_routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/dashboard")]
        self.assertTrue(dashboard_routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in dashboard_routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_main_route_mapping_for_dashboard_overview(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/dashboard/overview",
            "raw_path": b"/api/dashboard/overview",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "dashboard")
        self.assertEqual(action, DASHBOARD_READ)
        self.assertEqual(resource_type, "DashboardOverview")
        self.assertIsNone(resource_id)

    def test_dashboard_files_no_write_signatures(self) -> None:
        files = [
            Path("app/routers/dashboard.py"),
            Path("app/services/dashboard_service.py"),
            Path("app/schemas/dashboard.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "outbox",
            "worker",
            "run-once",
            "internal",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)


if __name__ == "__main__":
    unittest.main()
