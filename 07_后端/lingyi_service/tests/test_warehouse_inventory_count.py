"""TASK-050C warehouse inventory-count baseline tests."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class WarehouseInventoryCountApiBase(unittest.TestCase):
    """In-memory app wiring for warehouse inventory-count APIs."""

    COUNT_SCENARIO_TAG = "Z002-WAREHOUSE-COUNT-20260420-001"

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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()
        self._seed_stock_balance(item_code="ITEM-A", qty="10")
        self._seed_stock_balance(item_code="ITEM-B", qty="5")

    @classmethod
    def _warehouse_code(cls, value: str) -> str:
        hash_value = 2166136261
        for byte in value.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"

    @classmethod
    def _request_id(cls, *, warehouse: str = "WH-A", count_date: str = "2026-04-20") -> str:
        date_code = date.fromisoformat(count_date).strftime("%Y%m%d")
        return f"{cls.COUNT_SCENARIO_TAG}-REQ-COUNT-W{cls._warehouse_code(warehouse)}-D{date_code}"

    @classmethod
    def _headers(cls, roles: str, *, warehouse: str = "WH-A", count_date: str = "2026-04-20") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.counter",
            "X-LY-Dev-Roles": roles,
            "X-Request-ID": cls._request_id(warehouse=warehouse, count_date=count_date),
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
            "idempotency_key": WarehouseInventoryCountApiBase._request_id(warehouse=warehouse, count_date=count_date),
            "source_ref": WarehouseInventoryCountApiBase._request_id(warehouse=warehouse, count_date=count_date),
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

    def _seed_stock_balance(
        self,
        *,
        company: str = "COMP-A",
        warehouse: str = "WH-A",
        item_code: str = "ITEM-A",
        qty: str = "10",
    ) -> None:
        created_at = datetime.combine(date(2026, 4, 19), datetime.min.time(), timezone.utc)
        stable_key = f"{company}-{warehouse}-{item_code}"
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company=company,
                purpose="Material Receipt",
                source_type="manual",
                source_id=f"BAL-{stable_key}",
                source_warehouse=None,
                target_warehouse=warehouse,
                status="pending_outbox",
                created_by="warehouse.counter",
                created_at=created_at,
                idempotency_key=f"idem-bal-{stable_key}",
                event_key=f"event-bal-{stable_key}",
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=draft.id,
                    company=company,
                    item_code=item_code,
                    qty=Decimal(qty),
                    uom="Pcs",
                    source_warehouse=None,
                    target_warehouse=warehouse,
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    draft_id=draft.id,
                    event_type="warehouse_stock_entry_sync",
                    event_key=f"event-bal-{stable_key}",
                    payload={"business_date": "2026-04-19"},
                    status="in_pending",
                    retry_count=0,
                    created_at=created_at,
                )
            )
            session.commit()


class WarehouseInventoryCountApiTest(WarehouseInventoryCountApiBase):
    """Warehouse inventory-count state-machine contract."""

    def test_create_inventory_count_draft_with_permission(self) -> None:
        payload = self._payload()
        payload["items"][0]["system_qty"] = "999"
        payload["items"][1]["system_qty"] = "999"
        response = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count,warehouse:read"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["warehouse"], "WH-A")
        self.assertEqual(data["variance_stats"]["variance_items"], 1)
        self.assertEqual(data["items"][0]["system_qty"], "10.000000")
        self.assertEqual(data["items"][0]["variance_qty"], "-2.000000")
        self.assertEqual(data["items"][1]["system_qty"], "5.000000")
        self.assertEqual(data["items"][1]["variance_qty"], "0.000000")
        with self.SessionLocal() as session:
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.resource_type == "warehouse_inventory_count",
                    LyOperationAuditLog.resource_id == int(data["id"]),
                    LyOperationAuditLog.result == "success",
                )
                .one()
            )
            self.assertEqual(audit.resource_no, data["count_no"])

    def test_create_inventory_count_replay_returns_same_record(self) -> None:
        payload = self._payload()
        headers = self._headers("warehouse:inventory_count,warehouse:read")
        first = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)
        second = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        first_data = first.json()["data"]
        second_data = second.json()["data"]
        self.assertEqual(second_data["id"], first_data["id"])
        self.assertEqual(second_data["count_no"], first_data["count_no"])
        self.assertEqual(second_data["idempotency_key"], payload["idempotency_key"])
        self.assertEqual(second_data["source_ref"], payload["source_ref"])
        self.assertRegex(second_data["request_hash"], r"^[a-f0-9]{64}$")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseInventoryCount).count(), 1)
            self.assertEqual(session.query(LyWarehouseInventoryCountItem).count(), 2)

    def test_create_inventory_count_idempotency_conflict_is_409_and_audited(self) -> None:
        payload = self._payload()
        headers = self._headers("warehouse:inventory_count,warehouse:read")
        first = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201, first.text)

        changed = self._payload()
        changed["items"][0]["counted_qty"] = "7"
        conflict = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=changed)
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "WAREHOUSE_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseInventoryCount).count(), 1)
            self.assertEqual(session.query(LyWarehouseInventoryCountItem).count(), 2)
            failed_audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "WAREHOUSE_IDEMPOTENCY_CONFLICT",
                )
                .one()
            )
            self.assertEqual(failed_audit.resource_no, payload["source_ref"])

    def test_create_inventory_count_same_source_ref_with_different_idempotency_key_conflicts(self) -> None:
        payload = self._payload()
        headers = self._headers("warehouse:inventory_count,warehouse:read")
        first = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201, first.text)

        changed = self._payload()
        changed["idempotency_key"] = f"{changed['idempotency_key']}-ALT"
        conflict = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=changed)
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "WAREHOUSE_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseInventoryCount).count(), 1)
            failed_audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "WAREHOUSE_IDEMPOTENCY_CONFLICT",
                )
                .one()
            )
            self.assertEqual(failed_audit.resource_no, payload["source_ref"])

    def test_create_inventory_count_integrity_replay_returns_same_record(self) -> None:
        payload = self._payload()
        headers = self._headers("warehouse:inventory_count,warehouse:read")
        first = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201, first.text)
        first_data = first.json()["data"]

        with patch(
            "app.services.warehouse_service.WarehouseService.create_inventory_count",
            side_effect=IntegrityError("insert inventory count", {}, Exception("unique")),
        ):
            second = self.client.post("/api/warehouse/inventory-counts", headers=headers, json=payload)

        self.assertEqual(second.status_code, 201, second.text)
        second_data = second.json()["data"]
        self.assertEqual(second_data["id"], first_data["id"])
        self.assertEqual(second_data["count_no"], first_data["count_no"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseInventoryCount).count(), 1)
            self.assertEqual(session.query(LyWarehouseInventoryCountItem).count(), 2)
            self.assertEqual(
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.result == "success",
                )
                .count(),
                2,
            )
            self.assertEqual(
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.result == "failed",
                )
                .count(),
                0,
            )

    def test_inventory_balance_reconciliation_reads_count_against_stock_movements(self) -> None:
        create_count = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_count.status_code, 201, create_count.text)

        readback = self.client.get(
            "/api/warehouse/inventory-balance-reconciliation?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(readback.status_code, 200, readback.text)
        rows = readback.json()["data"]["items"]
        self.assertEqual(readback.json()["data"]["total"], 1)
        self.assertNotEqual(rows[0]["ref_no"], "INV-BAL-FR-001")
        self.assertEqual(rows[0]["warehouse"], "WH-A")
        self.assertEqual(rows[0]["item_code"], "ITEM-A")
        self.assertEqual(Decimal(str(rows[0]["book_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(rows[0]["actual_qty"])), Decimal("8.000000"))
        self.assertEqual(Decimal(str(rows[0]["diff_qty"])), Decimal("-2.000000"))
        self.assertEqual(rows[0]["status"], "pending")

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
        with self.SessionLocal() as session:
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:inventory_count",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "WAREHOUSE_INVALID_QTY",
                )
                .one()
            )
            self.assertEqual(audit.resource_no, payload["source_ref"])

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

        summary_after_confirm = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(summary_after_confirm.status_code, 200, summary_after_confirm.text)
        summary_rows = summary_after_confirm.json()["data"]["items"]
        self.assertEqual(Decimal(str(summary_rows[0]["actual_qty"])), Decimal("8.000000"))

        repeat_confirm = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/confirm",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(repeat_confirm.status_code, 200, repeat_confirm.text)
        self.assertEqual(repeat_confirm.json()["data"]["status"], "confirmed")

        with self.SessionLocal() as session:
            item = (
                session.query(LyWarehouseInventoryCountItem)
                .filter(LyWarehouseInventoryCountItem.id == variance_item_id)
                .one()
            )
            self.assertEqual(str(item.counted_qty), "8.000000")
            adjustment_drafts = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "inventory_count_adjustment")
                .all()
            )
            self.assertEqual(len(adjustment_drafts), 1)
            self.assertEqual(adjustment_drafts[0].purpose, "Material Issue")
            self.assertEqual(adjustment_drafts[0].source_warehouse, "WH-A")
            self.assertIsNone(adjustment_drafts[0].target_warehouse)
            adjustment_item = (
                session.query(LyWarehouseStockEntryDraftItem)
                .filter(LyWarehouseStockEntryDraftItem.draft_id == adjustment_drafts[0].id)
                .one()
            )
            self.assertEqual(adjustment_item.item_code, "ITEM-A")
            self.assertEqual(str(adjustment_item.qty), "2.000000")
            self.assertEqual(adjustment_item.uom, "Pcs")
            self.assertEqual(
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == adjustment_drafts[0].id)
                .count(),
                1,
            )

    def test_zero_variance_inventory_count_confirms_without_adjustment(self) -> None:
        payload = self._payload()
        payload["items"][0]["counted_qty"] = "10"
        payload["items"][0]["variance_reason"] = None
        create_resp = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count,warehouse:read"),
            json=payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        count_id = int(create_resp.json()["data"]["id"])

        submit_resp = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/submit",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(submit_resp.status_code, 200, submit_resp.text)

        confirm_ok = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/confirm",
            headers=self._headers("warehouse:inventory_count"),
        )
        self.assertEqual(confirm_ok.status_code, 200, confirm_ok.text)
        self.assertEqual(confirm_ok.json()["data"]["status"], "confirmed")
        with self.SessionLocal() as session:
            self.assertEqual(
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "inventory_count_adjustment")
                .count(),
                0,
            )

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
            json={"reason": f"{self.COUNT_SCENARIO_TAG} manual cancel"},
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")

        cancel_again = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/cancel",
            headers=self._headers("warehouse:inventory_count"),
            json={"reason": f"{self.COUNT_SCENARIO_TAG} repeat cancel"},
        )
        self.assertEqual(cancel_again.status_code, 409)
        self.assertEqual(cancel_again.json()["code"], "WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED")

    def test_list_filters_by_company_and_warehouse(self) -> None:
        self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count"),
            json=self._payload(company="COMP-A", warehouse="WH-A"),
        )
        self._seed_stock_balance(company="COMP-B", warehouse="WH-B", item_code="ITEM-A", qty="10")
        self._seed_stock_balance(company="COMP-B", warehouse="WH-B", item_code="ITEM-B", qty="5")
        self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers("warehouse:inventory_count", warehouse="WH-B", count_date="2026-04-21"),
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
