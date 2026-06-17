"""Audit tests for subcontract module (TASK-002B)."""

from __future__ import annotations

from decimal import Decimal
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.exceptions import AuditWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.audit_service import AuditService
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.core.exceptions import PermissionSourceUnavailable


class SubcontractAuditTest(unittest.TestCase):
    """Validate operation/security audit behavior for subcontract writes."""

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
                    bom_no="BOM-AUD-001",
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
                    subcontract_cost_per_piece=Decimal("1"),
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1,
                    bom_id=1,
                    material_item_code="MAT-A",
                    color=None,
                    size=None,
                    qty_per_piece=Decimal("1"),
                    loss_rate=Decimal("0"),
                    uom="Nos",
                    remark=None,
                )
            )
            session.add(
                LySubcontractOrder(
                    id=100,
                    subcontract_no="SC-ISSUE-100",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="draft",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=101,
                    subcontract_no="SC-RECV-101",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="processing",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=102,
                    subcontract_no="SC-INSP-102",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=2000,
                    subcontract_id=102,
                    company="COMP-A",
                    receipt_batch_no="SRB-AUD-2000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("30"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-AUD-2000",
                    idempotency_key="idem-seed-aud-2000",
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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id >= 2000).delete()
            session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 100).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=101,
                    subcontract_no="SC-RECV-101",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="processing",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=102,
                    subcontract_no="SC-INSP-102",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=2000,
                    subcontract_id=102,
                    company="COMP-A",
                    receipt_batch_no="SRB-AUD-2000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("30"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-AUD-2000",
                    idempotency_key="idem-seed-aud-2000",
                )
            )
            session.commit()

    @staticmethod
    def _headers(
        user: str = "audit.user",
        role: str = "Subcontract Manager",
        *,
        request_id: str | None = None,
    ) -> dict[str, str]:
        headers = {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    @staticmethod
    def _fnv_carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in value.strip().encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-3:]

    @classmethod
    def _write_carrier(
        cls,
        *,
        operation: str,
        idempotency_key: str,
        source_suffix: str,
        subcontract_ref: str,
        supplier_ref: str,
        work_order_ref: str,
        item_code: str,
        quantity: str,
        status_action: str,
    ) -> dict[str, str]:
        scenario_tag = "Z003-SUBCONTRACT-20260524-004"
        source_ref = f"{scenario_tag}-SRC-{source_suffix}"
        operation_codes = {
            "create": "CR",
            "issue_material": "IM",
            "receive": "RV",
            "inspect": "IN",
        }
        request_id = (
            f"{scenario_tag}-SC-{operation_codes[operation]}-"
            f"{cls._fnv_carrier_code(idempotency_key)}-"
            f"{cls._fnv_carrier_code(source_ref)}-"
            f"{cls._fnv_carrier_code(subcontract_ref)}-"
            f"{cls._fnv_carrier_code(supplier_ref)}-"
            f"{cls._fnv_carrier_code(work_order_ref)}-"
            f"{cls._fnv_carrier_code(item_code)}-"
            f"{cls._fnv_carrier_code(status_action)}"
        )
        return {
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "scenario_tag": scenario_tag,
            "source_ref": source_ref,
            "subcontract_ref": subcontract_ref,
            "supplier_ref": supplier_ref,
            "work_order_ref": work_order_ref,
            "operation": operation,
            "item_code": item_code,
            "quantity": quantity,
            "status_action": status_action,
        }

    @classmethod
    def _create_payload(cls, *, planned_qty: str = "100") -> dict[str, str]:
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": "COMP-A",
            "bom_id": 1,
            "planned_qty": planned_qty,
            "process_name": "外发裁剪",
        }
        payload.update(
            cls._write_carrier(
                operation="create",
                idempotency_key=f"idem-audit-create-{planned_qty}",
                source_suffix=f"CREATE-{planned_qty}",
                subcontract_ref=f"NEW-AUDIT-{planned_qty}",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                quantity=planned_qty,
                status_action="create",
            )
        )
        return payload

    @classmethod
    def _issue_payload(cls, *, idem: str = "idem-audit-001", issued_qty: str = "10") -> dict[str, object]:
        payload: dict[str, object] = {
            "warehouse": "WH-A",
            "materials": [
                {"material_item_code": "MAT-A", "required_qty": "100", "issued_qty": issued_qty},
            ],
        }
        payload.update(
            cls._write_carrier(
                operation="issue_material",
                idempotency_key=idem,
                source_suffix="ISSUE-100",
                subcontract_ref="SC-ISSUE-100",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                quantity=issued_qty,
                status_action="issue_material",
            )
        )
        return payload

    @classmethod
    def _receive_payload(
        cls,
        *,
        idem: str = "idem-audit-recv-1",
        received_qty: str = "10",
    ) -> dict[str, str]:
        payload = {
            "receipt_warehouse": "WH-RECV-A",
            "received_qty": received_qty,
        }
        payload.update(
            cls._write_carrier(
                operation="receive",
                idempotency_key=idem,
                source_suffix="RECEIVE-101",
                subcontract_ref="SC-RECV-101",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                quantity=received_qty,
                status_action="receive",
            )
        )
        return payload

    @classmethod
    def _inspect_payload(
        cls,
        *,
        idem: str = "idem-audit-inspect-1",
        inspected_qty: str = "30",
        rejected_qty: str = "1",
        deduction_amount_per_piece: str = "0.1",
    ) -> dict[str, str]:
        payload = {
            "receipt_batch_no": "SRB-AUD-2000",
            "inspected_qty": inspected_qty,
            "rejected_qty": rejected_qty,
            "deduction_amount_per_piece": deduction_amount_per_piece,
        }
        payload.update(
            cls._write_carrier(
                operation="inspect",
                idempotency_key=idem,
                source_suffix="INSPECT-102",
                subcontract_ref="SC-INSP-102",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                quantity=inspected_qty,
                status_action="inspect",
            )
        )
        return payload

    def test_create_success_writes_operation_audit_with_real_operator(self) -> None:
        payload = self._create_payload(planned_qty="100")
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers(user="real.operator", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(LyOperationAuditLog.module == "subcontract", LyOperationAuditLog.action == "subcontract:create")
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)
        self.assertEqual(row.operator, "real.operator")
        self.assertEqual(row.result, "success")
        self.assertIn("Subcontract Manager", row.operator_roles)

    def test_create_replays_same_idempotency_without_duplicate_order_or_status_log(self) -> None:
        payload = self._create_payload(planned_qty="70")
        first = self.client.post(
            "/api/subcontract/",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        second = self.client.post(
            "/api/subcontract/",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["data"]["name"], second.json()["data"]["name"])

        with self.SessionLocal() as session:
            created_orders = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 102).all()
            created_order = created_orders[0]
            status_logs = (
                session.query(LySubcontractStatusLog)
                .filter(LySubcontractStatusLog.subcontract_id == int(created_order.id))
                .all()
            )
        self.assertEqual(len(created_orders), 1)
        self.assertEqual(created_order.idempotency_key, payload["idempotency_key"])
        self.assertEqual(created_order.source_ref, payload["source_ref"])
        self.assertEqual(len(status_logs), 1)

    def test_create_same_idempotency_with_different_payload_returns_conflict(self) -> None:
        payload = self._create_payload(planned_qty="72")
        first = self.client.post(
            "/api/subcontract/",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(first.status_code, 200, first.text)

        conflict_payload = dict(payload)
        conflict_payload["planned_qty"] = "73"
        conflict_payload["quantity"] = "73"
        second = self.client.post(
            "/api/subcontract/",
            headers=self._headers(request_id=payload["request_id"]),
            json=conflict_payload,
        )
        self.assertEqual(second.status_code, 409, second.text)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            created_orders = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 102).all()
        self.assertEqual(len(created_orders), 1)

    def test_issue_material_creates_pending_outbox_and_success_audit(self) -> None:
        payload = self._issue_payload(idem="idem-audit-001", issued_qty="10")
        response = self.client.post(
            "/api/subcontract/100/issue-material",
            headers=self._headers(request_id=str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertNotIn("STE-ISS-", response.text)
        self.assertIsNone(response.json()["data"]["stock_entry_name"])
        self.assertEqual(response.json()["data"]["sync_status"], "pending")

        with self.SessionLocal() as session:
            materials = session.query(LySubcontractMaterial).all()
            outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.subcontract_id == 100)
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:issue_material",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertEqual(len(materials), 1)
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.stock_action, "issue")
        self.assertEqual(outbox.status, "pending")
        self.assertIsNotNone(row)
        self.assertEqual(row.result, "success")
        self.assertIsNone(row.error_code)

    def test_audit_write_failure_returns_audit_write_failed_and_rolls_back(self) -> None:
        payload = self._create_payload(planned_qty="80")
        with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(request_id=payload["request_id"]),
                json=payload,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        with self.SessionLocal() as session:
            rows = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 100).count()
        self.assertEqual(rows, 2)

    def test_receive_fail_closed_after_auth_does_not_change_order_status(self) -> None:
        payload = self._receive_payload(idem="idem-audit-recv-1", received_qty="10")
        response = self.client.post(
            "/api/subcontract/101/receive",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["sync_status"], "succeeded")
        self.assertTrue(str(response.json()["data"]["stock_entry_name"]).startswith("LOCAL-RECEIPT-"))
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 101).first()
            receipt_count = session.query(LySubcontractReceipt).count()
            outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(
                    LySubcontractStockOutbox.subcontract_id == 101,
                    LySubcontractStockOutbox.stock_action == "receipt",
                )
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
            success_logs = (
                session.query(LySubcontractStatusLog)
                .filter(LySubcontractStatusLog.subcontract_id == 101)
                .count()
            )
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_inspection")
        self.assertEqual(receipt_count, 2)  # seeded row for 102 + new row for 101
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.status, "succeeded")
        self.assertEqual(success_logs, 1)

    def test_inspect_success_updates_receipt_and_rollup(self) -> None:
        payload = self._inspect_payload()
        response = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 102).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id == 2000).first()
            inspection = (
                session.query(LySubcontractInspection)
                .filter(
                    LySubcontractInspection.subcontract_id == 102,
                    LySubcontractInspection.idempotency_key == "idem-audit-inspect-1",
                )
                .first()
            )
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_receive")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.inspect_status, "inspected")
        self.assertIsNotNone(inspection)

    def test_inspection_operation_audit_contains_current_inspection_summary(self) -> None:
        payload = self._inspect_payload(idem="idem-audit-inspect-summary")
        response = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:inspect",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)
        after_data = row.after_data
        if isinstance(after_data, str):
            after_data = json.loads(after_data)
        self.assertIsInstance(after_data, dict)
        inspection = after_data.get("inspection", {})
        self.assertEqual(inspection.get("inspection_no"), data["inspection_no"])
        self.assertEqual(inspection.get("receipt_batch_no"), data["receipt_batch_no"])
        self.assertEqual(str(inspection.get("inspected_qty")), str(data["inspected_qty"]))
        self.assertEqual(str(inspection.get("rejected_qty")), str(data["rejected_qty"]))
        self.assertEqual(Decimal(str(inspection.get("gross_amount"))), Decimal(str(data["gross_amount"])))
        self.assertEqual(Decimal(str(inspection.get("deduction_amount"))), Decimal(str(data["deduction_amount"])))
        self.assertEqual(Decimal(str(inspection.get("net_amount"))), Decimal(str(data["net_amount"])))

    def test_receive_audit_write_failed_rolls_back_business_changes(self) -> None:
        with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
            payload = self._receive_payload(idem="idem-audit-recv-fail", received_qty="10")
            response = self.client.post(
                "/api/subcontract/101/receive",
                headers=self._headers(request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 101).first()
            receipt_count = session.query(LySubcontractReceipt).count()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "processing")
        self.assertEqual(receipt_count, 1)

    def test_inspect_audit_write_failed_rolls_back_business_changes(self) -> None:
        with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
            payload = self._inspect_payload(idem="idem-audit-inspect-fail")
            response = self.client.post(
                "/api/subcontract/102/inspect",
                headers=self._headers(request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 102).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id == 2000).first()
            inspection_count = session.query(LySubcontractInspection).filter(LySubcontractInspection.subcontract_id == 102).count()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_inspection")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.inspect_status, "pending")
        self.assertEqual(inspection_count, 0)

    def test_inspect_security_audit_on_401_403_503(self) -> None:
        unauth_payload = self._inspect_payload(idem="idem-audit-401")
        unauth = self.client.post("/api/subcontract/102/inspect", json=unauth_payload)
        self.assertEqual(unauth.status_code, 401)
        self.assertEqual(unauth.json()["code"], "AUTH_UNAUTHORIZED")

        forbidden_payload = self._inspect_payload(idem="idem-audit-403")
        forbidden = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(role="NoRole", request_id=forbidden_payload["request_id"]),
            json=forbidden_payload,
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], "AUTH_FORBIDDEN")

        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="permission source unavailable",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            unavailable_payload = self._inspect_payload(idem="idem-audit-503")
            unavailable = self.client.post(
                "/api/subcontract/102/inspect",
                headers=self._headers(request_id=unavailable_payload["request_id"]),
                json=unavailable_payload,
            )
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

        with self.SessionLocal() as session:
            events = (
                session.query(LySecurityAuditLog.event_type, LySecurityAuditLog.action)
                .filter(LySecurityAuditLog.module == "subcontract")
                .all()
            )
        self.assertTrue(any(event == "AUTH_UNAUTHORIZED" and action == "subcontract:inspect" for event, action in events))
        self.assertTrue(any(event == "AUTH_FORBIDDEN" and action == "subcontract:inspect" for event, action in events))
        self.assertTrue(
            any(event == "PERMISSION_SOURCE_UNAVAILABLE" and action == "subcontract:inspect" for event, action in events)
        )


if __name__ == "__main__":
    unittest.main()
