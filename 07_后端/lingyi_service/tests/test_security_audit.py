"""Security audit coverage for permission denied scenarios (TASK-001E)."""

from __future__ import annotations

from datetime import date
import os
import unittest
from unittest.mock import patch

# Ensure env-dependent app settings are stable before importing app modules.
os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.permissions import SAMPLE_MANAGE
from app.core.permissions import SAMPLE_READ
from app.core.exceptions import PermissionSourceUnavailable
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopTicket
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import WorkOrderInfo
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class SecurityAuditTest(unittest.TestCase):
    """Verify 401/403/503 security audit persistence."""

    LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
    WORKSHOP_SCENARIO_TAG = "Z003-WORKSHOP-TICKET-20260524-003"

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)

        BomBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)
        WorkshopBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add_all(
                [
                    LyApparelBom(
                        id=1,
                        bom_no="BOM-ITEM-A-V1",
                        item_code="ITEM-A",
                        version_no="V1",
                        is_default=True,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                    LyApparelBom(
                        id=2,
                        bom_no="BOM-ITEM-B-V1",
                        item_code="ITEM-B",
                        version_no="V1",
                        is_default=False,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                ]
            )
            session.add_all(
                [
                    LyApparelBomItem(
                        id=1,
                        bom_id=1,
                        material_item_code="MAT-A",
                        color=None,
                        size=None,
                        qty_per_piece=1,
                        loss_rate=0,
                        uom="PCS",
                        remark=None,
                    ),
                    LyApparelBomItem(
                        id=2,
                        bom_id=2,
                        material_item_code="MAT-B",
                        color=None,
                        size=None,
                        qty_per_piece=2,
                        loss_rate=0.05,
                        uom="PCS",
                        remark=None,
                    ),
                ]
            )
            session.add_all(
                [
                    LyBomOperation(
                        id=1,
                        bom_id=1,
                        process_name="cut",
                        sequence_no=1,
                        is_subcontract=False,
                        wage_rate=1,
                        subcontract_cost_per_piece=None,
                        remark=None,
                    ),
                    LyBomOperation(
                        id=2,
                        bom_id=2,
                        process_name="sew",
                        sequence_no=1,
                        is_subcontract=True,
                        wage_rate=None,
                        subcontract_cost_per_piece=2,
                        remark=None,
                    ),
                ]
            )
            session.add(
                LyOperationWageRate(
                    id=1,
                    item_code="ITEM-A",
                    company="COMP-A",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.5",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
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
        app.dependency_overrides[bom_db_dep] = _override_db
        app.dependency_overrides[workshop_db_dep] = _override_db

        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(YsWorkshopTicket).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "BOM Editor", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "security.user", "X-LY-Dev-Roles": role}
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    @staticmethod
    def _carrier_code(value: object, *, length: int) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-length:]

    @classmethod
    def _scenario_value(cls, scenario_tag: str, value: str) -> str:
        return value if scenario_tag in value else f"{scenario_tag}-{value}"

    @staticmethod
    def _ticket_operation_code(operation: str) -> str:
        return {"register": "R", "reversal": "V", "batch": "B"}[operation]

    @classmethod
    def _ticket_request_id(cls, payload: dict) -> str:
        operation = payload["operation"]
        operator_id = payload.get("operator_id") or payload.get("employee")
        return (
            f"{payload['scenario_tag']}-RW-{cls._ticket_operation_code(operation)}-"
            f"{cls._carrier_code(payload['idempotency_key'], length=3)}-"
            f"{cls._carrier_code(payload['source_ref'], length=3)}-"
            f"{cls._carrier_code(payload['ticket_key'], length=3)}-"
            f"{cls._carrier_code(payload['job_card'], length=3)}-"
            f"{cls._carrier_code(operator_id, length=3)}-"
            f"{cls._carrier_code(payload['batch_no'], length=3)}"
        )

    def _latest_security_log(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            if not row:
                self.fail("expected security audit log row")
            return row

    def test_sample_routes_infer_security_target(self) -> None:
        read_request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/api/sample/orders",
                "raw_path": b"/api/sample/orders",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            }
        )
        module, action, resource_type, resource_id = main_module._infer_security_target(read_request)
        self.assertEqual(module, "sample")
        self.assertEqual(action, SAMPLE_READ)
        self.assertEqual(resource_type, "SampleOrder")
        self.assertIsNone(resource_id)

        write_scope = dict(read_request.scope)
        write_scope["method"] = "POST"
        write_scope["path"] = "/api/sample/tracking-templates"
        write_scope["raw_path"] = b"/api/sample/tracking-templates"
        module, action, resource_type, resource_id = main_module._infer_security_target(Request(write_scope))
        self.assertEqual(module, "sample")
        self.assertEqual(action, SAMPLE_MANAGE)
        self.assertEqual(resource_type, "SampleTrackingTemplate")
        self.assertIsNone(resource_id)

    def test_unauthorized_get_bom_list_writes_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        response = self.client.get("/api/bom/")
        payload = response.json()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(payload.get("code"), "AUTH_UNAUTHORIZED")

        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_UNAUTHORIZED")
        self.assertEqual(row.module, "bom")
        self.assertEqual(row.action, "bom:read")
        self.assertEqual(row.request_path, "/api/bom/")
        self.assertIsNone(row.user_id)
        self.assertIsNotNone(row.request_id)
        self.assertIsNotNone(row.created_at)

    def test_forbidden_action_writes_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        response = self.client.get("/api/bom/", headers=self._headers(role="NoRole"))
        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload.get("code"), "AUTH_FORBIDDEN")

        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "bom:read")
        self.assertEqual(row.user_id, "security.user")
        self.assertIn("缺少动作权限", row.deny_reason)

    def test_resource_level_forbidden_writes_resource_context(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        explode_payload = {
            "scenario_tag": "Z002-BOM-20260524-003",
            "idempotency_key": "Z002-BOM-20260524-003-EXPLODE-ITEM-B",
            "source_ref": "BOM-ITEM-B-V1",
            "bom_no": "BOM-ITEM-B-V1",
            "item_code": "ITEM-B",
            "order_qty": 100,
            "size_ratio": {},
        }
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies=set(),
            ),
        ):
            detail_resp = self.client.get("/api/bom/2", headers=self._headers())
            explode_resp = self.client.post(
                "/api/bom/2/explode",
                headers=self._headers(),
                json=explode_payload,
            )

        self.assertEqual(detail_resp.status_code, 403)
        self.assertEqual(explode_resp.status_code, 403)

        with self.SessionLocal() as session:
            rows = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.asc()).all()
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[-1].event_type, "AUTH_FORBIDDEN")
        self.assertEqual(rows[-1].resource_type, "BOM")
        self.assertEqual(rows[-1].resource_id, "2")
        self.assertEqual(rows[-1].resource_no, "ITEM-B")

    def test_permission_source_unavailable_writes_503_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="ERP timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            bom_resp = self.client.get("/api/bom/", headers=self._headers())
            auth_resp = self.client.get("/api/auth/actions?module=bom", headers=self._headers())

        self.assertEqual(bom_resp.status_code, 503)
        self.assertEqual(bom_resp.json().get("code"), "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(auth_resp.status_code, 503)
        self.assertEqual(auth_resp.json().get("code"), "PERMISSION_SOURCE_UNAVAILABLE")

        with self.SessionLocal() as session:
            rows = (
                session.query(LySecurityAuditLog)
                .filter(LySecurityAuditLog.event_type == "PERMISSION_SOURCE_UNAVAILABLE")
                .order_by(LySecurityAuditLog.id.asc())
                .all()
            )
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0].module, "bom")
        self.assertEqual(rows[1].module, "auth")
        self.assertIsNotNone(rows[0].request_method)
        self.assertIsNotNone(rows[0].request_path)
        self.assertIsNotNone(rows[0].ip_address)
        self.assertIsNotNone(rows[0].user_agent)

    def test_workshop_resource_forbidden_writes_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_DB_URL"] = self.LOCAL_ALLOWED_DB_URL
        scenario_tag = self.WORKSHOP_SCENARIO_TAG
        ticket_key = self._scenario_value(scenario_tag, "SEC-WK-001")
        source_ref = self._scenario_value(scenario_tag, "SRC-SEC-WK-001")
        batch_no = self._scenario_value(scenario_tag, "BATCH-SEC-WK-001")
        ticket_payload = {
            "scenario_tag": scenario_tag,
            "idempotency_key": self._scenario_value(scenario_tag, "IDEMP-SEC-WK-001"),
            "ticket_key": ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "qty": "10",
            "work_date": "2026-04-12",
            "source": "manual",
            "source_ref": source_ref,
            "operation": "register",
            "batch_no": batch_no,
        }
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_job_card",
            return_value=JobCardInfo(
                name="JC-001",
                operation="sew",
                status="Open",
                work_order="WO-001",
                item_code="",
                company="",
            ),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=WorkOrderInfo(name="WO-001", production_item="ITEM-A", company="COMP-A"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=EmployeeInfo(name="EMP-001", status="Active", disabled=False),
        ):
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(role="Workshop Manager", request_id=self._ticket_request_id(ticket_payload)),
                json=ticket_payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("code"), "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            ticket = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "SEC-WK-001").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.module, "workshop")
        self.assertEqual(row.action, "workshop:ticket_register")
        self.assertEqual((row.resource_type or "").upper(), "ITEM")
        self.assertEqual(row.resource_no, "DEMO-TEE")
        self.assertIsNone(ticket)


if __name__ == "__main__":
    unittest.main()
