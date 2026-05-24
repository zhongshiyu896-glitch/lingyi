"""Wage-rate resource permission tests for TASK-003B."""

from __future__ import annotations

from datetime import date
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"

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
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import CompanyInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class WorkshopWagePermissionTest(unittest.TestCase):
    """Verify wage-rate item/company resource boundary enforcement."""

    WAGE_SCENARIO_TAG = "Z002-WORKSHOP-WAGE-20260524-005"

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
            session.add_all(
                [
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
                    ),
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
                    ),
                    LyOperationWageRate(
                        id=3,
                        item_code=None,
                        company="COMP-A",
                        is_global=True,
                        process_name="sew",
                        wage_rate="0.4",
                        effective_from=date(2026, 1, 1),
                        effective_to=None,
                        status="active",
                        created_by="seed",
                    ),
                ]
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
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationWageRate).filter(LyOperationWageRate.id > 3).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Workshop Wage Clerk", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "wage.perm.user", "X-LY-Dev-Roles": role}
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
    def _scenario_value(cls, value: str) -> str:
        return value if cls.WAGE_SCENARIO_TAG in value else f"{cls.WAGE_SCENARIO_TAG}-{value}"

    @classmethod
    def _wage_payload(
        cls,
        *,
        item_code: str | None,
        company: str | None,
        process_name: str = "sew",
        wage_rate: str = "0.9",
        effective_from: str = "2026-05-01",
        effective_to: str | None = None,
    ) -> dict[str, str | None]:
        item_scope = item_code or "GLOBAL"
        company_scope = company or "GLOBAL"
        return {
            "scenario_tag": cls.WAGE_SCENARIO_TAG,
            "idempotency_key": cls._scenario_value(f"IDEMP-{item_scope}-{company_scope}-{wage_rate}"),
            "source_ref": cls._scenario_value(f"REF-{item_scope}-{company_scope}-{wage_rate}"),
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
    def _headers_for_wage_payload(cls, payload: dict[str, object], role: str = "Workshop Wage Clerk") -> dict[str, str]:
        return cls._headers(role=role, request_id=cls._wage_request_id(payload))

    def _latest_security_log(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        if row is None:
            self.fail("expected security audit row")
        return row

    @staticmethod
    def _perm(*, items: set[str], companies: set[str], unrestricted: bool = False) -> UserPermissionResult:
        return UserPermissionResult(
            source_available=True,
            unrestricted=unrestricted,
            allowed_items=items,
            allowed_companies=companies,
        )

    @staticmethod
    def _active_item(item_code: str, companies: tuple[str, ...]) -> ItemInfo:
        return ItemInfo(name=item_code, item_code=item_code, disabled=False, companies=companies)

    def test_list_filters_out_unauthorized_items(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get("/api/workshop/wage-rates", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(all(row.get("item_code") == "ITEM-B" for row in items))

    def test_wage_rate_list_and_ticket_matching_use_same_company_scope(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=99,
                    item_code="ITEM-B",
                    company=None,
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.65",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get("/api/workshop/wage-rates?item_code=ITEM-B", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertTrue(items)
        self.assertTrue(all(row.get("company") == "COMP-A" for row in items))
        self.assertTrue(all(row.get("id") != 99 for row in items))

    def test_query_unauthorized_item_returns_403_and_audit(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get(
                "/api/workshop/wage-rates?item_code=ITEM-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:wage_rate_read")
        self.assertEqual((row.resource_type or "").upper(), "ITEM")
        self.assertEqual(row.resource_no, "ITEM-A")

    def test_company_only_user_cannot_create_item_wage_rate(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items=set(), companies={"COMP-A"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=self._active_item("ITEM-Z", ("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ):
            payload = self._wage_payload(item_code="ITEM-Z", company="COMP-A", wage_rate="0.8")
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            created = session.query(LyOperationWageRate).filter(LyOperationWageRate.item_code == "ITEM-Z").first()
        self.assertIsNone(created)
        row = self._latest_security_log()
        self.assertEqual(row.action, "workshop:wage_rate_manage")

    def test_item_allowed_but_company_forbidden_returns_403(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-Z"}, companies={"COMP-B"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=self._active_item("ITEM-Z", ("COMP-A",)),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_company",
            return_value=CompanyInfo(name="COMP-A", disabled=False),
        ):
            payload = self._wage_payload(item_code="ITEM-Z", company="COMP-A", wage_rate="0.9")
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            created = session.query(LyOperationWageRate).filter(LyOperationWageRate.item_code == "ITEM-Z").first()
        self.assertIsNone(created)

    def test_wage_rate_create_requires_company_for_item_specific_rate(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-Z"}, companies={"COMP-A"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=self._active_item("ITEM-Z", tuple()),
        ):
            payload = self._wage_payload(item_code="ITEM-Z", company=None, wage_rate="0.9")
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_COMPANY_REQUIRED")
        with self.SessionLocal() as session:
            created = session.query(LyOperationWageRate).filter(LyOperationWageRate.item_code == "ITEM-Z").first()
        self.assertIsNone(created)

    def test_wage_rate_create_rejects_empty_company_for_item_rate(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-Z"}, companies={"COMP-A"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=self._active_item("ITEM-Z", ("COMP-A",)),
        ):
            payload = self._wage_payload(item_code="ITEM-Z", company="", wage_rate="0.9")
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_COMPANY_REQUIRED")

    def test_wage_rate_create_rejects_whitespace_company_for_item_rate(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-Z"}, companies={"COMP-A"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "get_item",
            return_value=self._active_item("ITEM-Z", ("COMP-A",)),
        ):
            payload = self._wage_payload(item_code="ITEM-Z", company="   ", wage_rate="0.9")
            response = self.client.post(
                "/api/workshop/wage-rates",
                headers=self._headers_for_wage_payload(payload),
                json=payload,
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_COMPANY_REQUIRED")

    def test_wage_rate_list_filters_empty_company_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=100,
                    item_code="ITEM-B",
                    company="",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.66",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get("/api/workshop/wage-rates?item_code=ITEM-B", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        ids = {int(row["id"]) for row in response.json()["data"]["items"]}
        self.assertNotIn(100, ids)

    def test_wage_rate_list_filters_whitespace_company_item_rate(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=101,
                    item_code="ITEM-B",
                    company="   ",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.67",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
                )
            )
            session.commit()
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get("/api/workshop/wage-rates?item_code=ITEM-B", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        ids = {int(row["id"]) for row in response.json()["data"]["items"]}
        self.assertNotIn(101, ids)

    def test_wage_rate_list_rejects_blank_company_query(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get("/api/workshop/wage-rates?company=%20%20%20", headers=self._headers())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "WORKSHOP_WAGE_RATE_COMPANY_REQUIRED")

    def test_global_scope_requires_read_all_action(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.get(
                "/api/workshop/wage-rates?is_global=true",
                headers=self._headers(role="Workshop Wage Clerk"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_log()
        self.assertEqual(row.action, "workshop:wage_rate_read_all")

    def test_wage_rate_list_permission_source_unavailable_fail_closed(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            response = self.client.get("/api/workshop/wage-rates", headers=self._headers())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        row = self._latest_security_log()
        self.assertEqual(row.event_type, "PERMISSION_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
