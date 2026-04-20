"""TASK-050D warehouse worker permission/internal principal tests."""

from __future__ import annotations

import os
import unittest

from app.models.audit import LySecurityAuditLog
from tests.test_warehouse_stock_entry_draft import WarehouseStockEntryDraftApiBase


class WarehouseWorkerPermissionTest(WarehouseStockEntryDraftApiBase):
    """Ensure /internal/stock-entry-sync/run-once enforces worker gates."""

    def test_worker_denied_without_warehouse_worker_action(self) -> None:
        response = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once",
            headers=self._headers("warehouse:read"),
            json={"batch_size": 5, "dry_run": True},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_worker_denied_when_principal_check_fails(self) -> None:
        old_trusted_roles = os.getenv("LINGYI_INTERNAL_WORKER_TRUSTED_ROLES")
        os.environ["LINGYI_INTERNAL_WORKER_TRUSTED_ROLES"] = "LY Integration Service"
        try:
            response = self.client.post(
                "/api/warehouse/internal/stock-entry-sync/run-once",
                headers=self._headers("System Manager"),
                json={"batch_size": 5, "dry_run": True},
            )
        finally:
            if old_trusted_roles is None:
                os.environ.pop("LINGYI_INTERNAL_WORKER_TRUSTED_ROLES", None)
            else:
                os.environ["LINGYI_INTERNAL_WORKER_TRUSTED_ROLES"] = old_trusted_roles

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            latest = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(latest)
            self.assertEqual(str(latest.module), "warehouse")
            self.assertEqual(str(latest.action), "warehouse:worker")

    def test_worker_dry_run_success_for_system_manager(self) -> None:
        response = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once",
            headers=self._headers("System Manager"),
            json={"batch_size": 5, "dry_run": True},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertTrue(body["data"]["dry_run"])
        self.assertGreaterEqual(body["data"]["processed_count"], 0)
        self.assertGreaterEqual(body["data"]["skipped_count"], 0)

    def test_worker_rejects_batch_size_over_limit(self) -> None:
        response = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once",
            headers=self._headers("System Manager"),
            json={"batch_size": 51, "dry_run": True},
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
