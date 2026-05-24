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

    @staticmethod
    def _local_gate_env() -> dict[str, str]:
        return {
            "APP_ENV": "development",
            "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db",
        }

    @staticmethod
    def _carrier_code(value: object) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-3:]

    def _create_payload(self) -> dict[str, object]:
        scenario_tag = "Z003-QUALITY-INSPECTION-20260416-001"
        idempotency_key = f"{scenario_tag}-CREATE-BASELINE"
        source_ref = f"manual:{scenario_tag}:quality-create-baseline"
        inspection_ref = f"QI:{scenario_tag}:create-baseline"
        payload = self._payload()
        payload.update(
            {
                "idempotency_key": idempotency_key,
                "scenario_tag": scenario_tag,
                "source_ref": source_ref,
                "inspection_ref": inspection_ref,
                "source_doc": source_ref,
                "operation": "create",
            }
        )
        payload["request_id"] = (
            f"{scenario_tag}-QI-C-"
            f"{self._carrier_code(idempotency_key)}-"
            f"{self._carrier_code(source_ref)}-"
            f"{self._carrier_code(inspection_ref)}-"
            f"{self._carrier_code(payload['item_code'])}-"
            f"{self._carrier_code(payload['result'])}"
        )
        return payload

    def _headers_for_payload(self, payload: dict[str, object], *, role: str = "Quality Manager") -> dict[str, str]:
        headers = self._headers(role=role)
        headers["X-Request-ID"] = str(payload["request_id"])
        return headers

    def test_post_create_returns_201_and_draft(self) -> None:
        payload = self._create_payload()
        with patch.dict("os.environ", self._local_gate_env()), patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers_for_payload(payload),
                json=payload,
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
        payload = self._create_payload()
        with patch.dict("os.environ", self._local_gate_env()), patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers_for_payload(payload, role="Quality Viewer"),
                json=payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
