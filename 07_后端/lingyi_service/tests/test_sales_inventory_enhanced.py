"""Enhanced read-only sales inventory tests (TASK-040A)."""

from __future__ import annotations

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
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


class SalesInventoryEnhancedApiBase(unittest.TestCase):
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


class SalesInventoryEnhancedApiTest(SalesInventoryEnhancedApiBase):
    """TASK-040A enhanced read-only endpoints."""

    def test_inventory_aggregation_company_filter_and_low_stock_flags(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_warehouses",
            return_value=(
                [
                    {"name": "WH-A", "company": "COMP-A"},
                ],
                1,
            ),
        ), patch.object(
            ERPNextSalesInventoryAdapter,
            "_list_resource",
            return_value=[
                {
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "actual_qty": "3",
                    "ordered_qty": "2",
                    "indented_qty": "1",
                    "safety_stock": "5",
                    "reorder_level": "4",
                },
                {
                    "item_code": "ITEM-A",
                    "warehouse": "WH-B",
                    "actual_qty": "9",
                    "ordered_qty": "0",
                    "indented_qty": "0",
                    "safety_stock": "2",
                    "reorder_level": "1",
                },
            ],
        ):
            response = self.client.get(
                "/api/sales-inventory/aggregation?company=COMP-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(len(payload["items"]), 1)
        row = payload["items"][0]
        self.assertEqual(row["item_code"], "ITEM-A")
        self.assertEqual(row["warehouse"], "WH-A")
        self.assertEqual(row["actual_qty"], "3")
        self.assertTrue(row["is_below_safety"])
        self.assertTrue(row["is_below_reorder"])

    def test_sales_order_fulfillment_rate_min_one_and_company_scoped(self) -> None:
        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_warehouses",
            return_value=(
                [
                    {"name": "WH-A", "company": "COMP-A"},
                ],
                1,
            ),
        ), patch.object(
            ERPNextSalesInventoryAdapter,
            "_list_resource",
            return_value=[
                {
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "actual_qty": "8",
                    "ordered_qty": "0",
                    "indented_qty": "0",
                    "safety_stock": "3",
                    "reorder_level": "2",
                },
                {
                    "item_code": "ITEM-B",
                    "warehouse": "WH-A",
                    "actual_qty": "2",
                    "ordered_qty": "0",
                    "indented_qty": "0",
                    "safety_stock": "3",
                    "reorder_level": "2",
                },
            ],
        ), patch.object(
            ERPNextSalesInventoryAdapter,
            "list_sales_orders",
            side_effect=[
                (
                    [
                        {
                            "name": "SO-001",
                            "company": "COMP-A",
                        }
                    ],
                    1,
                ),
                ([], 0),
            ],
        ), patch.object(
            ERPNextSalesInventoryAdapter,
            "get_sales_order",
            return_value={
                "name": "SO-001",
                "company": "COMP-A",
                "docstatus": 1,
                "items": [
                    {"item_code": "ITEM-A", "warehouse": "WH-A", "qty": "5"},
                    {"item_code": "ITEM-B", "warehouse": "WH-A", "qty": "10"},
                ],
            },
        ):
            response = self.client.get(
                "/api/sales-inventory/sales-order-fulfillment?company=COMP-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(len(payload["items"]), 2)

        first, second = payload["items"]
        self.assertEqual(first["sales_order"], "SO-001")
        self.assertEqual(first["item_code"], "ITEM-A")
        self.assertEqual(first["fulfillment_rate"], "1")

        self.assertEqual(second["sales_order"], "SO-001")
        self.assertEqual(second["item_code"], "ITEM-B")
        self.assertEqual(second["fulfillment_rate"], "0.2")


if __name__ == "__main__":
    unittest.main()
