"""TASK-030C baseline tests for quality inspection cancel workflow."""

from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import patch

from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityOperationLog
from tests.test_quality_api import QualityApiBase


class QualityCancelBaselineTest(QualityApiBase):
    """Verify cancel endpoint only allows confirmed -> cancelled."""

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

    @classmethod
    def _request_id(
        cls,
        *,
        scenario_tag: str,
        operation_code: str,
        idempotency_key: str,
        source_ref: str,
        inspection_ref: str,
        item_code: str,
        result: str,
    ) -> str:
        return (
            f"{scenario_tag}-QI-{operation_code}-"
            f"{cls._carrier_code(idempotency_key)}-"
            f"{cls._carrier_code(source_ref)}-"
            f"{cls._carrier_code(inspection_ref)}-"
            f"{cls._carrier_code(item_code)}-"
            f"{cls._carrier_code(result)}"
        )

    def _write_payload(
        self,
        inspection: dict[str, object],
        *,
        scenario_tag: str,
        operation: str,
        result: str,
        **extra: object,
    ) -> tuple[dict[str, object], dict[str, str]]:
        operation_code = {
            "update": "U",
            "confirm": "F",
            "cancel": "X",
            "defects": "D",
        }[operation]
        inspection_ref = str(inspection["inspection_no"])
        source_ref = f"{scenario_tag}/{inspection_ref}"
        item_code = "ITEM-A"
        idempotency_key = f"{scenario_tag}:{operation}:{inspection_ref}"
        request_id = self._request_id(
            scenario_tag=scenario_tag,
            operation_code=operation_code,
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            inspection_ref=inspection_ref,
            item_code=item_code,
            result=result,
        )
        payload = {
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "scenario_tag": scenario_tag,
            "source_ref": source_ref,
            "inspection_ref": inspection_ref,
            "source_type": "manual",
            "source_doc": source_ref,
            "item_code": item_code,
            "operation": operation,
            "result": result,
        }
        payload.update(extra)
        headers = {**self._headers(), "X-Request-ID": request_id}
        return payload, headers

    def test_cancel_confirmed_success(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-CANCEL-001",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        payload, headers = self._write_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-005",
            operation="cancel",
            result="pass",
            reason="抽检争议",
        )

        with patch.dict("os.environ", self._local_gate_env()):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/cancel",
                headers=headers,
                json=payload,
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["status"], "cancelled")
        self.assertEqual(body["data"]["cancelled_by"], "quality.user")
        self.assertIsNotNone(body["data"]["cancelled_at"])
        self.assertEqual(body["data"]["cancel_reason"], "抽检争议")

        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])).one()
            self.assertEqual(row.status, "cancelled")
            self.assertEqual(row.cancelled_by, "quality.user")
            self.assertIsNotNone(row.cancelled_at)
            self.assertEqual(row.cancel_reason, "抽检争议")
            cancel_log = (
                session.query(LyQualityOperationLog)
                .filter(LyQualityOperationLog.inspection_id == int(seeded["id"]))
                .order_by(LyQualityOperationLog.id.desc())
                .first()
            )
            self.assertIsNotNone(cancel_log)
            self.assertEqual(cancel_log.action, "cancel")
            self.assertEqual(cancel_log.remark, "抽检争议")

        detail_resp = self.client.get(
            f"/api/quality/inspections/{int(seeded['id'])}",
            headers=self._headers(),
        )
        self.assertEqual(detail_resp.status_code, 200, detail_resp.text)
        detail_body = detail_resp.json()
        self.assertEqual(detail_body["code"], "0")
        self.assertEqual(detail_body["data"]["cancel_reason"], "抽检争议")

    def test_cancel_on_draft_or_cancelled_returns_409(self) -> None:
        draft = self._insert_inspection(
            inspection_no="QI-CANCEL-002",
            status="draft",
            result="pending",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        cancelled = self._insert_inspection(
            inspection_no="QI-CANCEL-003",
            status="cancelled",
            result="fail",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("5"),
            rejected_qty=Decimal("5"),
            defect_qty=Decimal("2"),
        )
        draft_payload, draft_headers = self._write_payload(
            draft,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-006",
            operation="cancel",
            result="pending",
            reason="不应允许",
        )
        cancelled_payload, cancelled_headers = self._write_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-007",
            operation="cancel",
            result="fail",
            reason="重复取消",
        )

        with patch.dict("os.environ", self._local_gate_env()):
            draft_resp = self.client.post(
                f"/api/quality/inspections/{int(draft['id'])}/cancel",
                headers=draft_headers,
                json=draft_payload,
            )
            cancelled_resp = self.client.post(
                f"/api/quality/inspections/{int(cancelled['id'])}/cancel",
                headers=cancelled_headers,
                json=cancelled_payload,
            )

        self.assertEqual(draft_resp.status_code, 409)
        self.assertEqual(draft_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancelled_resp.status_code, 409)
        self.assertEqual(cancelled_resp.json()["code"], "QUALITY_INVALID_STATUS")

    def test_cancelled_rejects_update_defect_confirm_cancel_with_409(self) -> None:
        cancelled = self._insert_inspection(
            inspection_no="QI-CANCEL-004",
            status="cancelled",
            result="fail",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("6"),
            rejected_qty=Decimal("4"),
            defect_qty=Decimal("2"),
        )
        inspection_id = int(cancelled["id"])
        patch_payload, patch_headers = self._write_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-008",
            operation="update",
            result="fail",
            remark="不应允许",
        )
        defect_payload, defect_headers = self._write_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-009",
            operation="defects",
            result="fail",
            defects=[
                {
                    "defect_code": "DEF-999",
                    "defect_name": "不应录入",
                    "defect_qty": "1",
                    "severity": "minor",
                    "item_line_no": 1,
                }
            ],
        )
        confirm_payload, confirm_headers = self._write_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-010",
            operation="confirm",
            result="fail",
            remark="不应允许",
        )
        cancel_payload, cancel_headers = self._write_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-011",
            operation="cancel",
            result="fail",
            reason="不应允许",
        )

        with patch.dict("os.environ", self._local_gate_env()):
            patch_resp = self.client.patch(
                f"/api/quality/inspections/{inspection_id}",
                headers=patch_headers,
                json=patch_payload,
            )
            defect_resp = self.client.post(
                f"/api/quality/inspections/{inspection_id}/defects",
                headers=defect_headers,
                json=defect_payload,
            )
            confirm_resp = self.client.post(
                f"/api/quality/inspections/{inspection_id}/confirm",
                headers=confirm_headers,
                json=confirm_payload,
            )
            cancel_resp = self.client.post(
                f"/api/quality/inspections/{inspection_id}/cancel",
                headers=cancel_headers,
                json=cancel_payload,
            )

        self.assertEqual(patch_resp.status_code, 409)
        self.assertEqual(patch_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(defect_resp.status_code, 409)
        self.assertEqual(defect_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(confirm_resp.status_code, 409)
        self.assertEqual(confirm_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancel_resp.status_code, 409)
        self.assertEqual(cancel_resp.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
