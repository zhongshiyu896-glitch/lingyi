"""Quality write idempotency tests for create/update/confirm/cancel."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityOperationLog
from app.models.quality import LyQualityWriteIdempotency
from app.models.quality_outbox import LyQualityOutbox
from app.services.quality_service import QualitySourceValidationSnapshot
from tests.test_quality_api import QualityApiBase


class QualityWriteIdempotencyTest(QualityApiBase):
    """Verify quality writes replay same idempotency and reject payload drift."""

    @staticmethod
    def _snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}},
            source=None,
        )

    def test_create_same_idempotency_replays_without_duplicate_inspection(self) -> None:
        payload = self._payload(
            scenario_tag="Z003-QUALITY-INSPECTION-20260619-301",
            idempotency_key="quality-create-idem-301",
            remark="首提交",
        )
        conflict_payload = {**payload, "remark": "同键改内容"}

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post("/api/quality/inspections", headers=self._headers_for_payload(payload), json=payload)
            second = self.client.post("/api/quality/inspections", headers=self._headers_for_payload(payload), json=payload)
            conflict = self.client.post("/api/quality/inspections", headers=self._headers_for_payload(conflict_payload), json=conflict_payload)

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 1)
            self.assertEqual(session.query(LyQualityOperationLog).count(), 1)
            self.assertEqual(session.query(LyQualityWriteIdempotency).count(), 1)

    def test_update_same_idempotency_replays_without_duplicate_log(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-IDEM-UPDATE-001",
            status="draft",
            result="partial",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260619-302",
            operation="update",
            idempotency_key="quality-update-idem-302",
            result="partial",
            accepted_qty="9",
            rejected_qty="1",
            defect_qty="1",
            remark="更新草稿",
        )
        conflict_payload = {**payload, "remark": "同键改更新内容"}

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.patch(f"/api/quality/inspections/{int(seeded['id'])}", headers=self._headers_for_payload(payload), json=payload)

        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])).one()
            row.status = "confirmed"
            session.commit()

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            second = self.client.patch(f"/api/quality/inspections/{int(seeded['id'])}", headers=self._headers_for_payload(payload), json=payload)
            conflict = self.client.patch(f"/api/quality/inspections/{int(seeded['id'])}", headers=self._headers_for_payload(conflict_payload), json=conflict_payload)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["remark"], second.json()["data"]["remark"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])).one()
            self.assertEqual(str(row.accepted_qty), "9.000000")
            self.assertEqual(session.query(LyQualityOperationLog).filter(LyQualityOperationLog.inspection_id == int(seeded["id"])).count(), 2)
            self.assertEqual(session.query(LyQualityWriteIdempotency).count(), 1)

    def test_confirm_same_idempotency_replays_without_duplicate_outbox(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-IDEM-CONFIRM-001",
            status="draft",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260619-303",
            operation="confirm",
            idempotency_key="quality-confirm-idem-303",
            result="pass",
            remark="确认",
        )
        conflict_payload = {**payload, "remark": "同键改确认备注"}

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/confirm", headers=self._headers_for_payload(payload), json=payload)
            second = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/confirm", headers=self._headers_for_payload(payload), json=payload)
            conflict = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/confirm", headers=self._headers_for_payload(conflict_payload), json=conflict_payload)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["status"], "confirmed")
        self.assertEqual(second.json()["data"]["status"], "confirmed")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityOutbox).filter(LyQualityOutbox.inspection_id == int(seeded["id"])).count(), 1)
            self.assertEqual(session.query(LyQualityOperationLog).filter(LyQualityOperationLog.inspection_id == int(seeded["id"])).count(), 2)
            self.assertEqual(session.query(LyQualityWriteIdempotency).count(), 1)

    def test_cancel_same_idempotency_replays_without_duplicate_log(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-IDEM-CANCEL-001",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260619-304",
            operation="cancel",
            idempotency_key="quality-cancel-idem-304",
            result="pass",
            reason="取消原因",
        )
        conflict_payload = {**payload, "reason": "同键改取消原因"}

        with patch.dict("os.environ", self._local_gate_env()):
            first = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/cancel", headers=self._headers_for_payload(payload), json=payload)
            second = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/cancel", headers=self._headers_for_payload(payload), json=payload)
            conflict = self.client.post(f"/api/quality/inspections/{int(seeded['id'])}/cancel", headers=self._headers_for_payload(conflict_payload), json=conflict_payload)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["status"], "cancelled")
        self.assertEqual(second.json()["data"]["status"], "cancelled")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityOperationLog).filter(LyQualityOperationLog.inspection_id == int(seeded["id"])).count(), 2)
            self.assertEqual(session.query(LyQualityWriteIdempotency).count(), 1)
