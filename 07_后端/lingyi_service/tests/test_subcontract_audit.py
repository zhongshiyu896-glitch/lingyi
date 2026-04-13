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
        os.environ["APP_ENV"] = "test"
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
    def _headers(user: str = "audit.user", role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    @staticmethod
    def _inspect_payload(
        *,
        idem: str = "idem-audit-inspect-1",
        inspected_qty: str = "30",
        rejected_qty: str = "1",
        deduction_amount_per_piece: str = "0.1",
    ) -> dict[str, str]:
        return {
            "receipt_batch_no": "SRB-AUD-2000",
            "idempotency_key": idem,
            "inspected_qty": inspected_qty,
            "rejected_qty": rejected_qty,
            "deduction_amount_per_piece": deduction_amount_per_piece,
        }

    def test_create_success_writes_operation_audit_with_real_operator(self) -> None:
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": "COMP-A",
            "bom_id": 1,
            "planned_qty": "100",
            "process_name": "外发裁剪",
        }
        response = self.client.post("/api/subcontract/", headers=self._headers(user="real.operator"), json=payload)
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

    def test_issue_material_creates_pending_outbox_and_success_audit(self) -> None:
        response = self.client.post(
            "/api/subcontract/100/issue-material",
            headers=self._headers(),
            json={
                "idempotency_key": "idem-audit-001",
                "warehouse": "WH-A",
                "materials": [
                    {"material_item_code": "MAT-A", "required_qty": "100", "issued_qty": "10"},
                ],
            },
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
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": "COMP-A",
            "bom_id": 1,
            "planned_qty": "80",
            "process_name": "外发裁剪",
        }
        with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
            response = self.client.post("/api/subcontract/", headers=self._headers(), json=payload)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        with self.SessionLocal() as session:
            rows = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 100).count()
        self.assertEqual(rows, 2)

    def test_receive_fail_closed_after_auth_does_not_change_order_status(self) -> None:
        response = self.client.post(
            "/api/subcontract/101/receive",
            headers=self._headers(),
            json={
                "idempotency_key": "idem-audit-recv-1",
                "receipt_warehouse": "WH-RECV-A",
                "received_qty": "10",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["sync_status"], "pending")
        self.assertIsNone(response.json()["data"]["stock_entry_name"])
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
        self.assertEqual(success_logs, 1)

    def test_inspect_success_updates_receipt_and_rollup(self) -> None:
        response = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(),
            json=self._inspect_payload(),
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
        response = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(),
            json=self._inspect_payload(idem="idem-audit-inspect-summary"),
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
            response = self.client.post(
                "/api/subcontract/101/receive",
                headers=self._headers(),
                json={
                    "idempotency_key": "idem-audit-recv-fail",
                    "receipt_warehouse": "WH-RECV-A",
                    "received_qty": "10",
                },
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
            response = self.client.post(
                "/api/subcontract/102/inspect",
                headers=self._headers(),
                json=self._inspect_payload(idem="idem-audit-inspect-fail"),
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
        unauth = self.client.post("/api/subcontract/102/inspect", json=self._inspect_payload(idem="idem-audit-401"))
        self.assertEqual(unauth.status_code, 401)
        self.assertEqual(unauth.json()["code"], "AUTH_UNAUTHORIZED")

        forbidden = self.client.post(
            "/api/subcontract/102/inspect",
            headers=self._headers(role="NoRole"),
            json=self._inspect_payload(idem="idem-audit-403"),
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
            unavailable = self.client.post(
                "/api/subcontract/102/inspect",
                headers=self._headers(),
                json=self._inspect_payload(idem="idem-audit-503"),
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
