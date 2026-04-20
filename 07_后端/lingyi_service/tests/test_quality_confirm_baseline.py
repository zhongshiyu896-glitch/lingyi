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

        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/confirm",
                headers=self._headers(),
                json={"remark": "确认通过"},
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

        confirmed_resp = self.client.post(
            f"/api/quality/inspections/{int(confirmed['id'])}/confirm",
            headers=self._headers(),
            json={"remark": "重复确认"},
        )
        cancelled_resp = self.client.post(
            f"/api/quality/inspections/{int(cancelled['id'])}/confirm",
            headers=self._headers(),
            json={"remark": "不应允许"},
        )

        self.assertEqual(confirmed_resp.status_code, 409)
        self.assertEqual(confirmed_resp.json()["code"], "QUALITY_INVALID_STATUS")
        self.assertEqual(cancelled_resp.status_code, 409)
        self.assertEqual(cancelled_resp.json()["code"], "QUALITY_INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()
