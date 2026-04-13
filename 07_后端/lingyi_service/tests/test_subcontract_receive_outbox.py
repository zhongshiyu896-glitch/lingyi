"""Tests for subcontract receive outbox flow (TASK-002E)."""

from __future__ import annotations

from decimal import Decimal
import os
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
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.core.exceptions import PermissionSourceUnavailable
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService


class SubcontractReceiveOutboxTest(unittest.TestCase):
    """Validate receive local facts and pending receipt outbox behavior."""

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
                    bom_no="BOM-RECV-001",
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
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=1,
                    subcontract_no="SC-RECV-001",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="issued",
                    settlement_status="unsettled",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=2,
                    subcontract_no="SC-RECV-DRAFT",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("50"),
                    status="draft",
                    settlement_status="unsettled",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=3,
                    subcontract_no="SC-RECV-SETTLED",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("80"),
                    status="processing",
                    settlement_status="settled",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=4,
                    subcontract_no="SC-RECV-BLOCKED",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("80"),
                    status="processing",
                    settlement_status="unsettled",
                    resource_scope_status="blocked_scope",
                    scope_error_code="SUBCONTRACT_COMPANY_UNRESOLVED",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "recv.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _payload(*, idem: str = "idem-recv-1", qty: str = "10") -> dict[str, object]:
        return {
            "idempotency_key": idem,
            "receipt_warehouse": "WH-RECV-A",
            "received_qty": qty,
            "uom": "Nos",
        }

    def test_receive_creates_receipt_rows_and_pending_outbox(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-create"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["sync_status"], "pending")
        self.assertIsNone(data["stock_entry_name"])

        with self.SessionLocal() as session:
            receipt = (
                session.query(LySubcontractReceipt)
                .filter(LySubcontractReceipt.subcontract_id == 1)
                .order_by(LySubcontractReceipt.id.desc())
                .first()
            )
            outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.subcontract_id == 1)
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 1).first()

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.sync_status, "pending")
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.stock_action, "receipt")
        self.assertEqual(outbox.status, "pending")
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_inspection")

    def test_receive_does_not_call_erpnext_before_commit(self) -> None:
        with patch.object(ERPNextStockEntryService, "find_by_event_key") as find_mock, patch.object(
            ERPNextStockEntryService,
            "create_and_submit_material_receipt",
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/1/receive",
                headers=self._headers(),
                json=self._payload(idem="idem-recv-no-erp"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(find_mock.call_count, 0)
        self.assertEqual(create_mock.call_count, 0)

    def test_receive_returns_outbox_without_fake_stock_entry_name(self) -> None:
        response = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-fake"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("outbox_id", payload)
        self.assertIsNone(payload["stock_entry_name"])
        self.assertNotIn("STE-REC", str(payload))

    def test_receive_idempotent_same_payload_returns_existing_result(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-same", qty="12"),
        )
        second = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-same", qty="12"),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["outbox_id"], second.json()["data"]["outbox_id"])
        self.assertEqual(first.json()["data"]["receipt_batch_no"], second.json()["data"]["receipt_batch_no"])

        with self.SessionLocal() as session:
            outbox_count = session.query(LySubcontractStockOutbox).count()
            receipt_count = session.query(LySubcontractReceipt).count()
        self.assertEqual(outbox_count, 1)
        self.assertEqual(receipt_count, 1)

    def test_receive_idempotency_key_different_payload_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-conflict", qty="10"),
        )
        second = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-conflict", qty="20"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

    def test_receive_event_key_excludes_receipt_batch_no(self) -> None:
        stable_payload_a = {
            "stock_action": "receipt",
            "subcontract_id": 1,
            "subcontract_no": "SC-RECV-001",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "receipt_warehouse": "WH-RECV-A",
            "received_qty": "10",
            "receipt_batch_no": "SRB-1",
        }
        stable_payload_b = dict(stable_payload_a)
        stable_payload_b["receipt_batch_no"] = "SRB-2"

        hash_a = SubcontractStockOutboxService.build_payload_hash(stable_payload_a)
        hash_b = SubcontractStockOutboxService.build_payload_hash(stable_payload_b)
        self.assertEqual(hash_a, hash_b)

        key_a = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="receipt",
            idempotency_key="idem-recv-event",
            payload_hash=hash_a,
        )
        key_b = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="receipt",
            idempotency_key="idem-recv-event",
            payload_hash=hash_b,
        )
        self.assertEqual(key_a, key_b)

    def test_receive_idempotent_retry_after_full_receipt_does_not_check_remaining_qty_first(self) -> None:
        full_payload = self._payload(idem="idem-recv-full", qty="100")
        first = self.client.post("/api/subcontract/1/receive", headers=self._headers(), json=full_payload)
        self.assertEqual(first.status_code, 200)
        second = self.client.post("/api/subcontract/1/receive", headers=self._headers(), json=full_payload)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.json()["code"], "SUBCONTRACT_RECEIPT_QTY_EXCEEDED")

    def test_receive_rejects_draft_order(self) -> None:
        response = self.client.post(
            "/api/subcontract/2/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-draft"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STATUS_INVALID")

    def test_receive_rejects_qty_exceeding_remaining_receivable_qty(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-over-1", qty="90"),
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-over-2", qty="20"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_RECEIPT_QTY_EXCEEDED")

    def test_receive_blocked_scope_order_rejected(self) -> None:
        response = self.client.post(
            "/api/subcontract/4/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-blocked"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")

    def test_receive_settled_order_rejected(self) -> None:
        response = self.client.post(
            "/api/subcontract/3/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-settled"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SETTLEMENT_LOCKED")

    def test_receive_waiting_inspection_allows_additional_batch_receipt(self) -> None:
        first = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-batch-1", qty="60"),
        )
        second = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-batch-2", qty="10"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        with self.SessionLocal() as session:
            receipts = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.subcontract_id == 1).count()
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 1).first()
        self.assertEqual(receipts, 2)
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_inspection")

    def test_inspect_requires_receipt_batch_no_after_task_002f(self) -> None:
        _ = self.client.post(
            "/api/subcontract/1/receive",
            headers=self._headers(),
            json=self._payload(idem="idem-recv-for-inspect", qty="10"),
        )
        response = self.client.post(
            "/api/subcontract/1/inspect",
            headers=self._headers(),
            json={},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_RECEIPT_BATCH_REQUIRED")

    def test_receive_forbidden_when_receipt_warehouse_not_allowed(self) -> None:
        from app.services.erpnext_permission_adapter import UserPermissionResult

        previous_source = os.environ.get("LINGYI_PERMISSION_SOURCE")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        denied_permissions = UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items={"ITEM-A"},
            allowed_companies={"COMP-A"},
            allowed_suppliers={"SUP-A"},
            allowed_warehouses={"WH-NOT-ALLOWED"},
        )
        try:
            with patch(
                "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
                return_value=denied_permissions,
            ):
                response = self.client.post(
                    "/api/subcontract/1/receive",
                    headers=self._headers(),
                    json=self._payload(idem="idem-recv-warehouse-denied"),
                )
        finally:
            if previous_source is None:
                os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
            else:
                os.environ["LINGYI_PERMISSION_SOURCE"] = previous_source
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            receipt_count = session.query(LySubcontractReceipt).count()
            outbox_count = session.query(LySubcontractStockOutbox).count()
        self.assertEqual(receipt_count, 0)
        self.assertEqual(outbox_count, 0)

    def test_receive_permission_source_unavailable_fails_closed(self) -> None:
        previous_source = os.environ.get("LINGYI_PERMISSION_SOURCE")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        try:
            with patch(
                "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
                side_effect=PermissionSourceUnavailable("permission source timeout"),
            ):
                response = self.client.post(
                    "/api/subcontract/1/receive",
                    headers=self._headers(),
                    json=self._payload(idem="idem-recv-perm-unavailable"),
                )
        finally:
            if previous_source is None:
                os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
            else:
                os.environ["LINGYI_PERMISSION_SOURCE"] = previous_source
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            receipt_count = session.query(LySubcontractReceipt).count()
            outbox_count = session.query(LySubcontractStockOutbox).count()
        self.assertEqual(receipt_count, 0)
        self.assertEqual(outbox_count, 0)


if __name__ == "__main__":
    unittest.main()
