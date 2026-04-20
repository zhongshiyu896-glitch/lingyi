"""TASK-030B baseline tests for quality inspection creation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityOperationLog
from app.services.quality_service import QualitySourceValidationSnapshot
from tests.test_quality_api import QualityApiBase


class QualityCreateBaselineTest(QualityApiBase):
    """Verify create endpoint restores draft creation semantics."""

    @staticmethod
    def _snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}},
            source=None,
        )

    def test_post_create_returns_201_and_draft(self) -> None:
        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(),
                json=self._payload(),
            )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["status"], "draft")
        self.assertTrue(body["data"]["inspection_no"].startswith("QI"))

        with self.SessionLocal() as session:
            inspection = session.query(LyQualityInspection).one()
            self.assertEqual(inspection.status, "draft")
            self.assertEqual(session.query(LyQualityOperationLog).count(), 1)

    def test_post_create_requires_permission(self) -> None:
        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(role="Quality Viewer"),
                json=self._payload(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
