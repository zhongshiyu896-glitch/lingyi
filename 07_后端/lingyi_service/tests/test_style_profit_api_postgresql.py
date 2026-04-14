"""PostgreSQL integration tests for style-profit API idempotency gate (TASK-005E1)."""

from __future__ import annotations

import os
import re
import threading
import unittest
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.main import app
from app.core.exceptions import DatabaseWriteFailed
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitSnapshot
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.style_profit import get_db_session as style_profit_db_dep
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
import app.routers.style_profit as style_profit_router


DESTRUCTIVE_FLAG_ENV = "POSTGRES_TEST_ALLOW_DESTRUCTIVE"
_DB_PATTERNS = (
    re.compile(r".*_test$", re.IGNORECASE),
    re.compile(r"lingyi_test_.*", re.IGNORECASE),
)


def _dsn_or_skip() -> str:
    dsn = str(os.getenv("POSTGRES_TEST_DSN", "") or "").strip()
    if not dsn or dsn.startswith("${"):
        raise unittest.SkipTest("POSTGRES_TEST_DSN is not set; skipping style-profit PostgreSQL integration tests")
    return dsn


def _ensure_destructive_gate(engine, dsn: str) -> None:
    if str(os.getenv(DESTRUCTIVE_FLAG_ENV, "") or "").strip().lower() != "true":
        raise unittest.SkipTest(f"{DESTRUCTIVE_FLAG_ENV} is not true; skipping destructive PostgreSQL tests")

    parsed = make_url(dsn)
    db_name = str(parsed.database or "").strip()
    if not db_name or not any(pattern.fullmatch(db_name) for pattern in _DB_PATTERNS):
        raise unittest.SkipTest("POSTGRES_TEST_DSN database name is not allowed for destructive tests")

    with engine.connect() as conn:
        current_db = str(conn.execute(text("SELECT current_database()")).scalar_one() or "")
    if current_db != db_name:
        raise unittest.SkipTest("current_database mismatch; skipping destructive tests")


@pytest.mark.postgresql
class StyleProfitApiPostgreSQLTest(unittest.TestCase):
    """Guarded PostgreSQL API behavior tests."""

    @classmethod
    def setUpClass(cls) -> None:
        dsn = _dsn_or_skip()
        cls.engine = create_engine(dsn, future=True, pool_pre_ping=True)
        _ensure_destructive_gate(cls.engine, dsn)

        with cls.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS ly_schema CASCADE"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ly_schema"))

        StyleProfitBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[style_profit_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(style_profit_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Style Profit Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "style.pg.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _payload(*, idem: str, to_date: str = "2026-04-30") -> dict[str, object]:
        return {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-PG-001",
            "from_date": "2026-04-01",
            "to_date": to_date,
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": idem,
        }

    @staticmethod
    def _trusted_request(selector) -> StyleProfitSnapshotCreateRequest:
        return StyleProfitSnapshotCreateRequest(
            company=selector.company,
            item_code=selector.item_code,
            sales_order=selector.sales_order,
            from_date=selector.from_date,
            to_date=selector.to_date,
            revenue_mode=selector.revenue_mode,
            include_provisional_subcontract=selector.include_provisional_subcontract,
            formula_version=selector.formula_version,
            idempotency_key=selector.idempotency_key,
            sales_invoice_rows=[],
            sales_order_rows=[
                {
                    "docstatus": 1,
                    "status": "To Bill",
                    "company": selector.company,
                    "sales_order": selector.sales_order,
                    "item_code": selector.item_code,
                    "name": f"{selector.sales_order}-ROW-1",
                    "line_no": "1",
                    "qty": "10",
                    "rate": "10",
                    "base_amount": "100",
                }
            ],
            bom_material_rows=[],
            bom_operation_rows=[],
            stock_ledger_rows=[],
            purchase_receipt_rows=[],
            workshop_ticket_rows=[],
            subcontract_rows=[],
            allowed_material_item_codes=[],
            work_order=selector.work_order,
        )

    def test_same_key_concurrent_create_replays_single_snapshot(self) -> None:
        payload = self._payload(idem="idem-pg-concurrent")
        statuses: list[int] = []

        def _send() -> None:
            resp = self.client.post("/api/reports/style-profit/snapshots", json=payload, headers=self._headers())
            statuses.append(resp.status_code)

        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ):
            threads = [threading.Thread(target=_send), threading.Thread(target=_send)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(len(statuses), 2)
        self.assertTrue(all(code == 200 for code in statuses))
        with self.SessionLocal() as session:
            count = (
                session.query(LyStyleProfitSnapshot)
                .filter(
                    LyStyleProfitSnapshot.company == "COMP-A",
                    LyStyleProfitSnapshot.idempotency_key == "idem-pg-concurrent",
                )
                .count()
            )
            self.assertEqual(count, 1)

    def test_same_key_with_different_payload_returns_conflict(self) -> None:
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ):
            ok = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=self._payload(idem="idem-pg-conflict"),
                headers=self._headers(),
            )
            self.assertEqual(ok.status_code, 200)

            conflict = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=self._payload(idem="idem-pg-conflict", to_date="2026-05-01"),
                headers=self._headers(),
            )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "STYLE_PROFIT_IDEMPOTENCY_CONFLICT")

    def test_commit_failure_rolls_back_and_returns_database_write_failed(self) -> None:
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ), patch.object(style_profit_router, "_commit_or_raise_write_error", side_effect=DatabaseWriteFailed()):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=self._payload(idem="idem-pg-rollback"),
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

        with self.SessionLocal() as session:
            count = session.query(LyStyleProfitSnapshot).filter(LyStyleProfitSnapshot.idempotency_key == "idem-pg-rollback").count()
            self.assertEqual(count, 0)

    def test_resource_permission_forbidden_returns_403_and_security_audit(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(ERPNextPermissionAdapter, "get_user_roles", return_value=["System Manager"]), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"STYLE-B"},
                allowed_companies={"COMP-B"},
            ),
        ):
            response = self.client.get(
                "/api/reports/style-profit/snapshots",
                params={"company": "COMP-A", "item_code": "STYLE-A"},
                headers=self._headers(role="System Manager"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.event_type, "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
