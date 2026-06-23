"""Integration tests for workshop wage and wage-rate APIs (TASK-003)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import ERPNextServiceUnavailableError
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import LyOperationWageRateCompanyBackfillLog
from app.models.workshop import YsWorkshopDailyWage
from app.models.workshop import YsWorkshopTicket
from app.models.workshop import YsWorkshopWagePayment
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import CompanyInfo
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.permission_service import FASTAPI_ROLE_ACTIONS_ENV
from app.services.workshop_service import WageRateCompanyBackfillPlanRow
from app.services.workshop_service import WorkshopService


class WorkshopWageApiTest(unittest.TestCase):
    """Cover daily wage formula and wage-rate overlap rules."""

    TICKET_SCENARIO_TAG = "Z003-WORKSHOP-TICKET-20260524-005"
    WAGE_SCENARIO_TAG = "Z002-WORKSHOP-WAGE-20260524-006"
    PAYMENT_SCENARIO_TAG = "Z006-WORKSHOP-WAGE-PAYMENT-20260620-001"

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
        with self.SessionLocal() as session:
            session.query(YsWorkshopWagePayment).delete()
            session.query(YsWorkshopTicket).delete()
            session.query(YsWorkshopDailyWage).delete()
            session.query(LyOperationWageRateCompanyBackfillLog).delete()
            session.query(LyOperationWageRate).filter(LyOperationWageRate.id > 1).delete()
            base = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 1).first()
            if base is not None:
                base.item_code = "ITEM-A"
                base.company = "COMP-A"
                base.is_global = False
                base.process_name = "sew"
                base.wage_rate = Decimal("0.5")
                base.effective_from = date(2026, 1, 1)
                base.effective_to = None
                base.status = "active"
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Manager", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "wage.user", "X-LY-Dev-Roles": role}
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    @staticmethod
    def _job_card() -> JobCardInfo:
        return JobCardInfo(
            name="JC-001",
            operation="sew",
            status="Open",
            work_order=None,
            item_code="ITEM-A",
            company="COMP-A",
        )

    @staticmethod
    def _employee() -> EmployeeInfo:
        return EmployeeInfo(name="EMP-001", status="Active", disabled=False)

    @staticmethod
    def _carrier_code(value: object, *, length: int) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-length:]

    @staticmethod
    def _scenario_value(scenario_tag: str, value: str) -> str:
        return value if scenario_tag in value else f"{scenario_tag}-{value}"

    @staticmethod
    def _ticket_operation_code(operation: str) -> str:
        return {"register": "R", "reversal": "V"}[operation]

    @classmethod
    def _ticket_request_id(cls, payload: dict[str, object]) -> str:
        operator_id = payload.get("operator_id") or payload["employee"]
        return (
            f"{payload['scenario_tag']}-RW-{cls._ticket_operation_code(str(payload['operation']))}-"
            f"{cls._carrier_code(payload['idempotency_key'], length=3)}-"
            f"{cls._carrier_code(payload['source_ref'], length=3)}-"
            f"{cls._carrier_code(payload['ticket_key'], length=3)}-"
            f"{cls._carrier_code(payload['job_card'], length=3)}-"
            f"{cls._carrier_code(operator_id, length=3)}-"
            f"{cls._carrier_code(payload['batch_no'], length=3)}"
        )

    @classmethod
    def _ticket_payload(cls, *, operation: str, ticket_key: str, qty: str) -> dict[str, str]:
        scenario_tag = cls.TICKET_SCENARIO_TAG
        ticket_key_value = cls._scenario_value(scenario_tag, ticket_key)
        return {
            "scenario_tag": scenario_tag,
            "idempotency_key": cls._scenario_value(scenario_tag, f"IDEMP-{ticket_key}"),
            "ticket_key": ticket_key_value,
            "job_card": "JC-001",
            "employee": "EMP-001",
            "process_name": "sew",
            "color": "black",
            "size": "M",
            "qty": qty,
            "work_date": "2026-04-12",
            "source": "manual",
            "source_ref": cls._scenario_value(scenario_tag, f"SRC-{ticket_key}"),
            "operation": operation,
            "batch_no": cls._scenario_value(scenario_tag, f"BATCH-{ticket_key}"),
        }

    @classmethod
    def _wage_payload(
        cls,
        *,
        item_code: str | None,
        company: str | None,
        process_name: str = "sew",
        wage_rate: str,
        effective_from: str,
        effective_to: str | None,
        carrier_suffix: str,
    ) -> dict[str, str | None]:
        scenario_tag = cls.WAGE_SCENARIO_TAG
        return {
            "scenario_tag": scenario_tag,
            "idempotency_key": cls._scenario_value(scenario_tag, f"IDEMP-{carrier_suffix}"),
            "source_ref": cls._scenario_value(scenario_tag, f"REF-{carrier_suffix}"),
            "item_code": item_code,
            "company": company,
            "process_name": process_name,
            "wage_rate": wage_rate,
            "effective_from": effective_from,
            "effective_to": effective_to,
        }

    @classmethod
    def _wage_request_id(cls, payload: dict[str, object]) -> str:
        company = payload.get("company") or "GLOBAL"
        item_scope = payload.get("item_code") or "GLOBAL"
        effective_from = str(payload["effective_from"]).replace("-", "")
        return (
            f"{payload['scenario_tag']}-RW-"
            f"C{cls._carrier_code(company, length=4)}-"
            f"P{cls._carrier_code(payload['process_name'], length=4)}-"
            f"I{cls._carrier_code(item_scope, length=4)}-"
            f"D{effective_from}"
        )

    @classmethod
    def _payment_payload(
        cls,
        *,
        row: dict[str, object],
        paid_amount: str,
        carrier_suffix: str,
    ) -> dict[str, object]:
        scenario_tag = cls.PAYMENT_SCENARIO_TAG
        return {
            "scenario_tag": scenario_tag,
            "idempotency_key": cls._scenario_value(scenario_tag, f"IDEMP-{carrier_suffix}"),
            "source_ref": cls._scenario_value(scenario_tag, f"SRC-{carrier_suffix}"),
            "employee": str(row["employee"]),
            "work_date": str(row["work_date"]),
            "process_name": str(row["process_name"]),
            "item_code": row.get("item_code"),
            "paid_amount": paid_amount,
            "mode_of_payment": "Bank Transfer",
            "reference_no": cls._scenario_value(scenario_tag, f"REF-{carrier_suffix}"),
            "reference_date": str(row["work_date"]),
            "operation": "create_wage_payment",
        }

    @classmethod
    def _cancel_payment_payload(cls, *, carrier_suffix: str) -> dict[str, object]:
        scenario_tag = cls.PAYMENT_SCENARIO_TAG
        return {
            "scenario_tag": scenario_tag,
            "idempotency_key": cls._scenario_value(scenario_tag, f"CANCEL-IDEMP-{carrier_suffix}"),
            "source_ref": cls._scenario_value(scenario_tag, f"CANCEL-SRC-{carrier_suffix}"),
            "reason": cls._scenario_value(scenario_tag, f"cancel-{carrier_suffix}"),
            "operation": "cancel_wage_payment",
        }

    @classmethod
    def _headers_for_ticket_payload(cls, payload: dict[str, object]) -> dict[str, str]:
        return cls._headers(request_id=cls._ticket_request_id(payload))

    @classmethod
    def _headers_for_wage_payload(cls, payload: dict[str, object]) -> dict[str, str]:
        return cls._headers(request_id=cls._wage_request_id(payload))

    def _register(self, ticket_key: str, qty: str) -> None:
        payload = self._ticket_payload(operation="register", ticket_key=ticket_key, qty=qty)
        response = self.client.post(
            "/api/workshop/tickets/register",
            headers=self._headers_for_ticket_payload(payload),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

    def _reversal(self, ticket_key: str, qty: str) -> None:
        payload = self._ticket_payload(operation="reversal", ticket_key=ticket_key, qty=qty)
        payload["reason"] = "fix"
        response = self.client.post(
            "/api/workshop/tickets/reversal",
            headers=self._headers_for_ticket_payload(payload),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

    def _create_daily_wage_for_payment(self, *, ticket_key: str, qty: str, employee: str) -> dict[str, object]:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=EmployeeInfo(name=employee, status="Active", disabled=False),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=ItemInfo(name="ITEM-A", item_code="ITEM-A", disabled=False, companies=("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            payload = self._ticket_payload(operation="register", ticket_key=ticket_key, qty=qty)
            payload["employee"] = employee
            response = self.client.post(
                "/api/workshop/tickets/register",
                headers=self._headers_for_ticket_payload(payload),
                json=payload,
            )
            self.assertEqual(response.status_code, 200)

        daily = self.client.get(
            f"/api/workshop/daily-wages?employee={employee}&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(),
        )
        self.assertEqual(daily.status_code, 200)
        rows = daily.json()["data"]["items"]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_local_synthetic_ticket_uses_fastapi_wage_rate_table(self) -> None:
        create_payload = self._wage_payload(
            item_code="ITEM-A",
            company="LY-LOCAL-TEST",
            wage_rate="2.25",
            effective_from="2026-01-01",
            effective_to=None,
            carrier_suffix="LOCAL-ITEM-A-LY-LOCAL-TEST-20260101",
        )
        create_response = self.client.post(
            "/api/workshop/wage-rates",
            headers=self._headers_for_wage_payload(create_payload),
            json=create_payload,
        )
        self.assertEqual(create_response.status_code, 200)

        ticket_payload = self._ticket_payload(operation="register", ticket_key="LOCAL-WAGE-RG-001", qty="10")
        ticket_payload["item_code"] = "ITEM-A"
        ticket_response = self.client.post(
            "/api/workshop/tickets/register",
            headers=self._headers_for_ticket_payload(ticket_payload),
            json=ticket_payload,
        )
        self.assertEqual(ticket_response.status_code, 200)
        self.assertEqual(Decimal(str(ticket_response.json()["data"]["unit_wage"])), Decimal("2.250000"))
        self.assertEqual(Decimal(str(ticket_response.json()["data"]["wage_amount"])), Decimal("22.500000"))

    def test_fastapi_native_local_ticket_does_not_construct_erpnext_adapter(self) -> None:
        create_payload = self._wage_payload(
            item_code="ITEM-FASTAPI",
            company="LY-LOCAL-TEST",
            wage_rate="1.75",
            effective_from="2026-01-01",
            effective_to=None,
            carrier_suffix="FASTAPI-ITEM-LY-LOCAL-TEST-20260101",
        )
        wage_headers = self._headers_for_wage_payload(create_payload)
        wage_headers["X-LY-Dev-Roles"] = "System Manager"
        ticket_payload = self._ticket_payload(operation="register", ticket_key="FASTAPI-WAGE-RG-001", qty="8")
        ticket_payload["item_code"] = "ITEM-FASTAPI"
        ticket_headers = self._headers_for_ticket_payload(ticket_payload)
        ticket_headers["X-LY-Dev-Roles"] = "System Manager"
        read_headers = self._headers(role="System Manager")

        with patch.dict(
            os.environ,
            {
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                FASTAPI_ROLE_ACTIONS_ENV: json.dumps({"roles": {"System Manager": {"unrestricted": True}}}),
            },
        ), patch(
            "app.routers.workshop.ERPNextJobCardAdapter",
            side_effect=AssertionError("FastAPI workshop API must not construct ERPNextJobCardAdapter"),
        ):
            create_response = self.client.post(
                "/api/workshop/wage-rates",
                headers=wage_headers,
                json=create_payload,
            )
            self.assertEqual(create_response.status_code, 200)

            ticket_response = self.client.post(
                "/api/workshop/tickets/register",
                headers=ticket_headers,
                json=ticket_payload,
            )
            self.assertEqual(ticket_response.status_code, 200)
            self.assertEqual(Decimal(str(ticket_response.json()["data"]["unit_wage"])), Decimal("1.750000"))
            self.assertEqual(Decimal(str(ticket_response.json()["data"]["wage_amount"])), Decimal("14.000000"))

            tickets_response = self.client.get("/api/workshop/tickets?employee=EMP-001", headers=read_headers)
            self.assertEqual(tickets_response.status_code, 200)
            self.assertEqual(tickets_response.json()["data"]["total"], 1)

            daily_response = self.client.get(
                "/api/workshop/daily-wages?employee=EMP-001&from_date=2026-04-12&to_date=2026-04-12",
                headers=read_headers,
            )
            self.assertEqual(daily_response.status_code, 200)
            self.assertEqual(daily_response.json()["data"]["items"][0]["wage_amount"], 14.0)

    def test_daily_wage_formula_and_snapshot_not_changed(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=ItemInfo(name="ITEM-A", item_code="ITEM-A", disabled=False, companies=("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ):
            self._register("WAGE-RG-001", "100")
            self._reversal("WAGE-RV-001", "10")

            daily = self.client.get(
                "/api/workshop/daily-wages?employee=EMP-001&from_date=2026-04-12&to_date=2026-04-12",
                headers=self._headers(),
            )
            self.assertEqual(daily.status_code, 200)
            row = daily.json()["data"]["items"][0]
            self.assertEqual(Decimal(str(row["net_qty"])), Decimal("90.000000"))
            self.assertEqual(Decimal(str(row["wage_amount"])), Decimal("90.000000"))

            deactivate_payload = {
                **self._wage_payload(
                    item_code="ITEM-A",
                    company="COMP-A",
                    wage_rate="0.5",
                    effective_from="2026-01-01",
                    effective_to=None,
                    carrier_suffix="DEACTIVATE-ITEM-A-COMP-A-20260101",
                ),
                "reason": self._scenario_value(self.WAGE_SCENARIO_TAG, "new-range"),
                "rate_id": 1,
            }
            deactivate_old_rate = self.client.post(
                "/api/workshop/wage-rates/1/deactivate",
                headers=self._headers_for_wage_payload(deactivate_payload),
                json=deactivate_payload,
            )
            self.assertEqual(deactivate_old_rate.status_code, 200)

            create_payload = self._wage_payload(
                item_code="ITEM-A",
                company="COMP-A",
                wage_rate="0.8",
                effective_from="2026-05-01",
                effective_to=None,
                carrier_suffix="CREATE-ITEM-A-COMP-A-20260501",
            )
            create_new_rate = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(create_payload),
                json=create_payload,
            )
            self.assertEqual(create_new_rate.status_code, 200)

            tickets = self.client.get("/api/workshop/tickets?employee=EMP-001", headers=self._headers())
            self.assertEqual(tickets.status_code, 200)
            first_ticket = tickets.json()["data"]["items"][0]
            self.assertEqual(Decimal(str(first_ticket["unit_wage"])), Decimal("1.000000"))

    def test_wage_payment_closes_daily_wage_and_replays_idempotently(self) -> None:
        row = self._create_daily_wage_for_payment(ticket_key="PAY-RG-001", qty="8", employee="EMP-PAY-001")
        wage_amount = Decimal(str(row["wage_amount"]))
        payload = self._payment_payload(
            row=row,
            paid_amount=str(wage_amount),
            carrier_suffix="PAY-001",
        )

        response = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["employee"], "EMP-PAY-001")
        self.assertEqual(Decimal(str(data["paid_amount"])), wage_amount)
        self.assertEqual(Decimal(str(data["outstanding_after"])), Decimal("0.000000"))
        self.assertEqual(data["financial_ledger_status"], "closed")
        self.assertEqual(data["financial_ledger_status_name"], "总账已闭合")
        self.assertTrue(data["financial_ledger_closed"])

        replay = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=payload,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["data"]["id"], data["id"])

        daily = self.client.get(
            "/api/workshop/daily-wages?employee=EMP-PAY-001&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(role="Workshop Wage Clerk"),
        )
        self.assertEqual(daily.status_code, 200)
        paid_row = daily.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(paid_row["paid_amount"])), wage_amount)
        self.assertEqual(Decimal(str(paid_row["outstanding_amount"])), Decimal("0.000000"))
        self.assertEqual(paid_row["payment_status"], "paid")
        self.assertEqual(paid_row["payment_count"], 1)
        self.assertEqual(paid_row["financial_ledger_status"], "closed")
        self.assertEqual(Decimal(str(paid_row["financial_ledger_cash_out_amount"])), wage_amount)
        self.assertEqual(Decimal(str(paid_row["financial_ledger_outstanding_amount"])), Decimal("0.000000"))

        payments = self.client.get(
            "/api/workshop/wage-payments?employee=EMP-PAY-001&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(role="Workshop Wage Clerk"),
        )
        self.assertEqual(payments.status_code, 200)
        self.assertEqual(payments.json()["data"]["total"], 1)
        self.assertEqual(payments.json()["data"]["items"][0]["payment_entry"], data["payment_entry"])

        cancel_payload = self._cancel_payment_payload(carrier_suffix="PAY-001")
        cancel = self.client.post(
            f"/api/workshop/wage-payments/{data['id']}/cancel",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=cancel_payload,
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()["data"]["status"], "cancelled")

        replay_cancel = self.client.post(
            f"/api/workshop/wage-payments/{data['id']}/cancel",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=cancel_payload,
        )
        self.assertEqual(replay_cancel.status_code, 200)
        self.assertEqual(replay_cancel.json()["data"]["status"], "cancelled")

        reopened = self.client.get(
            "/api/workshop/daily-wages?employee=EMP-PAY-001&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(role="Workshop Wage Clerk"),
        )
        self.assertEqual(reopened.status_code, 200)
        reopened_row = reopened.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(reopened_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(reopened_row["outstanding_amount"])), wage_amount)
        self.assertEqual(reopened_row["payment_status"], "unpaid")
        self.assertEqual(reopened_row["financial_ledger_status"], "posted")
        self.assertEqual(reopened_row["financial_ledger_status_name"], "应付已归集")
        self.assertEqual(Decimal(str(reopened_row["financial_ledger_cash_out_amount"])), Decimal("0.000000"))

        submitted_payments = self.client.get(
            "/api/workshop/wage-payments?employee=EMP-PAY-001&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(role="Workshop Wage Clerk"),
        )
        self.assertEqual(submitted_payments.status_code, 200)
        self.assertEqual(submitted_payments.json()["data"]["total"], 0)

    def test_wage_payment_partial_financial_ledger_status(self) -> None:
        row = self._create_daily_wage_for_payment(ticket_key="PAY-RG-PART", qty="8", employee="EMP-PAY-PART")
        wage_amount = Decimal(str(row["wage_amount"]))
        partial_amount = wage_amount / Decimal("2")
        payload = self._payment_payload(
            row=row,
            paid_amount=str(partial_amount),
            carrier_suffix="PAY-PART",
        )

        response = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        payment = response.json()["data"]
        self.assertEqual(payment["financial_ledger_status"], "partial")
        self.assertEqual(payment["financial_ledger_status_name"], "部分归集")
        self.assertEqual(Decimal(str(payment["financial_ledger_cash_out_amount"])), partial_amount)

        daily = self.client.get(
            "/api/workshop/daily-wages?employee=EMP-PAY-PART&from_date=2026-04-12&to_date=2026-04-12",
            headers=self._headers(role="Workshop Wage Clerk"),
        )
        self.assertEqual(daily.status_code, 200)
        daily_row = daily.json()["data"]["items"][0]
        self.assertEqual(daily_row["payment_status"], "partly_paid")
        self.assertEqual(daily_row["financial_ledger_status"], "partial")
        self.assertEqual(Decimal(str(daily_row["financial_ledger_cash_out_amount"])), partial_amount)
        self.assertEqual(Decimal(str(daily_row["financial_ledger_outstanding_amount"])), partial_amount)

    def test_wage_payment_over_amount_returns_409(self) -> None:
        row = self._create_daily_wage_for_payment(ticket_key="PAY-RG-002", qty="4", employee="EMP-PAY-002")
        over_amount = Decimal(str(row["wage_amount"])) + Decimal("0.010000")
        payload = self._payment_payload(
            row=row,
            paid_amount=str(over_amount),
            carrier_suffix="PAY-002",
        )

        response = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=payload,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_PAYMENT_AMOUNT_EXCEEDED")

    def test_wage_payment_create_requires_payment_permission(self) -> None:
        row = self._create_daily_wage_for_payment(ticket_key="PAY-RG-003", qty="6", employee="EMP-PAY-003")
        payload = self._payment_payload(
            row=row,
            paid_amount=str(row["wage_amount"]),
            carrier_suffix="PAY-003",
        )

        response = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Clerk"),
            json=payload,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_wage_payment_cancel_requires_payment_permission(self) -> None:
        row = self._create_daily_wage_for_payment(ticket_key="PAY-RG-004", qty="6", employee="EMP-PAY-004")
        create_payload = self._payment_payload(
            row=row,
            paid_amount=str(row["wage_amount"]),
            carrier_suffix="PAY-004",
        )
        created = self.client.post(
            "/api/workshop/wage-payments",
            headers=self._headers(role="Workshop Wage Clerk"),
            json=create_payload,
        )
        self.assertEqual(created.status_code, 200)
        cancel_payload = self._cancel_payment_payload(carrier_suffix="PAY-004")

        response = self.client.post(
            f"/api/workshop/wage-payments/{created.json()['data']['id']}/cancel",
            headers=self._headers(role="Workshop Clerk"),
            json=cancel_payload,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_wage_rate_overlap_returns_409(self) -> None:
        with patch.object(ERPNextJobCardAdapter, "get_job_card", return_value=self._job_card()), patch.object(
            ERPNextJobCardAdapter,
            "get_employee",
            return_value=self._employee(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=ItemInfo(name="ITEM-A", item_code="ITEM-A", disabled=False, companies=("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ):
            overlap_payload = self._wage_payload(
                item_code="ITEM-A",
                company="COMP-A",
                wage_rate="0.6",
                effective_from="2026-02-01",
                effective_to="2026-12-31",
                carrier_suffix="OVERLAP-ITEM-A-COMP-A-20260201",
            )
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(overlap_payload),
                json=overlap_payload,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_OVERLAP")

    def test_is_missing_company_treats_none_empty_and_whitespace_as_missing(self) -> None:
        self.assertTrue(WorkshopService._is_missing_company(None))
        self.assertTrue(WorkshopService._is_missing_company(""))
        self.assertTrue(WorkshopService._is_missing_company("   "))
        self.assertFalse(WorkshopService._is_missing_company("COMP-A"))

    def test_backfill_sets_company_for_uniquely_resolved_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=10,
                        item_code="ITEM-U",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=11,
                        item_code="ITEM-U",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 10).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.company, "COMP-A")
            logs = (
                session.query(LyOperationWageRateCompanyBackfillLog)
                .filter(LyOperationWageRateCompanyBackfillLog.wage_rate_id == 10)
                .all()
            )
        self.assertEqual(report.backfilled_count, 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].result, "backfilled")

    def test_backfill_scans_null_empty_and_whitespace_company(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=60,
                        item_code="ITEM-SCAN-1",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=61,
                        item_code="ITEM-SCAN-2",
                        company="",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=62,
                        item_code="ITEM-SCAN-3",
                        company="   ",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=63,
                        item_code="ITEM-SCAN-1",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=64,
                        item_code="ITEM-SCAN-2",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=65,
                        item_code="ITEM-SCAN-3",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.rollback()
        self.assertEqual(report.total_scanned, 3)

    def test_wage_rate_company_backfill_dry_run_leaves_session_new_empty(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=66,
                    item_code="ITEM-DRY-NEW",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-DRY-NEW", item_code="ITEM-DRY-NEW", disabled=False, companies=tuple()),
            ):
                service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)

    def test_wage_rate_company_backfill_dry_run_leaves_session_dirty_empty(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=67,
                    item_code="ITEM-DRY-DIRTY",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-DRY-DIRTY", item_code="ITEM-DRY-DIRTY", disabled=False, companies=tuple()),
            ):
                service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

    def test_wage_rate_company_backfill_dry_run_commit_persists_no_backfill_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=68,
                    item_code="ITEM-DRY-LOG",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            before_count = session.query(LyOperationWageRateCompanyBackfillLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-DRY-LOG", item_code="ITEM-DRY-LOG", disabled=False, companies=tuple()),
            ):
                service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.commit()
            after_count = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(before_count, after_count)

    def test_wage_rate_company_backfill_dry_run_commit_changes_no_wage_rates(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=69,
                        item_code="ITEM-DRY-RATE",
                        company="   ",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=72,
                        item_code="ITEM-DRY-RATE",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 69).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.company, "   ")
            self.assertEqual(row.status, "active")

    def test_wage_rate_company_backfill_dry_run_writes_no_audit_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=73,
                    item_code="ITEM-DRY-AUDIT",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            before_op = session.query(LyOperationAuditLog).count()
            before_sec = session.query(LySecurityAuditLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-DRY-AUDIT", item_code="ITEM-DRY-AUDIT", disabled=False, companies=tuple()),
            ):
                service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.commit()
            after_op = session.query(LyOperationAuditLog).count()
            after_sec = session.query(LySecurityAuditLog).count()
        self.assertEqual(before_op, after_op)
        self.assertEqual(before_sec, after_sec)

    def test_wage_rate_company_backfill_dry_run_report_uses_plain_rows_not_orm(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=74,
                    item_code="ITEM-DRY-PLAN",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-DRY-PLAN", item_code="ITEM-DRY-PLAN", disabled=False, companies=tuple()),
            ):
                plan = service.build_wage_rate_company_backfill_plan()
        self.assertTrue(plan)
        self.assertIsInstance(plan[0], WageRateCompanyBackfillPlanRow)
        self.assertFalse(hasattr(plan[0], "_sa_instance_state"))

    def test_wage_rate_company_backfill_dry_run_exception_leaves_session_clean(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=75,
                    item_code="ITEM-DRY-ERR",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(service, "_resolve_backfill_companies", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

    def test_resolve_backfill_companies_sqlalchemy_error_returns_database_read_failed(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT * FROM ly_schema.ly_operation_wage_rate]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed) as raised:
                    service._resolve_backfill_companies(item_code="ITEM-READ-FAIL")
        self.assertEqual(raised.exception.code, "DATABASE_READ_FAILED")

    def test_resolve_backfill_companies_sqlalchemy_error_does_not_return_ambiguous(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=760,
                    item_code="ITEM-READ-AMB",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed) as raised:
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertNotEqual(raised.exception.code, "WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS")

    def test_resolve_backfill_companies_sqlalchemy_error_does_not_return_unresolved(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=761,
                    item_code="ITEM-READ-UNRES",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed) as raised:
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertNotEqual(raised.exception.code, "WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED")

    def test_backfill_plan_database_read_failed_does_not_return_success_report(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=762,
                    item_code="ITEM-READ-PLAN",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")

    def test_backfill_dry_run_database_read_failed_leaves_session_clean(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=763,
                    item_code="ITEM-READ-DRY-CLEAN",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

    def test_backfill_dry_run_database_read_failed_commit_persists_no_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=764,
                    item_code="ITEM-READ-DRY-COMMIT",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            log_count_before = session.query(LyOperationWageRateCompanyBackfillLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.commit()
            log_count_after = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(log_count_before, log_count_after)

    def test_backfill_execute_database_read_failed_rolls_back_wage_rate_changes(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=765,
                    item_code="ITEM-READ-EXEC-ROLLBACK",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 765).first()
        self.assertIsNotNone(row)
        self.assertIsNone(row.company)
        self.assertEqual(row.status, "active")

    def test_backfill_execute_database_read_failed_writes_no_backfill_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=766,
                    item_code="ITEM-READ-EXEC-NOLOG",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            log_count_before = session.query(LyOperationWageRateCompanyBackfillLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            log_count_after = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(log_count_before, log_count_after)

    def test_backfill_database_read_failed_logs_sanitized_error(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError(
                        "db down [SQL: SELECT * FROM ly_schema.ly_operation_wage_rate] "
                        "[parameters: {'token': 'abc', 'password': '123'}]"
                    )
                return original_query(*entities, **kwargs)

            with self.assertLogs("app.services.workshop_service", level="ERROR") as logs:
                with patch.object(session, "query", side_effect=_query_side_effect):
                    with self.assertRaises(DatabaseReadFailed):
                        service._resolve_backfill_companies(item_code="ITEM-READ-LOG")
        payload = "\n".join(logs.output)
        self.assertIn("workshop_backfill_company_candidates_read_failed", payload)
        self.assertNotIn("[SQL:", payload)
        self.assertNotIn("[parameters:", payload)
        self.assertNotIn("password", payload.lower())
        self.assertNotIn("token", payload.lower())

    def test_backfill_business_ambiguous_still_returns_ambiguous_when_queries_succeed(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=767,
                        item_code="ITEM-READ-AMB-OK",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=768,
                        item_code="ITEM-READ-AMB-OK",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=769,
                        item_code="ITEM-READ-AMB-OK",
                        company="COMP-B",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.9",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertEqual(report.ambiguous_count, 1)

    def test_backfill_business_unresolved_still_returns_unresolved_when_queries_succeed(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=770,
                    item_code="ITEM-READ-UNRES-OK",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-READ-UNRES-OK", item_code="ITEM-READ-UNRES-OK", disabled=False, companies=tuple()),
            ):
                report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertEqual(report.unresolved_count, 1)

    def test_backfill_management_endpoint_propagates_database_read_failed_if_present(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=771,
                    item_code="ITEM-READ-MGMT",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            original_query = session.query

            def _query_side_effect(*entities, **kwargs):
                if len(entities) == 1 and entities[0] is LyOperationWageRate.company:
                    raise SQLAlchemyError("db down [SQL: SELECT]")
                return original_query(*entities, **kwargs)

            with patch.object(session, "query", side_effect=_query_side_effect):
                with self.assertRaises(DatabaseReadFailed):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")

    def test_resolve_backfill_companies_erpnext_item_unavailable_raises_service_unavailable(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError) as raised:
                    service._resolve_backfill_companies(item_code="ITEM-ERPNEXT-UNAV-1")
        self.assertEqual(raised.exception.code, "ERPNEXT_SERVICE_UNAVAILABLE")

    def test_resolve_backfill_companies_erpnext_item_unavailable_does_not_return_empty_candidates(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    _ = service._resolve_backfill_companies(item_code="ITEM-ERPNEXT-UNAV-2")

    def test_backfill_plan_erpnext_item_unavailable_does_not_return_unresolved(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=880,
                    item_code="ITEM-ERPNEXT-UNAV-PLAN",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError) as raised:
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertNotEqual(raised.exception.code, "WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED")

    def test_backfill_plan_erpnext_item_unavailable_does_not_create_blocked_plan_row(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=881,
                    item_code="ITEM-ERPNEXT-UNAV-BLOCK",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            status_before = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 881).one().status
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 881).one()
        self.assertEqual(status_before, "active")
        self.assertEqual(row.status, "active")

    def test_backfill_dry_run_erpnext_item_unavailable_does_not_return_success_report(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=882,
                    item_code="ITEM-ERPNEXT-UNAV-DRY",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")

    def test_backfill_dry_run_erpnext_item_unavailable_leaves_session_clean(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=883,
                    item_code="ITEM-ERPNEXT-UNAV-CLEAN",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)

    def test_backfill_dry_run_erpnext_item_unavailable_commit_persists_no_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=884,
                    item_code="ITEM-ERPNEXT-UNAV-NOLOG",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            log_before = session.query(LyOperationWageRateCompanyBackfillLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            session.commit()
            log_after = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(log_before, log_after)

    def test_backfill_execute_erpnext_item_unavailable_rolls_back_wage_rate_changes(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=885,
                    item_code="ITEM-ERPNEXT-UNAV-EXEC",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 885).one()
        self.assertEqual(row.status, "active")
        self.assertIsNone(row.company)

    def test_backfill_execute_erpnext_item_unavailable_writes_no_backfill_logs(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=886,
                    item_code="ITEM-ERPNEXT-UNAV-EXEC-NOLOG",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            log_before = session.query(LyOperationWageRateCompanyBackfillLog).count()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            log_after = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(log_before, log_after)

    def test_backfill_erpnext_item_unavailable_logs_sanitized_error(self) -> None:
        with self.SessionLocal() as session:
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with self.assertLogs("app.services.workshop_service", level="ERROR") as logs:
                with patch.object(
                    ERPNextJobCardAdapter,
                    "get_item",
                    side_effect=ERPNextServiceUnavailableError(
                        "Authorization bearer abc token=xyz cookie=session password=123 secret=456"
                    ),
                ):
                    with self.assertRaises(ERPNextServiceUnavailableError):
                        service._resolve_backfill_companies(item_code="ITEM-ERPNEXT-UNAV-LOG")
        payload = "\n".join(logs.output).lower()
        self.assertIn("workshop_backfill_item_lookup_unavailable", payload)
        self.assertNotIn("authorization", payload)
        self.assertNotIn("token", payload)
        self.assertNotIn("cookie", payload)
        self.assertNotIn("password", payload)
        self.assertNotIn("secret", payload)

    def test_backfill_item_404_still_returns_company_unresolved_when_query_succeeds(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=887,
                    item_code="ITEM-ERPNEXT-404",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(ERPNextJobCardAdapter, "get_item", return_value=None):
                report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertEqual(report.unresolved_count, 1)

    def test_backfill_item_success_without_company_still_returns_company_unresolved(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=888,
                    item_code="ITEM-ERPNEXT-NOCOMP",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-ERPNEXT-NOCOMP", item_code="ITEM-ERPNEXT-NOCOMP", disabled=False, companies=tuple()),
            ):
                report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertEqual(report.unresolved_count, 1)

    def test_backfill_scoped_wage_rate_unique_company_still_backfills(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=889,
                        item_code="ITEM-SCOPED-UNIQUE",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=890,
                        item_code="ITEM-SCOPED-UNIQUE",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 889).one()
        self.assertEqual(report.backfilled_count, 1)
        self.assertEqual(row.company, "COMP-A")

    def test_backfill_scoped_wage_rate_multiple_companies_still_ambiguous(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=891,
                        item_code="ITEM-SCOPED-AMB",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=892,
                        item_code="ITEM-SCOPED-AMB",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=893,
                        item_code="ITEM-SCOPED-AMB",
                        company="COMP-B",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.9",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
        self.assertEqual(report.ambiguous_count, 1)

    def test_backfill_management_endpoint_propagates_erpnext_service_unavailable_if_present(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=894,
                    item_code="ITEM-MGMT-ERPNEXT-UNAV",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                side_effect=ERPNextServiceUnavailableError("ERPNext unavailable"),
            ):
                with self.assertRaises(ERPNextServiceUnavailableError):
                    service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")

    def test_wage_rate_company_backfill_execute_still_writes_logs_and_updates_rates(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=76,
                        item_code="ITEM-EXEC-OK",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=77,
                        item_code="ITEM-EXEC-OK",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 76).first()
            logs = session.query(LyOperationWageRateCompanyBackfillLog).filter(
                LyOperationWageRateCompanyBackfillLog.wage_rate_id == 76
            ).all()
        self.assertEqual(report.backfilled_count, 1)
        self.assertIsNotNone(row)
        self.assertEqual(row.company, "COMP-A")
        self.assertTrue(logs)

    def test_wage_rate_company_backfill_plan_and_execute_counts_match(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=78,
                        item_code="ITEM-MATCH-1",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=79,
                        item_code="ITEM-MATCH-1",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=80,
                        item_code="ITEM-MATCH-2",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(
                ERPNextJobCardAdapter,
                "get_item",
                return_value=ItemInfo(name="ITEM-MATCH-2", item_code="ITEM-MATCH-2", disabled=False, companies=tuple()),
            ):
                dry_report = service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
                exec_report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
        self.assertEqual(dry_report.total_scanned, exec_report.total_scanned)
        self.assertEqual(dry_report.backfilled_count, exec_report.backfilled_count)
        self.assertEqual(dry_report.blocked_count, exec_report.blocked_count)
        self.assertEqual(dry_report.ambiguous_count, exec_report.ambiguous_count)
        self.assertEqual(dry_report.unresolved_count, exec_report.unresolved_count)

    def test_wage_rate_company_backfill_dry_run_handles_blank_company_without_session_side_effects(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=81,
                        item_code="ITEM-DRY-BLANK",
                        company="",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=82,
                        item_code="ITEM-DRY-BLANK",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            session.commit()
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            service.backfill_wage_rate_company_scope(dry_run=True, operator="tester")
            self.assertEqual(len(session.new), 0)
            self.assertEqual(len(session.dirty), 0)
            self.assertEqual(len(session.deleted), 0)
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 81).first()
            logs = session.query(LyOperationWageRateCompanyBackfillLog).filter(
                LyOperationWageRateCompanyBackfillLog.wage_rate_id == 81
            ).all()
            self.assertIsNotNone(row)
            self.assertEqual(row.company, "")
            self.assertEqual(row.status, "active")
            self.assertEqual(len(logs), 0)

    def test_backfill_normalizes_blank_company_before_resolution(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=70,
                        item_code="ITEM-NORM",
                        company="   ",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=71,
                        item_code="ITEM-NORM",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 70).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.company, "COMP-A")
            logs = (
                session.query(LyOperationWageRateCompanyBackfillLog)
                .filter(LyOperationWageRateCompanyBackfillLog.wage_rate_id == 70)
                .all()
            )
        self.assertEqual(report.backfilled_count, 1)
        self.assertTrue(any(log.result == "normalized_blank_company" for log in logs))
        self.assertTrue(any(log.result == "backfilled" for log in logs))

    def test_backfill_blocks_ambiguous_company_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=20,
                        item_code="ITEM-X",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=21,
                        item_code="ITEM-X",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.8",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=22,
                        item_code="ITEM-X",
                        company="COMP-B",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.9",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 20).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "inactive")
            self.assertIsNone(row.company)
            log = (
                session.query(LyOperationWageRateCompanyBackfillLog)
                .filter(LyOperationWageRateCompanyBackfillLog.wage_rate_id == 20)
                .order_by(LyOperationWageRateCompanyBackfillLog.id.desc())
                .first()
            )
        self.assertEqual(report.ambiguous_count, 1)
        self.assertIsNotNone(log)
        self.assertEqual(log.reason, "WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS")

    def test_backfill_blocks_unresolved_company_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=30,
                    item_code="ITEM-Y",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(ERPNextJobCardAdapter, "get_item", return_value=ItemInfo(name="ITEM-Y", item_code="ITEM-Y", disabled=False, companies=tuple())):
                report = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            row = session.query(LyOperationWageRate).filter(LyOperationWageRate.id == 30).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.status, "inactive")
            log = (
                session.query(LyOperationWageRateCompanyBackfillLog)
                .filter(LyOperationWageRateCompanyBackfillLog.wage_rate_id == 30)
                .order_by(LyOperationWageRateCompanyBackfillLog.id.desc())
                .first()
            )
        self.assertEqual(report.unresolved_count, 1)
        self.assertIsNotNone(log)
        self.assertEqual(log.reason, "WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED")

    def test_backfill_is_idempotent(self) -> None:
        with self.SessionLocal() as session:
            session.add_all(
                [
                    LyOperationWageRate(
                        id=40,
                        item_code="ITEM-I",
                        company=None,
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.7",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                    LyOperationWageRate(
                        id=41,
                        item_code="ITEM-I",
                        company="COMP-A",
                        is_global=False,
                        process_name="sew",
                        wage_rate="0.9",
                        effective_from=date(2025, 1, 1),
                        effective_to=None,
                        status="inactive",
                        created_by="seed",
                    ),
                ]
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            report_first = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            first_log_count = session.query(LyOperationWageRateCompanyBackfillLog).count()
            report_second = service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            second_log_count = session.query(LyOperationWageRateCompanyBackfillLog).count()
        self.assertEqual(report_first.backfilled_count, 1)
        self.assertEqual(report_second.total_scanned, 0)
        self.assertEqual(first_log_count, second_log_count)

    def test_no_active_item_specific_wage_rate_with_null_company_after_migration(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=50,
                    item_code="ITEM-N",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.7",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            service = WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=None))
            with patch.object(ERPNextJobCardAdapter, "get_item", return_value=ItemInfo(name="ITEM-N", item_code="ITEM-N", disabled=False, companies=tuple())):
                service.backfill_wage_rate_company_scope(dry_run=False, operator="tester")
            session.commit()
            count = (
                session.query(LyOperationWageRate)
                .filter(
                    LyOperationWageRate.item_code.isnot(None),
                    ((LyOperationWageRate.company.is_(None)) | (func.trim(LyOperationWageRate.company) == "")),
                    LyOperationWageRate.status == "active",
                )
                .count()
            )
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
