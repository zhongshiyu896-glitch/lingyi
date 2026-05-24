"""TASK-030B baseline tests for quality inspection draft update."""

from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import patch

from app.models.quality import LyQualityInspection
from app.services.quality_service import QualitySourceValidationSnapshot
from tests.test_quality_api import QualityApiBase


class QualityUpdateBaselineTest(QualityApiBase):
    """Verify update endpoint only allows draft inspections."""

    @staticmethod
    def _snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}},
            source=None,
        )

    @staticmethod
    def _carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in value.strip().encode("utf-8"):
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
            f"{scenario_tag}-QI-U-"
            f"{cls._carrier_code(idempotency_key)}-"
            f"{cls._carrier_code(source_ref)}-"
            f"{cls._carrier_code(inspection_ref)}-"
            f"{cls._carrier_code(item_code)}-"
            f"{cls._carrier_code(result)}"
        )

    def _required_update_request(
        self,
        inspection: dict[str, object],
        *,
        scenario_tag: str,
        result: str | None = None,
    ) -> tuple[dict[str, str], dict[str, str]]:
        source_ref = str(inspection.get("source_id") or scenario_tag)
        inspection_ref = str(inspection["id"])
        item_code = str(inspection.get("item_code") or "ITEM-A")
        result = str(result or inspection.get("result") or "pending")
        idempotency_key = f"{scenario_tag}:idempotency"
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
            "source_type": str(inspection.get("source_type") or "manual"),
            "source_doc": source_ref,
            "item_code": item_code,
            "operation": "update",
            "result": result,
        }
        headers = {**self._headers(), "X-Request-ID": request_id}
        return payload, headers

    def test_patch_draft_inspection_success(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-UPDATE-001",
            status="draft",
            result="partial",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        payload, headers = self._required_update_request(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-002",
            result="partial",
        )

        with (
            patch.dict(
                "os.environ",
                {
                    "APP_ENV": "development",
                    "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db",
                },
            ),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            response = self.client.patch(
                f"/api/quality/inspections/{int(seeded['id'])}",
                headers=headers,
                json={
                    **payload,
                    "accepted_qty": "9",
                    "rejected_qty": "1",
                    "defect_qty": "1",
                    "result": "partial",
                    "remark": "更新草稿",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["status"], "draft")
        self.assertEqual(body["data"]["remark"], "更新草稿")

        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])) .one()
            self.assertEqual(str(row.accepted_qty), "9.000000")
            self.assertEqual(str(row.rejected_qty), "1.000000")
            self.assertEqual(str(row.defect_qty), "1.000000")

    def test_patch_confirmed_rejected_with_403_cancelled_rejected_with_409(self) -> None:
        confirmed = self._insert_inspection(
            inspection_no="QI-UPDATE-002",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        cancelled = self._insert_inspection(
            inspection_no="QI-UPDATE-003",
            status="cancelled",
            result="fail",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("3"),
            rejected_qty=Decimal("7"),
            defect_qty=Decimal("2"),
        )
        confirmed_payload, confirmed_headers = self._required_update_request(
            confirmed,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-003",
        )
        cancelled_payload, cancelled_headers = self._required_update_request(
            cancelled,
            scenario_tag="Z003-QUALITY-INSPECTION-20260524-004",
        )

        with (
            patch.dict(
                "os.environ",
                {
                    "APP_ENV": "development",
                    "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db",
                },
            ),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            confirmed_resp = self.client.patch(
                f"/api/quality/inspections/{int(confirmed['id'])}",
                headers=confirmed_headers,
                json={
                    **confirmed_payload,
                    "remark": "不应允许",
                },
            )
            cancelled_resp = self.client.patch(
                f"/api/quality/inspections/{int(cancelled['id'])}",
                headers=cancelled_headers,
                json={
                    **cancelled_payload,
                    "remark": "不应允许",
                },
            )

        self.assertEqual(confirmed_resp.status_code, 403)
        self.assertEqual(confirmed_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancelled_resp.status_code, 409)
        self.assertEqual(cancelled_resp.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
