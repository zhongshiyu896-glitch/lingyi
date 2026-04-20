"""TASK-050C warehouse inventory-count baseline tests."""

from __future__ import annotations

from datetime import date
import os
import unittest

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
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class WarehouseInventoryCountApiBase(unittest.TestCase):
    """In-memory app wiring for warehouse inventory-count APIs."""

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
        with self.SessionLocal() as session:
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.counter",
            "X-LY-Dev-Roles": roles,
        }

    @staticmethod
    def _payload(
        *,
        company: str = "COMP-A",
        warehouse: str = "WH-A",
        count_date: str = "2026-04-20",
    ) -> dict:
        return {
            "company": company,
            "warehouse": warehouse,
            "count_date": count_date,
            "remark": "cycle count",
            "items": [
                {
                    "item_code": "ITEM-A",
                    "batch_no": None,
                    "serial_no": None,
                    "system_qty": "10",
                    "counted_qty": "8",
                    "variance_reason": "盘亏",
                },
                {
                    "item_code": "ITEM-B",
                    "batch_no": None,
                    "serial_no": None,
                    "system_qty": "5",
                    "counted_qty": "5",
                    "variance_reason": None,
                },
            ],
        }


class WarehouseInventoryCountApiTest(WarehouseInventoryCountApiBase):
    """Warehouse inventory-count state-machine contract."""

    def test_create_inventory_count_draft_with_permission(self) -> None:
        response = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["warehouse"], "WH-A")
        self.assertEqual(data["variance_stats"]["variance_items"], 1)
        self.assertEqual(data["items"][0]["variance_qty"], "-2.000000")

    def test_inventory_write_only_cannot_create_inventory_count(self) -> None:
        response = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("inventory:write"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_counted_qty_negative_returns_400(self) -> None:
        payload = self._payload()
        payload["items"][0]["counted_qty"] = "-1"
        response = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_QTY")

    def test_variance_without_reason_returns_400(self) -> None:
        payload = self._payload()
        payload["items"][0]["variance_reason"] = ""
        response = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WAREHOUSE_VARIANCE_REASON_REQUIRED")

    def test_state_machine_submit_review_confirm(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        count_id = int(create_resp.json()["data"]["id"])

        submit_resp = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/submit",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(submit_resp.status_code, 200, submit_resp.text)
        self.assertEqual(submit_resp.json()["data"]["status"], "counted")

        review_resp = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/variance-review",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(review_resp.status_code, 200, review_resp.text)
        self.assertEqual(review_resp.json()["data"]["status"], "variance_review")

        confirm_blocked = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/confirm",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(confirm_blocked.status_code, 409)
        self.assertEqual(confirm_blocked.json()["code"], "WAREHOUSE_VARIANCE_REVIEW_PENDING")

        detail = self.client.get(
            f"/api/warehouse/inventory-counts/{count_id}",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        variance_item_id = int(detail.json()["data"]["items"][0]["id"])
        review_complete = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/variance-review",
            headers=self._headers("warehouse:inventory_count"),
            json={
                "items": [
                    {
                        "item_id": variance_item_id,
                        "review_status": "accepted",
                        "variance_reason": "复核通过",
                    }
                ]
            },
        )
        self.assertEqual(review_complete.status_code, 200, review_complete.text)
        self.assertEqual(review_complete.json()["data"]["variance_stats"]["pending_review_items"], 0)

        confirm_ok = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/confirm",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(confirm_ok.status_code, 200, confirm_ok.text)
        self.assertEqual(confirm_ok.json()["data"]["status"], "confirmed")

        with self.SessionLocal() as session:
            item = (
                session.query(LyWarehouseInventoryCountItem)
                .filter(LyWarehouseInventoryCountItem.id == variance_item_id)
                .one()
            )
            self.assertEqual(str(item.counted_qty), "8.000000")

    def test_cancel_and_repeat_cancel(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=self._payload(),
        )
        count_id = int(create_resp.json()["data"]["id"])

        cancel_resp = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/cancel",
            headers=self._headers("warehouse:inventory_count"),
            json={"reason": "manual cancel"},
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")

        cancel_again = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/cancel",
            headers=self._headers("warehouse:inventory_count"),
            json={"reason": "again"},
        )
        self.assertEqual(cancel_again.status_code, 409)
        self.assertEqual(cancel_again.json()["code"], "WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED")

    def test_list_filters_by_company_and_warehouse(self) -> None:
        self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=self._payload(company="COMP-A", warehouse="WH-A"),
        )
        self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=self._payload(company="COMP-B", warehouse="WH-B", count_date="2026-04-21"),
        )

        list_resp = self.client.get(
            "/api/warehouse/inventory-counts?company=COMP-A&warehouse=WH-A",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(list_resp.status_code, 200, list_resp.text)
        rows = list_resp.json()["data"]["items"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "COMP-A")
        self.assertEqual(rows[0]["warehouse"], "WH-A")

    def test_list_invalid_date_range_returns_400(self) -> None:
        list_resp = self.client.get(
            "/api/warehouse/inventory-counts?from_date=2026-04-20&to_date=2026-04-19",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(list_resp.status_code, 400)
        self.assertEqual(list_resp.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_no_erpnext_write_call_signature(self) -> None:
        from app.routers import warehouse as warehouse_router_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked = [
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "/api/resource/Stock Reconciliation",
            "/api/resource/Stock Entry",
            "/api/resource/Stock Ledger Entry",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, content)

    def test_no_forbidden_business_semantics_signature(self) -> None:
        from app.models import warehouse as warehouse_model_module
        from app.routers import warehouse as warehouse_router_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_model_module.__file__, encoding="utf-8").read(),
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked = [
            "Stock Reconciliation",
            "GL Entry",
            "Payment Entry",
            "Purchase Invoice",
            "docstatus = 1",
            "docstatus==1",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, content)


if __name__ == "__main__":
    unittest.main()
