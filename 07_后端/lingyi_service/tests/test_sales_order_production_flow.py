"""A4 FastAPI-native sales order to production plan flow."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
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
from app.models.production import LyProductionPlanOperation
from app.models.production import LyProductionPlanMaterial
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


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
        QualityBase.metadata.create_all(bind=cls.engine)
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
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyProductionPlanOperation).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            style = LyStyleMaster(
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
            session.add(style)
            session.flush()
            session.add(
                LyStyleMaster(
                    company="COMP-A",
                    ys_style_no="DEMO-DISABLED",
                    ys_style_name_cn="Disabled Tee",
                    ys_season="SS",
                    ys_year="2026",
                    ys_brand="LY",
                    ys_style_status="disabled",
                    colors=[],
                    sizes=[],
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-DEMO-TEE-V1",
                    company="COMP-A",
                    style_master_id=int(style.id),
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

    def _style_id(self, style_no: str) -> int:
        with self.SessionLocal() as session:
            row = session.query(LyStyleMaster).filter(LyStyleMaster.ys_style_no == style_no).one()
            return int(row.id)

    def _add_stock_entry(
        self,
        *,
        source_id: str,
        purpose: str,
        qty: str,
        business_date: date,
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
    ) -> None:
        created_at = datetime.combine(business_date, datetime.min.time(), timezone.utc)
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose=purpose,
                source_type="manual",
                source_id=source_id,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
                status="pending_outbox",
                created_by="a4.flow.seed",
                created_at=created_at,
                idempotency_key=f"idem-{source_id}",
                event_key=f"event-{source_id}",
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company="COMP-A",
                    item_code="FABRIC-DEMO",
                    qty=Decimal(qty),
                    uom="米",
                    source_warehouse=source_warehouse,
                    target_warehouse=target_warehouse,
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    draft_id=int(draft.id),
                    event_type="warehouse_stock_entry_sync",
                    event_key=f"event-{source_id}",
                    payload={"business_date": business_date.isoformat()},
                    status="in_pending",
                    retry_count=0,
                    created_at=created_at,
                )
            )
            session.commit()

    def test_sales_order_update_resets_material_calc_before_purchase_or_issue(self) -> None:
        order_payload = {
            "company": "COMP-A",
            "customer": "CUST-A",
            "operation": "create_draft",
            "sales_order_no": "SO-A4-RESET-001",
            "source_order_ref": "SO-A4-RESET-001",
            "idempotency_key": "idem-so-a4-reset-001",
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
        self.assertEqual(create_order.status_code, 201, create_order.text)
        draft_id = int(create_order.json()["data"]["id"])
        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A4-RESET-001", headers=self._headers())
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        create_plan = self.client.post(
            "/api/production/plans",
            headers=self._headers(),
            json={
                "sales_order": "SO-A4-RESET-001",
                "sales_order_item": sales_order_item,
                "item_code": "DEMO-TEE",
                "bom_id": 1,
                "planned_qty": 40,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a4-reset-001",
                "company": "COMP-A",
            },
        )
        self.assertEqual(create_plan.status_code, 200, create_plan.text)
        plan_id = int(create_plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260617-903"
        material_check_request_id = f"req-{material_check_scenario}"
        with patch.dict(os.environ, {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}):
            material_check = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers={**self._headers(), "X-Request-ID": material_check_request_id},
                json={
                    "warehouse": "WH-RESET",
                    "operation": "material_check",
                    "idempotency_key": f"{material_check_scenario}-idem-material-check-a4-reset-001",
                    "scenario_tag": material_check_scenario,
                    "plan_id": plan_id,
                    "sales_order": "SO-A4-RESET-001",
                    "sales_order_item": sales_order_item,
                    "item_code": "DEMO-TEE",
                    "bom_id": 1,
                    "request_id": material_check_request_id,
                },
            )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        self.assertEqual(material_check.json()["data"]["snapshot_count"], 1)
        self.assertEqual(Decimal(str(material_check.json()["data"]["items"][0]["shortage_qty"])), Decimal("84.000000"))

        with self.SessionLocal() as session:
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.status), "pending")
            self.assertEqual(str(requirement.sales_order), "SO-A4-RESET-001")

        update_payload = {
            **order_payload,
            "operation": "update_draft",
            "idempotency_key": "idem-so-a4-reset-001-update",
            "delivery_date": "2026-07-05",
            "items": [{**order_payload["items"][0], "qty": 150}],
        }
        update_order = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json=update_payload,
        )
        self.assertEqual(update_order.status_code, 200, update_order.text)
        self.assertEqual(update_order.json()["data"]["items"][0]["ys_material_calc_state"], "待算料")
        self.assertEqual(Decimal(str(update_order.json()["data"]["items"][0]["qty"])), Decimal("150.000000"))

        listed = self.client.get("/api/sales-inventory/sales-orders?keyword=SO-A4-RESET-001", headers=self._headers())
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["items"][0]["ys_material_calc_state"], "待算料")

        with self.SessionLocal() as session:
            item = session.query(LySalesOrderItem).one()
            plan = session.query(LyProductionPlan).one()
            self.assertEqual(item.ys_material_calc_state, "待算料")
            self.assertEqual(str(plan.status), "planned")
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 0)
            self.assertEqual(
                session.query(LyProductionPlanOperation)
                .filter(LyProductionPlanOperation.operation == "material_check")
                .count(),
                0,
            )

    def test_sales_order_material_check_auto_creates_plans_and_purchase_requirements(self) -> None:
        order_payload = {
            "company": "COMP-A",
            "customer": "CUST-A",
            "operation": "create_draft",
            "sales_order_no": "SO-A4-BATCH-MAT-001",
            "source_order_ref": "SO-A4-BATCH-MAT-001",
            "idempotency_key": "idem-so-a4-batch-mat-001",
            "transaction_date": "2026-06-16",
            "delivery_date": "2026-06-30",
            "currency": "CNY",
            "items": [
                {
                    "item_code": "DEMO-TEE",
                    "item_name": "Ignored Name",
                    "color": "白色",
                    "size": "M",
                    "qty": 30,
                    "rate": 80,
                    "uom": "件",
                },
                {
                    "item_code": "DEMO-TEE",
                    "item_name": "Ignored Name",
                    "color": "白色",
                    "size": "M",
                    "qty": 20,
                    "rate": 80,
                    "uom": "件",
                },
            ],
        }
        create_order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=order_payload,
        )
        self.assertEqual(create_order.status_code, 201, create_order.text)

        material_check_payload = {
            "warehouse": "WH-BATCH",
            "company": "COMP-A",
            "planned_start_date": "2026-06-18",
            "operation": "sales_order_material_check",
            "idempotency_key": "idem-sales-order-material-check-a4-batch-001",
        }
        with patch.dict(os.environ, {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}):
            material_check = self.client.post(
                "/api/production/sales-orders/SO-A4-BATCH-MAT-001/material-check",
                headers={**self._headers(), "X-Request-ID": "req-a4-order-material-check"},
                json=material_check_payload,
            )
            material_check_replay = self.client.post(
                "/api/production/sales-orders/SO-A4-BATCH-MAT-001/material-check",
                headers={**self._headers(), "X-Request-ID": "req-a4-order-material-check"},
                json=material_check_payload,
            )

        self.assertEqual(material_check.status_code, 200, material_check.text)
        self.assertEqual(material_check_replay.status_code, 200, material_check_replay.text)
        data = material_check.json()["data"]
        replay_data = material_check_replay.json()["data"]
        self.assertEqual(data["sales_order"], "SO-A4-BATCH-MAT-001")
        self.assertEqual(data["plan_count"], 2)
        self.assertEqual(data["created_plan_count"], 2)
        self.assertEqual(data["snapshot_count"], 2)
        self.assertEqual(Decimal(str(data["required_qty_total"])), Decimal("105.000000"))
        self.assertEqual(Decimal(str(data["available_qty_total"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(data["shortage_qty_total"])), Decimal("105.000000"))
        self.assertEqual(replay_data["plan_count"], 2)
        self.assertEqual(replay_data["created_plan_count"], 2)
        self.assertEqual(replay_data["snapshot_count"], 2)
        self.assertEqual(Decimal(str(replay_data["shortage_qty_total"])), Decimal("105.000000"))
        self.assertEqual(replay_data["items"], data["items"])
        self.assertEqual(
            [Decimal(str(item["planned_qty"])) for item in data["items"]],
            [Decimal("30.000000"), Decimal("20.000000")],
        )
        self.assertTrue(all(item["created_plan"] for item in data["items"]))

        list_after_material_check = self.client.get(
            "/api/sales-inventory/sales-orders?keyword=SO-A4-BATCH-MAT-001",
            headers=self._headers(),
        )
        detail_after_material_check = self.client.get(
            "/api/sales-inventory/sales-orders/SO-A4-BATCH-MAT-001",
            headers=self._headers(),
        )
        self.assertEqual(list_after_material_check.status_code, 200, list_after_material_check.text)
        self.assertEqual(detail_after_material_check.status_code, 200, detail_after_material_check.text)
        self.assertEqual(list_after_material_check.json()["data"]["items"][0]["ys_material_calc_state"], "已算料")
        self.assertEqual(detail_after_material_check.json()["data"]["ys_material_calc_state"], "已算料")
        self.assertEqual(
            [row["ys_material_calc_state"] for row in detail_after_material_check.json()["data"]["items"]],
            ["已算料", "已算料"],
        )

        with self.SessionLocal() as session:
            plans = session.query(LyProductionPlan).order_by(LyProductionPlan.id.asc()).all()
            snapshots = session.query(LyProductionPlanMaterial).order_by(LyProductionPlanMaterial.id.asc()).all()
            requirements = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.id.asc()).all()
            sales_items = session.query(LySalesOrderItem).order_by(LySalesOrderItem.id.asc()).all()
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}

            self.assertEqual(len(plans), 2)
            self.assertEqual(len(snapshots), 2)
            self.assertEqual(len(requirements), 2)
            self.assertEqual([str(plan.status) for plan in plans], ["material_checked", "material_checked"])
            self.assertEqual([item.ys_material_calc_state for item in sales_items], ["已算料", "已算料"])
            self.assertEqual(sum(Decimal(str(row.required_qty)) for row in snapshots), Decimal("105.000000"))
            self.assertEqual(sum(Decimal(str(row.net_required_qty)) for row in requirements), Decimal("105.000000"))
            self.assertEqual({row.status for row in requirements}, {"pending"})
            self.assertEqual({row.sales_order for row in requirements}, {"SO-A4-BATCH-MAT-001"})
            self.assertEqual(session.query(LyProductionPlanOperation).filter(LyProductionPlanOperation.operation == "material_check").count(), 2)
            self.assertEqual(session.query(LyProductionPlanOperation).filter(LyProductionPlanOperation.operation == "sales_order_material_check").count(), 1)
            self.assertIn("production:material_check", audit_actions)

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
        style_id = self._style_id("DEMO-TEE")
        self.assertEqual(sales_order_item, "SO-A4-001-001")
        self.assertEqual(create_order.json()["data"]["items"][0]["style_master_id"], style_id)
        self.assertEqual(detail_data["items"][0]["style_master_id"], style_id)
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
        draft_id = int(create_order.json()["data"]["id"])
        update_payload = {
            "company": "COMP-A",
            "customer": "CUST-A",
            "operation": "update_draft",
            "sales_order_no_or_source_order_ref": "SO-A4-001",
            "idempotency_key": "idem-so-a4-001-update",
            "transaction_date": "2026-06-16",
            "delivery_date": "2026-07-05",
            "currency": "CNY",
            "items": [
                {
                    "item_code": "DEMO-TEE",
                    "item_name": "Ignored Name Again",
                    "color": "白色",
                    "size": "M",
                    "qty": 120,
                    "rate": 80,
                    "uom": "件",
                }
            ],
        }
        update_order = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json=update_payload,
        )
        replay_update = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json=update_payload,
        )
        conflict_update = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json={
                **update_payload,
                "delivery_date": "2026-07-06",
            },
        )
        over_reduce_update = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json={
                **update_payload,
                "idempotency_key": "idem-so-a4-001-update-below-plan",
                "items": [{**update_payload["items"][0], "qty": 30}],
            },
        )
        self.assertEqual(update_order.status_code, 200, update_order.text)
        self.assertEqual(replay_update.status_code, 200, replay_update.text)
        self.assertEqual(conflict_update.status_code, 409, conflict_update.text)
        self.assertEqual(conflict_update.json()["code"], "SALES_ORDER_IDEMPOTENCY_CONFLICT")
        self.assertEqual(over_reduce_update.status_code, 409, over_reduce_update.text)
        self.assertEqual(over_reduce_update.json()["code"], "SALES_ORDER_QTY_BELOW_PLANNED")
        self.assertEqual(update_order.json()["data"]["items"][0]["ys_material_calc_state"], "待算料")
        self.assertEqual(Decimal(str(update_order.json()["data"]["items"][0]["qty"])), Decimal("120.000000"))

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260617-901"
        material_check_request_id = f"req-{material_check_scenario}"
        self._add_stock_entry(
            source_id="A4-OPENING-FABRIC",
            purpose="Material Receipt",
            target_warehouse="WH-A",
            qty="84",
            business_date=date(2026, 6, 17),
        )

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
        snapshot = material_check.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(snapshot["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(snapshot["available_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(snapshot["shortage_qty"])), Decimal("0.000000"))

        material_issue_scenario = "Z003-PROD-PLAN-DETAIL-20260617-902"
        material_issue_request_id = f"req-{material_issue_scenario}"
        material_issue_payload = {
            "warehouse": "WH-A",
            "business_date": "2026-06-18",
            "operation": "material_issue",
            "idempotency_key": f"{material_issue_scenario}-idem-material-issue-a4-001",
            "scenario_tag": material_issue_scenario,
            "plan_id": plan_id,
            "sales_order": "SO-A4-001",
            "sales_order_item": sales_order_item,
            "item_code": "DEMO-TEE",
            "bom_id": 1,
            "request_id": material_issue_request_id,
        }
        with patch.dict(os.environ, {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}):
            material_issue = self.client.post(
                f"/api/production/plans/{plan_id}/material-issue",
                headers={**self._headers(), "X-Request-ID": material_issue_request_id},
                json=material_issue_payload,
            )
            material_issue_replay = self.client.post(
                f"/api/production/plans/{plan_id}/material-issue",
                headers={**self._headers(), "X-Request-ID": material_issue_request_id},
                json=material_issue_payload,
            )
            material_issue_conflict = self.client.post(
                f"/api/production/plans/{plan_id}/material-issue",
                headers={**self._headers(), "X-Request-ID": material_issue_request_id},
                json={**material_issue_payload, "business_date": "2026-06-19"},
            )
        self.assertEqual(material_issue.status_code, 200, material_issue.text)
        self.assertEqual(material_issue_replay.status_code, 200, material_issue_replay.text)
        self.assertEqual(material_issue_conflict.status_code, 409, material_issue_conflict.text)
        self.assertEqual(material_issue_conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")
        self.assertEqual(material_issue.json()["data"]["draft_id"], material_issue_replay.json()["data"]["draft_id"])
        self.assertEqual(material_issue.json()["data"]["stock_entry_status"], "pending_outbox")
        self.assertEqual(material_issue.json()["data"]["items"][0]["material_item_code"], "FABRIC-DEMO")
        self.assertEqual(Decimal(str(material_issue.json()["data"]["items"][0]["qty"])), Decimal("84.000000"))

        material_issue_rows = self.client.get(
            "/api/production/material-issues?company=COMP-A&keyword=SO-A4-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(material_issue_rows.status_code, 200, material_issue_rows.text)
        material_issue_payload = material_issue_rows.json()["data"]
        self.assertEqual(material_issue_payload["total"], 1)
        issue_row = material_issue_payload["items"][0]
        self.assertEqual(issue_row["plan_id"], plan_id)
        self.assertEqual(issue_row["sales_order"], "SO-A4-001")
        self.assertEqual(issue_row["item_code"], "DEMO-TEE")
        self.assertEqual(issue_row["material_item_code"], "FABRIC-DEMO")
        self.assertEqual(issue_row["warehouse"], "WH-A")
        self.assertEqual(issue_row["status"], "issued")
        self.assertEqual(issue_row["stock_entry_status"], "pending_outbox")
        self.assertEqual(issue_row["source_id"], f"production_plan:{plan_id}:material_issue")
        self.assertEqual(Decimal(str(issue_row["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(issue_row["available_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(issue_row["issued_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(issue_row["shortage_qty"])), Decimal("0.000000"))

        ledger_after_issue = self.client.get(
            "/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&item_code=FABRIC-DEMO&page=1&page_size=20",
            headers=self._headers(),
        )
        summary_after_issue = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=WH-A&item_code=FABRIC-DEMO",
            headers=self._headers(),
        )
        self.assertEqual(ledger_after_issue.status_code, 200, ledger_after_issue.text)
        self.assertEqual(summary_after_issue.status_code, 200, summary_after_issue.text)
        ledger_rows = ledger_after_issue.json()["data"]["items"]
        self.assertEqual([Decimal(str(row["actual_qty"])) for row in ledger_rows], [Decimal("84.000000"), Decimal("-84.000000")])
        self.assertEqual([Decimal(str(row["qty_after_transaction"])) for row in ledger_rows], [Decimal("84.000000"), Decimal("0.000000")])
        self.assertEqual(ledger_rows[-1]["voucher_type"], "Stock Entry Draft/Material Issue")
        summary_rows = summary_after_issue.json()["data"]["items"]
        self.assertEqual(len(summary_rows), 1)
        self.assertEqual(Decimal(str(summary_rows[0]["actual_qty"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(summary_rows[0]["projected_qty"])), Decimal("0.000000"))

        list_after_material_check = self.client.get(
            "/api/sales-inventory/sales-orders?keyword=SO-A4-001",
            headers=self._headers(),
        )
        self.assertEqual(list_after_material_check.status_code, 200)
        self.assertEqual(list_after_material_check.json()["data"]["items"][0]["ys_material_calc_state"], "已算料")

        locked_update = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}",
            headers=self._headers(),
            json={
                **update_payload,
                "idempotency_key": "idem-so-a4-001-update-after-issue",
                "delivery_date": "2026-07-06",
                "items": [{**update_payload["items"][0], "qty": 130}],
            },
        )
        self.assertEqual(locked_update.status_code, 409, locked_update.text)
        self.assertEqual(locked_update.json()["code"], "SALES_ORDER_MATERIAL_ISSUED_LOCKED")

        list_after_update = self.client.get(
            "/api/sales-inventory/sales-orders?keyword=SO-A4-001",
            headers=self._headers(),
        )
        detail_after_update = self.client.get("/api/sales-inventory/sales-orders/SO-A4-001", headers=self._headers())
        self.assertEqual(list_after_update.status_code, 200)
        self.assertEqual(detail_after_update.status_code, 200)
        self.assertEqual(list_after_update.json()["data"]["items"][0]["ys_material_calc_state"], "已算料")
        self.assertEqual(detail_after_update.json()["data"]["ys_material_calc_state"], "已算料")
        self.assertEqual(detail_after_update.json()["data"]["items"][0]["ys_material_calc_state"], "已算料")

        with self.SessionLocal() as session:
            order = session.query(LySalesOrder).one()
            item = session.query(LySalesOrderItem).one()
            plan = session.query(LyProductionPlan).one()
            stock_entries = session.query(LyWarehouseStockEntryDraft).order_by(LyWarehouseStockEntryDraft.id.asc()).all()
            issue_entry = [row for row in stock_entries if row.purpose == "Material Issue"][0]
            issue_line = (
                session.query(LyWarehouseStockEntryDraftItem)
                .filter(LyWarehouseStockEntryDraftItem.draft_id == int(issue_entry.id))
                .one()
            )
            self.assertEqual(order.status, "planned")
            self.assertEqual(order.delivery_date, date(2026, 7, 5))
            self.assertEqual(Decimal(str(order.grand_total)), Decimal("9600.000000"))
            self.assertEqual(Decimal(str(item.qty)), Decimal("120.000000"))
            self.assertEqual(Decimal(str(item.planned_qty)), Decimal("40.000000"))
            self.assertEqual(item.ys_material_calc_state, "已算料")
            self.assertEqual(plan.status, "material_issued")
            self.assertEqual(issue_entry.source_type, "production_plan")
            self.assertEqual(issue_entry.source_id, f"production_plan:{plan_id}:material_issue")
            self.assertEqual(issue_entry.source_warehouse, "WH-A")
            self.assertEqual(issue_line.item_code, "FABRIC-DEMO")
            self.assertEqual(Decimal(str(issue_line.qty)), Decimal("84.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("sales_inventory:write", audit_actions)
            self.assertIn("production:plan_create", audit_actions)
            self.assertIn("production:material_check", audit_actions)
            self.assertIn("production:material_issue", audit_actions)

    def test_sales_order_draft_validates_style_master_id(self) -> None:
        style_id = self._style_id("DEMO-TEE")
        disabled_style_id = self._style_id("DEMO-DISABLED")

        valid = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json={
                "company": "COMP-A",
                "customer": "CUST-A",
                "operation": "create_draft",
                "sales_order_no": "SO-A4-STYLE-001",
                "source_order_ref": "SO-A4-STYLE-001",
                "idempotency_key": "idem-so-a4-style-001",
                "transaction_date": "2026-06-16",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": style_id,
                        "item_code": "DEMO-TEE",
                        "item_name": "Ignored Name",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        mismatch = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json={
                "company": "COMP-A",
                "customer": "CUST-A",
                "operation": "create_draft",
                "sales_order_no": "SO-A4-STYLE-MISMATCH",
                "source_order_ref": "SO-A4-STYLE-MISMATCH",
                "idempotency_key": "idem-so-a4-style-mismatch",
                "items": [
                    {
                        "style_master_id": style_id,
                        "item_code": "OTHER-STYLE",
                        "qty": 10,
                        "uom": "件",
                    }
                ],
            },
        )
        disabled = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json={
                "company": "COMP-A",
                "customer": "CUST-A",
                "operation": "create_draft",
                "sales_order_no": "SO-A4-STYLE-DISABLED",
                "source_order_ref": "SO-A4-STYLE-DISABLED",
                "idempotency_key": "idem-so-a4-style-disabled",
                "items": [
                    {
                        "style_master_id": disabled_style_id,
                        "item_code": "DEMO-DISABLED",
                        "qty": 10,
                        "uom": "件",
                    }
                ],
            },
        )

        self.assertEqual(valid.status_code, 201, valid.text)
        self.assertEqual(valid.json()["data"]["items"][0]["style_master_id"], style_id)
        self.assertEqual(valid.json()["data"]["items"][0]["item_name"], "Demo Tee")
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertEqual(disabled.status_code, 409)
        self.assertEqual(disabled.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

    def test_sales_order_cancel_uses_payload_idempotency_key(self) -> None:
        order_payload = {
            "company": "COMP-A",
            "customer": "CUST-A",
            "operation": "create_draft",
            "sales_order_no": "SO-A4-CANCEL-001",
            "source_order_ref": "SO-A4-CANCEL-001",
            "idempotency_key": "idem-so-a4-cancel-create",
            "transaction_date": "2026-06-16",
            "delivery_date": "2026-06-30",
            "currency": "CNY",
            "items": [
                {
                    "item_code": "DEMO-TEE",
                    "color": "白色",
                    "size": "M",
                    "qty": 10,
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
        self.assertEqual(create_order.status_code, 201, create_order.text)
        draft_id = int(create_order.json()["data"]["id"])

        cancel_payload = {
            "company": "COMP-A",
            "operation": "cancel_draft",
            "scenario_tag": "",
            "idempotency_key": "idem-so-a4-cancel-001",
            "sales_order_no_or_source_order_ref": "SO-A4-CANCEL-001",
            "reason": "用户撤单",
        }
        cancel_order = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        replay_cancel = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        conflict_cancel = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel",
            headers=self._headers(),
            json={**cancel_payload, "reason": "重复撤单但内容不同"},
        )
        second_key_cancel = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel",
            headers=self._headers(),
            json={**cancel_payload, "idempotency_key": "idem-so-a4-cancel-002"},
        )

        self.assertEqual(cancel_order.status_code, 200, cancel_order.text)
        self.assertEqual(replay_cancel.status_code, 200, replay_cancel.text)
        self.assertEqual(cancel_order.json()["data"]["id"], replay_cancel.json()["data"]["id"])
        self.assertEqual(cancel_order.json()["data"]["status"], "cancelled")
        self.assertEqual(replay_cancel.json()["data"]["cancel_reason"], "用户撤单")
        self.assertEqual(conflict_cancel.status_code, 409, conflict_cancel.text)
        self.assertEqual(conflict_cancel.json()["code"], "SALES_ORDER_IDEMPOTENCY_CONFLICT")
        self.assertEqual(second_key_cancel.status_code, 409, second_key_cancel.text)
        self.assertEqual(second_key_cancel.json()["code"], "SALES_ORDER_DRAFT_ALREADY_CANCELLED")

        with self.SessionLocal() as session:
            order = session.query(LySalesOrder).one()
            idem = (
                session.query(LySalesOrderIdempotency)
                .filter(
                    LySalesOrderIdempotency.operation == "cancel_draft",
                    LySalesOrderIdempotency.idempotency_key == "idem-so-a4-cancel-001",
                )
                .one()
            )
            audits = session.query(LyOperationAuditLog).order_by(LyOperationAuditLog.id.asc()).all()
            self.assertEqual(order.status, "cancelled")
            self.assertEqual(order.cancel_reason, "用户撤单")
            self.assertEqual(idem.sales_order_id, draft_id)
            self.assertGreaterEqual(len([row for row in audits if row.result == "success"]), 3)
            self.assertTrue(
                any(row.result == "failed" and row.error_code == "SALES_ORDER_IDEMPOTENCY_CONFLICT" for row in audits)
            )
