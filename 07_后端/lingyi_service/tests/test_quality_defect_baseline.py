"""TASK-030B baseline tests for defect recording endpoint."""

from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import patch

from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from tests.test_quality_api import QualityApiBase


class QualityDefectBaselineTest(QualityApiBase):
    """Verify defect recording only works on draft inspections."""

    SCENARIO_TAG = "Z003-QUALITY-INSPECTION-20260524-003"

    @staticmethod
    def _carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in value.strip().encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-3:]

    @classmethod
    def _defect_request_id(
        cls,
        *,
        idempotency_key: str,
        source_ref: str,
        inspection_ref: str,
        item_code: str,
        result: str,
    ) -> str:
        return (
            f"{cls.SCENARIO_TAG}-QI-D-"
            f"{cls._carrier_code(idempotency_key)}-"
            f"{cls._carrier_code(source_ref)}-"
            f"{cls._carrier_code(inspection_ref)}-"
            f"{cls._carrier_code(item_code)}-"
            f"{cls._carrier_code(result)}"
        )

    def test_add_defect_to_draft_returns_201(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-DEFECT-001",
            status="draft",
            result="partial",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        idempotency_key = "idem-defect-draft"
        source_ref = f"{self.SCENARIO_TAG}/QI-DEFECT-001"
        inspection_ref = str(seeded["inspection_no"])
        item_code = "ITEM-A"
        result = "partial"
        request_id = self._defect_request_id(
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            inspection_ref=inspection_ref,
            item_code=item_code,
            result=result,
        )

        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db",
            },
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/defects",
                headers={**self._headers(), "X-Request-ID": request_id},
                json={
                    "request_id": request_id,
                    "idempotency_key": idempotency_key,
                    "scenario_tag": self.SCENARIO_TAG,
                    "source_ref": source_ref,
                    "inspection_ref": inspection_ref,
                    "source_type": "manual",
                    "source_doc": source_ref,
                    "item_code": item_code,
                    "operation": "defects",
                    "result": result,
                    "defects": [
                        {
                            "defect_code": "DEF-002",
                            "defect_name": "破洞",
                            "defect_qty": "1",
                            "severity": "major",
                            "item_line_no": 1,
                        }
                    ]
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["status"], "draft")
        self.assertEqual(len(body["data"]["defects"]), 2)

        with self.SessionLocal() as session:
            self.assertEqual(
                session.query(LyQualityDefect).filter(LyQualityDefect.inspection_id == int(seeded["id"])) .count(),
                2,
            )
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])) .one()
            self.assertEqual(str(row.defect_qty), "2.000000")

    def test_add_defect_to_non_draft_rejected_with_403(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-DEFECT-002",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        idempotency_key = "idem-defect-confirmed"
        source_ref = f"{self.SCENARIO_TAG}/QI-DEFECT-002"
        inspection_ref = str(seeded["inspection_no"])
        item_code = "ITEM-A"
        result = "pass"
        request_id = self._defect_request_id(
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            inspection_ref=inspection_ref,
            item_code=item_code,
            result=result,
        )

        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db",
            },
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/defects",
                headers={**self._headers(), "X-Request-ID": request_id},
                json={
                    "request_id": request_id,
                    "idempotency_key": idempotency_key,
                    "scenario_tag": self.SCENARIO_TAG,
                    "source_ref": source_ref,
                    "inspection_ref": inspection_ref,
                    "source_type": "manual",
                    "source_doc": source_ref,
                    "item_code": item_code,
                    "operation": "defects",
                    "result": result,
                    "defects": [
                        {
                            "defect_code": "DEF-003",
                            "defect_name": "污渍",
                            "defect_qty": "1",
                            "severity": "minor",
                            "item_line_no": 1,
                        }
                    ]
                },
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
