"""TASK-030B baseline tests for defect recording endpoint."""

from __future__ import annotations

from decimal import Decimal
import unittest

from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from tests.test_quality_api import QualityApiBase


class QualityDefectBaselineTest(QualityApiBase):
    """Verify defect recording only works on draft inspections."""

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

        response = self.client.post(
            f"/api/quality/inspections/{int(seeded['id'])}/defects",
            headers=self._headers(),
            json={
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

        response = self.client.post(
            f"/api/quality/inspections/{int(seeded['id'])}/defects",
            headers=self._headers(),
            json={
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
