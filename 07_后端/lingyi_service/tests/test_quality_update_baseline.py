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

        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.patch(
                f"/api/quality/inspections/{int(seeded['id'])}",
                headers=self._headers(),
                json={
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

        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            confirmed_resp = self.client.patch(
                f"/api/quality/inspections/{int(confirmed['id'])}",
                headers=self._headers(),
                json={"remark": "不应允许"},
            )
            cancelled_resp = self.client.patch(
                f"/api/quality/inspections/{int(cancelled['id'])}",
                headers=self._headers(),
                json={"remark": "不应允许"},
            )

        self.assertEqual(confirmed_resp.status_code, 403)
        self.assertEqual(confirmed_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancelled_resp.status_code, 409)
        self.assertEqual(cancelled_resp.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
