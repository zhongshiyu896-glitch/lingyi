"""A4 FastAPI-native sales order to production plan flow."""

from __future__ import annotations

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
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

        StyleMasterBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
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
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.add(
                LyStyleMaster(
                    company="COMP-A",
                    ys_style_no="DEMO-TEE",
                    ys_style_name_cn="Demo Tee",
                    ys_season="SS",
                    ys_year="2026",
                    ys_brand="LY",
                    ys_style_status="enabled",
                    colors=[{"ys_color_code": "WHITE", "ys_color_name": "白色"}],
                    sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
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
            session.add(
                LyApparelBomItem(
                    id=1,
                    bom_id=1,
                    material_item_code="FABRIC-DEMO",
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0.05"),
                    uom="米",
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
            "items": [
                {
                    "item_code": "DEMO-TEE",
                    "item_name": "Ignored Name",
                    "color": "白色",
                    "size": "M",
                    "qty": 100,
                    "rate": 80,
                    "uom": "件",
                }
            ],
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
        self.assertEqual(list_orders.json()["data"]["items"][0]["ys_material_calc_state"], "待算料")

        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A4-001", headers=self._headers())
        self.assertEqual(detail.status_code, 200)
        detail_data = detail.json()["data"]
        sales_order_item = detail_data["items"][0]["name"]
        self.assertEqual(sales_order_item, "SO-A4-001-001")
        self.assertEqual(detail_data["items"][0]["item_name"], "Demo Tee")
        self.assertEqual(detail_data["items"][0]["color"], "白色")
        self.assertEqual(detail_data["items"][0]["size"], "M")
        self.assertEqual(detail_data["items"][0]["ys_material_calc_state"], "待算料")

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
        plan_id = int(create_plan.json()["data"]["plan_id"])
        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260617-901"
        material_check_request_id = f"req-{material_check_scenario}"

        with patch.dict(os.environ, {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}):
            material_check = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers={**self._headers(), "X-Request-ID": material_check_request_id},
                json={
                    "warehouse": "WH-A",
                    "operation": "material_check",
                    "idempotency_key": f"{material_check_scenario}-idem-material-check-a4-001",
                    "scenario_tag": material_check_scenario,
                    "plan_id": plan_id,
                    "sales_order": "SO-A4-001",
                    "sales_order_item": sales_order_item,
                    "item_code": "DEMO-TEE",
                    "bom_id": 1,
                    "request_id": material_check_request_id,
                },
            )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        self.assertEqual(material_check.json()["data"]["snapshot_count"], 1)

        list_after_material_check = self.client.get(
            "/api/sales-inventory/sales-orders?keyword=SO-A4-001",
            headers=self._headers(),
        )
        self.assertEqual(list_after_material_check.status_code, 200)
        self.assertEqual(list_after_material_check.json()["data"]["items"][0]["ys_material_calc_state"], "已算料")

        with self.SessionLocal() as session:
            order = session.query(LySalesOrder).one()
            item = session.query(LySalesOrderItem).one()
            self.assertEqual(order.status, "planned")
            self.assertEqual(Decimal(str(item.planned_qty)), Decimal("40.000000"))
            self.assertEqual(item.ys_material_calc_state, "已算料")
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("sales_inventory:write", audit_actions)
            self.assertIn("production:plan_create", audit_actions)
            self.assertIn("production:material_check", audit_actions)
