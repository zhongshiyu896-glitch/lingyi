"""Integration tests for workshop ticket APIs (TASK-003)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import WorkOrderInfo
from app.services.workshop_service import WorkshopService


class WorkshopTicketApiTest(unittest.TestCase):
    """Cover ticket register/reversal/idempotency behavior."""

    SCENARIO_TAG = "Z003-WORKSHOP-TICKET-20260412-001"

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
        self._synthetic_context_patch = patch.object(WorkshopService, "_is_local_synthetic_context_enabled", return_value=False)
        self._synthetic_context_patch.start()
        with self.SessionLocal() as session:
            session.query(YsWorkshopTicket).delete()
            session.query(LyOperationWageRate).filter(LyOperationWageRate.id > 1).delete()
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            if base is not None:
                base.status = "active"
                base.company = "COMP-A"
            session.commit()

    def tearDown(self) -> None:
        self._synthetic_context_patch.stop()

    @staticmethod
    def _carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in str(value).encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-3:]

    @staticmethod
    def _operation_code(operation: str) -> str:
        return {"register": "R", "reversal": "V"}[operation]

    @classmethod
    def _request_id_for_payload(cls, payload: dict) -> str:
        operation = payload.get("operation", "register")
        operator = payload.get("operator_id") or payload["employee"]
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                cls._operation_code(operation),
                cls._carrier_code(payload["idempotency_key"]),
                cls._carrier_code(payload["source_ref"]),
                cls._carrier_code(payload["ticket_key"]),
                cls._carrier_code(payload["job_card"]),
                cls._carrier_code(operator),
                cls._carrier_code(payload["batch_no"]),
            ]
        )

    @classmethod
    def _headers(cls, payload: dict | None = None, role: str = "Workshop Manager") -> dict[str, str]:
        headers = {"X-LY-Dev-User": "workshop.user", "X-LY-Dev-Roles": role}
        if payload is not None:
            headers["X-Request-ID"] = cls._request_id_for_payload(payload)
        return headers

    @classmethod
    def _register_payload(cls, ticket_key: str = "TK-001", qty: str = "100") -> dict:
        scoped_ticket_key = f"{cls.SCENARIO_TAG}-{ticket_key}"
        return {
            "scenario_tag": cls.SCENARIO_TAG,
            "idempotency_key": f"{scoped_ticket_key}-IDEMP",
            "ticket_key": scoped_ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": qty,
            "work_date": "2026-04-12",
            "source": "manual",
            "source_ref": f"{scoped_ticket_key}-SRC",
            "operation": "register",
            "operator_id": "workshop.user",
            "batch_no": f"{cls.SCENARIO_TAG}-BATCH-001",
        }

    @classmethod
    def _reversal_payload(cls, ticket_key: str = "TK-R-001", qty: str = "10") -> dict:
        scoped_ticket_key = f"{cls.SCENARIO_TAG}-{ticket_key}"
        return {
            "scenario_tag": cls.SCENARIO_TAG,
            "idempotency_key": f"{scoped_ticket_key}-IDEMP",
            "ticket_key": scoped_ticket_key,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": qty,
            "work_date": "2026-04-12",
            "source_ref": f"{scoped_ticket_key}-SRC",
            "reason": "fix",
            "operation": "reversal",
            "operator_id": "workshop.user",
            "batch_no": f"{cls.SCENARIO_TAG}-BATCH-001",
        }

    @staticmethod
    def _mock_job_card(status: str = "Open", operation: str = "sew", item_code: str = "ITEM-A", work_order: str | None = None, company: str = "COMP-A") -> JobCardInfo:
        return JobCardInfo(
            name="JC-001",
            operation=operation,
            status=status,
            work_order=work_order,
            item_code=item_code,
            company=company,
        )

    @staticmethod
    def _mock_employee(active: bool = True) -> EmployeeInfo:
        return EmployeeInfo(name="EMP-001", status="Active" if active else "Left", disabled=not active)

    @staticmethod
    def _mock_work_order(item_code: str = "ITEM-A", company: str = "COMP-A", name: str = "WO-001") -> WorkOrderInfo:
        return WorkOrderInfo(name=name, production_item=item_code, company=company)

    def test_register_ticket_success_and_wage_amount(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            payload = self._register_payload(ticket_key="TK-S-001", qty="100")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "0")
        self.assertEqual(Decimal(str(payload["data"]["wage_amount"])), Decimal("50.000000"))
        self.assertIn(payload["data"]["sync_status"], {"synced", "failed", "pending"})

    def test_register_idempotent_same_payload_returns_same_ticket(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            payload = self._register_payload(ticket_key="TK-IDEMP-001")
            first = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )
            second = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["ticket_id"], second.json()["data"]["ticket_id"])
        with self.SessionLocal() as session:
            count = session.query(YsWorkshopTicket).filter(YsWorkshopTicket.ticket_key == payload["ticket_key"]).count()
        self.assertEqual(count, 1)

    def test_register_idempotency_conflict_returns_409(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            first_payload = self._register_payload(ticket_key="TK-CONFLICT-001", qty="100")
            second_payload = self._register_payload(ticket_key="TK-CONFLICT-001", qty="90")
            first = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(first_payload),
                json=first_payload,
            )
            second = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(second_payload),
                json=second_payload,
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "WORKSHOP_IDEMPOTENCY_CONFLICT")

    def test_register_invalid_qty_returns_400(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-QTY-001", qty="0")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_INVALID_QTY")

    def test_register_job_card_not_found_returns_400(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=None), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-NOJC-001")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_JOB_CARD_NOT_FOUND")

    def test_register_employee_invalid_returns_400(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(active=False),
        ):
            payload = self._register_payload(ticket_key="TK-NOEMP-001")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_EMPLOYEE_NOT_FOUND")

    def test_register_job_card_status_invalid_returns_409(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card(status="Cancelled")), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-JCS-001")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_JOB_CARD_STATUS_INVALID")

    def test_register_process_mismatch_returns_400(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card(operation="cut")), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-PM-001")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_PROCESS_MISMATCH")

    def test_register_wage_rate_not_found_returns_400(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card(operation="iron")), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-NORATE-001")
            payload["process_name"] = "iron"
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_NOT_FOUND")

    def test_ticket_register_does_not_match_item_rate_with_null_company(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=2,
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

        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-NULL-CO-IGNORED", qty="100")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(Decimal(str(response.json()["data"]["unit_wage"])), Decimal("0.500000"))

    def test_ticket_register_does_not_match_empty_company_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=4,
                    item_code="ITEM-A",
                    company="",
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

        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-EMPTY-CO-IGNORED", qty="100")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(Decimal(str(response.json()["data"]["unit_wage"])), Decimal("0.500000"))

    def test_ticket_register_fails_when_only_legacy_null_company_rate_exists(self) -> None:
        with self.SessionLocal() as session:
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            self.assertIsNotNone(base)
            base.status = "inactive"
            session.add(
                LyOperationWageRate(
                    id=3,
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

        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-NULL-CO-ONLY")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_SCOPE_REQUIRED")

    def test_ticket_register_empty_company_legacy_candidate_returns_scope_required(self) -> None:
        with self.SessionLocal() as session:
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            self.assertIsNotNone(base)
            base.status = "inactive"
            session.add(
                LyOperationWageRate(
                    id=5,
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

        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-EMPTY-CO-ONLY")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_SCOPE_REQUIRED")

    def test_company_b_job_card_cannot_use_company_a_item_wage_rate(self) -> None:
        with patch.object(
            ERPNextJobCardAdapter,
            "get_job_card",
            return_value=self._mock_job_card(company="", item_code="", work_order="WO-B-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_work_order",
            return_value=self._mock_work_order(item_code="ITEM-A", company="COMP-B", name="WO-B-001"),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ):
            payload = self._register_payload(ticket_key="TK-COMP-B-MISS")
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_NOT_FOUND")

    def test_reversal_success_and_exceed_guard(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._mock_job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._mock_employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            register_payload = self._register_payload(ticket_key="TK-REV-RG-001", qty="100")
            reversal_ok_payload = self._reversal_payload(ticket_key="TK-REV-OK-001", qty="10")
            reversal_bad_payload = self._reversal_payload(ticket_key="TK-REV-BAD-001", qty="200")
            register_resp = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers(register_payload),
                json=register_payload,
            )
            reversal_ok = self.client.post(
                "/api/workshop/tickets/reversal",
                headers=self._headers(reversal_ok_payload),
                json=reversal_ok_payload,
            )
            reversal_bad = self.client.post(
                "/api/workshop/tickets/reversal",
                headers=self._headers(reversal_bad_payload),
                json=reversal_bad_payload,
            )

        self.assertEqual(register_resp.status_code, 200)
        self.assertEqual(reversal_ok.status_code, 200)
        self.assertEqual(Decimal(str(reversal_ok.json()["data"]["net_qty"])), Decimal("90.000000"))
        self.assertEqual(reversal_bad.status_code, 409)
        self.assertEqual(reversal_bad.json()["code"], "WORKSHOP_REVERSAL_EXCEEDS_REGISTERED")


if __name__ == "__main__":
    unittest.main()
