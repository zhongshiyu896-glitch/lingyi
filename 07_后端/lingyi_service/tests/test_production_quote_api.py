"""API tests for FastAPI-native production quote writes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionQuote
from app.models.production import LyProductionQuoteOperation
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionQuoteApiTest(unittest.TestCase):
    """Validate quote create/list writes for the existing product quote page."""

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
        StyleMasterBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LyProductionQuoteOperation).delete()
            session.query(LyProductionQuote).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrder).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyStyleMaster).delete()
            session.commit()
        self.plan_id = self._seed_plan()

    @staticmethod
    def _headers(role: str = "Production Manager", request_id: str = "PROD-QUOTE-REQ") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "prod.quote.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    def _seed_plan(self) -> int:
        with self.SessionLocal() as session:
            session.add(
                LyStyleMaster(
                    id=900,
                    company="COMP-Q",
                    ys_style_no="STYLE-QUOTE-001",
                    ys_style_name_cn="报价款",
                    ys_season="夏",
                    ys_year="2026",
                    ys_brand="LY",
                    ys_style_status="enabled",
                    colors=[],
                    sizes=[],
                    created_by="seed",
                    updated_by="seed",
                )
            )
            bom = LyApparelBom(
                id=901,
                bom_no="BOM-QUOTE-001",
                company="COMP-Q",
                item_code="STYLE-QUOTE-001",
                version_no="V1",
                is_default=True,
                status="active",
                created_by="seed",
                updated_by="seed",
            )
            session.add(bom)
            session.add(
                LyApparelBomItem(
                    id=902,
                    bom_id=901,
                    material_item_code="MAT-QUOTE-001",
                    qty_per_piece=Decimal("1.50"),
                    loss_rate=Decimal("0.10"),
                    uom="米",
                    remark="unit_price=8.5",
                )
            )
            plan = LyProductionPlan(
                id=903,
                plan_no="PP-QUOTE-001",
                company="COMP-Q",
                sales_order="SO-QUOTE-001",
                sales_order_item="SOI-QUOTE-001",
                customer="客户Q",
                item_code="STYLE-QUOTE-001",
                bom_id=901,
                bom_version="V1",
                planned_qty=Decimal("20"),
                planned_start_date=date(2026, 6, 25),
                status="planned",
                idempotency_key="idem-plan-quote",
                request_hash="hash-plan-quote",
                created_by="seed",
            )
            session.add(plan)
            session.commit()
            return int(plan.id)

    def _payload(self, idem: str) -> dict[str, object]:
        return {
            "company": "COMP-Q",
            "plan_id": self.plan_id,
            "quote_no": "QT-SAVED-001",
            "quote_qty": 20,
            "labor_cost": 30,
            "management_fee": 12,
            "valid_until": "2026-07-01",
            "status": "quoted",
            "remark": "首版报价",
            "idempotency_key": idem,
        }

    def test_create_quote_persists_calculated_material_cost_and_lists_saved_quote(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CREATE"),
            json=self._payload("IDEM-PROD-QUOTE-C"),
        )
        self.assertEqual(created.status_code, 200, created.text)
        data = created.json()["data"]
        self.assertEqual(created.json()["code"], "0")
        self.assertEqual(data["quote_no"], "QT-SAVED-001")
        self.assertEqual(data["source"], "saved")
        self.assertEqual(Decimal(str(data["material_cost"])), Decimal("280.500000"))
        self.assertEqual(Decimal(str(data["labor_cost"])), Decimal("30.000000"))
        self.assertEqual(Decimal(str(data["management_fee"])), Decimal("12.000000"))
        self.assertEqual(Decimal(str(data["quote_amount"])), Decimal("322.500000"))

        retry = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CREATE-RETRY"),
            json=self._payload("IDEM-PROD-QUOTE-C"),
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["data"]["quote_id"], data["quote_id"])

        listed = self.client.get(
            "/api/production/quotes?keyword=QT-SAVED-001&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-LIST"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        items = listed.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quote_no"], "QT-SAVED-001")
        self.assertEqual(items[0]["source"], "saved")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionQuote).count(), 1)
            self.assertEqual(session.query(LyProductionQuoteOperation).count(), 1)
            self.assertGreaterEqual(session.query(LyOperationAuditLog).filter_by(resource_type="production_quote").count(), 1)

    def test_quote_create_idempotency_conflict_and_permission_fail_closed(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CREATE-2"),
            json=self._payload("IDEM-PROD-QUOTE-CONFLICT"),
        )
        self.assertEqual(created.status_code, 200, created.text)

        conflicting = self._payload("IDEM-PROD-QUOTE-CONFLICT")
        conflicting["labor_cost"] = 31
        conflict = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CONFLICT"),
            json=conflicting,
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        forbidden = self.client.post(
            "/api/production/quotes",
            headers=self._headers(role="Production Viewer", request_id="PROD-QUOTE-FORBIDDEN"),
            json={**self._payload("IDEM-PROD-QUOTE-F"), "quote_no": "QT-SAVED-F"},
        )
        self.assertEqual(forbidden.status_code, 403, forbidden.text)

    def test_convert_quote_creates_sales_order_draft_and_marks_converted_idempotently(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT-CREATE"),
            json=self._payload("IDEM-PROD-QUOTE-CONVERT-CREATE"),
        )
        self.assertEqual(created.status_code, 200, created.text)
        quote_id = int(created.json()["data"]["quote_id"])

        payload = {
            "company": "COMP-Q",
            "sales_order_no": "SO-FROM-QT-001",
            "transaction_date": "2026-06-30",
            "delivery_date": "2026-07-10",
            "idempotency_key": "IDEM-PROD-QUOTE-CONVERT",
        }
        converted = self.client.post(
            f"/api/production/quotes/{quote_id}/convert-to-order",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT"),
            json=payload,
        )
        self.assertEqual(converted.status_code, 200, converted.text)
        body = converted.json()
        self.assertEqual(body["code"], "0")
        data = body["data"]
        self.assertEqual(data["quote"]["status"], "converted")
        self.assertEqual(data["sales_order"]["sales_order_no"], "SO-FROM-QT-001")
        self.assertEqual(data["sales_order"]["source_order_ref"], "QUOTE-QT-SAVED-001")
        self.assertEqual(data["sales_order"]["items"][0]["item_code"], "STYLE-QUOTE-001")
        self.assertEqual(Decimal(str(data["sales_order"]["items"][0]["qty"])), Decimal("20.000000"))
        self.assertEqual(Decimal(str(data["sales_order"]["items"][0]["rate"])), Decimal("16.125000"))

        retry = self.client.post(
            f"/api/production/quotes/{quote_id}/convert-to-order",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT-RETRY"),
            json=payload,
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["data"]["sales_order"]["id"], data["sales_order"]["id"])

        conflict_payload = dict(payload)
        conflict_payload["sales_order_no"] = "SO-FROM-QT-002"
        conflict = self.client.post(
            f"/api/production/quotes/{quote_id}/convert-to-order",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT-CONFLICT"),
            json=conflict_payload,
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        listed = self.client.get(
            "/api/production/quotes?status=converted&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT-LIST"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["items"][0]["quote_no"], "QT-SAVED-001")

        with self.SessionLocal() as session:
            quote = session.query(LyProductionQuote).filter_by(id=quote_id).one()
            self.assertEqual(quote.status, "converted")
            self.assertEqual(session.query(LySalesOrder).count(), 1)
            self.assertEqual(session.query(LySalesOrderItem).count(), 1)
            self.assertEqual(session.query(LySalesOrderIdempotency).count(), 1)
            self.assertEqual(session.query(LyProductionQuoteOperation).count(), 2)
            self.assertGreaterEqual(
                session.query(LyOperationAuditLog).filter_by(resource_type="production_quote", action="convert").count(),
                1,
            )

    def test_quote_convert_permission_fail_closed(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CONVERT-F-CREATE"),
            json={**self._payload("IDEM-PROD-QUOTE-CONVERT-F-CREATE"), "quote_no": "QT-SAVED-FC"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        quote_id = int(created.json()["data"]["quote_id"])

        forbidden = self.client.post(
            f"/api/production/quotes/{quote_id}/convert-to-order",
            headers=self._headers(role="Production Viewer", request_id="PROD-QUOTE-CONVERT-FORBIDDEN"),
            json={"company": "COMP-Q", "idempotency_key": "IDEM-PROD-QUOTE-CONVERT-F"},
        )
        self.assertEqual(forbidden.status_code, 403, forbidden.text)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySalesOrder).count(), 0)
            quote = session.query(LyProductionQuote).filter_by(id=quote_id).one()
            self.assertEqual(quote.status, "quoted")
