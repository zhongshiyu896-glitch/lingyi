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

    def _seed_plan_for_company(self, *, company: str, plan_id: int, style_no: str, plan_no: str, sales_order: str) -> int:
        with self.SessionLocal() as session:
            session.add(
                LyStyleMaster(
                    id=plan_id * 10,
                    company=company,
                    ys_style_no=style_no,
                    ys_style_name_cn=f"报价款{company}",
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
                id=plan_id * 10 + 1,
                bom_no=f"BOM-{plan_no}",
                company=company,
                item_code=style_no,
                version_no="V1",
                is_default=True,
                status="active",
                created_by="seed",
                updated_by="seed",
            )
            session.add(bom)
            session.add(
                LyApparelBomItem(
                    id=plan_id * 10 + 2,
                    bom_id=plan_id * 10 + 1,
                    material_item_code=f"MAT-{style_no}",
                    qty_per_piece=Decimal("1.00"),
                    loss_rate=Decimal("0.00"),
                    uom="米",
                    remark="unit_price=1",
                )
            )
            plan = LyProductionPlan(
                id=plan_id,
                plan_no=plan_no,
                company=company,
                sales_order=sales_order,
                sales_order_item=f"SOI-{plan_no}",
                customer=f"客户{company}",
                item_code=style_no,
                bom_id=plan_id * 10 + 1,
                bom_version="V1",
                planned_qty=Decimal("10"),
                planned_start_date=date(2026, 6, 26),
                status="planned",
                idempotency_key=f"idem-{plan_no}",
                request_hash=f"hash-{plan_no}",
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

    def test_list_quotes_filters_saved_and_derived_rows_by_company(self) -> None:
        self._seed_plan_for_company(
            company="COMP-Q-OTHER",
            plan_id=913,
            style_no="STYLE-QUOTE-OTHER",
            plan_no="PP-QUOTE-OTHER",
            sales_order="SO-QUOTE-OTHER",
        )
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-COMPANY-CREATE"),
            json=self._payload("IDEM-PROD-QUOTE-COMPANY"),
        )
        self.assertEqual(created.status_code, 200, created.text)

        filtered = self.client.get(
            "/api/production/quotes?company=COMP-Q&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-COMPANY-LIST"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        filtered_items = filtered.json()["data"]["items"]
        self.assertTrue(filtered_items)
        self.assertTrue(all(item["company"] == "COMP-Q" for item in filtered_items))
        self.assertNotIn("PP-QUOTE-OTHER", {item["plan_no"] for item in filtered_items})

        other = self.client.get(
            "/api/production/quotes?company=COMP-Q-OTHER&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-COMPANY-OTHER"),
        )
        self.assertEqual(other.status_code, 200, other.text)
        other_items = other.json()["data"]["items"]
        self.assertEqual(len(other_items), 1)
        self.assertEqual(other_items[0]["company"], "COMP-Q-OTHER")
        self.assertEqual(other_items[0]["source"], "derived")

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

    def test_copy_quote_persists_independent_snapshot_idempotently(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-COPY-CREATE"),
            json=self._payload("IDEM-PROD-QUOTE-COPY-CREATE"),
        )
        self.assertEqual(created.status_code, 200, created.text)
        source = created.json()["data"]
        quote_id = int(source["quote_id"])

        payload = {
            "company": "COMP-Q",
            "quote_no": "QT-SAVED-COPY-001",
            "status": "draft",
            "remark": "复制报价",
            "idempotency_key": "IDEM-PROD-QUOTE-COPY",
        }
        copied = self.client.post(
            f"/api/production/quotes/{quote_id}/copy",
            headers=self._headers(request_id="PROD-QUOTE-COPY"),
            json=payload,
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        copy_data = copied.json()["data"]
        self.assertEqual(copy_data["quote_no"], "QT-SAVED-COPY-001")
        self.assertEqual(copy_data["status"], "draft")
        self.assertNotEqual(copy_data["quote_id"], source["quote_id"])
        self.assertEqual(Decimal(str(copy_data["quote_amount"])), Decimal(str(source["quote_amount"])))
        self.assertEqual(Decimal(str(copy_data["material_cost"])), Decimal(str(source["material_cost"])))

        replay = self.client.post(
            f"/api/production/quotes/{quote_id}/copy",
            headers=self._headers(request_id="PROD-QUOTE-COPY-REPLAY"),
            json=payload,
        )
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["quote_id"], copy_data["quote_id"])

        conflicting = dict(payload)
        conflicting["quote_no"] = "QT-SAVED-COPY-002"
        conflict = self.client.post(
            f"/api/production/quotes/{quote_id}/copy",
            headers=self._headers(request_id="PROD-QUOTE-COPY-CONFLICT"),
            json=conflicting,
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        listed = self.client.get(
            "/api/production/quotes?status=draft&keyword=QT-SAVED-COPY-001&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-COPY-LIST"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["items"][0]["quote_no"], "QT-SAVED-COPY-001")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionQuote).count(), 2)
            self.assertEqual(session.query(LyProductionQuoteOperation).filter_by(operation="copy").count(), 1)
            self.assertGreaterEqual(
                session.query(LyOperationAuditLog).filter_by(resource_type="production_quote", action="copy").count(),
                1,
            )

    def test_void_quote_marks_quote_void_and_blocks_convert(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-VOID-CREATE"),
            json=self._payload("IDEM-PROD-QUOTE-VOID-CREATE"),
        )
        self.assertEqual(created.status_code, 200, created.text)
        quote_id = int(created.json()["data"]["quote_id"])

        payload = {
            "company": "COMP-Q",
            "reason": "客户取消报价",
            "idempotency_key": "IDEM-PROD-QUOTE-VOID",
        }
        voided = self.client.post(
            f"/api/production/quotes/{quote_id}/void",
            headers=self._headers(request_id="PROD-QUOTE-VOID"),
            json=payload,
        )
        self.assertEqual(voided.status_code, 200, voided.text)
        self.assertEqual(voided.json()["data"]["status"], "void")

        replay = self.client.post(
            f"/api/production/quotes/{quote_id}/void",
            headers=self._headers(request_id="PROD-QUOTE-VOID-REPLAY"),
            json=payload,
        )
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["quote_id"], quote_id)

        convert = self.client.post(
            f"/api/production/quotes/{quote_id}/convert-to-order",
            headers=self._headers(request_id="PROD-QUOTE-VOID-CONVERT"),
            json={"company": "COMP-Q", "idempotency_key": "IDEM-PROD-QUOTE-VOID-CONVERT"},
        )
        self.assertEqual(convert.status_code, 400, convert.text)
        self.assertEqual(convert.json()["code"], "PRODUCTION_TRACKING_EXCEPTION_INVALID")

        listed = self.client.get(
            "/api/production/quotes?status=void&page=1&page_size=10",
            headers=self._headers(request_id="PROD-QUOTE-VOID-LIST"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["items"][0]["quote_no"], "QT-SAVED-001")

        with self.SessionLocal() as session:
            quote = session.query(LyProductionQuote).filter_by(id=quote_id).one()
            self.assertEqual(quote.status, "void")
            self.assertEqual(session.query(LyProductionQuoteOperation).filter_by(operation="void").count(), 1)
            self.assertGreaterEqual(
                session.query(LyOperationAuditLog).filter_by(resource_type="production_quote", action="void").count(),
                1,
            )

    def test_quote_copy_void_permission_fail_closed(self) -> None:
        created = self.client.post(
            "/api/production/quotes",
            headers=self._headers(request_id="PROD-QUOTE-CV-F-CREATE"),
            json={**self._payload("IDEM-PROD-QUOTE-CV-F-CREATE"), "quote_no": "QT-SAVED-CVF"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        quote_id = int(created.json()["data"]["quote_id"])

        copy_forbidden = self.client.post(
            f"/api/production/quotes/{quote_id}/copy",
            headers=self._headers(role="Production Viewer", request_id="PROD-QUOTE-COPY-FORBIDDEN"),
            json={"company": "COMP-Q", "idempotency_key": "IDEM-PROD-QUOTE-COPY-F"},
        )
        void_forbidden = self.client.post(
            f"/api/production/quotes/{quote_id}/void",
            headers=self._headers(role="Production Viewer", request_id="PROD-QUOTE-VOID-FORBIDDEN"),
            json={"company": "COMP-Q", "idempotency_key": "IDEM-PROD-QUOTE-VOID-F"},
        )
        self.assertEqual(copy_forbidden.status_code, 403, copy_forbidden.text)
        self.assertEqual(void_forbidden.status_code, 403, void_forbidden.text)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionQuote).count(), 1)
            quote = session.query(LyProductionQuote).filter_by(id=quote_id).one()
            self.assertEqual(quote.status, "quoted")
            self.assertEqual(session.query(LyProductionQuoteOperation).filter(LyProductionQuoteOperation.operation.in_(["copy", "void"])).count(), 0)

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
