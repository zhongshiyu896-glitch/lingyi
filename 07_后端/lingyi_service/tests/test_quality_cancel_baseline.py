"""TASK-030C baseline tests for quality inspection cancel workflow."""

from __future__ import annotations

from decimal import Decimal
import unittest

from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityOperationLog
from tests.test_quality_api import QualityApiBase


class QualityCancelBaselineTest(QualityApiBase):
    """Verify cancel endpoint only allows confirmed -> cancelled."""

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

        response = self.client.post(
            f"/api/quality/inspections/{int(seeded['id'])}/cancel",
            headers=self._headers(),
            json={"reason": "抽检争议"},
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

        draft_resp = self.client.post(
            f"/api/quality/inspections/{int(draft['id'])}/cancel",
            headers=self._headers(),
            json={"reason": "不应允许"},
        )
        cancelled_resp = self.client.post(
            f"/api/quality/inspections/{int(cancelled['id'])}/cancel",
            headers=self._headers(),
            json={"reason": "重复取消"},
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

        patch_resp = self.client.patch(
            f"/api/quality/inspections/{inspection_id}",
            headers=self._headers(),
            json={"remark": "不应允许"},
        )
        defect_resp = self.client.post(
            f"/api/quality/inspections/{inspection_id}/defects",
            headers=self._headers(),
            json={
                "defects": [
                    {
                        "defect_code": "DEF-999",
                        "defect_name": "不应录入",
                        "defect_qty": "1",
                        "severity": "minor",
                        "item_line_no": 1,
                    }
                ]
            },
        )
        confirm_resp = self.client.post(
            f"/api/quality/inspections/{inspection_id}/confirm",
            headers=self._headers(),
            json={"remark": "不应允许"},
        )
        cancel_resp = self.client.post(
            f"/api/quality/inspections/{inspection_id}/cancel",
            headers=self._headers(),
            json={"reason": "不应允许"},
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
