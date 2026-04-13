"""Security/permission tests for workshop module (TASK-003A)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.exceptions import PermissionSourceUnavailable
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopDailyWage
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import WorkOrderInfo
from app.services.erpnext_job_card_adapter import CompanyInfo
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class WorkshopPermissionTest(unittest.TestCase):
    """Validate workshop read/write permission and audit behavior."""

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
        WorkshopBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
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
            session.add(
                YsWorkshopTicket(
                    id=1,
                    ticket_no="TICKET-1",
                    ticket_key="KEY-1",
                    job_card="JC-001",
                    work_order="WO-001",
                    bom_id=None,
                    item_code="ITEM-A",
                    employee="EMP-001",
                    process_name="sew",
                    color="black",
                    size="M",
                    operation_type="register",
                    qty=Decimal("10"),
                    unit_wage=Decimal("0.5"),
                    wage_amount=Decimal("5"),
                    work_date=date(2026, 4, 12),
                    source="manual",
                    source_ref=None,
                    original_ticket_id=None,
                    sync_status="synced",
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
        app.dependency_overrides[workshop_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(YsWorkshopDailyWage).delete()
            session.query(YsWorkshopJobCardSyncLog).delete()
            session.query(YsWorkshopTicket).filter(YsWorkshopTicket.id > 1).delete()
            session.query(LyOperationWageRate).filter(LyOperationWageRate.id > 1).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "perm.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _register_payload(ticket_key: str = "TK-REG-001") -> dict:
        return {
            "ticket_key": ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": "10",
            "work_date": "2026-04-12",
            "source": "manual",
            "source_ref": "REF-1",
        }

    @staticmethod
    def _reversal_payload(ticket_key: str = "TK-RV-001") -> dict:
        return {
            "ticket_key": ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": "1",
            "work_date": "2026-04-12",
            "original_ticket_id": 1,
            "reason": "fix",
        }

    @staticmethod
    def _job_card(item_code: str = "ITEM-A", company: str = "COMP-A", work_order: str | None = "WO-001") -> JobCardInfo:
        return JobCardInfo(
            name="JC-001",
            operation="sew",
            status="Open",
            work_order=work_order,
            item_code=item_code,
            company=company,
        )

    @staticmethod
    def _job_card_b(item_code: str = "ITEM-B", company: str = "COMP-A", work_order: str | None = "WO-002") -> JobCardInfo:
        return JobCardInfo(
            name="JC-002",
            operation="sew",
            status="Open",
            work_order=work_order,
            item_code=item_code,
            company=company,
        )

    @staticmethod
    def _work_order(item_code: str = "ITEM-A", company: str = "COMP-A", name: str = "WO-001") -> WorkOrderInfo:
        return WorkOrderInfo(name=name, production_item=item_code, company=company)

    @staticmethod
    def _employee() -> EmployeeInfo:
        return EmployeeInfo(name="EMP-001", status="Active", disabled=False)

    def _latest_security_log(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertIsNotNone(row)
        return row  # type: ignore[return-value]

    def test_unauthorized_returns_401_and_security_audit(self) -> None:
        response = self.client.get("/api/workshop/tickets")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_UNAUTHORIZED")
        self.assertEqual(row.module, "workshop")

    def test_forbidden_returns_403_and_security_audit(self) -> None:
        response = self.client.get("/api/workshop/tickets", headers=self._headers(role="NoRole"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:read")

    def test_register_item_scope_forbidden_does_not_write(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card(item_code="", company="", work_order="WO-001")), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as sync_mock:
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="TK-DENY-ITEM-A"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        self.assertFalse(sync_mock.called)
        with self.SessionLocal() as session:
            ticket = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "TK-DENY-ITEM-A").first()
            daily_rows = session.query(YsWorkshopDailyWage).all()
        self.assertIsNone(ticket)
        self.assertEqual(len(daily_rows), 0)
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_register")
        self.assertEqual((row.resource_type or "").upper(), "ITEM")
        self.assertEqual(row.resource_no, "ITEM-A")

    def test_reversal_item_scope_forbidden_does_not_write(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card(item_code="", company="", work_order="WO-001")), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            response = self.client.post(
                "/api/workshop/tickets/reversal",
                headers=self._headers(),
                json=self._reversal_payload(ticket_key="TK-RV-DENY-A"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            ticket = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "TK-RV-DENY-A").first()
        self.assertIsNone(ticket)
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_reversal")

    def test_batch_mixed_items_forbidden_and_allowed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with self.SessionLocal() as session:
            if not session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 2).first():
                session.add(
                    LyOperationWageRate(
                        id=2,
                        item_code="ITEM-B",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.6",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    )
                )
                session.commit()

        def _job_card_side_effect(job_card: str):
            if job_card == "JC-001":
                return self._job_card(item_code="", company="", work_order="WO-001")
            if job_card == "JC-002":
                return self._job_card_b(item_code="", company="", work_order="WO-002")
            return None

        def _work_order_side_effect(work_order: str):
            if work_order == "WO-001":
                return self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001")
            if work_order == "WO-002":
                return self._work_order(item_code="ITEM-B", company="COMP-A", name="WO-002")
            return None

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", side_effect=_job_card_side_effect), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            side_effect=_work_order_side_effect,
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            response = self.client.post(
                "/api/workshop/tickets/batch",
                headers=self._headers(),
                json={
                    "tickets": [
                        {
                            "operation_type": "register",
                            "ticket_key": "BATCH-A-001",
                            "job_card": "JC-001",
                            "employee": "EMP-001",
                            "process_name": "sew",
                            "qty": "5",
                            "work_date": "2026-04-12",
                            "source": "import",
                        },
                        {
                            "operation_type": "register",
                            "ticket_key": "BATCH-B-001",
                            "job_card": "JC-002",
                            "employee": "EMP-001",
                            "process_name": "sew",
                            "qty": "8",
                            "work_date": "2026-04-12",
                            "source": "import",
                        },
                    ]
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["success_count"], 1)
        self.assertEqual(data["failed_count"], 1)
        self.assertEqual(data["failed_items"][0]["row_index"], 1)
        self.assertEqual(data["failed_items"][0]["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            denied_row = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "BATCH-A-001").first()
            allowed_row = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "BATCH-B-001").first()
        self.assertIsNone(denied_row)
        self.assertIsNotNone(allowed_row)
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_batch")

    def test_job_card_sync_item_scope_forbidden(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card(item_code="", company="", work_order="WO-001")), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as sync_mock:
            response = self.client.post("/api/workshop/job-cards/JC-001/sync", headers=self._headers())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        self.assertFalse(sync_mock.called)
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:job_card_sync")

    def test_wage_rate_item_scope_forbidden(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies=set(),
            ),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=ItemInfo(name="ITEM-A", item_code="ITEM-A", disabled=False, companies=("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ):
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers(),
                json={
                    "item_code": "ITEM-A",
                    "company": "COMP-A",
                    "process_name": "sew",
                    "wage_rate": "0.8",
                    "effective_from": "2026-05-01",
                    "effective_to": None,
                },
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.item_code == "ITEM-A", LyOperationWageRate.id > 1).first()
        self.assertIsNone(row)
        audit_row = self._latest_security_log()
        self.assertEqual(audit_row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(audit_row.action, "workshop:wage_rate_manage")

    def test_global_wage_rate_without_manage_all_forbidden(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        response = self.client.post(
            "/api/workshop/wage-rates",
            headers=self._headers(role="Workshop Wage Clerk"),
            json={
                "item_code": None,
                "process_name": "sew",
                "wage_rate": "0.8",
                "effective_from": "2026-05-01",
                "effective_to": None,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_item_mismatch_returns_400_and_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card(item_code="", company="", work_order="WO-001")), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            payload = self._register_payload(ticket_key="TK-MISMATCH-001")
            payload["item_code"] = "ITEM-Z"
            response = self.client.post("/api/workshop/tickets/register", headers=self._headers(), json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_ITEM_MISMATCH")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_register")

    def test_legacy_null_company_rate_denial_writes_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            self.assertIsNotNone(base)
            base.status = "inactive"
            session.add(
                LyOperationWageRate(
                    id=99,
                    item_code="ITEM-A",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.9",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()

        with patch.object(
            ERPNextJobCardAdapter,
            "get_job_card",
            return_value=self._job_card(item_code="ITEM-A", company="COMP-A", work_order=None),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="TK-LEGACY-SCOPE-DENY"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_SCOPE_REQUIRED")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_register")
        self.assertEqual((row.resource_type or "").upper(), "WAGERATE")
        self.assertEqual(row.resource_no, "ITEM-A")

    def test_legacy_empty_company_rate_denial_writes_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            self.assertIsNotNone(base)
            base.status = "inactive"
            session.add(
                LyOperationWageRate(
                    id=100,
                    item_code="ITEM-A",
                    company="   ",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.9",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()

        with patch.object(
            ERPNextJobCardAdapter,
            "get_job_card",
            return_value=self._job_card(item_code="ITEM-A", company="COMP-A", work_order=None),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ):
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="TK-LEGACY-EMPTY-SCOPE-DENY"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_SCOPE_REQUIRED")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:ticket_register")
        self.assertEqual((row.resource_type or "").upper(), "WAGERATE")
        self.assertEqual(row.resource_no, "ITEM-A")

    def test_permission_source_unavailable_returns_503_for_write(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ), patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card(item_code="", company="", work_order="WO-001")), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._work_order(item_code="ITEM-A", company="COMP-A", name="WO-001"),
        ):
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(),
                json=self._register_payload(ticket_key="TK-503-001"),
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            row = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == "TK-503-001").first()
        self.assertIsNone(row)
        audit_row = self._latest_security_log()
        self.assertEqual(audit_row.event_type, "PERMISSION_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
