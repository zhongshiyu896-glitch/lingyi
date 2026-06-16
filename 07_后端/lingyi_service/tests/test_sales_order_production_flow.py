"""A4 FastAPI-native sales order to production plan flow."""

from __future__ import annotations

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
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep


class SalesOrderProductionFlowTest(unittest.TestCase):
    """Validate existing order/tracking pages can run on FastAPI-native data."""

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

        SalesOrderBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyApparelBom).delete()
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-DEMO-TEE-V1",
                    item_code="DEMO-TEE",
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "a4.flow.user",
            "X-LY-Dev-Roles": "System Manager",
            "X-Request-ID": "req-a4-flow",
        }

    def test_sales_order_draft_can_create_plan_and_blocks_overplanning(self) -> None:
        order_payload = {
            "company": "COMP-A",
            "customer": "CUST-A",
            "operation": "create_draft",
            "sales_order_no": "SO-A4-001",
            "source_order_ref": "SO-A4-001",
            "idempotency_key": "idem-so-a4-001",
            "transaction_date": "2026-06-16",
            "delivery_date": "2026-06-30",
            "currency": "CNY",
            "items": [{"item_code": "DEMO-TEE", "item_name": "Demo Tee", "qty": 100, "rate": 80, "uom": "件"}],
        }

        create_order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=order_payload,
        )
        replay_order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=order_payload,
        )
        list_orders = self.client.get(
            "/api/sales-inventory/sales-orders?keyword=SO-A4-001",
            headers=self._headers(),
        )

        self.assertEqual(create_order.status_code, 201)
        self.assertEqual(replay_order.status_code, 201)
        self.assertEqual(create_order.json()["data"]["id"], replay_order.json()["data"]["id"])
        self.assertEqual(list_orders.status_code, 200)
        self.assertEqual(list_orders.json()["data"]["total"], 1)
        self.assertEqual(list_orders.json()["data"]["items"][0]["name"], "SO-A4-001")

        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A4-001", headers=self._headers())
        self.assertEqual(detail.status_code, 200)
        sales_order_item = detail.json()["data"]["items"][0]["name"]
        self.assertEqual(sales_order_item, "SO-A4-001-001")

        create_plan = self.client.post(
            "/api/production/plans",
            headers=self._headers(),
            json={
                "sales_order": "SO-A4-001",
                "sales_order_item": sales_order_item,
                "item_code": "DEMO-TEE",
                "bom_id": 1,
                "planned_qty": 40,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a4-001",
                "company": "COMP-A",
            },
        )
        over_plan = self.client.post(
            "/api/production/plans",
            headers=self._headers(),
            json={
                "sales_order": "SO-A4-001",
                "sales_order_item": sales_order_item,
                "item_code": "DEMO-TEE",
                "bom_id": 1,
                "planned_qty": 70,
                "planned_start_date": "2026-06-19",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a4-002",
                "company": "COMP-A",
            },
        )
        list_plans = self.client.get("/api/production/plans?sales_order=SO-A4-001", headers=self._headers())

        self.assertEqual(create_plan.status_code, 200)
        self.assertEqual(over_plan.status_code, 409)
        self.assertEqual(over_plan.json()["code"], "PRODUCTION_PLANNED_QTY_EXCEEDED")
        self.assertEqual(list_plans.status_code, 200)
        self.assertEqual(list_plans.json()["data"]["total"], 1)

        with self.SessionLocal() as session:
            order = session.query(LySalesOrder).one()
            item = session.query(LySalesOrderItem).one()
            self.assertEqual(order.status, "planned")
            self.assertEqual(Decimal(str(item.planned_qty)), Decimal("40.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("sales_inventory:write", audit_actions)
            self.assertIn("production:plan_create", audit_actions)
