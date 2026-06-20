"""TASK-030D quality worker permission and internal-principal tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.main import app
from app.models.audit import LySecurityAuditLog
from tests.test_quality_api import QualityApiBase


class QualityWorkerPermissionTest(QualityApiBase):
    """Ensure /internal/outbox-sync/run-once enforces worker gates."""

    def test_internal_worker_denied_without_quality_worker_action(self) -> None:
        response = self.client.post(
            "/api/quality/internal/outbox-sync/run-once",
            headers=self._headers(role="Quality Manager"),
            json={"batch_size": 5, "dry_run": True},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_internal_worker_denied_when_principal_check_fails(self) -> None:
        old_trusted_roles = os.getenv("LINGYI_INTERNAL_WORKER_TRUSTED_ROLES")
        os.environ["LINGYI_INTERNAL_WORKER_TRUSTED_ROLES"] = "LY Integration Service"
        try:
            response = self.client.post(
                "/api/quality/internal/outbox-sync/run-once",
                headers=self._headers(role="System Manager"),
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
            self.assertEqual(str(latest.module), "quality")
            self.assertEqual(str(latest.action), "quality:worker")

    def test_worker_non_dry_run_disabled_in_production_without_sync_flag(self) -> None:
        old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "ENABLE_INTERNAL_WORKER_API": os.environ.get("ENABLE_INTERNAL_WORKER_API"),
            "QUALITY_ENABLE_OUTBOX_WORKER_SYNC": os.environ.get("QUALITY_ENABLE_OUTBOX_WORKER_SYNC"),
        }
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["QUALITY_ENABLE_OUTBOX_WORKER_SYNC"] = "false"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="quality.worker",
            roles=["System Manager"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch("app.routers.quality._quality_outbox_worker") as worker_mock:
                response = self.client.post(
                    "/api/quality/internal/outbox-sync/run-once",
                    json={"batch_size": 5, "dry_run": False},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "INTERNAL_API_DISABLED")
        self.assertEqual(response.json()["message"], "质量 Outbox ERP 同步未启用")
        self.assertEqual(worker_mock.call_count, 0)
        with self.SessionLocal() as session:
            latest = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertIsNotNone(latest)
        self.assertEqual(str(latest.event_type), "INTERNAL_API_DISABLED")
        self.assertEqual(str(latest.action), "quality:worker")

    def test_internal_worker_dry_run_success_for_system_manager(self) -> None:
        response = self.client.post(
            "/api/quality/internal/outbox-sync/run-once",
            headers=self._headers(role="System Manager"),
            json={"batch_size": 5, "dry_run": True},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertTrue(body["data"]["dry_run"])
        self.assertGreaterEqual(body["data"]["processed_count"], 0)


if __name__ == "__main__":
    unittest.main()
