"""TASK-050D warehouse stock-entry outbox worker tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.exceptions import BusinessException
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.warehouse import _build_carrier_code
from app.routers.warehouse import _stock_entry_operation_code
from app.routers.warehouse import _stock_entry_status_action_code
from tests.test_warehouse_stock_entry_draft import WarehouseStockEntryDraftApiBase


class WarehouseStockEntryWorkerTest(WarehouseStockEntryDraftApiBase):
    """Validate run-once worker lifecycle for warehouse stock-entry outbox."""

    SCENARIO_TAG = "Z003-WAREHOUSE-20260525-005"
    LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"

    def setUp(self) -> None:
        super().setUp()
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = self.LOCAL_ALLOWED_DB_URL

    @staticmethod
    def _worker_headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.worker",
            "X-LY-Dev-Roles": "System Manager",
        }

    @staticmethod
    def _scenario_value(value: str) -> str:
        scenario_tag = WarehouseStockEntryWorkerTest.SCENARIO_TAG
        return value if scenario_tag in value else f"{scenario_tag}-{value}"

    @classmethod
    def _request_id(cls, payload: dict) -> str:
        operation_code = _stock_entry_operation_code(payload["operation"])
        status_code = _stock_entry_status_action_code(payload["status_action"])
        return (
            f"{payload['scenario_tag']}-RW-{operation_code}-"
            f"{_build_carrier_code(payload['idempotency_key'])}-"
            f"{_build_carrier_code(payload['source_ref'])}-"
            f"{_build_carrier_code(payload['warehouse'])}-"
            f"{_build_carrier_code(payload['item_code'])}-"
            f"{_build_carrier_code(payload['quantity'])}-"
            f"{_build_carrier_code(payload['business_date'])}-"
            f"{_build_carrier_code(status_code)}"
        )

    @classmethod
    def _headers_for_payload(cls, roles: str, payload: dict) -> dict[str, str]:
        headers = cls._headers(roles)
        headers["X-Request-ID"] = cls._request_id(payload)
        return headers

    @classmethod
    def _payload(cls, *, qty: str = "5", source_id: str = "SRC-001", idempotency_key: str = "idem-001") -> dict:
        source_ref = cls._scenario_value(source_id)
        return {
            "company": "COMP-A",
            "purpose": "Material Issue",
            "source_type": "manual",
            "source_id": source_ref,
            "source_ref": source_ref,
            "warehouse": "WH-A",
            "item_code": "ITEM-A",
            "operation": "create_stock_entry_draft",
            "quantity": qty,
            "business_date": "2026-05-25",
            "status_action": "create",
            "scenario_tag": cls.SCENARIO_TAG,
            "source_warehouse": "WH-A",
            "target_warehouse": None,
            "idempotency_key": cls._scenario_value(idempotency_key),
            "items": [
                {
                    "item_code": "ITEM-A",
                    "qty": qty,
                    "uom": "Nos",
                    "batch_no": None,
                    "serial_no": None,
                    "source_warehouse": "WH-A",
                    "target_warehouse": None,
                }
            ],
        }

    @classmethod
    def _cancel_payload(cls, draft_payload: dict, *, reason: str) -> dict:
        return {
            "reason": reason,
            "idempotency_key": draft_payload["idempotency_key"],
            "source_ref": draft_payload["source_ref"],
            "warehouse": draft_payload["warehouse"],
            "item_code": draft_payload["item_code"],
            "operation": "cancel_stock_entry_draft",
            "quantity": draft_payload["quantity"],
            "business_date": draft_payload["business_date"],
            "status_action": "cancel",
            "scenario_tag": draft_payload["scenario_tag"],
        }

    def _create_draft(self) -> int:
        payload = self._payload()
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers_for_payload("warehouse:stock_entry_draft,warehouse:read", payload),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return int(response.json()["data"]["id"])

    def test_worker_dry_run_does_not_modify_outbox(self) -> None:
        draft_id = self._create_draft()
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.create_stock_entry_draft_from_outbox"
        ) as mocked:
            response = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": True},
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()["data"]
        self.assertTrue(body["dry_run"])
        self.assertGreaterEqual(int(body["processed_count"]), 1)
        self.assertEqual(int(body["skipped_count"]), 0)
        mocked.assert_not_called()

        with self.SessionLocal() as session:
            row = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(row.status), "in_pending")
            self.assertEqual(int(row.retry_count), 0)
            self.assertIsNone(row.external_ref)

    def test_worker_success_transitions_to_succeeded(self) -> None:
        draft_id = self._create_draft()
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.create_stock_entry_draft_from_outbox",
            return_value="STE-DRAFT-001",
        ):
            response = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": False},
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()["data"]
        self.assertFalse(body["dry_run"])
        self.assertEqual(int(body["processed_count"]), 1)
        self.assertEqual(int(body["skipped_count"]), 0)
        self.assertEqual(int(body["succeeded_count"]), 1)
        self.assertEqual(int(body["failed_count"]), 0)
        self.assertEqual(int(body["dead_count"]), 0)

        with self.SessionLocal() as session:
            row = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(row.status), "succeeded")
            self.assertEqual(str(row.external_ref), "STE-DRAFT-001")
            self.assertIsNotNone(row.processed_at)

    def test_worker_failure_retries_then_dead(self) -> None:
        draft_id = self._create_draft()
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.create_stock_entry_draft_from_outbox",
            side_effect=BusinessException(code="ERPNEXT_STOCK_ENTRY_CREATE_FAILED", message="create failed"),
        ):
            first = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": False},
            )
            second = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": False},
            )
            third = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": False},
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(third.status_code, 200, third.text)
        self.assertEqual(int(first.json()["data"]["skipped_count"]), 0)
        self.assertEqual(int(second.json()["data"]["skipped_count"]), 0)
        self.assertEqual(int(third.json()["data"]["skipped_count"]), 0)
        self.assertEqual(int(first.json()["data"]["failed_count"]), 1)
        self.assertEqual(int(second.json()["data"]["failed_count"]), 1)
        self.assertEqual(int(third.json()["data"]["dead_count"]), 1)

        with self.SessionLocal() as session:
            row = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(row.status), "dead")
            self.assertEqual(int(row.retry_count), 3)
            self.assertIsNotNone(row.error_message)

    def test_cancelled_outbox_or_draft_not_processed(self) -> None:
        draft_payload = self._payload()
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers_for_payload("warehouse:stock_entry_draft,warehouse:read", draft_payload),
            json=draft_payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])
        cancel_payload = self._cancel_payload(draft_payload, reason="cancel for worker skip")
        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers_for_payload("warehouse:stock_entry_cancel,warehouse:read", cancel_payload),
            json=cancel_payload,
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        with self.SessionLocal() as session:
            row = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            row.status = "in_pending"
            row.error_message = None
            row.processed_at = None
            session.commit()

        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.create_stock_entry_draft_from_outbox"
        ) as mocked:
            response = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._worker_headers(),
                json={"batch_size": 5, "dry_run": False},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(int(response.json()["data"]["processed_count"]), 1)
        self.assertEqual(int(response.json()["data"]["skipped_count"]), 1)
        mocked.assert_not_called()
        with self.SessionLocal() as session:
            row = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(row.status), "cancelled")

    def test_worker_default_batch_size_is_10(self) -> None:
        for idx in range(12):
            payload = self._payload(source_id=f"SRC-{idx:03d}", idempotency_key=f"idem-{idx:03d}")
            create_resp = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers_for_payload("warehouse:stock_entry_draft,warehouse:read", payload),
                json=payload,
            )
            self.assertEqual(create_resp.status_code, 201, create_resp.text)
        response = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once",
            headers=self._worker_headers(),
            json={"dry_run": True},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()["data"]
        self.assertTrue(body["dry_run"])
        self.assertEqual(int(body["processed_count"]), 10)
        self.assertEqual(int(body["skipped_count"]), 0)


if __name__ == "__main__":
    unittest.main()
