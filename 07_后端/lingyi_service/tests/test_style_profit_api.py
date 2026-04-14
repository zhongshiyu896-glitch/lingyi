"""API baseline tests for style-profit router (TASK-005E1)."""

from __future__ import annotations

from datetime import date
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
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.style_profit import get_db_session as style_profit_db_dep
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
import app.routers.style_profit as style_profit_router


class StyleProfitApiBase(unittest.TestCase):
    """Shared in-memory app wiring for style-profit API tests."""

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
        StyleProfitBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

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
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyStyleProfitSourceMap).delete()
            session.query(LyStyleProfitDetail).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.commit()
            self._seed_snapshot(session)
            session.commit()

    @staticmethod
    def _headers(role: str = "Finance Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "style.profit.user",
            "X-LY-Dev-Roles": role,
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

    @staticmethod
    def _seed_snapshot(session) -> None:
        snapshot = LyStyleProfitSnapshot(
            snapshot_no="SP-API-0001",
            company="COMP-A",
            sales_order="SO-API-001",
            item_code="STYLE-A",
            revenue_status="estimated",
            estimated_revenue_amount=Decimal("100"),
            actual_revenue_amount=Decimal("0"),
            revenue_amount=Decimal("100"),
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            standard_material_cost=Decimal("20"),
            standard_operation_cost=Decimal("10"),
            standard_total_cost=Decimal("30"),
            actual_material_cost=Decimal("15"),
            actual_workshop_cost=Decimal("8"),
            actual_subcontract_cost=Decimal("5"),
            allocated_overhead_amount=Decimal("0"),
            actual_total_cost=Decimal("28"),
            profit_amount=Decimal("72"),
            profit_rate=Decimal("0.72"),
            snapshot_status="complete",
            allocation_status="not_enabled",
            formula_version="STYLE_PROFIT_V1",
            include_provisional_subcontract=False,
            unresolved_count=0,
            idempotency_key="idem-api-001",
            request_hash="hash-api-001",
            created_by="seed",
        )
        session.add(snapshot)
        session.flush()

        detail = LyStyleProfitDetail(
            snapshot_id=int(snapshot.id),
            line_no=1,
            cost_type="revenue",
            source_type="Sales Order",
            source_name="SO-API-001",
            item_code="STYLE-A",
            qty=Decimal("10"),
            unit_rate=Decimal("10"),
            amount=Decimal("100"),
            formula_code="REV_ESTIMATED",
            is_unresolved=False,
            raw_ref={"source": "seed"},
        )
        session.add(detail)
        session.flush()

        session.add(
            LyStyleProfitSourceMap(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                company="COMP-A",
                sales_order="SO-API-001",
                style_item_code="STYLE-A",
                source_item_code="STYLE-A",
                source_system="erpnext",
                source_doctype="Sales Order",
                source_status="to bill",
                source_name="SO-API-001",
                source_line_no="1",
                qty=Decimal("10"),
                unit_rate=Decimal("10"),
                amount=Decimal("100"),
                include_in_profit=True,
                mapping_status="mapped",
                raw_ref={"source": "seed"},
            )
        )


class StyleProfitApiTest(StyleProfitApiBase):
    """Core API path tests."""

    def test_list_requires_company_and_item_code(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SOURCE_READ_FAILED")

    def test_list_success(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            params={"company": "COMP-A", "item_code": "STYLE-A"},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["total"], 1)
        self.assertEqual(payload["data"]["items"][0]["snapshot_no"], "SP-API-0001")

    def test_detail_success_returns_snapshot_details_and_source_maps(self) -> None:
        with self.SessionLocal() as session:
            snapshot_id = int(session.query(LyStyleProfitSnapshot.id).filter(LyStyleProfitSnapshot.snapshot_no == "SP-API-0001").scalar())

        response = self.client.get(
            f"/api/reports/style-profit/snapshots/{snapshot_id}",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["snapshot"]["snapshot_no"], "SP-API-0001")
        self.assertEqual(len(payload["data"]["details"]), 1)
        self.assertEqual(len(payload["data"]["source_maps"]), 1)

    def test_create_rejects_client_source_rows(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-NEW-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-api-create-forbidden",
            "sales_invoice_rows": [{"name": "hack"}],
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN")

    def test_create_fails_closed_when_default_collector_has_no_trusted_source(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-API-FAIL-CLOSED-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-api-create-fail-closed",
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SOURCE_UNAVAILABLE")

        with self.SessionLocal() as session:
            row = (
                session.query(LyStyleProfitSnapshot)
                .filter(
                    LyStyleProfitSnapshot.company == "COMP-A",
                    LyStyleProfitSnapshot.idempotency_key == "idem-api-create-fail-closed",
                )
                .first()
            )
            self.assertIsNone(row)

    def test_create_fails_closed_does_not_call_service(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-API-FAIL-CLOSED-002",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-api-create-fail-closed-no-service",
        }
        with patch.object(style_profit_router.StyleProfitService, "create_snapshot") as create_snapshot:
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SOURCE_UNAVAILABLE")
        create_snapshot.assert_not_called()

    def test_create_fails_closed_when_fake_collector_returns_empty_rows(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-API-FAIL-CLOSED-003",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-api-create-fail-closed-empty-fake",
        }

        def _empty_request(*args, **kwargs) -> StyleProfitSnapshotCreateRequest:
            selector = args[-1]
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
            )

        with patch.object(StyleProfitApiSourceCollector, "collect", side_effect=_empty_request):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_REVENUE_SOURCE_REQUIRED")

    def test_create_success_with_fake_collector(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-API-NEW-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-api-create-success",
        }
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertIn("snapshot_no", body["data"])


if __name__ == "__main__":
    unittest.main()
