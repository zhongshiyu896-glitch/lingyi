"""TASK-090C finished-goods inbound interaction baseline tests."""

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
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter


class WarehouseFinishedGoodsInboundApiBase(unittest.TestCase):
    """In-memory app wiring for TASK-090C warehouse finished-goods APIs."""

    STOCK_ENTRY_SCENARIO_TAG = "Z003-WAREHOUSE-20260525-001"
    BUSINESS_DATE = "2026-05-25"

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
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in value.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-3:]

    @classmethod
    def _stock_entry_request_id(
        cls,
        payload: dict,
        *,
        operation: str = "create_stock_entry_draft",
        status_action: str = "create",
    ) -> str:
        operation_code = "C" if operation == "create_stock_entry_draft" else "X"
        status_action_code = "C" if status_action == "create" else "X"
        return (
            f"{payload['scenario_tag']}-RW-{operation_code}-"
            f"{cls._carrier_code(payload['idempotency_key'])}-"
            f"{cls._carrier_code(payload['source_ref'])}-"
            f"{cls._carrier_code(payload['warehouse'])}-"
            f"{cls._carrier_code(payload['item_code'])}-"
            f"{cls._carrier_code(str(payload['quantity']))}-"
            f"{cls._carrier_code(payload['business_date'])}-"
            f"{cls._carrier_code(status_action_code)}"
        )

    @classmethod
    def _headers(cls, roles: str, *, request_id: str | None = None) -> dict[str, str]:
        headers = {
            "X-LY-Dev-User": "warehouse.fg",
            "X-LY-Dev-Roles": roles,
        }
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    @classmethod
    def _draft_payload(cls, *, qty: str = "5", item_code: str = "FG-ITEM-001") -> dict:
        source_id = f"{cls.STOCK_ENTRY_SCENARIO_TAG}-MANUAL-SOURCE"
        return {
            "company": "COMP-A",
            "purpose": "Material Issue",
            "source_type": "manual",
            "source_id": source_id,
            "source_ref": source_id,
            "warehouse": "FG-WH-001",
            "item_code": item_code,
            "operation": "create_stock_entry_draft",
            "quantity": qty,
            "business_date": cls.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": cls.STOCK_ENTRY_SCENARIO_TAG,
            "finished_goods_source_id": "MLI-0001",
            "source_warehouse": None,
            "target_warehouse": "FG-WH-001",
            "idempotency_key": f"{cls.STOCK_ENTRY_SCENARIO_TAG}-fg-inbound-idem-001",
            "items": [
                {
                    "item_code": item_code,
                    "qty": qty,
                    "uom": "Nos",
                    "batch_no": None,
                    "serial_no": None,
                    "source_warehouse": None,
                    "target_warehouse": "FG-WH-001",
                }
            ],
        }


