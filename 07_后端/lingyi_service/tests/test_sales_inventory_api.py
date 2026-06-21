"""API tests for sales/inventory read-only integration (TASK-011B)."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from decimal import Decimal
import json
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
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
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
        QualityBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)

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
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Sales Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "sales.inventory.user", "X-LY-Dev-Roles": role}

    def _seed_stock_entry(
        self,
        *,
        company: str = "COMP-A",
        item_code: str = "ITEM-A",
        warehouse: str = "WH-A",
        qty: str = "10",
        purpose: str = "Material Receipt",
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
        event_key: str = "EVT-SALES-INV-STOCK-001",
        created_at: datetime | None = None,
    ) -> None:
        posting_at = created_at or datetime(2026, 4, 1, tzinfo=timezone.utc)
        source_wh = (
            source_warehouse
            if source_warehouse is not None
            else (warehouse if purpose in {"Material Issue", "Material Transfer"} else None)
        )
        target_wh = (
            target_warehouse
            if target_warehouse is not None
            else (warehouse if purpose != "Material Issue" else None)
        )
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company=company,
                purpose=purpose,
                source_type="test",
                source_id=event_key,
                source_warehouse=source_wh,
                target_warehouse=target_wh,
                status="pending_outbox",
                created_by="seed",
                created_at=posting_at,
                idempotency_key=f"{event_key}:idem",
                event_key=event_key,
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company=company,
                    item_code=item_code,
                    qty=Decimal(qty),
                    uom="PCS",
                    source_warehouse=source_wh,
                    target_warehouse=target_wh,
                )
            )
            session.commit()

    def _seed_sales_order(
        self,
        *,
        sales_order_no: str,
        company: str = "COMP-A",
        customer: str = "CUST-A",
        item_code: str = "ITEM-A",
    ) -> None:
        with self.SessionLocal() as session:
            order = LySalesOrder(
                sales_order_no=sales_order_no,
                source_order_ref=sales_order_no,
                company=company,
                customer=customer,
                status="draft",
                docstatus=0,
                transaction_date=datetime(2026, 4, 1).date(),
                delivery_date=datetime(2026, 4, 10).date(),
                currency="CNY",
                grand_total=Decimal("120.50"),
                idempotency_key=f"{sales_order_no}:idem",
                request_hash=f"{sales_order_no}:hash",
                payload={},
                created_by="seed",
            )
            session.add(order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company=company,
                    line_no=1,
                    sales_order_item=f"{sales_order_no}-001",
                    item_code=item_code,
                    item_name=item_code,
                    qty=Decimal("1"),
                    rate=Decimal("120.50"),
                    amount=Decimal("120.50"),
                    uom="PCS",
                    ys_material_calc_state="待算料",
                )
            )
            session.commit()


class SalesInventoryApiTest(SalesInventoryApiBase):
    """Read-only API behavior."""

    def test_fastapi_diagnostic_does_not_construct_erpnext_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        with patch(
            "app.routers.sales_inventory.ERPNextSalesInventoryAdapter",
            side_effect=AssertionError("ERPNext must not be used in fastapi diagnostic"),
        ):
            response = self.client.get("/api/sales-inventory/diagnostic", headers=self._headers(role="System Manager"))

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["source"], "fastapi")
        self.assertEqual(payload["data"]["status"], "ok")
        self.assertIn("checked_at", payload["data"])

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

    def test_stock_ledger_local_fallback_uses_warehouse_movement_balances(self) -> None:
        self._seed_stock_entry(
            qty="10",
            purpose="Material Receipt",
            event_key="EVT-SALES-INV-STOCK-001",
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        self._seed_stock_entry(
            qty="4",
            purpose="Material Issue",
            event_key="EVT-SALES-INV-STOCK-002",
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        self._seed_stock_entry(
            qty="2",
            purpose="Material Transfer",
            source_warehouse="WH-A",
            target_warehouse="WH-B",
            event_key="EVT-SALES-INV-STOCK-003",
            created_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
        )
        external_down = ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down")
        with patch.object(ERPNextSalesInventoryAdapter, "list_stock_ledger", side_effect=external_down):
            ledger = self.client.get(
                "/api/sales-inventory/items/ITEM-A/stock-ledger?company=COMP-A&page=1&page_size=20",
                headers=self._headers(),
            )
        with patch.object(ERPNextSalesInventoryAdapter, "get_stock_summary", side_effect=external_down):
            summary = self.client.get(
                "/api/sales-inventory/items/ITEM-A/stock-summary?company=COMP-A",
                headers=self._headers(),
            )

        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_payload = ledger.json()["data"]
        self.assertEqual(ledger_payload["dropped_count"], 0)
        self.assertEqual(ledger_payload["total"], 4)
        movement_rows = [
            (
                row["warehouse"],
                Decimal(str(row["actual_qty"])),
                Decimal(str(row["qty_after_transaction"])),
                row["voucher_type"],
            )
            for row in ledger_payload["items"]
        ]
        self.assertEqual(
            movement_rows,
            [
                ("WH-A", Decimal("10.000000"), Decimal("10.000000"), "Stock Entry Draft/Material Receipt"),
                ("WH-A", Decimal("-4.000000"), Decimal("6.000000"), "Stock Entry Draft/Material Issue"),
                ("WH-A", Decimal("-2.000000"), Decimal("4.000000"), "Stock Entry Draft/Material Transfer"),
                ("WH-B", Decimal("2.000000"), Decimal("2.000000"), "Stock Entry Draft/Material Transfer"),
            ],
        )
        self.assertNotIn("valuation_rate", ledger_payload["items"][0])
        self.assertIsNone(ledger_payload["items"][0]["name"])
        self.assertIsNone(ledger_payload["items"][0]["posting_time"])

        self.assertEqual(summary.status_code, 200, summary.text)
        summary_rows = {
            row["warehouse"]: Decimal(str(row["balance_qty"]))
            for row in summary.json()["data"]["items"]
        }
        self.assertEqual(summary_rows, {"WH-A": Decimal("4.000000"), "WH-B": Decimal("2.000000")})

    def test_stock_reads_fastapi_use_local_source_without_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "sales.inventory.user": {
                        "companies": ["COMP-A"],
                        "item_codes": ["ITEM-A"],
                        "warehouses": ["WH-A"],
                    }
                }
            }
        )
        self._seed_stock_entry(
            qty="10",
            purpose="Material Receipt",
            event_key="EVT-SALES-INV-FASTAPI-STOCK-001",
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        self._seed_stock_entry(
            qty="3",
            purpose="Material Issue",
            event_key="EVT-SALES-INV-FASTAPI-STOCK-002",
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        with patch.object(ERPNextSalesInventoryAdapter, "list_stock_ledger") as mocked_ledger, patch.object(
            ERPNextSalesInventoryAdapter,
            "get_stock_summary",
        ) as mocked_summary, patch.object(
            ERPNextSalesInventoryAdapter,
            "_list_resource",
        ) as mocked_bin:
            ledger = self.client.get(
                "/api/sales-inventory/items/ITEM-A/stock-ledger?company=COMP-A&page=1&page_size=20",
                headers=self._headers(),
            )
            summary = self.client.get(
                "/api/sales-inventory/items/ITEM-A/stock-summary?company=COMP-A",
                headers=self._headers(),
            )
            aggregation = self.client.get(
                "/api/sales-inventory/aggregation?company=COMP-A&item_code=ITEM-A",
                headers=self._headers(),
            )

        self.assertEqual(ledger.status_code, 200, ledger.text)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(aggregation.status_code, 200, aggregation.text)
        self.assertEqual(ledger.json()["data"]["total"], 2)
        self.assertEqual(Decimal(str(summary.json()["data"]["items"][0]["balance_qty"])), Decimal("7.000000"))
        aggregation_payload = aggregation.json()["data"]
        self.assertEqual(aggregation_payload["items"][0]["warehouse"], "WH-A")
        self.assertEqual(Decimal(str(aggregation_payload["items"][0]["actual_qty"])), Decimal("7.000000"))
        mocked_ledger.assert_not_called()
        mocked_summary.assert_not_called()
        mocked_bin.assert_not_called()

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

    def test_sales_orders_fastapi_scope_filters_rows(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "sales.inventory.user": {
                        "companies": ["COMP-A"],
                        "customers": ["CUST-A"],
                    }
                }
            }
        )
        self._seed_sales_order(sales_order_no="SO-FASTAPI-A", company="COMP-A", customer="CUST-A")
        self._seed_sales_order(sales_order_no="SO-FASTAPI-B", company="COMP-B", customer="CUST-B")
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_sales_orders",
        ) as mocked_list:
            response = self.client.get("/api/sales-inventory/sales-orders", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["name"], "SO-FASTAPI-A")
        mocked_list.assert_not_called()

    def test_sales_orders_fastapi_empty_local_does_not_call_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        with patch.object(ERPNextSalesInventoryAdapter, "list_sales_orders") as mocked_list:
            response = self.client.get("/api/sales-inventory/sales-orders", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["items"], [])
        self.assertEqual(response.json()["data"]["total"], 0)
        mocked_list.assert_not_called()

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

    def test_warehouses_fastapi_scope_filters_allowed_warehouses(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "sales.inventory.user": {
                        "companies": ["COMP-A"],
                        "warehouses": ["WH-A"],
                    }
                }
            }
        )
        self._seed_stock_entry(
            company="COMP-A",
            item_code="ITEM-A",
            warehouse="WH-A",
            event_key="EVT-SALES-INV-FASTAPI-WH-A",
        )
        self._seed_stock_entry(
            company="COMP-A",
            item_code="ITEM-B",
            warehouse="WH-B",
            event_key="EVT-SALES-INV-FASTAPI-WH-B",
        )
        with patch.object(ERPNextSalesInventoryAdapter, "list_warehouses") as mocked_list:
            response = self.client.get("/api/sales-inventory/warehouses?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["name"], "WH-A")
        mocked_list.assert_not_called()

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

    def test_fulfillment_denies_out_of_scope_warehouse_query_fastapi(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "sales.inventory.user": {
                        "companies": ["COMP-A"],
                        "item_codes": ["ITEM-A"],
                        "warehouses": ["WH-A"],
                    }
                }
            }
        )
        with patch(
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
        local_write_routes = {
            "/api/sales-inventory/delivery-invoices": {"POST"},
            "/api/sales-inventory/delivery-invoices/{invoice_id}/cancel": {"POST"},
            "/api/sales-inventory/payment-entries": {"POST"},
            "/api/sales-inventory/payment-entries/{payment_id}/cancel": {"POST"},
            "/api/sales-inventory/sales-orders/drafts": {"POST"},
            "/api/sales-inventory/sales-orders/drafts/{draft_id}": {"PATCH"},
            "/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel": {"POST"},
            "/api/sales-inventory/sales-orders/drafts/{draft_id}/submit": {"POST"},
        }
        post_routes = {path for path, methods in methods_by_path.items() if "POST" in methods}
        self.assertEqual(post_routes, {path for path, methods in local_write_routes.items() if "POST" in methods})
        self.assertLessEqual(set(local_write_routes), set(methods_by_path))
        for path, methods in methods_by_path.items():
            expected_methods = local_write_routes.get(path, {"GET", "HEAD", "OPTIONS"})
            self.assertLessEqual(set(methods), expected_methods, path)
