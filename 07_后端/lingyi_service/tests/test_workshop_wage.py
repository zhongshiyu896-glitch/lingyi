"""Integration tests for workshop wage and wage-rate APIs (TASK-003)."""

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
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import EmployeeInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import CompanyInfo
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.workshop_service import WageRateCompanyBackfillPlanRow
from app.services.workshop_service import WorkshopService


class WorkshopWageApiTest(unittest.TestCase):
    """Cover daily wage formula and wage-rate overlap rules."""

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
    def _headers(role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "wage.user", "X-LY-Dev-Roles": role}

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

    def _register(self, ticket_key: str, qty: str) -> None:
        response = self.client.post(
            "/api/workshop/tickets/register",
            headers=self._headers(),
            json={
                "ticket_key": ticket_key,
                "job_card": "JC-001",
                "employee": "EMP-001",
                "process_name": "sew",
                "color": "black",
                "size": "M",
                "qty": qty,
                "work_date": "2026-04-12",
                "source": "manual",
                "source_ref": "RG",
            },
        )
        self.assertEqual(response.status_code, 200)

    def _reversal(self, ticket_key: str, qty: str) -> None:
        response = self.client.post(
            "/api/workshop/tickets/reversal",
            headers=self._headers(),
            json={
                "ticket_key": ticket_key,
                "job_card": "JC-001",
                "employee": "EMP-001",
                "process_name": "sew",
                "color": "black",
                "size": "M",
                "qty": qty,
                "work_date": "2026-04-12",
                "reason": "fix",
            },
        )
        self.assertEqual(response.status_code, 200)

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
            self.assertEqual(Decimal(str(row["wage_amount"])), Decimal("45.000000"))

            deactivate_old_rate = self.client.post(
                "/api/workshop/wage-rates/1/deactivate",
                headers=self._headers(),
                json={"reason": "new range"},
            )
            self.assertEqual(deactivate_old_rate.status_code, 200)

            create_new_rate = self.client.post(
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
            self.assertEqual(create_new_rate.status_code, 200)

            tickets = self.client.get("/api/workshop/tickets?employee=EMP-001", headers=self._headers())
            self.assertEqual(tickets.status_code, 200)
            first_ticket = tickets.json()["data"]["items"][0]
            self.assertEqual(Decimal(str(first_ticket["unit_wage"])), Decimal("0.500000"))

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
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers(),
                json={
                    "item_code": "ITEM-A",
                    "company": "COMP-A",
                    "process_name": "sew",
                    "wage_rate": "0.6",
                    "effective_from": "2026-02-01",
                    "effective_to": "2026-12-31",
                },
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