class WarehouseFinishedGoodsInboundApiTest(WarehouseFinishedGoodsInboundApiBase):
    """TASK-090C contract-level tests."""

    def test_candidates_show_disabled_entry_and_show_completed_contract(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_finished_goods_inbound_candidates",
            return_value=[
                {
                    "source_id": "MLI-0001",
                    "source_label": "MO-001 / 外协 / FG-ITEM-001",
                    "item_code": "FG-ITEM-001",
                    "qty": Decimal("12"),
                    "uom": "Nos",
                    "strict_alloc_qty": Decimal("8"),
                    "disabled": False,
                    "disabled_reason": None,
                }
            ],
        ):
            response = self.client.get(
                "/api/warehouse/finished-goods-inbound-candidates?company=COMP-A",
                headers=self._headers("warehouse:read"),
            )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertTrue(data["show_completed_forced"])
        self.assertEqual(data["disabled_entry_label"], "成品预约入仓 -> 创建成品入仓")
        self.assertEqual(data["allocation_contract"], "strict_alloc -> zero_placeholder_fallback")
        self.assertEqual(len(data["items"]), 1)

    def test_create_finished_goods_draft_strict_alloc(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.get_finished_goods_inbound_candidate",
            return_value={
                "source_id": "MLI-0001",
                "item_code": "FG-ITEM-001",
                "qty": Decimal("12"),
                "uom": "Nos",
                "strict_alloc_qty": Decimal("12"),
                "disabled": False,
                "disabled_reason": None,
            },
        ):
            payload = self._draft_payload(qty="5")
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers(
                    "warehouse:stock_entry_draft,warehouse:read",
                    request_id=self._stock_entry_request_id(payload),
                ),
                json=payload,
            )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["purpose"], "Material Receipt")
        self.assertEqual(body["source_type"], "finished_goods_inbound")
        self.assertEqual(body["source_id"], "MLI-0001")
        self.assertEqual(body["allocation_mode"], "strict_alloc")
        self.assertIsNone(body["strict_failure_reason"])
        self.assertTrue(body["show_completed_forced"])
        self.assertEqual(body["outbox"]["status"], "in_pending")

        with self.SessionLocal() as session:
            draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.id == int(body["id"]))
                .one()
            )
            self.assertEqual(str(draft.purpose), "Material Receipt")
            self.assertEqual(str(draft.source_type), "finished_goods_inbound")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == int(body["id"]))
                .one()
            )
            self.assertEqual(outbox.payload.get("allocation_mode"), "strict_alloc")
            self.assertTrue(outbox.payload.get("show_completed_forced"))

    def test_create_finished_goods_draft_fallback_mode(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.get_finished_goods_inbound_candidate",
            return_value={
                "source_id": "MLI-0001",
                "item_code": "FG-ITEM-001",
                "qty": Decimal("12"),
                "uom": "Nos",
                "strict_alloc_qty": Decimal("0"),
                "disabled": False,
                "disabled_reason": None,
            },
        ):
            payload = self._draft_payload(qty="4")
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers(
                    "warehouse:stock_entry_draft,warehouse:read",
                    request_id=self._stock_entry_request_id(payload),
                ),
                json=payload,
            )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["allocation_mode"], "zero_placeholder_fallback")
        self.assertIn("找不到可分配的制单明细", body.get("strict_failure_reason") or "")

    def test_create_finished_goods_draft_fastapi_local_source_without_erpnext(self) -> None:
        payload = self._draft_payload(qty="3", item_code="FG-LOCAL-001")
        payload["source_id"] = f"{self.STOCK_ENTRY_SCENARIO_TAG}-LOCAL-FG-001"
        payload["source_ref"] = payload["source_id"]
        payload["finished_goods_source_id"] = payload["source_id"]
        payload["items"][0]["item_code"] = "FG-LOCAL-001"
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._stock_entry_request_id(payload),
            ),
            json=payload,
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["source_type"], "finished_goods_inbound")
        self.assertEqual(body["source_id"], payload["finished_goods_source_id"])
        self.assertEqual(body["allocation_mode"], "zero_placeholder_fallback")
        self.assertEqual(body["strict_failure_reason"], "FastAPI local finished goods inbound source")
        readback = self.client.get(
            "/api/warehouse/finished-goods-inbound?company=COMP-A&item_code=FG-LOCAL-001",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(readback.status_code, 200, readback.text)
        rows = readback.json()["data"]["items"]
        self.assertEqual(readback.json()["data"]["total"], 1)
        self.assertEqual(rows[0]["reservation_no"], payload["finished_goods_source_id"])
        self.assertEqual(rows[0]["warehouse"], "FG-WH-001")
        self.assertEqual(rows[0]["inbound_status"], "outbox_pending")
        self.assertEqual(Decimal(str(rows[0]["inbound_qty"])), Decimal("3.000000"))

    def test_cancel_finished_goods_draft_removes_effective_stock(self) -> None:
        payload = self._draft_payload(qty="3", item_code="FG-CANCEL-001")
        payload["source_id"] = f"{self.STOCK_ENTRY_SCENARIO_TAG}-LOCAL-FG-CANCEL"
        payload["source_ref"] = payload["source_id"]
        payload["finished_goods_source_id"] = payload["source_id"]
        payload["items"][0]["item_code"] = "FG-CANCEL-001"
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._stock_entry_request_id(payload),
            ),
            json=payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        summary_before = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=FG-WH-001&item_code=FG-CANCEL-001",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(summary_before.status_code, 200, summary_before.text)
        before_rows = summary_before.json()["data"]["items"]
        self.assertEqual(len(before_rows), 1)
        self.assertEqual(Decimal(str(before_rows[0]["actual_qty"])), Decimal("3.000000"))

        cancel_payload = {
            "reason": "成品入库取消不计库存",
            "idempotency_key": payload["idempotency_key"],
            "source_ref": payload["source_id"],
            "warehouse": "FG-WH-001",
            "item_code": "FG-CANCEL-001",
            "operation": "cancel_stock_entry_draft",
            "quantity": payload["quantity"],
            "business_date": payload["business_date"],
            "status_action": "cancel",
            "scenario_tag": payload["scenario_tag"],
        }
        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._stock_entry_request_id(
                    cancel_payload,
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=cancel_payload,
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")

        summary_after = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=FG-WH-001&item_code=FG-CANCEL-001",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(summary_after.status_code, 200, summary_after.text)
        self.assertEqual(summary_after.json()["data"]["items"], [])

        readback_after = self.client.get(
            "/api/warehouse/finished-goods-inbound?company=COMP-A&item_code=FG-CANCEL-001",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(readback_after.status_code, 200, readback_after.text)
        self.assertEqual(readback_after.json()["data"]["items"], [])

    def test_create_finished_goods_draft_candidate_disabled_fail_closed(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.get_finished_goods_inbound_candidate",
            return_value={
                "source_id": "MLI-0001",
                "item_code": "FG-ITEM-001",
                "qty": Decimal("0"),
                "uom": "Nos",
                "strict_alloc_qty": Decimal("0"),
                "disabled": True,
                "disabled_reason": "候选数量不足，禁止创建草稿",
            },
        ):
            payload = self._draft_payload(qty="1")
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers(
                    "warehouse:stock_entry_draft,warehouse:read",
                    request_id=self._stock_entry_request_id(payload),
                ),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("code"), "WAREHOUSE_FINISHED_GOODS_CANDIDATE_DISABLED")


class WarehouseFinishedGoodsInboundAdapterTest(unittest.TestCase):
    """Adapter-level contract for forced showCompleted behavior."""

    def test_finished_goods_option_payload_forces_show_completed(self) -> None:
        adapter = ERPNextWarehouseAdapter(request_obj=None)
        fake_payload = {
            "data": {
                "items": [
                    {
                        "manufactureLineItemId": "MLI-0001",
                        "productNo": "FG-ITEM-001",
                        "quantity": "2",
                        "productUnit": "Nos",
                        "surplusQuantity": "1",
                        "manufactureNo": "MO-001",
                        "processType": "外协",
                    }
                ]
            }
        }
        with patch.object(adapter, "_request_json", return_value=fake_payload) as mock_request:
            rows = adapter.list_finished_goods_inbound_candidates(company="COMP-A")

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["source_id"])
        self.assertEqual(mock_request.call_count, 1)
        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs.get("method"), "POST")
        payload = kwargs.get("payload") or {}
        self.assertTrue(payload.get("showCompleted"))


if __name__ == "__main__":
    unittest.main()
