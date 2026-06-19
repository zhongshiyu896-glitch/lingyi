"""Permission tests for subcontract module (TASK-002B)."""

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
from app.core.exceptions import PermissionSourceUnavailable
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractStockOutbox
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class SubcontractPermissionTest(unittest.TestCase):
    """Validate subcontract authz/resource scope behavior."""

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
                    bom_no="BOM-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBom(
                    id=2,
                    bom_no="BOM-002",
                    item_code="ITEM-B",
                    version_no="v1",
                    is_default=False,
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
                    subcontract_cost_per_piece=Decimal("0.5"),
                )
            )
            session.add(
                LyBomOperation(
                    id=2,
                    bom_id=2,
                    process_name="外发裁剪",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("0.6"),
                )
            )
            session.add(
                LySubcontractOrder(
                    id=10,
                    subcontract_no="SC-SEED-A",
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
                    id=11,
                    subcontract_no="SC-SEED-B",
                    supplier="SUP-B",
                    item_code="ITEM-B",
                    company="COMP-B",
                    bom_id=2,
                    process_name="外发裁剪",
                    planned_qty=Decimal("200"),
                    status="draft",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=12,
                    subcontract_no="SC-SEED-WAIT-INSPECT",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("80"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=13,
                    subcontract_no="SC-SEED-PROCESSING",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("120"),
                    status="processing",
                    resource_scope_status="ready",
                    profit_scope_status="resolved",
                    sales_order="SO-001",
                    sales_order_item="SO-001-1",
                    production_plan_id=3001,
                    work_order="WO-3001",
                    job_card="JC-3001",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=1000,
                    subcontract_id=12,
                    company="COMP-A",
                    receipt_batch_no="SRB-PERM-1000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("20"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-PERM-1000",
                    idempotency_key="idem-seed-perm-1000",
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
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 11).delete()
            session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id >= 1000).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=12,
                    subcontract_no="SC-SEED-WAIT-INSPECT",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("80"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=13,
                    subcontract_no="SC-SEED-PROCESSING",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("120"),
                    status="processing",
                    resource_scope_status="ready",
                    profit_scope_status="resolved",
                    sales_order="SO-001",
                    sales_order_item="SO-001-1",
                    production_plan_id=3001,
                    work_order="WO-3001",
                    job_card="JC-3001",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=1000,
                    subcontract_id=12,
                    company="COMP-A",
                    receipt_batch_no="SRB-PERM-1000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("20"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-PERM-1000",
                    idempotency_key="idem-seed-perm-1000",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager", *, request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "subcontract.user", "X-LY-Dev-Roles": role}
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
        operation_codes = {"create": "CR", "receive": "RV", "inspect": "IN"}
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
    def _create_payload(cls, item_code: str = "ITEM-A", supplier: str = "SUP-A") -> dict:
        payload = {
            "supplier": supplier,
            "item_code": item_code,
            "company": "COMP-A",
            "bom_id": 1 if item_code == "ITEM-A" else 2,
            "planned_qty": "100",
            "process_name": "外发裁剪",
        }
        payload.update(
            cls._write_carrier(
                operation="create",
                idempotency_key=f"idem-create-{item_code}-{supplier}",
                source_suffix=f"CREATE-{item_code}-{supplier}",
                subcontract_ref=f"NEW-{item_code}-{supplier}",
                supplier_ref=supplier,
                work_order_ref="NO-WORK-ORDER",
                item_code=item_code,
                quantity="100",
                status_action="create",
            )
        )
        return payload

    @classmethod
    def _receive_payload(
        cls,
        *,
        order_id: int,
        idem: str,
        received_qty: str = "10",
        receipt_warehouse: str = "WH-RECV-A",
    ) -> dict[str, str]:
        subcontract_refs = {
            10: "SC-SEED-A",
            13: "SC-SEED-PROCESSING",
        }
        payload = {
            "receipt_warehouse": receipt_warehouse,
            "received_qty": received_qty,
        }
        payload.update(
            cls._write_carrier(
                operation="receive",
                idempotency_key=idem,
                source_suffix=f"RECEIVE-{order_id}",
                subcontract_ref=subcontract_refs[order_id],
                supplier_ref="SUP-A",
                work_order_ref="WO-3001" if order_id == 13 else "NO-WORK-ORDER",
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
        idem: str = "idem-inspect-perm-1",
        inspected_qty: str = "20",
        rejected_qty: str = "1",
        deduction_amount_per_piece: str = "0.1",
    ) -> dict[str, str]:
        payload = {
            "receipt_batch_no": "SRB-PERM-1000",
            "inspected_qty": inspected_qty,
            "rejected_qty": rejected_qty,
            "deduction_amount_per_piece": deduction_amount_per_piece,
        }
        payload.update(
            cls._write_carrier(
                operation="inspect",
                idempotency_key=idem,
                source_suffix="INSPECT-12",
                subcontract_ref="SC-SEED-WAIT-INSPECT",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                quantity=inspected_qty,
                status_action="inspect",
            )
        )
        return payload

    def _latest_security_log(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertIsNotNone(row)
        return row  # type: ignore[return-value]

    def test_unauthorized_list_returns_401_and_security_audit(self) -> None:
        response = self.client.get("/api/subcontract/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_UNAUTHORIZED")
        self.assertEqual(row.module, "subcontract")

    def test_forbidden_list_without_read_permission(self) -> None:
        response = self.client.get("/api/subcontract/", headers=self._headers(role="NoRole"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "subcontract:read")

    def test_create_forbidden_without_create_permission(self) -> None:
        payload = self._create_payload()
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers(role="Subcontract Viewer", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "subcontract:create")

    def test_create_item_scope_forbidden_returns_403(self) -> None:
        with self.SessionLocal() as session:
            before_total = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 11).count()
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies=set(),
                allowed_suppliers={"SUP-A"},
                allowed_warehouses={"WH-A"},
            ),
        ):
            payload = self._create_payload(item_code="ITEM-A", supplier="SUP-A")
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
                json=payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            total = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 11).count()
        self.assertEqual(total, before_total)
        log_row = self._latest_security_log()
        self.assertEqual(log_row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(log_row.action, "subcontract:create")

    def test_permission_source_unavailable_returns_503_without_writes(self) -> None:
        with self.SessionLocal() as session:
            before_total = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 11).count()
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
            payload = self._create_payload(item_code="ITEM-A", supplier="SUP-A")
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            total = session.query(LySubcontractOrder).filter(LySubcontractOrder.id > 11).count()
        self.assertEqual(total, before_total)

    def test_list_filters_by_readable_item_scope(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies=set(),
                allowed_suppliers=set(),
                allowed_warehouses=set(),
            ),
        ):
            response = self.client.get("/api/subcontract/", headers=self._headers(role="Subcontract Manager"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        items = payload["data"]["items"]
        self.assertTrue(items)
        self.assertTrue(all(row["item_code"] == "ITEM-B" for row in items))

    def test_list_filters_by_fastapi_resource_scope(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "subcontract.user": {
                        "companies": ["COMP-B"],
                        "item_codes": ["ITEM-B"],
                        "suppliers": ["SUP-B"],
                    }
                }
            }
        )

        response = self.client.get("/api/subcontract/", headers=self._headers(role="Subcontract Manager"))

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        items = payload["data"]["items"]
        self.assertTrue(items)
        self.assertTrue(all(row["company"] == "COMP-B" for row in items))
        self.assertTrue(all(row["item_code"] == "ITEM-B" for row in items))
        self.assertTrue(all(row["supplier"] == "SUP-B" for row in items))

    def test_detail_returns_scope_bridge_fields_for_readonly_traceability(self) -> None:
        response = self.client.get("/api/subcontract/13", headers=self._headers(role="Subcontract Manager"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")

        detail = payload["data"]
        self.assertEqual(detail["sales_order"], "SO-001")
        self.assertEqual(detail["sales_order_item"], "SO-001-1")
        self.assertEqual(detail["production_plan_id"], 3001)
        self.assertEqual(detail["work_order"], "WO-3001")
        self.assertEqual(detail["job_card"], "JC-3001")
        self.assertEqual(detail["profit_scope_status"], "resolved")
        self.assertEqual(detail["resource_scope_status"], "ready")

    def test_create_subcontract_rejects_bom_item_mismatch(self) -> None:
        payload = self._create_payload(item_code="ITEM-A", supplier="SUP-A")
        payload["bom_id"] = 2
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_BOM_ITEM_MISMATCH")

    def test_create_subcontract_bom_item_mismatch_does_not_insert_order(self) -> None:
        payload = self._create_payload(item_code="ITEM-A", supplier="SUP-A")
        payload["bom_id"] = 2
        with self.SessionLocal() as session:
            before_total = session.query(LySubcontractOrder).count()
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_BOM_ITEM_MISMATCH")
        with self.SessionLocal() as session:
            after_total = session.query(LySubcontractOrder).count()
        self.assertEqual(after_total, before_total)

    def test_create_subcontract_bom_item_mismatch_does_not_write_success_audit(self) -> None:
        payload = self._create_payload(item_code="ITEM-A", supplier="SUP-A")
        payload["bom_id"] = 2
        with self.SessionLocal() as session:
            before_success = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:create",
                    LyOperationAuditLog.result == "success",
                )
                .count()
            )
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_BOM_ITEM_MISMATCH")
        with self.SessionLocal() as session:
            after_success = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:create",
                    LyOperationAuditLog.result == "success",
                )
                .count()
            )
            failure_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "subcontract",
                    LyOperationAuditLog.action == "subcontract:create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "SUBCONTRACT_BOM_ITEM_MISMATCH",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertEqual(after_success, before_success)
        self.assertIsNotNone(failure_row)

    def test_receive_fail_closed_after_auth_does_not_create_receipt(self) -> None:
        with self.SessionLocal() as session:
            before_count = session.query(LySubcontractReceipt).count()
        payload = self._receive_payload(order_id=13, idem="idem-recv-perm-1")
        response = self.client.post(
            "/api/subcontract/13/receive",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["sync_status"], "succeeded")
        self.assertTrue(str(response.json()["data"]["stock_entry_name"]).startswith("LOCAL-RECEIPT-"))
        with self.SessionLocal() as session:
            after_count = session.query(LySubcontractReceipt).count()
            outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(
                    LySubcontractStockOutbox.subcontract_id == 13,
                    LySubcontractStockOutbox.stock_action == "receipt",
                )
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 13).first()
        self.assertEqual(after_count, before_count + 1)
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.status, "succeeded")
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_inspection")

    def test_inspect_creates_fact_and_keeps_order_not_completed(self) -> None:
        payload = self._inspect_payload()
        response = self.client.post(
            "/api/subcontract/12/inspect",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["status"], "waiting_receive")
        self.assertEqual(Decimal(str(response.json()["data"]["accepted_qty"])), Decimal("19"))
        self.assertEqual(Decimal(str(response.json()["data"]["gross_amount"])), Decimal("10.00"))
        self.assertEqual(Decimal(str(response.json()["data"]["deduction_amount"])), Decimal("0.10"))
        self.assertEqual(Decimal(str(response.json()["data"]["net_amount"])), Decimal("9.90"))
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 12).first()
            receipt = session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id == 1000).first()
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == 12)
                .count()
            )
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "waiting_receive")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.inspect_status, "inspected")
        self.assertEqual(inspections, 1)

    def test_inspect_forbidden_when_receipt_warehouse_not_allowed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-A"},
                allowed_warehouses={"WH-OTHER"},
            ),
        ):
            payload = self._inspect_payload(idem="idem-inspect-no-wh")
            response = self.client.post(
                "/api/subcontract/12/inspect",
                headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            count = session.query(LySubcontractInspection).filter(LySubcontractInspection.subcontract_id == 12).count()
        self.assertEqual(count, 0)

    def test_inspect_permission_source_unavailable_fails_closed(self) -> None:
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
            payload = self._inspect_payload(idem="idem-inspect-perm-source-unavailable")
            response = self.client.post(
                "/api/subcontract/12/inspect",
                headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            count = session.query(LySubcontractInspection).filter(LySubcontractInspection.subcontract_id == 12).count()
        self.assertEqual(count, 0)

    def test_draft_order_cannot_receive_successfully(self) -> None:
        payload = self._receive_payload(order_id=10, idem="idem-recv-draft")
        response = self.client.post(
            "/api/subcontract/10/receive",
            headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_STATUS_INVALID")

    def test_receive_auth_is_checked_before_payload_validation_when_unauthorized(self) -> None:
        response = self.client.post("/api/subcontract/13/receive", json={})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")

    def test_receive_permission_is_checked_before_payload_validation_when_forbidden(self) -> None:
        payload = self._receive_payload(order_id=13, idem="idem-recv-forbidden")
        response = self.client.post(
            "/api/subcontract/13/receive",
            headers=self._headers(role="NoRole", request_id=payload["request_id"]),
            json=payload,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_receive_permission_source_unavailable_before_payload_validation(self) -> None:
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
            payload = self._receive_payload(order_id=13, idem="idem-recv-permission-source-unavailable")
            response = self.client.post(
                "/api/subcontract/13/receive",
                headers=self._headers(role="Subcontract Manager", request_id=payload["request_id"]),
                json=payload,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_internal_stock_sync_run_once_forbidden_for_non_worker_role(self) -> None:
        os.environ["ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API"] = "true"
        response = self.client.post(
            "/api/subcontract/internal/stock-sync/run-once?dry_run=true&batch_size=1",
            headers=self._headers(role="Subcontract Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySubcontractStockOutbox).count(), 0)


if __name__ == "__main__":
    unittest.main()
