"""TASK-050D warehouse worker permission/internal principal tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.routers.warehouse import get_current_user as warehouse_get_current_user
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

    def test_worker_non_dry_run_disabled_in_production_without_sync_flag(self) -> None:
        old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "ENABLE_INTERNAL_WORKER_API": os.environ.get("ENABLE_INTERNAL_WORKER_API"),
            "WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC": os.environ.get("WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC"),
        }
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC"] = "false"
        app_user = CurrentUser(
            username="warehouse.worker",
            roles=["System Manager"],
            is_service_account=True,
            source="test_override",
        )
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: app_user
        app.dependency_overrides[warehouse_get_current_user] = lambda: app_user
        try:
            with patch("app.services.warehouse_service.WarehouseService.run_stock_entry_outbox_once") as run_mock:
                with TestClient(app) as client:
                    response = client.post(
                        "/api/warehouse/internal/stock-entry-sync/run-once",
                        json={"batch_size": 5, "dry_run": False},
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(warehouse_get_current_user, None)
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "INTERNAL_API_DISABLED")
        self.assertEqual(response.json()["message"], "仓库 Stock Entry ERP 同步未启用")
        self.assertEqual(run_mock.call_count, 0)

    def test_worker_rejects_batch_size_over_limit(self) -> None:
        response = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once",
            headers=self._headers("System Manager"),
            json={"batch_size": 51, "dry_run": True},
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
