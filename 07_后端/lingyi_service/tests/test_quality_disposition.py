"""B-phase quality release/rework disposition tests."""

from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import patch

from app.models.audit import LyOperationAuditLog
from app.models.quality import LyQualityDisposition
from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityOperationLog
from app.models.quality_outbox import LyQualityOutbox
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.services.quality_service import QualitySourceValidationSnapshot
from tests.test_quality_api import QualityApiBase


class QualityDispositionTest(QualityApiBase):
    """Verify quality inspection release/rework is real and idempotent."""

    @staticmethod
    def _snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}},
            source=None,
        )

    def test_release_draft_confirms_records_disposition_and_creates_outbox(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-RELEASE-001",
            status="draft",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        self._seed_finished_goods_production_for_inspection(seeded, qty=Decimal("10"))
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-201",
            operation="release",
            idempotency_key="quality-disposition-release",
            result="pass",
            remark="放行",
        )

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "confirmed")
        self.assertEqual(data["action"], "release")
        self.assertEqual(Decimal(str(data["qty"])), Decimal("10"))
        self.assertEqual(data["downstream_type"], "finished_goods_inbound")
        self.assertIsInstance(data["warehouse_draft_id"], int)
        self.assertTrue(str(data["warehouse_source_id"]).startswith("quality-release:QI-RELEASE-001:"))

        with self.SessionLocal() as session:
            inspection = session.query(LyQualityInspection).filter(LyQualityInspection.id == int(seeded["id"])).one()
            self.assertEqual(inspection.status, "confirmed")
            disposition = session.query(LyQualityDisposition).filter(LyQualityDisposition.inspection_id == int(seeded["id"])).one()
            self.assertEqual(disposition.action, "release")
            self.assertEqual(disposition.idempotency_key, "quality-disposition-release")
            self.assertEqual(disposition.result_json["downstream_type"], "finished_goods_inbound")
            self.assertEqual(disposition.result_json["warehouse_draft_id"], data["warehouse_draft_id"])
            outbox = session.query(LyQualityOutbox).filter(LyQualityOutbox.inspection_id == int(seeded["id"])).one()
            self.assertEqual(outbox.status, "pending")
            draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.id == int(data["warehouse_draft_id"]))
                .one()
            )
            self.assertEqual(str(draft.purpose), "Material Receipt")
            self.assertEqual(str(draft.source_type), "finished_goods_inbound")
            self.assertEqual(str(draft.source_id), data["warehouse_source_id"])
            self.assertEqual(str(draft.target_warehouse), "WH-A")
            draft_item = (
                session.query(LyWarehouseStockEntryDraftItem)
                .filter(LyWarehouseStockEntryDraftItem.draft_id == int(draft.id))
                .one()
            )
            self.assertEqual(str(draft_item.item_code), "ITEM-A")
            self.assertEqual(Decimal(str(draft_item.qty)), Decimal("10.000000"))
            self.assertEqual(str(draft_item.target_warehouse), "WH-A")
            warehouse_outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == int(draft.id))
                .one()
            )
            self.assertEqual(str(warehouse_outbox.status), "in_pending")
            self.assertEqual(warehouse_outbox.payload["finished_goods_source_id"], data["warehouse_source_id"])
            log = (
                session.query(LyQualityOperationLog)
                .filter(LyQualityOperationLog.inspection_id == int(seeded["id"]), LyQualityOperationLog.action == "confirm")
                .order_by(LyQualityOperationLog.id.desc())
                .first()
            )
            self.assertIsNotNone(log)
            self.assertIn("release", str(log.remark))
            audit_log = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.resource_id == int(seeded["id"]),
                    LyOperationAuditLog.action == "quality:release",
                    LyOperationAuditLog.result == "success",
                )
                .one()
            )
            self.assertEqual(audit_log.after_data["downstream_type"], "finished_goods_inbound")
            self.assertEqual(audit_log.after_data["warehouse_draft_id"], data["warehouse_draft_id"])

    def test_rework_draft_confirms_and_records_disposition_without_outbox(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-REWORK-001",
            status="draft",
            result="fail",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("0"),
            rejected_qty=Decimal("10"),
            defect_qty=Decimal("3"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-202",
            operation="rework",
            idempotency_key="quality-disposition-rework",
            result="fail",
            remark="返工",
        )

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/rework",
                headers=self._headers_for_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "confirmed")
        self.assertEqual(data["action"], "rework")
        self.assertEqual(Decimal(str(data["qty"])), Decimal("10"))

        with self.SessionLocal() as session:
            disposition = session.query(LyQualityDisposition).filter(LyQualityDisposition.inspection_id == int(seeded["id"])).one()
            self.assertEqual(disposition.action, "rework")
            self.assertEqual(session.query(LyQualityOutbox).filter(LyQualityOutbox.inspection_id == int(seeded["id"])).count(), 0)
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 0)

    def test_release_same_idempotency_replays_same_disposition(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-RELEASE-REPLAY",
            status="draft",
            result="pass",
            inspected_qty=Decimal("8"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        self._seed_finished_goods_production_for_inspection(seeded, qty=Decimal("8"))
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-203",
            operation="release",
            idempotency_key="quality-disposition-replay",
            result="pass",
            remark="放行",
        )

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(payload),
                json=payload,
            )
            second = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(payload),
                json=payload,
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["idempotency_key"], second.json()["data"]["idempotency_key"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityDisposition).filter(LyQualityDisposition.inspection_id == int(seeded["id"])).count(), 1)

    def test_release_same_idempotency_changed_payload_conflicts(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-RELEASE-CONFLICT",
            status="draft",
            result="pass",
            inspected_qty=Decimal("8"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        self._seed_finished_goods_production_for_inspection(seeded, qty=Decimal("8"))
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-204",
            operation="release",
            idempotency_key="quality-disposition-conflict",
            result="pass",
            remark="放行A",
        )
        conflict_payload = dict(payload)
        conflict_payload["remark"] = "放行B"

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(payload),
                json=payload,
            )
            second = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(conflict_payload),
                json=conflict_payload,
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")

    def test_rework_same_idempotency_replays_same_disposition(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-REWORK-REPLAY",
            status="draft",
            result="fail",
            inspected_qty=Decimal("8"),
            accepted_qty=Decimal("0"),
            rejected_qty=Decimal("8"),
            defect_qty=Decimal("2"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-206",
            operation="rework",
            idempotency_key="quality-rework-replay",
            result="fail",
            remark="返工",
        )

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/rework",
                headers=self._headers_for_payload(payload),
                json=payload,
            )
            second = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/rework",
                headers=self._headers_for_payload(payload),
                json=payload,
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["idempotency_key"], second.json()["data"]["idempotency_key"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityDisposition).filter(LyQualityDisposition.inspection_id == int(seeded["id"])).count(), 1)

    def test_rework_same_idempotency_changed_payload_conflicts(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-REWORK-CONFLICT",
            status="draft",
            result="fail",
            inspected_qty=Decimal("8"),
            accepted_qty=Decimal("0"),
            rejected_qty=Decimal("8"),
            defect_qty=Decimal("2"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-207",
            operation="rework",
            idempotency_key="quality-rework-conflict",
            result="fail",
            remark="返工A",
        )
        conflict_payload = dict(payload)
        conflict_payload["remark"] = "返工B"

        with (
            patch.dict("os.environ", self._local_gate_env()),
            patch(
                "app.services.quality_service.QualitySourceValidator.validate_for_payload",
                return_value=self._snapshot(),
            ),
        ):
            first = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/rework",
                headers=self._headers_for_payload(payload),
                json=payload,
            )
            second = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/rework",
                headers=self._headers_for_payload(conflict_payload),
                json=conflict_payload,
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "QUALITY_IDEMPOTENCY_CONFLICT")

    def test_quality_viewer_cannot_release_or_rework(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-RELEASE-FORBIDDEN",
            status="draft",
            result="pass",
            inspected_qty=Decimal("5"),
            accepted_qty=Decimal("5"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        payload = self._action_payload(
            seeded,
            scenario_tag="Z003-QUALITY-INSPECTION-20260617-205",
            operation="release",
            idempotency_key="quality-disposition-forbidden",
            result="pass",
            remark="无权限放行",
        )

        with patch.dict("os.environ", self._local_gate_env()):
            response = self.client.post(
                f"/api/quality/inspections/{int(seeded['id'])}/release",
                headers=self._headers_for_payload(payload, role="Quality Viewer"),
                json=payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
