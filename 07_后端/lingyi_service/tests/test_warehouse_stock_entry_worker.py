"""TASK-050D warehouse stock-entry outbox worker tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.exceptions import BusinessException
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from tests.test_warehouse_stock_entry_draft import WarehouseStockEntryDraftApiBase


class WarehouseStockEntryWorkerTest(WarehouseStockEntryDraftApiBase):
    """Validate run-once worker lifecycle for warehouse stock-entry outbox."""

    @staticmethod
    def _worker_headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.worker",
            "X-LY-Dev-Roles": "System Manager",
        }

    def _create_draft(self) -> int:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
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
        draft_id = self._create_draft()
        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers("warehouse:stock_entry_cancel,warehouse:read"),
            json={"reason": "cancel for worker skip"},
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
            payload = self._payload()
            payload["idempotency_key"] = f"idem-{idx:03d}"
            payload["source_id"] = f"SRC-{idx:03d}"
            create_resp = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
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
