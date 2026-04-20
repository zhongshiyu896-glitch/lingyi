"""Warehouse read-only baseline tests (TASK-050A)."""

from __future__ import annotations

from datetime import date
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import WAREHOUSE_ALERT_READ
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.core.permissions import WAREHOUSE_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.schemas.warehouse import WarehouseStockSummaryData
from app.schemas.warehouse import WarehouseStockSummaryItem
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.warehouse_service import WarehouseService


class WarehouseReadonlyApiBase(unittest.TestCase):
    """Shared in-memory app wiring for warehouse tests."""

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
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
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
    def _headers(read_only: bool = False) -> dict[str, str]:
        if read_only:
            roles = "warehouse:read"
        else:
            roles = "warehouse:read,warehouse:alert_read"
        return WarehouseReadonlyApiBase._headers_with_roles(roles)

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.user",
            "X-LY-Dev-Roles": roles,
        }


class WarehouseReadonlyApiTest(WarehouseReadonlyApiBase):
    """Read-only API behavior and boundaries."""

    def test_stock_ledger_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_ledger",
            return_value=(
                [
                    {
                        "company": "COMP-A",
                        "warehouse": "WH-A",
                        "item_code": "ITEM-A",
                        "posting_date": date(2026, 4, 20),
                        "voucher_type": "Stock Entry",
                        "voucher_no": "STE-001",
                        "actual_qty": "2",
                        "qty_after_transaction": "10",
                        "valuation_rate": "8.5",
                    }
                ],
                1,
            ),
        ):
            response = self.client.get("/api/warehouse/stock-ledger?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["warehouse"], "WH-A")

    def test_stock_summary_returns_aggregation(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=[
                {
                    "company": "COMP-A",
                    "warehouse": "WH-A",
                    "item_code": "ITEM-A",
                    "actual_qty": "2",
                    "projected_qty": "3",
                    "reserved_qty": "1",
                    "ordered_qty": "5",
                    "reorder_level": "6",
                    "safety_stock": "4",
                }
            ],
        ):
            response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        row = response.json()["data"]["items"][0]
        self.assertTrue(row["is_below_reorder"])
        self.assertTrue(row["is_below_safety"])
        self.assertFalse(row["threshold_missing"])

    def test_alerts_returns_low_stock(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=[
                {
                    "company": "COMP-A",
                    "warehouse": "WH-A",
                    "item_code": "ITEM-A",
                    "actual_qty": "1",
                    "projected_qty": "1",
                    "reserved_qty": "0",
                    "ordered_qty": "0",
                    "reorder_level": "5",
                    "safety_stock": "3",
                }
            ],
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.latest_movement_by_item_warehouse",
            return_value={("ITEM-A", "WH-A"): date(2026, 4, 1)},
        ):
            response = self.client.get("/api/warehouse/alerts?alert_type=low_stock", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["alert_type"], "low_stock")

    def test_company_filter_passed_to_service(self) -> None:
        with patch.object(WarehouseService, "get_stock_summary") as mocked_summary:
            mocked_summary.return_value = WarehouseStockSummaryData(company="COMP-A", warehouse=None, item_code=None, items=[])
            response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        mocked_summary.assert_called_once()
        self.assertEqual(mocked_summary.call_args.kwargs["company"], "COMP-A")

    def test_warehouse_permission_filter_effective(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
                allowed_items={"ITEM-A"},
            ),
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=[
                {
                    "company": "COMP-A",
                    "warehouse": "WH-A",
                    "item_code": "ITEM-A",
                    "actual_qty": "2",
                    "projected_qty": "3",
                    "reserved_qty": "1",
                    "ordered_qty": "5",
                    "reorder_level": "6",
                    "safety_stock": "4",
                },
                {
                    "company": "COMP-A",
                    "warehouse": "WH-B",
                    "item_code": "ITEM-A",
                    "actual_qty": "2",
                    "projected_qty": "3",
                    "reserved_qty": "1",
                    "ordered_qty": "5",
                    "reorder_level": "6",
                    "safety_stock": "4",
                },
            ],
        ):
            response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["warehouse"], "WH-A")

    def test_invalid_date_range_returns_400(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-ledger?from_date=2026-05-01&to_date=2026-04-01",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_inventory_read_only_forbidden_on_stock_ledger(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-ledger",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_read_only_forbidden_on_stock_summary(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-summary",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_read_only_forbidden_on_alerts(self) -> None:
        response = self.client.get(
            "/api/warehouse/alerts",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_erpnext_malformed_data_fail_closed(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_ledger",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ):
            response = self.client.get("/api/warehouse/stock-ledger", headers=self._headers())

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESPONSE_INVALID")

    def test_no_write_route_registered(self) -> None:
        warehouse_routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/warehouse")]
        self.assertTrue(warehouse_routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        allowed_write_routes = {
            ("POST", "/api/warehouse/stock-entry-drafts"),  # TASK-050B 审计意见书第383份
            ("POST", "/api/warehouse/stock-entry-drafts/{draft_id}/cancel"),  # TASK-050B 审计意见书第383份
            ("POST", "/api/warehouse/internal/stock-entry-sync/run-once"),  # TASK-050D_FIX1 审计意见书第389份
            ("POST", "/api/warehouse/inventory-counts"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/submit"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/variance-review"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/confirm"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/cancel"),  # TASK-050C 审计意见书第385份
        }
        discovered_write_routes: set[tuple[str, str]] = set()
        for route in warehouse_routes:
            path = str(getattr(route, "path", ""))
            methods = {method.upper() for method in getattr(route, "methods", set())}
            for method in methods:
                if method in readonly_methods:
                    continue
                self.assertNotIn(method, {"PUT", "PATCH", "DELETE"})
                discovered_write_routes.add((method, path))
        self.assertSetEqual(discovered_write_routes, allowed_write_routes)

    def test_no_erpnext_write_call_signature(self) -> None:
        from app.routers import warehouse as warehouse_router_module
        from app.services import erpnext_warehouse_adapter as adapter_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
                open(adapter_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked_snippets = [
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "/api/resource/Stock Entry",
            "/api/resource/Stock Reconciliation",
            "/api/resource/Stock Ledger Entry",
        ]
        for snippet in blocked_snippets:
            self.assertNotIn(snippet, content)

    def test_warehouse_actions_registered(self) -> None:
        actions = MODULE_ACTION_REGISTRY.get("warehouse")
        self.assertIsNotNone(actions)
        expected = {WAREHOUSE_READ, WAREHOUSE_ALERT_READ, WAREHOUSE_EXPORT, WAREHOUSE_DIAGNOSTIC}
        self.assertTrue(expected.issubset(actions or set()))


if __name__ == "__main__":
    unittest.main()
