"""TASK-030D quality worker permission and internal-principal tests."""

from __future__ import annotations

import os
import unittest

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

