"""API tests for sales/inventory read-only integration (TASK-011B)."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.schemas.sales_inventory import SalesOrderFulfillmentData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


class SalesInventoryApiBase(unittest.TestCase):
    """Shared in-memory app wiring."""

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
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
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
    def _headers(role: str = "Sales Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "sales.inventory.user", "X-LY-Dev-Roles": role}


class SalesInventoryApiTest(SalesInventoryApiBase):
    """Read-only API behavior."""

    def test_list_sales_orders_success(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_sales_orders",
            return_value=(
                [
                    {
                        "name": "SO-001",
                        "company": "COMP-A",
                        "customer": "CUST-A",
                        "transaction_date": "2026-04-01",
                        "delivery_date": "2026-04-10",
                        "status": "To Deliver",
                        "docstatus": 1,
                        "grand_total": "120.50",
                        "currency": "CNY",
                    }
                ],
                1,
            ),
        ):
            response = self.client.get("/api/sales-inventory/sales-orders", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["total"], 1)
        self.assertEqual(payload["data"]["items"][0]["name"], "SO-001")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyOperationAuditLog).count(), 0)

    def test_list_sales_orders_supports_item_name_and_date_range_filters(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_sales_orders",
            return_value=([], 0),
        ) as mocked_list:
            response = self.client.get(
                "/api/sales-inventory/sales-orders"
                "?company=COMP-A&customer=CUST-A&item_code=ITEM-A&item_name=%E6%B5%8B%E8%AF%95&from_date=2026-04-01&to_date=2026-04-30",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once()
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["company"], "COMP-A")
        self.assertEqual(kwargs["customer"], "CUST-A")
        self.assertEqual(kwargs["item_code"], "ITEM-A")
        self.assertEqual(kwargs["item_name"], "测试")
        self.assertEqual(str(kwargs["from_date"]), "2026-04-01")
        self.assertEqual(str(kwargs["to_date"]), "2026-04-30")

    def test_list_sales_orders_invalid_date_range_returns_bad_request(self) -> None:
        response = self.client.get(
            "/api/sales-inventory/sales-orders?from_date=2026-05-01&to_date=2026-04-01",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_stock_ledger_supports_date_range_filters(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_stock_ledger",
            return_value=([], 0, 0),
        ) as mocked_list:
            response = self.client.get(
                "/api/sales-inventory/items/ITEM-A/stock-ledger"
                "?company=COMP-A&warehouse=WH-A&from_date=2026-04-01&to_date=2026-04-30",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once()
        kwargs = mocked_list.call_args.kwargs
        self.assertEqual(kwargs["company"], "COMP-A")
        self.assertEqual(kwargs["warehouse"], "WH-A")
        self.assertEqual(str(kwargs["from_date"]), "2026-04-01")
        self.assertEqual(str(kwargs["to_date"]), "2026-04-30")

    def test_stock_ledger_invalid_date_format_returns_bad_request(self) -> None:
        response = self.client.get(
            "/api/sales-inventory/items/ITEM-A/stock-ledger?from_date=2026/04/01",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_detail_denied_before_erpnext_read_to_hide_existence(self) -> None:
        with patch.object(ERPNextSalesInventoryAdapter, "get_sales_order") as mocked_detail:
            response = self.client.get(
                "/api/sales-inventory/sales-orders/SO-SECRET",
                headers=self._headers(role="Viewer"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        mocked_detail.assert_not_called()
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_detail_resource_denied_returns_not_found_to_hide_existence(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "get_sales_order",
            return_value={
                "name": "SO-002",
                "company": "COMP-B",
                "customer": "CUST-B",
                "transaction_date": "2026-04-01",
                "status": "To Deliver",
                "docstatus": 1,
                "items": [],
            },
        ), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
            ),
        ):
            response = self.client.get(
                "/api/sales-inventory/sales-orders/SO-002",
                headers=self._headers(role="Sales Manager"),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESOURCE_NOT_FOUND")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).one()
            self.assertEqual(row.event_type, "RESOURCE_ACCESS_DENIED")
            self.assertEqual(row.module, "sales_inventory")

    def test_detail_not_found_and_out_of_scope_share_not_found_shape(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "get_sales_order",
            side_effect=ERPNextAdapterException(
                error_code="ERPNEXT_RESOURCE_NOT_FOUND",
                http_status=404,
                safe_message="ERPNext 资源不存在",
            ),
        ):
            response = self.client.get(
                "/api/sales-inventory/sales-orders/SO-MISSING",
                headers=self._headers(role="Sales Manager"),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESOURCE_NOT_FOUND")

    def test_customers_empty_customer_permissions_filter_all(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_customers",
            return_value=(
                [
                    {"name": "CUST-A", "customer_name": "客户 A", "disabled": 0},
                    {"name": "CUST-B", "customer_name": "客户 B", "disabled": 0},
                ],
                2,
            ),
        ), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
                allowed_customers=set(),
            ),
        ):
            response = self.client.get("/api/sales-inventory/customers", headers=self._headers(role="Sales Manager"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total"], 0)
        self.assertEqual(response.json()["data"]["items"], [])

    def test_erpnext_unavailable_fails_closed_and_records_security_audit(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_sales_orders",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="ERPNext down"),
        ):
            response = self.client.get("/api/sales-inventory/sales-orders", headers=self._headers())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "EXTERNAL_SERVICE_UNAVAILABLE")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).one()
            self.assertEqual(row.event_type, "EXTERNAL_SERVICE_UNAVAILABLE")
            self.assertEqual(row.module, "sales_inventory")

    def test_stock_ledger_read_drops_invalid_sle_rows(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_stock_ledger",
            return_value=(
                [
                    {
                        "name": "SLE-OK",
                        "company": "COMP-A",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "posting_date": "2026-04-01",
                        "actual_qty": Decimal("1"),
                        "qty_after_transaction": Decimal("9"),
                    }
                ],
                1,
                1,
            ),
        ):
            response = self.client.get("/api/sales-inventory/items/ITEM-A/stock-ledger", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["dropped_count"], 1)
        self.assertEqual(payload["items"][0]["name"], "SLE-OK")

    def test_warehouses_filter_by_allowed_warehouses(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_warehouses",
            return_value=(
                [
                    {"name": "WH-A", "company": "COMP-A", "warehouse_name": "仓A", "disabled": 0},
                    {"name": "WH-B", "company": "COMP-A", "warehouse_name": "仓B", "disabled": 0},
                ],
                2,
            ),
        ), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
            ),
        ):
            response = self.client.get("/api/sales-inventory/warehouses?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["name"], "WH-A")

    def test_aggregation_filter_by_allowed_warehouses(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_warehouses",
            return_value=([{"name": "WH-A", "company": "COMP-A"}], 1),
        ), patch.object(
            ERPNextSalesInventoryAdapter,
            "_list_resource",
            return_value=[
                {
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "actual_qty": "5",
                    "ordered_qty": "1",
                    "indented_qty": "0",
                    "safety_stock": "3",
                    "reorder_level": "2",
                },
                {
                    "item_code": "ITEM-A",
                    "warehouse": "WH-B",
                    "actual_qty": "8",
                    "ordered_qty": "1",
                    "indented_qty": "0",
                    "safety_stock": "3",
                    "reorder_level": "2",
                },
            ],
        ), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
            ),
        ):
            response = self.client.get(
                "/api/sales-inventory/aggregation?company=COMP-A&item_code=ITEM-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["warehouse"], "WH-A")

    def test_fulfillment_denies_out_of_scope_warehouse_query(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
            ),
        ), patch(
            "app.routers.sales_inventory.SalesInventoryService.get_sales_order_fulfillment",
            return_value=SalesOrderFulfillmentData(company="COMP-A", items=[]),
        ) as mocked_fulfillment:
            response = self.client.get(
                "/api/sales-inventory/sales-order-fulfillment?company=COMP-A&warehouse=WH-B",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")
        mocked_fulfillment.assert_not_called()

    def test_only_get_routes_are_exposed(self) -> None:
        methods_by_path = {
            route.path: route.methods
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/sales-inventory")
        }
        self.assertTrue(methods_by_path)
        for methods in methods_by_path.values():
            self.assertLessEqual(set(methods), {"GET", "HEAD", "OPTIONS"})
