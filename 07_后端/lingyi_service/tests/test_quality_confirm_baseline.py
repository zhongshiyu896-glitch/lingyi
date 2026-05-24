"""TASK-030C baseline tests for quality inspection confirm workflow."""

from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import patch

from app.models.quality import LyQualityInspection
from app.models.quality_outbox import LyQualityOutbox
from app.services.quality_service import QualitySourceValidationSnapshot
from tests.test_quality_api import QualityApiBase


class QualityConfirmBaselineTest(QualityApiBase):
    """Verify confirm endpoint only allows draft -> confirmed."""

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

    @classmethod
    def _request_id(
        cls,
        *,
        scenario_tag: str,
        idempotency_key: str,
        source_ref: str,
        inspection_ref: str,
        item_code: str,
        result: str,
    ) -> str:
        return (
            f"{scenario_tag}-QI-F-"
            f"{cls._carrier_code(idempotency_key)}-"
            f"{cls._carrier_code(source_ref)}-"
            f"{cls._carrier_code(inspection_ref)}-"
            f"{cls._carrier_code(item_code)}-"
            f"{cls._carrier_code(result)}"
        )

    def _confirm_payload(
        self,
        inspection: dict[str, object],
        *,
        scenario_tag: str,
        result: str,
        remark: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        inspection_ref = str(inspection["inspection_no"])
        source_ref = f"{scenario_tag}/{inspection_ref}"
        item_code = "ITEM-A"
        idempotency_key = f"{scenario_tag}:confirm"
        request_id = self._request_id(
            scenario_tag=scenario_tag,
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
            "operation": "confirm",
            "result": result,
            "remark": remark,
        }
        headers = {**self._headers(), "X-Request-ID": request_id}
        return payload, headers

    def test_confirm_draft_success(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-CONFIRM-001",
            status="draft",
            result="partial",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        payload, headers = self._confirm_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-004",
            result="partial",
            remark="确认通过",
        )

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/confirm",
                headers=headers,
                json=payload,
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["status"], "confirmed")
        self.assertEqual(body["data"]["confirmed_by"], "quality.user")
        self.assertIsNotNone(body["data"]["confirmed_at"])

        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])).one()
            self.assertEqual(row.status, "confirmed")
            self.assertEqual(row.confirmed_by, "quality.user")
            self.assertIsNotNone(row.confirmed_at)
            outbox = session.query(LyQualityOutbox).filter(LyQualityOutbox.inspection_id == int(seeded["id"])).one()
            self.assertEqual(outbox.status, "pending")
            self.assertEqual(int(outbox.attempts), 0)
            self.assertEqual(int(outbox.max_attempts), 3)
            self.assertTrue(str(outbox.event_key).startswith("qo:"))
            self.assertIsNotNone(outbox.payload_hash)

        status_resp = self.client.get(
            f"/api/quality/inspections/{int(seeded['id'])}/outbox-status",
            headers=self._headers(),
        )
        self.assertEqual(status_resp.status_code, 200, status_resp.text)
        status_data = status_resp.json()["data"]
        self.assertEqual(status_data["inspection_id"], int(seeded["id"]))
        self.assertEqual(status_data["status"], "pending")
        self.assertEqual(status_data["attempts"], 0)
        self.assertEqual(status_data["max_attempts"], 3)

    def test_confirm_on_confirmed_or_cancelled_returns_409(self) -> None:
        confirmed = self._insert_inspection(
            inspection_no="QI-CONFIRM-002",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        cancelled = self._insert_inspection(
            inspection_no="QI-CONFIRM-003",
            status="cancelled",
            result="fail",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("5"),
            rejected_qty=Decimal("5"),
            defect_qty=Decimal("2"),
        )
        confirmed_payload, confirmed_headers = self._confirm_payload(
            confirmed,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-005",
            result="pass",
            remark="重复确认",
        )
        cancelled_payload, cancelled_headers = self._confirm_payload(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-006",
            result="fail",
            remark="不应允许",
        )

        with patch.dict("os.environ", self._local_gate_env()):
            confirmed_resp = self.client.post(
                f"/api/quality/inspections/{int(confirmed['id'])}/confirm",
                headers=confirmed_headers,
                json=confirmed_payload,
            )
            cancelled_resp = self.client.post(
                f"/api/quality/inspections/{int(cancelled['id'])}/confirm",
                headers=cancelled_headers,
                json=cancelled_payload,
            )

        self.assertEqual(confirmed_resp.status_code, 409)
        self.assertEqual(confirmed_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancelled_resp.status_code, 409)
        self.assertEqual(cancelled_resp.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
