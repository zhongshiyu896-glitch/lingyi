"""Inspection amount-calculation tests for subcontract module (TASK-002F)."""

from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.schemas.subcontract import InspectRequest
from app.core.exceptions import BusinessException
from app.core.error_codes import SUBCONTRACT_INSPECTION_QTY_EXCEEDED
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService
from app.services.subcontract_service import SubcontractService
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService


class SubcontractInspectionTest(unittest.TestCase):
    """Validate inspection formula, idempotency and status transitions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        BomBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-INSP-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=1,
                    process_name="外发裁剪",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("10"),
                )
            )
            session.commit()

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[subcontract_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()

            session.add_all(
                [
                    LySubcontractOrder(
                        id=1,
                        subcontract_no="SC-INSP-001",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        subcontract_rate=Decimal("10"),
                        status="waiting_inspection",
                    ),
                    LySubcontractOrder(
                        id=2,
                        subcontract_no="SC-INSP-002",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        subcontract_rate=Decimal("10"),
                        status="waiting_inspection",
                    ),
                    LySubcontractOrder(
                        id=3,
                        subcontract_no="SC-INSP-003",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        subcontract_rate=Decimal("10"),
                        status="waiting_inspection",
                    ),
                    LySubcontractOrder(
                        id=4,
                        subcontract_no="SC-INSP-004",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("120"),
                        subcontract_rate=Decimal("10"),
                        status="waiting_inspection",
                    ),
                ]
            )

            session.add_all(
                [
                    LySubcontractReceipt(
                        id=100,
                        subcontract_id=1,
                        company="COMP-A",
                        receipt_batch_no="RB-1",
                        receipt_warehouse="WH-RECV-A",
                        item_code="ITEM-A",
                        received_qty=Decimal("100"),
                        inspected_qty=Decimal("0"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("0"),
                        inspect_status="pending",
                        sync_status="succeeded",
                        stock_entry_name="STE-REAL-100",
                        idempotency_key="idem-seed-rb-1",
                    ),
                    LySubcontractReceipt(
                        id=200,
                        subcontract_id=2,
                        company="COMP-A",
                        receipt_batch_no="RB-2",
                        receipt_warehouse="WH-RECV-A",
                        item_code="ITEM-A",
                        received_qty=Decimal("100"),
                        inspected_qty=Decimal("0"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("0"),
                        inspect_status="pending",
                        sync_status="succeeded",
                        stock_entry_name="STE-REAL-200",
                        idempotency_key="idem-seed-rb-2",
                    ),
                    LySubcontractReceipt(
                        id=201,
                        subcontract_id=2,
                        company="COMP-A",
                        receipt_batch_no="RB-2B",
                        receipt_warehouse="WH-RECV-A",
                        item_code="ITEM-A",
                        received_qty=Decimal("50"),
                        inspected_qty=Decimal("0"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("0"),
                        inspect_status="pending",
                        sync_status="succeeded",
                        stock_entry_name="STE-REAL-201",
                        idempotency_key="idem-seed-rb-2b",
                    ),
                    LySubcontractReceipt(
                        id=300,
                        subcontract_id=3,
                        company="COMP-A",
                        receipt_batch_no="RB-3",
                        receipt_warehouse="WH-RECV-A",
                        item_code="ITEM-A",
                        received_qty=Decimal("100"),
                        inspected_qty=Decimal("0"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("0"),
                        inspect_status="pending",
                        sync_status="failed",
                        stock_entry_name=None,
                        idempotency_key="idem-seed-rb-3",
                    ),
                    LySubcontractReceipt(
                        id=400,
                        subcontract_id=4,
                        company="COMP-A",
                        receipt_batch_no="RB-4",
                        receipt_warehouse="WH-RECV-A",
                        item_code="ITEM-A",
                        received_qty=Decimal("100"),
                        inspected_qty=Decimal("0"),
                        rejected_qty=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        deduction_amount=Decimal("0"),
                        net_amount=Decimal("0"),
                        inspect_status="pending",
                        sync_status="succeeded",
                        stock_entry_name="STE-REAL-400",
                        idempotency_key="idem-seed-rb-4",
                    ),
                ]
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "inspect.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _payload(
        *,
        batch: str = "RB-1",
        idem: str = "idem-inspect-1",
        inspected_qty: str = "100",
        rejected_qty: str = "5",
        deduction_amount_per_piece: str = "2.00",
    ) -> dict[str, str]:
        return {
            "receipt_batch_no": batch,
            "idempotency_key": idem,
            "inspected_qty": inspected_qty,
            "rejected_qty": rejected_qty,
            "deduction_amount_per_piece": deduction_amount_per_piece,
            "remark": "unit-test",
        }

    def test_inspect_creates_inspection_and_amounts(self) -> None:
        response = self.client.post("/api/subcontract/1/inspect", headers=self._headers(), json=self._payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["status"], "completed")
        self.assertEqual(Decimal(str(data["accepted_qty"])), Decimal("95"))
        self.assertEqual(Decimal(str(data["rejected_rate"])), Decimal("0.050000"))
        self.assertEqual(Decimal(str(data["gross_amount"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(data["deduction_amount"])), Decimal("10.00"))
        self.assertEqual(Decimal(str(data["net_amount"])), Decimal("990.00"))

        with self.SessionLocal() as session:
            inspection = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == 1)
                .order_by(LySubcontractInspection.id.desc())
                .first()
            )
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 1).first()
        self.assertIsNotNone(inspection)
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "completed")
        self.assertEqual(Decimal(str(order.net_amount)), Decimal("990.00"))

    def test_inspect_requires_receipt_batch_no(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json={
                "idempotency_key": "idem-inspect-no-batch",
                "inspected_qty": "10",
                "rejected_qty": "0",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_RECEIPT_BATCH_REQUIRED")

    def test_inspect_rejects_receipt_batch_from_other_order(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-2", idem="idem-inspect-other-order"),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND")

    def test_inspect_rejects_unsynced_receipt_batch(self) -> None:
        response = self.client.post(
            "/api/subcontract/3/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-3", idem="idem-inspect-unsynced"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_RECEIPT_NOT_SYNCED")

    def test_inspect_idempotent_same_payload_returns_existing_result(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-same", inspected_qty="60", rejected_qty="2"),
        )
        second = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-same", inspected_qty="60", rejected_qty="2"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["inspection_no"], second.json()["data"]["inspection_no"])
        with self.SessionLocal() as session:
            count = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == 1)
                .count()
            )
        self.assertEqual(count, 1)

    def test_inspect_same_key_different_receipt_batch_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-2", idem="idem-batch-conflict", inspected_qty="10", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        second = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-2B", idem="idem-batch-conflict", inspected_qty="10", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

    def test_inspect_same_key_different_receipt_batch_does_not_create_second_success_response(self) -> None:
        first = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-2", idem="idem-batch-no-second", inspected_qty="10", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        second = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-2B", idem="idem-batch-no-second", inspected_qty="10", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        with self.SessionLocal() as session:
            count = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == 2)
                .count()
            )
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 2).first()
        self.assertEqual(count, 1)
        self.assertIsNotNone(order)
        self.assertEqual(Decimal(str(order.inspected_qty)), Decimal("10"))
        self.assertEqual(Decimal(str(order.gross_amount)), Decimal("100.00"))
        self.assertEqual(Decimal(str(order.net_amount)), Decimal("100.00"))

    def test_inspect_same_key_same_batch_decimal_equivalent_returns_existing_result(self) -> None:
        first = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(
                batch="RB-2",
                idem="idem-same-batch-decimal",
                inspected_qty="10.0",
                rejected_qty="1.000000",
                deduction_amount_per_piece="2.0",
            ),
        )
        second = self.client.post(
            "/api/subcontract/2/inspect",
            headers=self._headers(),
            json=self._payload(
                batch="RB-2",
                idem="idem-same-batch-decimal",
                inspected_qty="10.000000",
                rejected_qty="1",
                deduction_amount_per_piece="2.000000",
            ),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["inspection_no"], second.json()["data"]["inspection_no"])

    def test_inspect_idempotent_different_payload_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-conflict", inspected_qty="60", rejected_qty="2"),
        )
        second = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-conflict", inspected_qty="60", rejected_qty="3"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

    def test_inspect_same_key_same_batch_different_deduction_rate_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-deduction-conflict", inspected_qty="60", rejected_qty="2", deduction_amount_per_piece="1"),
        )
        second = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-deduction-conflict", inspected_qty="60", rejected_qty="2", deduction_amount_per_piece="2"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

    def test_inspect_idempotent_retry_after_full_inspection_does_not_check_remaining_first(self) -> None:
        payload = self._payload(idem="idem-inspect-full", inspected_qty="100", rejected_qty="0", deduction_amount_per_piece="0")
        first = self.client.post("/api/subcontract/1/inspect", headers=self._headers(), json=payload)
        second = self.client.post("/api/subcontract/1/inspect", headers=self._headers(), json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.json()["code"], "SUBCONTRACT_INSPECTION_QTY_EXCEEDED")

    def test_inspect_rejects_rejected_qty_greater_than_inspected_qty(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-rejected", inspected_qty="5", rejected_qty="6"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED")

    def test_inspect_rejects_deduction_amount_greater_than_gross_amount(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(
                idem="idem-inspect-deduction",
                inspected_qty="1",
                rejected_qty="1",
                deduction_amount_per_piece="11",
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS")

    def test_inspect_rejects_qty_exceeding_batch_remaining_qty(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-over-1", inspected_qty="90", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        second = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-over-2", inspected_qty="20", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_INSPECTION_QTY_EXCEEDED")

    def test_inspect_service_layer_prevents_overinspect_regression(self) -> None:
        with self.SessionLocal() as session:
            service = SubcontractService(session=session)
            first = service.inspect(
                order_id=1,
                payload=InspectRequest(
                    receipt_batch_no="RB-1",
                    idempotency_key="idem-service-overinspect-1",
                    inspected_qty=Decimal("70"),
                    rejected_qty=Decimal("0"),
                    deduction_amount_per_piece=Decimal("0"),
                    remark="service-guard",
                ),
                operator="inspect.user",
                request_id="rid-service-overinspect-1",
            )
            self.assertEqual(first.status, "waiting_inspection")

            with self.assertRaises(BusinessException) as exc_ctx:
                service.inspect(
                    order_id=1,
                    payload=InspectRequest(
                        receipt_batch_no="RB-1",
                        idempotency_key="idem-service-overinspect-2",
                        inspected_qty=Decimal("70"),
                        rejected_qty=Decimal("0"),
                        deduction_amount_per_piece=Decimal("0"),
                        remark="service-guard",
                    ),
                    operator="inspect.user",
                    request_id="rid-service-overinspect-2",
                )
            self.assertEqual(exc_ctx.exception.code, SUBCONTRACT_INSPECTION_QTY_EXCEEDED)
            session.rollback()

        with self.SessionLocal() as session:
            total_inspected = (
                session.query(LySubcontractInspection)
                .filter(
                    LySubcontractInspection.subcontract_id == 1,
                    LySubcontractInspection.receipt_batch_no == "RB-1",
                )
                .all()
            )
            received = (
                session.query(LySubcontractReceipt.received_qty)
                .filter(
                    LySubcontractReceipt.subcontract_id == 1,
                    LySubcontractReceipt.receipt_batch_no == "RB-1",
                )
                .first()
            )
        self.assertIsNotNone(received)
        total_inspected_qty = sum(Decimal(str(row.inspected_qty or "0")) for row in total_inspected)
        received_qty = Decimal(str(received[0] or "0"))
        self.assertLessEqual(total_inspected_qty, received_qty)

    def test_inspect_partial_batch_keeps_waiting_inspection(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-inspect-partial", inspected_qty="40", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "waiting_inspection")

    def test_inspect_all_received_but_not_all_planned_sets_waiting_receive(self) -> None:
        response = self.client.post(
            "/api/subcontract/4/inspect",
            headers=self._headers(),
            json=self._payload(batch="RB-4", idem="idem-inspect-waiting-receive", inspected_qty="100", rejected_qty="0", deduction_amount_per_piece="0"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "waiting_receive")

    def test_inspect_does_not_call_erpnext_or_create_finance_docs(self) -> None:
        with patch.object(ERPNextStockEntryService, "find_by_event_key") as find_mock, patch.object(
            ERPNextStockEntryService, "create_and_submit_material_issue"
        ) as issue_mock, patch.object(
            ERPNextStockEntryService, "create_and_submit_material_receipt"
        ) as receipt_mock:
            response = self.client.post(
                "/api/subcontract/1/inspect",
                headers=self._headers(),
                json=self._payload(idem="idem-inspect-no-erp", inspected_qty="10", rejected_qty="0", deduction_amount_per_piece="0"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(find_mock.call_count, 0)
        self.assertEqual(issue_mock.call_count, 0)
        self.assertEqual(receipt_mock.call_count, 0)

    def test_inspection_payload_hash_includes_receipt_batch_no(self) -> None:
        payload_a = {
            "stock_action": "inspection",
            "subcontract_id": 2,
            "subcontract_no": "SC-INSP-002",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "receipt_batch_no": "RB-2",
            "inspected_qty": "10",
            "rejected_qty": "1",
            "deduction_amount_per_piece": "2",
            "remark": "unit-test",
        }
        payload_b = dict(payload_a)
        payload_b["receipt_batch_no"] = "RB-2B"

        inspection_hash_a = SubcontractService.build_inspection_payload_hash(payload_a)
        inspection_hash_b = SubcontractService.build_inspection_payload_hash(payload_b)
        self.assertNotEqual(inspection_hash_a, inspection_hash_b)

    def test_inspection_payload_hash_does_not_use_stock_outbox_volatile_exclusions(self) -> None:
        payload_a = {
            "stock_action": "inspection",
            "subcontract_id": 2,
            "receipt_batch_no": "RB-2",
            "inspected_qty": "10",
            "rejected_qty": "1.0",
            "deduction_amount_per_piece": "2.000000",
        }
        payload_b = dict(payload_a)
        payload_b["receipt_batch_no"] = "RB-2B"

        inspection_hash_a = SubcontractService.build_inspection_payload_hash(payload_a)
        inspection_hash_b = SubcontractService.build_inspection_payload_hash(payload_b)
        outbox_hash_a = SubcontractStockOutboxService.build_payload_hash(payload_a)
        outbox_hash_b = SubcontractStockOutboxService.build_payload_hash(payload_b)

        self.assertNotEqual(inspection_hash_a, inspection_hash_b)
        self.assertEqual(outbox_hash_a, outbox_hash_b)

    def test_subcontract_detail_returns_inspections(self) -> None:
        inspect_resp = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-detail-inspections", inspected_qty="10", rejected_qty="1", deduction_amount_per_piece="2"),
        )
        self.assertEqual(inspect_resp.status_code, 200)

        detail_resp = self.client.get("/api/subcontract/1", headers=self._headers())
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()["code"], "0")
        inspections = detail_resp.json()["data"].get("inspections")
        self.assertIsInstance(inspections, list)
        self.assertGreaterEqual(len(inspections), 1)
        row = inspections[0]
        for key in (
            "inspection_no",
            "receipt_batch_no",
            "inspected_qty",
            "accepted_qty",
            "rejected_qty",
            "rejected_rate",
            "subcontract_rate",
            "gross_amount",
            "deduction_amount_per_piece",
            "deduction_amount",
            "net_amount",
            "inspected_by",
            "inspected_at",
        ):
            self.assertIn(key, row)

    def test_subcontract_detail_inspection_amounts_use_inspection_table_not_receipt_legacy_fields(self) -> None:
        inspect_resp = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json=self._payload(idem="idem-detail-amount-source", inspected_qty="20", rejected_qty="2", deduction_amount_per_piece="3"),
        )
        self.assertEqual(inspect_resp.status_code, 200)
        inspection_no = inspect_resp.json()["data"]["inspection_no"]

        with self.SessionLocal() as session:
            receipt = (
                session.query(LySubcontractReceipt)
                .filter(
                    LySubcontractReceipt.subcontract_id == 1,
                    LySubcontractReceipt.receipt_batch_no == "RB-1",
                )
                .first()
            )
            self.assertIsNotNone(receipt)
            receipt.inspected_qty = Decimal("999")
            receipt.rejected_qty = Decimal("999")
            receipt.rejected_rate = Decimal("0.999999")
            receipt.deduction_amount = Decimal("8888")
            receipt.net_amount = Decimal("-7777")
            session.commit()

        detail_resp = self.client.get("/api/subcontract/1", headers=self._headers())
        self.assertEqual(detail_resp.status_code, 200)
        rows = detail_resp.json()["data"]["inspections"]
        target = next((row for row in rows if row["inspection_no"] == inspection_no), None)
        self.assertIsNotNone(target)
        self.assertEqual(Decimal(str(target["gross_amount"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(target["deduction_amount"])), Decimal("6.00"))
        self.assertEqual(Decimal(str(target["net_amount"])), Decimal("194.00"))

    def test_no_gross_amount_accepted_qty_formula_in_business_code(self) -> None:
        source = Path("/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(source, r"gross_amount\s*=\s*accepted_qty\s*\*")

    def test_no_net_amount_quantity_minus_amount_formula_in_business_code(self) -> None:
        source = Path("/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(source, r"net_amount\s*=\s*inspected_qty\s*-\s*deduction_amount")


if __name__ == "__main__":
    unittest.main()
