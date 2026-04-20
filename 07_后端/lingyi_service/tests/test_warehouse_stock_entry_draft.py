"""TASK-050B warehouse stock-entry draft outbox baseline tests."""

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
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.services.erpnext_permission_adapter import UserPermissionResult


class WarehouseStockEntryDraftApiBase(unittest.TestCase):
    """In-memory app wiring for warehouse stock-entry draft APIs."""

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
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.writer",
            "X-LY-Dev-Roles": roles,
        }

    @staticmethod
    def _payload(*, qty: str = "5") -> dict:
        return {
            "company": "COMP-A",
            "purpose": "Material Transfer",
            "source_type": "manual",
            "source_id": "SRC-001",
            "source_warehouse": "WH-A",
            "target_warehouse": "WH-B",
            "idempotency_key": "idem-001",
            "items": [
                {
                    "item_code": "ITEM-A",
                    "qty": qty,
                    "uom": "Nos",
                    "batch_no": None,
                    "serial_no": None,
                    "source_warehouse": "WH-A",
                    "target_warehouse": "WH-B",
                }
            ],
        }


class WarehouseStockEntryDraftApiTest(WarehouseStockEntryDraftApiBase):
    """Warehouse stock-entry draft outbox contract."""

    def test_create_draft_with_permission(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["status"], "pending_outbox")
        self.assertEqual(body["company"], "COMP-A")
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["outbox"]["status"], "in_pending")

    def test_create_draft_generates_in_pending_outbox(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        draft_id = int(response.json()["data"]["id"])

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "pending_outbox")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "in_pending")

    def test_qty_lte_zero_returns_400(self) -> None:
        payload = self._payload(qty="0")
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_QTY")

    def test_without_stock_entry_draft_permission_returns_403(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_write_only_cannot_create_draft(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("inventory:write"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_company_scope_denied_returns_403_or_404(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-X"},
                allowed_warehouses={"WH-A", "WH-B"},
                allowed_items={"ITEM-A"},
            ),
        ):
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers("warehouse:stock_entry_draft"),
                json=self._payload(),
            )
        self.assertIn(response.status_code, {403, 404})

    def test_warehouse_scope_denied_returns_403_or_404(self) -> None:
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
        ):
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers("warehouse:stock_entry_draft"),
                json=self._payload(),
            )
        self.assertIn(response.status_code, {403, 404})

    def test_cancel_draft_success_and_outbox_cancelled(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers("warehouse:stock_entry_cancel,warehouse:read"),
            json={"reason": "manual cancel"},
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")
        self.assertEqual(cancel_resp.json()["data"]["outbox"]["status"], "cancelled")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "cancelled")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "cancelled")

    def test_repeat_cancel_returns_409(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read"),
            json=self._payload(),
        )
        draft_id = int(create_resp.json()["data"]["id"])

        first = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers("warehouse:stock_entry_cancel,warehouse:read"),
            json={"reason": "first"},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers("warehouse:stock_entry_cancel,warehouse:read"),
            json={"reason": "again"},
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "WAREHOUSE_DRAFT_ALREADY_CANCELLED")

    def test_outbox_status_returns_correct_payload(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        draft_id = int(create_resp.json()["data"]["id"])

        status_resp = self.client.get(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/outbox-status",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(status_resp.status_code, 200, status_resp.text)
        data = status_resp.json()["data"]
        self.assertEqual(int(data["draft_id"]), draft_id)
        self.assertEqual(data["status"], "in_pending")
        self.assertEqual(data["event_type"], "warehouse_stock_entry_sync")

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
            "/api/resource/Stock Entry",
            "/api/resource/Stock Reconciliation",
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
            "submit_stock_entry",
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
