"""Tests for subcontract stock sync internal worker (TASK-002D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.auth import CurrentUser
from app.core.auth import get_current_user
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
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStockOutbox
from app.models.subcontract import LySubcontractStockSyncLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_CANCELLED
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_CREATE_FAILED
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_STATUS_INVALID
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceUnavailableError
from app.services.erpnext_stock_entry_service import ERPNextStockEntryLookup
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService
from app.services.subcontract_stock_worker_service import SubcontractStockWorkerService


class SubcontractStockWorkerTest(unittest.TestCase):
    """Validate subcontract stock worker API and outbox transitions."""

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
                    bom_no="BOM-WORKER-001",
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
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API"] = "true"
        os.environ["SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN"] = "true"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.subcontract"

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySubcontractStockSyncLog).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=1,
                    subcontract_no="SC-WORKER-001",
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
            session.commit()

            payload_json = {
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Issue",
                "company": "COMP-A",
                "custom_ly_subcontract_no": "SC-WORKER-001",
                "custom_ly_subcontract_outbox_id": 1,
                "custom_ly_outbox_event_key": "",
                "custom_ly_stock_action": "issue",
                "items": [{"item_code": "MAT-A", "qty": "10", "uom": "Nos", "s_warehouse": "WH-A"}],
            }
            outbox_service = SubcontractStockOutboxService(session=session)
            outbox, _ = outbox_service.enqueue_issue(
                subcontract_id=1,
                company="COMP-A",
                supplier="SUP-A",
                item_code="ITEM-A",
                warehouse="WH-A",
                idempotency_key="idem-worker-1",
                payload_json=payload_json,
                request_id="rid-worker-1",
                created_by="seed",
            )
            payload_json["custom_ly_subcontract_outbox_id"] = int(outbox.id)
            payload_json["custom_ly_outbox_event_key"] = outbox.event_key
            outbox.payload_json = payload_json
            outbox.payload = payload_json
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.add(
                LySubcontractMaterial(
                    id=1,
                    subcontract_id=1,
                    stock_outbox_id=int(outbox.id),
                    company="COMP-A",
                    issue_batch_no="SIB-1",
                    material_item_code="MAT-A",
                    required_qty=Decimal("100"),
                    issued_qty=Decimal("10"),
                    sync_status="pending",
                    stock_entry_name=None,
                )
            )
            session.commit()

    @staticmethod
    def _headers(*, user: str, role: str) -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    @staticmethod
    def _mock_user_permissions(*, warehouses: set[str] | None = None):
        from app.services.erpnext_permission_adapter import UserPermissionResult

        return UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items={"ITEM-A"},
            allowed_companies={"COMP-A"},
            allowed_suppliers={"SUP-A"},
            allowed_warehouses=warehouses or {"WH-A"},
        )

    @staticmethod
    def _lookup(name: str, docstatus: int) -> ERPNextStockEntryLookup:
        return ERPNextStockEntryLookup(name=name, docstatus=docstatus)

    @staticmethod
    def _retry_payload(*, outbox_id: int, stock_action: str, idempotency_key: str, reason: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "outbox_id": outbox_id,
            "stock_action": stock_action,
            "idempotency_key": idempotency_key,
        }
        if reason is not None:
            payload["reason"] = reason
        return payload

    def _seed_receipt_outbox(self, *, idempotency_key: str = "idem-worker-receipt-1") -> int:
        with self.SessionLocal() as session:
            issue_row = (
                session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.subcontract_id == 1)
                .order_by(LySubcontractStockOutbox.id.asc())
                .first()
            )
            if issue_row is not None:
                issue_row.status = "succeeded"
                issue_row.next_retry_at = datetime.utcnow() + timedelta(days=1)

            payload_json = {
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Receipt",
                "company": "COMP-A",
                "custom_ly_subcontract_no": "SC-WORKER-001",
                "custom_ly_subcontract_outbox_id": 0,
                "custom_ly_outbox_event_key": "",
                "custom_ly_stock_action": "receipt",
                "items": [{"item_code": "ITEM-A", "qty": "10", "uom": "Nos", "t_warehouse": "WH-A"}],
            }
            outbox_service = SubcontractStockOutboxService(session=session)
            outbox, _ = outbox_service.enqueue_receipt(
                subcontract_id=1,
                company="COMP-A",
                supplier="SUP-A",
                item_code="ITEM-A",
                warehouse="WH-A",
                idempotency_key=idempotency_key,
                payload_json=payload_json,
                request_id="rid-worker-receipt-1",
                created_by="seed",
            )
            payload_json["custom_ly_subcontract_outbox_id"] = int(outbox.id)
            payload_json["custom_ly_outbox_event_key"] = outbox.event_key
            outbox.payload_json = payload_json
            outbox.payload = payload_json
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.add(
                LySubcontractReceipt(
                    id=100,
                    subcontract_id=1,
                    stock_outbox_id=int(outbox.id),
                    company="COMP-A",
                    receipt_batch_no="SRB-1",
                    receipt_warehouse="WH-A",
                    item_code="ITEM-A",
                    uom="Nos",
                    received_qty=Decimal("10"),
                    sync_status="pending",
                    idempotency_key=idempotency_key,
                    payload_hash=str(outbox.payload_hash),
                    received_by="seed",
                    received_at=datetime.utcnow(),
                    stock_entry_name=None,
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                )
            )
            session.commit()
            return int(outbox.id)

    def test_stock_worker_disabled_returns_before_outbox_query(self) -> None:
        os.environ["ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API"] = "false"
        with patch(
            "app.services.subcontract_stock_outbox_service.SubcontractStockOutboxService.list_due_issue_for_scope"
        ) as list_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_WORKER_DISABLED")
        self.assertEqual(list_mock.call_count, 0)

    def test_stock_worker_dry_run_disabled_returns_before_outbox_query(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API"] = "true"
        os.environ["SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN"] = "false"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.subcontract",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch(
                "app.services.subcontract_stock_outbox_service.SubcontractStockOutboxService.list_due_issue_for_scope"
            ) as list_mock:
                response = self.client.post(
                    "/api/subcontract/internal/stock-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_DRY_RUN_DISABLED")
        self.assertEqual(list_mock.call_count, 0)

    def test_stock_worker_requires_service_account_action(self) -> None:
        response = self.client.post(
            "/api/subcontract/internal/stock-sync/run-once",
            headers=self._headers(user="normal.user", role="Subcontract Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_stock_worker_dry_run_does_not_lock_or_call_erpnext_and_writes_audit(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key"
        ) as find_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?dry_run=true&batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(find_mock.call_count, 0)
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "pending")
            self.assertEqual(int(outbox.attempts), 0)
            op_audit = (
                session.query(LyOperationAuditLog)
                .filter(LyOperationAuditLog.action == "subcontract:stock_sync_worker")
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(op_audit)

    def test_stock_worker_creates_and_submits_erpnext_material_issue(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            return_value="STE-REAL-001",
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            material = session.query(LySubcontractMaterial).first()
            sync_log = session.query(LySubcontractStockSyncLog).order_by(LySubcontractStockSyncLog.id.desc()).first()
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.status, "succeeded")
        self.assertEqual(outbox.stock_entry_name, "STE-REAL-001")
        self.assertIsNotNone(material)
        self.assertEqual(material.sync_status, "succeeded")
        self.assertEqual(material.stock_entry_name, "STE-REAL-001")
        self.assertIsNotNone(sync_log)
        self.assertEqual(sync_log.sync_status, "success")

    def test_stock_worker_existing_erpnext_entry_by_event_key_prevents_duplicate_create(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value="STE-EXIST-001",
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.stock_entry_name, "STE-EXIST-001")

    def test_stock_worker_processes_receipt_outbox_as_material_receipt(self) -> None:
        outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-process")
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_receipt",
            return_value="STE-REC-REAL-001",
        ) as receipt_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as issue_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10&stock_action=receipt",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(receipt_mock.call_count, 1)
        self.assertEqual(issue_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == outbox_id).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.stock_outbox_id == outbox_id).first()
            sync_log = (
                session.query(LySubcontractStockSyncLog)
                .filter(LySubcontractStockSyncLog.outbox_id == outbox_id)
                .order_by(LySubcontractStockSyncLog.id.desc())
                .first()
            )
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.status, "succeeded")
        self.assertEqual(outbox.stock_entry_name, "STE-REC-REAL-001")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.sync_status, "succeeded")
        self.assertEqual(receipt.stock_entry_name, "STE-REC-REAL-001")
        self.assertIsNotNone(sync_log)
        self.assertEqual(sync_log.sync_status, "success")

    def test_stock_worker_receipt_find_existing_docstatus_0_submits_draft_then_succeeds(self) -> None:
        outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-doc0")
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            side_effect=[self._lookup("STE-REC-DOC-0", 0), self._lookup("STE-REC-DOC-0", 1)],
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry"
        ) as submit_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_receipt"
        ) as create_receipt_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10&stock_action=receipt",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create_receipt_mock.call_count, 0)
        self.assertEqual(submit_mock.call_count, 1)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.stock_entry_name, "STE-REC-DOC-0")

    def test_stock_worker_receipt_submit_draft_requires_final_docstatus_1(self) -> None:
        outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-doc0-invalid")
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            side_effect=[self._lookup("STE-REC-DOC-0-INVALID", 0), self._lookup("STE-REC-DOC-0-INVALID", 0)],
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry"
        ) as submit_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10&stock_action=receipt",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit_mock.call_count, 1)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertIn(outbox.status, {"failed", "dead"})
            self.assertEqual(outbox.last_error_code, ERPNEXT_STOCK_ENTRY_STATUS_INVALID)

    def test_stock_worker_receipt_find_existing_docstatus_2_does_not_succeed(self) -> None:
        outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-doc2")
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-REC-DOC-2", 2),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10&stock_action=receipt",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == outbox_id).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.stock_outbox_id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertNotEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.last_error_code, ERPNEXT_STOCK_ENTRY_CANCELLED)
            self.assertIsNotNone(receipt)
            self.assertTrue(str(receipt.sync_status).startswith("failed:"))

    def test_stock_worker_find_existing_docstatus_1_marks_succeeded_without_create(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-DOC-1", 1),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.stock_entry_name, "STE-DOC-1")

    def test_stock_worker_find_existing_docstatus_0_submits_draft_then_succeeds(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            side_effect=[self._lookup("STE-DOC-0", 0), self._lookup("STE-DOC-0", 1)],
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry"
        ) as submit_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create_mock.call_count, 0)
        self.assertEqual(submit_mock.call_count, 1)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.stock_entry_name, "STE-DOC-0")

    def test_stock_worker_find_existing_docstatus_0_submit_failed_marks_retry(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-DOC-0-FAIL", 0),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry",
            side_effect=BusinessException(code=ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED, message="submit failed"),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertIn(outbox.status, {"failed", "dead"})
            self.assertEqual(outbox.last_error_code, ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED)

    def test_stock_worker_find_existing_docstatus_2_does_not_succeed(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-DOC-2", 2),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertNotEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.last_error_code, ERPNEXT_STOCK_ENTRY_CANCELLED)

    def test_stock_worker_duplicate_event_key_fails_closed(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            side_effect=BusinessException(
                code=ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY,
                message="duplicate event key",
            ),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertIn(outbox.status, {"failed", "dead"})
            self.assertEqual(outbox.last_error_code, ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY)

    def test_stock_worker_claim_commits_before_erpnext_call(self) -> None:
        commit_calls: list[str] = []
        original_commit_phase = SubcontractStockWorkerService._commit_phase

        def _wrapped_commit(self):
            commit_calls.append("commit")
            return original_commit_phase(self)

        def _create_side_effect(*args, **kwargs):
            self.assertGreaterEqual(len(commit_calls), 1)
            return "STE-COMMIT-ORDER-001"

        with patch(
            "app.services.subcontract_stock_worker_service.SubcontractStockWorkerService._commit_phase",
            _wrapped_commit,
        ), patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=_create_side_effect,
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(commit_calls), 2)

    def test_stock_worker_result_write_failure_recovered_by_event_key_next_run(self) -> None:
        call_counter = {"count": 0}

        def _append_with_first_failure(*args, **kwargs):
            from app.core.exceptions import DatabaseWriteFailed

            call_counter["count"] += 1
            if call_counter["count"] == 1:
                raise DatabaseWriteFailed()
            return None

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            return_value="STE-RECOVER-001",
        ), patch(
            "app.services.subcontract_stock_worker_service.SubcontractStockWorkerService._append_sync_log",
            side_effect=_append_with_first_failure,
        ):
            first = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(first.status_code, 500)

        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            outbox.lease_until = datetime.utcnow() - timedelta(seconds=1)
            outbox.next_retry_at = datetime.utcnow() - timedelta(seconds=1)
            session.commit()

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-RECOVER-001", 1),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            second = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.stock_entry_name, "STE-RECOVER-001")

    def test_stock_worker_concurrent_run_does_not_double_process_outbox(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            return_value="STE-ONCE-001",
        ) as create_mock:
            first = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
            second = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(create_mock.call_count, 1)

    def test_stock_worker_lease_expiry_allows_reclaim_after_crash(self) -> None:
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            outbox.status = "processing"
            outbox.locked_by = "crashed-worker"
            outbox.locked_at = datetime.utcnow() - timedelta(minutes=10)
            outbox.lease_until = datetime.utcnow() - timedelta(minutes=5)
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=5)
            session.commit()

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=self._lookup("STE-RECLAIM-001", 1),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as create_mock:
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")

    def test_stock_worker_erpnext_timeout_marks_failed_with_retry(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=ERPNextServiceUnavailableError("timeout-token-secret"),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "failed")
            self.assertEqual(outbox.last_error_code, "ERPNEXT_SERVICE_UNAVAILABLE")
            self.assertTrue(outbox.next_retry_at is not None)

    def test_stock_worker_business_validation_dead_after_max_attempts(self) -> None:
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            outbox.status = "failed"
            outbox.attempts = 4
            outbox.max_attempts = 5
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=BusinessException(code=ERPNEXT_STOCK_ENTRY_CREATE_FAILED, message="create failed"),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "dead")
            self.assertEqual(int(outbox.attempts), 5)

    def test_stock_worker_sync_log_records_success_failure_and_dead(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=ERPNextServiceUnavailableError("timeout"),
        ):
            self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            outbox.status = "failed"
            outbox.attempts = 4
            outbox.max_attempts = 5
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=BusinessException(code=ERPNEXT_STOCK_ENTRY_CREATE_FAILED, message="create failed"),
        ):
            self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )

        with self.SessionLocal() as session:
            logs = session.query(LySubcontractStockSyncLog).order_by(LySubcontractStockSyncLog.id.asc()).all()
        self.assertGreaterEqual(len(logs), 2)
        self.assertTrue(all(log.sync_status in {"failed", "success"} for log in logs))

    def test_subcontract_stock_logs_are_sanitized_for_worker_failures(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key",
            return_value=None,
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue",
            side_effect=ERPNextServiceUnavailableError("Authorization Bearer token secret password Cookie sid=abc"),
        ):
            response = self.client.post(
                "/api/subcontract/internal/stock-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.subcontract", role="LY Integration Service"),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            text = (outbox.last_error_message or "").lower()
        for forbidden in ("authorization", "cookie", "token", "secret", "password"):
            self.assertNotIn(forbidden, text)

    def test_stock_sync_retry_resets_issue_outbox_to_pending(self) -> None:
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            outbox.status = "failed"
            outbox.attempts = 2
            outbox.last_error_code = "ERPNEXT_SERVICE_UNAVAILABLE"
            session.commit()
            outbox_id = int(outbox.id)
            idempotency_key = str(outbox.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(
                    outbox_id=outbox_id,
                    stock_action="issue",
                    idempotency_key=idempotency_key,
                    reason="manual retry",
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["stock_action"], "issue")
        with self.SessionLocal() as session:
            outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "pending")
            self.assertIsNone(outbox.last_error_code)

    def test_stock_sync_retry_requires_outbox_id_stock_action_and_idempotency_key(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json={},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_CONFLICT")

    def test_stock_sync_retry_targets_failed_issue_when_receipt_succeeded_latest(self) -> None:
        receipt_outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-succeeded")
        with self.SessionLocal() as session:
            issue_outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.subcontract_id == 1, LySubcontractStockOutbox.stock_action == "issue")
                .first()
            )
            receipt_outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(issue_outbox)
            self.assertIsNotNone(receipt_outbox)
            issue_outbox.status = "failed"
            issue_outbox.last_error_code = "ERPNEXT_SERVICE_UNAVAILABLE"
            receipt_outbox.status = "succeeded"
            session.commit()
            issue_outbox_id = int(issue_outbox.id)
            issue_idempotency_key = str(issue_outbox.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(
                    outbox_id=issue_outbox_id,
                    stock_action="issue",
                    idempotency_key=issue_idempotency_key,
                ),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            issue_outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == issue_outbox_id).first()
            receipt_outbox = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(issue_outbox)
            self.assertIsNotNone(receipt_outbox)
            self.assertEqual(issue_outbox.status, "pending")
            self.assertEqual(receipt_outbox.status, "succeeded")

    def test_stock_sync_retry_does_not_reset_succeeded_receipt_outbox(self) -> None:
        receipt_outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-succeeded-retry")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            row.status = "succeeded"
            session.commit()
            idem = str(row.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(
                    outbox_id=receipt_outbox_id,
                    stock_action="receipt",
                    idempotency_key=idem,
                ),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "succeeded")

    def test_stock_sync_retry_targets_failed_receipt_by_exact_outbox_id(self) -> None:
        receipt_outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-failed-retry")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            row.status = "failed"
            row.attempts = 2
            row.last_error_code = "ERPNEXT_SERVICE_UNAVAILABLE"
            session.commit()
            idem = str(row.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(
                    outbox_id=receipt_outbox_id,
                    stock_action="receipt",
                    idempotency_key=idem,
                ),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "pending")
            self.assertIsNone(row.last_error_code)

    def test_stock_sync_retry_rejects_wrong_stock_action(self) -> None:
        with self.SessionLocal() as session:
            issue_outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(issue_outbox)
            issue_outbox.status = "failed"
            session.commit()
            outbox_id = int(issue_outbox.id)
            idem = str(issue_outbox.idempotency_key)
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="receipt", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH")

    def test_stock_sync_retry_rejects_wrong_idempotency_key(self) -> None:
        with self.SessionLocal() as session:
            issue_outbox = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(issue_outbox)
            issue_outbox.status = "failed"
            session.commit()
            outbox_id = int(issue_outbox.id)
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key="wrong-key"),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH")

    def test_stock_sync_retry_rejects_outbox_from_other_order(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=2,
                    subcontract_no="SC-WORKER-002",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("10"),
                    status="issued",
                    settlement_status="unsettled",
                )
            )
            session.flush()
            outbox_service = SubcontractStockOutboxService(session=session)
            row, _ = outbox_service.enqueue_issue(
                subcontract_id=2,
                company="COMP-A",
                supplier="SUP-A",
                item_code="ITEM-A",
                warehouse="WH-A",
                idempotency_key="idem-worker-order2",
                payload_json={"items": [{"item_code": "MAT-A", "qty": "1"}]},
                request_id="rid-order2",
                created_by="seed",
            )
            row.status = "failed"
            session.commit()
            outbox_id = int(row.id)
            idem = str(row.idempotency_key)
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH")

    def test_stock_sync_retry_rejects_processing_outbox(self) -> None:
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(row)
            row.status = "processing"
            session.commit()
            outbox_id = int(row.id)
            idem = str(row.idempotency_key)
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE")

    def test_stock_sync_retry_rejects_pending_outbox(self) -> None:
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(row)
            row.status = "pending"
            session.commit()
            outbox_id = int(row.id)
            idem = str(row.idempotency_key)
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE")

    def test_stock_sync_retry_permission_source_unavailable_fails_closed(self) -> None:
        from app.core.exceptions import PermissionSourceUnavailable

        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(row)
            row.status = "failed"
            session.commit()
            outbox_id = int(row.id)
            idem = str(row.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            side_effect=PermissionSourceUnavailable("permission source timeout"),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == outbox_id).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "failed")

    def test_stock_sync_retry_checks_receipt_outbox_resource_permission(self) -> None:
        receipt_outbox_id = self._seed_receipt_outbox(idempotency_key="idem-worker-receipt-perm")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            row.status = "failed"
            session.commit()
            idem = str(row.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(warehouses={"WH-B"}),
        ):
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=receipt_outbox_id, stock_action="receipt", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).filter(LySubcontractStockOutbox.id == receipt_outbox_id).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "failed")

    def test_stock_sync_retry_does_not_call_erpnext(self) -> None:
        with self.SessionLocal() as session:
            row = session.query(LySubcontractStockOutbox).first()
            self.assertIsNotNone(row)
            row.status = "failed"
            session.commit()
            outbox_id = int(row.id)
            idem = str(row.idempotency_key)

        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=self._mock_user_permissions(),
        ), patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.find_by_event_key"
        ) as find_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_issue"
        ) as issue_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_and_submit_material_receipt"
        ) as receipt_mock, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry"
        ) as submit_mock:
            response = self.client.post(
                "/api/subcontract/1/stock-sync/retry",
                headers=self._headers(user="retry.user", role="Subcontract Manager"),
                json=self._retry_payload(outbox_id=outbox_id, stock_action="issue", idempotency_key=idem),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(find_mock.call_count, 0)
        self.assertEqual(issue_mock.call_count, 0)
        self.assertEqual(receipt_mock.call_count, 0)
        self.assertEqual(submit_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
