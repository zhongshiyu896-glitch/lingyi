"""Tests for production plan CRUD/material/outbox baseline (TASK-004A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.production import Base as ProductionBase
from app.models.production import LyFactoryPacking
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionPlanOperation
from app.models.production import LyProductionNotice
from app.models.production import LyProductionTrackingNodeEvent
from app.models.production import LyProductionWorkOrderLink
from app.models.production import LyProductionWorkOrderOutbox
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.warehouse import Base as WarehouseBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextSalesOrder
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem
from app.services.permission_service import FASTAPI_ROLE_ACTIONS_ENV
from app.services.production_service import ProductionService


class ProductionPlanTest(unittest.TestCase):
    """Validate production plan creation rules and outbox baseline."""

    CREATE_SCENARIO_TAG = "Z003-PROD-PLAN-20260413-001"
    DETAIL_SCENARIO_TAG = "Z003-PROD-PLAN-DETAIL-20260413-001"

    def test_finished_goods_source_parser_preserves_so_prefix(self) -> None:
        self.assertEqual(
            ProductionService._sales_order_from_finished_goods_source("Z003:finished-goods:SO-FG-TRACE-001"),
            "SO-FG-TRACE-001",
        )
        self.assertEqual(
            ProductionService._sales_order_from_finished_goods_source("Z003:finished-goods:fg:so-SO-FG-TRACE-002:pn-PN-001"),
            "SO-FG-TRACE-002",
        )

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
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)
        WarehouseBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=101,
                    bom_no="BOM-PROD-001",
                    company="COMP-A",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1001,
                    bom_id=101,
                    material_item_code="MAT-A",
                    qty_per_piece=Decimal("1.5"),
                    loss_rate=Decimal("0.1"),
                    uom="Nos",
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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        os.environ.pop(FASTAPI_ROLE_ACTIONS_ENV, None)

        with self.SessionLocal() as session:
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyProductionTrackingNodeEvent).delete()
            session.query(LyFactoryPacking).delete()
            session.query(LyProductionPlanOperation).delete()
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyProductionWorkOrderOutbox).delete()
            session.query(LyProductionWorkOrderLink).delete()
            session.query(LyProductionNotice).delete()
            session.query(LyProductionPlan).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrder).delete()
            session.query(LyMasterDataRecord).delete()
            session.commit()
        self._seed_sales_order()

    def test_fastapi_list_plans_does_not_construct_erpnext_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "prod.plan.user": {
                        "company": ["COMP-A"],
                        "item_code": ["ITEM-A"],
                    }
                }
            }
        )

        with patch("app.routers.production.ERPNextProductionAdapter", side_effect=AssertionError("erpnext adapter")):
            response = self.client.get(
                "/api/production/plans?company=COMP-A&item_code=ITEM-A",
                headers=self._headers(role="production:read"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "0")

    def test_fastapi_work_order_worker_dry_run_does_not_construct_erpnext_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ[FASTAPI_ROLE_ACTIONS_ENV] = json.dumps({"roles": {"System Manager": ["production:work_order_worker"]}})
        with patch("app.routers.production.ERPNextProductionAdapter", side_effect=AssertionError("erpnext adapter")):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(role="System Manager"),
                json={"batch_size": 1, "dry_run": True},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "0")
        self.assertTrue(response.json()["data"]["dry_run"])

    def test_fastapi_work_order_worker_sync_is_disabled_even_when_env_enabled(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ[FASTAPI_ROLE_ACTIONS_ENV] = json.dumps({"roles": {"System Manager": ["production:work_order_worker"]}})
        os.environ["PRODUCTION_ENABLE_WORK_ORDER_WORKER_SYNC"] = "true"
        with patch("app.routers.production.ERPNextProductionAdapter", side_effect=AssertionError("erpnext adapter")):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(role="System Manager"),
                json={"batch_size": 1, "dry_run": False},
            )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "INTERNAL_API_DISABLED")

    @staticmethod
    def _request_id(scenario_tag: str) -> str:
        return f"req-{scenario_tag}"

    @staticmethod
    def _headers(
        role: str = "Production Manager",
        *,
        scenario_tag: str | None = None,
    ) -> dict[str, str]:
        tag = scenario_tag or ProductionPlanTest.CREATE_SCENARIO_TAG
        return {
            "X-LY-Dev-User": "prod.plan.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": ProductionPlanTest._request_id(tag),
        }

    @staticmethod
    def _sales_order(*, qty: str = "100", docstatus: int = 1, status: str = "To Deliver") -> ERPNextSalesOrder:
        return ERPNextSalesOrder(
            name="SO-TEST-001",
            docstatus=docstatus,
            status=status,
            company="COMP-A",
            customer="CUST-A",
            items=(
                ERPNextSalesOrderItem(name="SOI-001", item_code="ITEM-A", qty=Decimal(qty)),
            ),
        )

    def _seed_sales_order(
        self,
        *,
        sales_order_no: str = "SO-TEST-001",
        company: str = "COMP-A",
        qty: str = "100",
        status: str = "draft",
        docstatus: int = 1,
        items: list[dict[str, str]] | None = None,
    ) -> None:
        line_rows = items or [
            {
                "sales_order_item": "SOI-001",
                "item_code": "ITEM-A",
                "qty": qty,
                "color": "黑",
                "size": "M",
            }
        ]
        with self.SessionLocal() as session:
            existing = (
                session.query(LySalesOrder)
                .filter(
                    LySalesOrder.company == company,
                    LySalesOrder.sales_order_no == sales_order_no,
                )
                .first()
            )
            if existing is not None:
                session.query(LySalesOrderItem).filter(LySalesOrderItem.sales_order_id == int(existing.id)).delete()
                session.delete(existing)
                session.flush()
            order = LySalesOrder(
                company=company,
                sales_order_no=sales_order_no,
                customer="CUST-A",
                status=status,
                docstatus=docstatus,
                currency="CNY",
                grand_total=Decimal("0"),
                idempotency_key=f"seed-{sales_order_no}",
                request_hash=f"seed-{sales_order_no}",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.flush()
            for index, line in enumerate(line_rows, start=1):
                session.add(
                    LySalesOrderItem(
                        sales_order_id=int(order.id),
                        company=company,
                        line_no=index,
                        sales_order_item=line["sales_order_item"],
                        item_code=line["item_code"],
                        item_name=line.get("item_name") or line["item_code"],
                        color=line.get("color"),
                        size=line.get("size"),
                        qty=Decimal(str(line["qty"])),
                        planned_qty=Decimal("0"),
                        delivered_qty=Decimal("0"),
                        ys_material_calc_state="待算料",
                        uom="Nos",
                    )
                )
            session.commit()

    def _clear_sales_orders(self) -> None:
        with self.SessionLocal() as session:
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrder).delete()
            session.commit()

    def _seed_warehouse_master(self, *, code: str, status: str = "active", company: str = "COMP-A") -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="warehouse",
                    company=company,
                    code=code,
                    name=code,
                    status=status,
                    payload={},
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

    def _seed_orphan_plan(self, *, status: str = "planned", with_ready_snapshot: bool = False) -> int:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                plan_no="PP-ORPHAN-001",
                company="COMP-A",
                sales_order="SO-TEST-001",
                sales_order_item="SOI-001",
                customer="CUST-A",
                item_code="ITEM-A",
                bom_id=101,
                bom_version="v1",
                planned_qty=Decimal("10"),
                status=status,
                idempotency_key=f"orphan-{status}",
                request_hash=f"orphan-{status}",
                created_by="seed",
            )
            session.add(plan)
            session.flush()
            if with_ready_snapshot:
                session.add(
                    LyProductionPlanMaterial(
                        plan_id=int(plan.id),
                        bom_item_id=1001,
                        material_item_code="MAT-A",
                        warehouse="WIP Warehouse - LY",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        required_qty=Decimal("1"),
                        available_qty=Decimal("1"),
                        shortage_qty=Decimal("0"),
                        checked_at=datetime.utcnow(),
                    )
                )
            plan_id = int(plan.id)
            session.commit()
            return plan_id

    def _seed_stock_entry_draft(
        self,
        *,
        source_id: str,
        source_type: str = "finished_goods_inbound",
        status: str = "pending_outbox",
        qty: str = "1",
        item_code: str = "ITEM-A",
        sales_order_item: str | None = "SOI-001",
        idempotency_key: str,
    ) -> None:
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type=source_type,
                source_id=source_id,
                source_warehouse=None,
                target_warehouse="FG-WH-001",
                status=status,
                created_by="seed",
                created_at=datetime.utcnow(),
                idempotency_key=idempotency_key,
                event_key=f"event-{idempotency_key}",
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company="COMP-A",
                    item_code=item_code,
                    qty=Decimal(qty),
                    uom="Nos",
                    source_warehouse=None,
                    target_warehouse="FG-WH-001",
                    sales_order_item=sales_order_item,
                )
            )
            session.commit()

    @staticmethod
    def _payload(
        *,
        idempotency_key: str,
        planned_qty: str = "10",
        planned_start_date: str | None = None,
        scenario_tag: str | None = None,
        sales_order_item: str = "SOI-001",
        bom_id: int = 101,
    ) -> dict[str, str | int]:
        tag = scenario_tag or ProductionPlanTest.CREATE_SCENARIO_TAG
        payload = {
            "sales_order": "SO-TEST-001",
            "sales_order_item": sales_order_item,
            "item_code": "ITEM-A",
            "bom_id": bom_id,
            "planned_qty": planned_qty,
            "scenario_tag": tag,
            "operation": "create",
            "idempotency_key": f"{tag}-{idempotency_key}",
            "company": "COMP-A",
        }
        if planned_start_date:
            payload["planned_start_date"] = planned_start_date
        return payload

    @staticmethod
    def _plan_action_carriers(
        *,
        plan_id: int,
        idempotency_key: str,
        operation: str,
        scenario_tag: str | None = None,
    ) -> dict[str, str | int]:
        tag = scenario_tag or ProductionPlanTest.DETAIL_SCENARIO_TAG
        return {
            "scenario_tag": tag,
            "operation": operation,
            "plan_id": int(plan_id),
            "sales_order": "SO-TEST-001",
            "sales_order_item": "SOI-001",
            "item_code": "ITEM-A",
            "bom_id": 101,
            "idempotency_key": f"{tag}-{idempotency_key}",
            "request_id": ProductionPlanTest._request_id(tag),
        }

    @staticmethod
    def _material_check_payload(
        *,
        plan_id: int,
        idempotency_key: str,
        warehouse: str | None = "WIP Warehouse - LY",
    ) -> dict[str, str | int | None]:
        return {
            **ProductionPlanTest._plan_action_carriers(
                plan_id=plan_id,
                idempotency_key=idempotency_key,
                operation="material_check",
            ),
            "warehouse": warehouse,
        }

    @staticmethod
    def _material_issue_payload(
        *,
        plan_id: int,
        idempotency_key: str,
        warehouse: str = "WIP Warehouse - LY",
    ) -> dict[str, str | int]:
        return {
            **ProductionPlanTest._plan_action_carriers(
                plan_id=plan_id,
                idempotency_key=idempotency_key,
                operation="material_issue",
            ),
            "warehouse": warehouse,
            "business_date": "2026-04-13",
        }

    @staticmethod
    def _create_work_order_payload(*, plan_id: int, idempotency_key: str) -> dict[str, str | int]:
        return {
            **ProductionPlanTest._plan_action_carriers(
                plan_id=plan_id,
                idempotency_key=idempotency_key,
                operation="create_work_order",
            ),
            "fg_warehouse": "FG-WH-001",
            "wip_warehouse": "WIP-WH-001",
            "start_date": "2026-04-13",
        }

    def _set_plan_status(self, *, plan_id: int, status: str) -> None:
        with self.SessionLocal() as session:
            row = session.query(LyProductionPlan).filter(LyProductionPlan.id == int(plan_id)).first()
            self.assertIsNotNone(row)
            row.status = status
            session.commit()

    def test_create_plan_success_and_idempotent_retry(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response_1 = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-001", planned_qty="10"),
            )
            response_2 = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-001", planned_qty="10"),
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        data_1 = response_1.json()["data"]
        data_2 = response_2.json()["data"]
        self.assertEqual(data_1["plan_id"], data_2["plan_id"])
        self.assertEqual(data_1["status"], "planned")
        self.assertEqual(data_1["sales_order_item"], "SOI-001")
        self.assertEqual(data_2["sales_order_item"], "SOI-001")
        self.assertEqual(data_1["color"], "黑")
        self.assertEqual(data_2["color"], "黑")
        self.assertEqual(data_1["size"], "M")
        self.assertEqual(data_2["size"], "M")
        self.assertEqual(Decimal(str(data_1["planned_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(data_2["planned_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(data_1["sales_order_item_qty"])), Decimal("100.000000"))
        self.assertEqual(Decimal(str(data_2["sales_order_item_qty"])), Decimal("100.000000"))

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 1)
            line = session.query(LySalesOrderItem).filter(LySalesOrderItem.sales_order_item == "SOI-001").first()
            self.assertIsNotNone(line)
            self.assertEqual(Decimal(str(line.planned_qty)), Decimal("10.000000"))

    def test_create_sales_order_plan_groups_all_unplanned_lines(self) -> None:
        sales_order_no = "SO-GROUP-001"
        self._seed_sales_order(
            sales_order_no=sales_order_no,
            items=[
                {"sales_order_item": "SO-GROUP-001-S", "item_code": "ITEM-A", "qty": "8", "color": "黑", "size": "S"},
                {"sales_order_item": "SO-GROUP-001-M", "item_code": "ITEM-A", "qty": "9", "color": "黑", "size": "M"},
                {"sales_order_item": "SO-GROUP-001-L", "item_code": "ITEM-A", "qty": "10", "color": "白", "size": "L"},
            ],
        )

        payload = {
            "company": "COMP-A",
            "planned_start_date": "2026-04-13",
            "operation": "sales_order_plan_create",
            "idempotency_key": "idem-sales-order-plan-group-001",
        }
        response = self.client.post(f"/api/production/sales-orders/{sales_order_no}/plans", headers=self._headers(), json=payload)
        replay = self.client.post(f"/api/production/sales-orders/{sales_order_no}/plans", headers=self._headers(), json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        data = response.json()["data"]
        self.assertEqual(replay.json()["data"], data)
        self.assertTrue(data["plan_group_no"].startswith("PPG-"))
        self.assertEqual(data["display_plan_no"], data["plan_group_no"])
        self.assertEqual(data["line_count"], 3)
        self.assertEqual(data["created_plan_count"], 3)
        self.assertEqual(Decimal(str(data["planned_qty"])), Decimal("27.000000"))
        self.assertEqual({item["sales_order_item"] for item in data["items"]}, {"SO-GROUP-001-S", "SO-GROUP-001-M", "SO-GROUP-001-L"})
        self.assertEqual({item["plan_group_no"] for item in data["items"]}, {data["plan_group_no"]})

        list_response = self.client.get(f"/api/production/plans?sales_order={sales_order_no}&page=1&page_size=20", headers=self._headers())
        self.assertEqual(list_response.status_code, 200, list_response.text)
        rows = list_response.json()["data"]["items"]
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["plan_group_no"] for row in rows}, {data["plan_group_no"]})
        self.assertEqual(sum(Decimal(str(row["planned_qty"])) for row in rows), Decimal("27.000000"))

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).filter(LyProductionPlan.sales_order == sales_order_no).count(), 3)
            self.assertEqual(
                {
                    row.sales_order_item: Decimal(str(row.planned_qty))
                    for row in session.query(LySalesOrderItem).filter(LySalesOrderItem.sales_order_item.like("SO-GROUP-001-%")).all()
                },
                {
                    "SO-GROUP-001-S": Decimal("8.000000"),
                    "SO-GROUP-001-M": Decimal("9.000000"),
                    "SO-GROUP-001-L": Decimal("10.000000"),
                },
            )

    def test_create_sales_order_plan_can_select_partial_lines(self) -> None:
        sales_order_no = "SO-GROUP-PART-001"
        self._seed_sales_order(
            sales_order_no=sales_order_no,
            items=[
                {"sales_order_item": "SO-GROUP-PART-001-S", "item_code": "ITEM-A", "qty": "6", "color": "黑", "size": "S"},
                {"sales_order_item": "SO-GROUP-PART-001-M", "item_code": "ITEM-A", "qty": "7", "color": "黑", "size": "M"},
            ],
        )

        response = self.client.post(
            f"/api/production/sales-orders/{sales_order_no}/plans",
            headers=self._headers(),
            json={
                "company": "COMP-A",
                "sales_order_items": ["SO-GROUP-PART-001-M"],
                "planned_start_date": "2026-04-13",
                "operation": "sales_order_plan_create",
                "idempotency_key": "idem-sales-order-plan-partial-001",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["line_count"], 1)
        self.assertEqual(Decimal(str(data["planned_qty"])), Decimal("7.000000"))
        self.assertEqual(data["items"][0]["sales_order_item"], "SO-GROUP-PART-001-M")
        with self.SessionLocal() as session:
            plans = session.query(LyProductionPlan).filter(LyProductionPlan.sales_order == sales_order_no).all()
            self.assertEqual(len(plans), 1)
            self.assertEqual(str(plans[0].sales_order_item), "SO-GROUP-PART-001-M")

    def test_create_plan_uses_company_when_sales_order_number_overlaps(self) -> None:
        sales_order_no = "SO-CROSS-COMPANY-001"
        sales_order_item = f"{sales_order_no}-001"
        self._seed_sales_order(
            sales_order_no=sales_order_no,
            company="COMP-A",
            qty="10",
            items=[{"sales_order_item": sales_order_item, "item_code": "ITEM-A", "qty": "10"}],
        )
        self._seed_sales_order(
            sales_order_no=sales_order_no,
            company="COMP-B",
            qty="20",
            items=[{"sales_order_item": sales_order_item, "item_code": "ITEM-A", "qty": "20"}],
        )
        with self.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=303,
                    bom_no="BOM-PROD-COMP-B",
                    company="COMP-B",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=False,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBomItem(
                    id=3003,
                    bom_id=303,
                    material_item_code="MAT-A",
                    qty_per_piece=Decimal("1"),
                    loss_rate=Decimal("0"),
                    uom="Nos",
                )
            )
            session.add(
                LyProductionPlan(
                    plan_no="PP-CROSS-COMPANY-A",
                    company="COMP-A",
                    sales_order=sales_order_no,
                    sales_order_item=sales_order_item,
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=101,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="seed-cross-company-plan-a",
                    request_hash="seed-cross-company-plan-a",
                    created_by="seed",
                )
            )
            session.commit()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json={
                    **self._payload(
                        idempotency_key="idem-pp-cross-company-b",
                        planned_qty="20",
                        sales_order_item=sales_order_item,
                        bom_id=303,
                    ),
                    "sales_order": sales_order_no,
                    "company": "COMP-B",
                },
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["company"], "COMP-B")
        self.assertEqual(data["sales_order_item"], sales_order_item)
        self.assertEqual(Decimal(str(data["sales_order_item_qty"])), Decimal("20.000000"))
        detail_b = self.client.get(f"/api/production/plans/{data['plan_id']}?company=COMP-B", headers=self._headers())
        self.assertEqual(detail_b.status_code, 200, detail_b.text)
        self.assertEqual(detail_b.json()["data"]["company"], "COMP-B")
        detail_a = self.client.get(f"/api/production/plans/{data['plan_id']}?company=COMP-A", headers=self._headers())
        self.assertEqual(detail_a.status_code, 404, detail_a.text)
        with self.SessionLocal() as session:
            line_a = (
                session.query(LySalesOrderItem)
                .join(LySalesOrder, LySalesOrder.id == LySalesOrderItem.sales_order_id)
                .filter(
                    LySalesOrder.company == "COMP-A",
                    LySalesOrder.sales_order_no == sales_order_no,
                    LySalesOrderItem.sales_order_item == sales_order_item,
                )
                .one()
            )
            line_b = (
                session.query(LySalesOrderItem)
                .join(LySalesOrder, LySalesOrder.id == LySalesOrderItem.sales_order_id)
                .filter(
                    LySalesOrder.company == "COMP-B",
                    LySalesOrder.sales_order_no == sales_order_no,
                    LySalesOrderItem.sales_order_item == sales_order_item,
                )
                .one()
            )
            self.assertEqual(Decimal(str(line_a.planned_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line_b.planned_qty)), Decimal("20.000000"))

    def test_create_plan_remaining_qty_is_scoped_by_sales_order_and_item(self) -> None:
        shared_item = "SOI-SHARED-001"
        self._seed_sales_order(
            sales_order_no="SO-SHARED-A",
            company="COMP-A",
            qty="10",
            items=[{"sales_order_item": shared_item, "item_code": "ITEM-A", "qty": "10"}],
        )
        self._seed_sales_order(
            sales_order_no="SO-SHARED-B",
            company="COMP-A",
            qty="20",
            items=[{"sales_order_item": shared_item, "item_code": "ITEM-A", "qty": "20"}],
        )
        with self.SessionLocal() as session:
            session.add(
                LyProductionPlan(
                    plan_no="PP-SHARED-A",
                    company="COMP-A",
                    sales_order="SO-SHARED-A",
                    sales_order_item=shared_item,
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=101,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="seed-shared-plan-a",
                    request_hash="seed-shared-plan-a",
                    created_by="seed",
                )
            )
            line_a = (
                session.query(LySalesOrderItem)
                .join(LySalesOrder, LySalesOrder.id == LySalesOrderItem.sales_order_id)
                .filter(
                    LySalesOrder.sales_order_no == "SO-SHARED-A",
                    LySalesOrderItem.sales_order_item == shared_item,
                )
                .one()
            )
            line_a.planned_qty = Decimal("10")
            session.commit()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json={
                    **self._payload(
                        idempotency_key="idem-pp-shared-b",
                        planned_qty="20",
                        sales_order_item=shared_item,
                    ),
                    "sales_order": "SO-SHARED-B",
                    "company": "COMP-A",
                },
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["sales_order_item"], shared_item)
        self.assertEqual(Decimal(str(data["sales_order_item_qty"])), Decimal("20.000000"))
        with self.SessionLocal() as session:
            plan_b = session.query(LyProductionPlan).filter(LyProductionPlan.id == int(data["plan_id"])).one()
            self.assertEqual(plan_b.sales_order, "SO-SHARED-B")
            self.assertEqual(plan_b.sales_order_item, shared_item)
            line_a = (
                session.query(LySalesOrderItem)
                .join(LySalesOrder, LySalesOrder.id == LySalesOrderItem.sales_order_id)
                .filter(
                    LySalesOrder.sales_order_no == "SO-SHARED-A",
                    LySalesOrderItem.sales_order_item == shared_item,
                )
                .one()
            )
            line_b = (
                session.query(LySalesOrderItem)
                .join(LySalesOrder, LySalesOrder.id == LySalesOrderItem.sales_order_id)
                .filter(
                    LySalesOrder.sales_order_no == "SO-SHARED-B",
                    LySalesOrderItem.sales_order_item == shared_item,
                )
                .one()
            )
            self.assertEqual(Decimal(str(line_a.planned_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(line_b.planned_qty)), Decimal("20.000000"))

    def test_create_plan_requires_explicit_sales_order_item_even_for_single_line(self) -> None:
        self._seed_sales_order()
        missing_payload = self._payload(idempotency_key="idem-pp-missing-so-item", planned_qty="10")
        missing_payload.pop("sales_order_item")
        null_payload = self._payload(idempotency_key="idem-pp-null-so-item", planned_qty="10")
        null_payload["sales_order_item"] = None

        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            missing_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=missing_payload,
            )
            null_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=null_payload,
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(missing_response.status_code, 422, missing_response.text)
        self.assertEqual(null_response.status_code, 422, null_response.text)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 0)

    def test_create_plan_rejects_missing_native_sales_order_without_adapter(self) -> None:
        self._clear_sales_orders()
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-native-missing", planned_qty="10"),
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 0)

    def test_create_plan_idempotency_conflict_when_payload_changed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            first = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-002", planned_qty="10"),
            )
            second = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-002", planned_qty="11"),
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_plan_idempotency_conflict_when_planned_start_date_changed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            first = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-start-date-conflict",
                    planned_qty="10",
                    planned_start_date="2026-04-13",
                ),
            )
            second = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-start-date-conflict",
                    planned_qty="10",
                    planned_start_date="2026-04-14",
                ),
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_plan_with_planned_start_date_returns_in_list_and_detail(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-with-start-date",
                    planned_qty="10",
                    planned_start_date="2026-04-13",
                ),
            )

        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        list_response = self.client.get(
            "/api/production/plans?page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(list_response.status_code, 200)
        rows = list_response.json()["data"]["items"]
        self.assertTrue(rows)
        matched = next((row for row in rows if int(row["id"]) == plan_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["planned_start_date"], "2026-04-13")

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["planned_start_date"], "2026-04-13")

    def test_list_plans_orders_by_latest_created_then_id(self) -> None:
        new_created_at = datetime(2026, 4, 13, 9, 0, 0)
        old_created_at = datetime(2026, 4, 13, 8, 0, 0)
        with self.SessionLocal() as session:
            session.add(
                LyProductionPlan(
                    plan_no="PP-NEW-LOW-ID",
                    company="COMP-A",
                    sales_order="SO-TEST-001",
                    sales_order_item="SOI-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=101,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="sort-new-low-id",
                    request_hash="sort-new-low-id",
                    created_by="seed",
                    created_at=new_created_at,
                )
            )
            session.flush()
            session.add(
                LyProductionPlan(
                    plan_no="PP-OLD-HIGH-ID",
                    company="COMP-A",
                    sales_order="SO-TEST-001",
                    sales_order_item="SOI-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=101,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="sort-old-high-id",
                    request_hash="sort-old-high-id",
                    created_by="seed",
                    created_at=old_created_at,
                )
            )
            session.flush()
            session.add(
                LyProductionPlan(
                    plan_no="PP-NEW-HIGH-ID",
                    company="COMP-A",
                    sales_order="SO-TEST-001",
                    sales_order_item="SOI-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=101,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="sort-new-high-id",
                    request_hash="sort-new-high-id",
                    created_by="seed",
                    created_at=new_created_at,
                )
            )
            session.commit()

        response = self.client.get("/api/production/plans?company=COMP-A&page=1&page_size=20", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        plan_nos = [row["plan_no"] for row in response.json()["data"]["items"]]
        self.assertEqual(plan_nos[:3], ["PP-NEW-HIGH-ID", "PP-NEW-LOW-ID", "PP-OLD-HIGH-ID"])

    def test_create_plan_accepts_native_draft_sales_order_from_existing_page(self) -> None:
        self._seed_sales_order(status="draft", docstatus=0)
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-003", planned_qty="10"),
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "planned")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 1)

    def test_create_plan_rejects_cancelled_native_sales_order(self) -> None:
        self._seed_sales_order(status="cancelled", docstatus=2)
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            cancelled_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-cancelled", planned_qty="10"),
            )
            adapter_lookup.assert_not_called()
        self.assertEqual(cancelled_response.status_code, 409)
        self.assertEqual(cancelled_response.json()["code"], "PRODUCTION_SO_CLOSED_OR_CANCELLED")

    def test_create_plan_rejects_missing_sales_order_item_carrier(self) -> None:
        so = ERPNextSalesOrder(
            name="SO-TEST-001",
            docstatus=1,
            status="To Deliver",
            company="COMP-A",
            customer="CUST-A",
            items=(
                ERPNextSalesOrderItem(name="SOI-001", item_code="ITEM-A", qty=Decimal("10")),
                ERPNextSalesOrderItem(name="SOI-002", item_code="ITEM-A", qty=Decimal("20")),
            ),
        )
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=so):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-004",
                    planned_qty="10",
                    sales_order_item="SOI-MISSING",
                ),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_ITEM_NOT_FOUND")

    def test_create_plan_rejects_when_planned_qty_exceeded(self) -> None:
        self._seed_sales_order(qty="8")
        with patch.object(
            ERPNextProductionAdapter,
            "get_sales_order",
            return_value=self._sales_order(qty="8"),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-005", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_PLANNED_QTY_EXCEEDED")

    def test_create_plan_rejects_bom_item_mismatch(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=102,
                    bom_no="BOM-PROD-002",
                    company="COMP-A",
                    item_code="ITEM-B",
                    version_no="v1",
                    is_default=False,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json={
                    **self._payload(idempotency_key="idem-pp-bom-mismatch", planned_qty="10"),
                    "bom_id": 102,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_BOM_ITEM_MISMATCH")

    def test_create_plan_database_write_failed_returns_database_write_failed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()), patch(
            "app.routers.production._commit_or_raise_write_error",
            side_effect=DatabaseWriteFailed(),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-db-failed", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

    def test_create_plan_audit_write_failed_returns_audit_write_failed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()), patch(
            "app.routers.production.AuditService.record_success",
            side_effect=AuditWriteFailed(),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-audit-failed", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")

    def test_material_check_and_create_work_order_creates_local_outbox_candidate(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code="MAT-A",
                    name="主料 A",
                    status="active",
                    payload={"material_item_code": "MAT-A", "material_name": "主料 A"},
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-006", planned_qty="12"),
            )

        self.assertEqual(create_response.status_code, 200)
        plan_id = create_response.json()["data"]["plan_id"]

        check_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._material_check_payload(
                plan_id=plan_id,
                idempotency_key="idem-material-check-001",
            ),
        )
        self.assertEqual(check_response.status_code, 200)
        self.assertEqual(check_response.json()["data"]["sales_order"], "SO-TEST-001")
        self.assertEqual(check_response.json()["data"]["sales_order_item"], "SOI-001")
        self.assertEqual(check_response.json()["data"]["item_code"], "ITEM-A")
        self.assertEqual(Decimal(str(check_response.json()["data"]["planned_qty"])), Decimal("12.000000"))
        self.assertEqual(check_response.json()["data"]["snapshot_count"], 1)
        snapshot = check_response.json()["data"]["items"][0]
        self.assertEqual(snapshot["material_item_code"], "MAT-A")
        self.assertEqual(snapshot["warehouse"], "WIP Warehouse - LY")
        self.assertEqual(snapshot["uom"], "Nos")
        self.assertEqual(snapshot["material_name"], "主料 A")
        self.assertEqual(Decimal(str(snapshot["qty_per_piece"])), Decimal("1.500000"))
        self.assertEqual(Decimal(str(snapshot["loss_rate"])), Decimal("0.100000"))
        self.assertEqual(Decimal(str(snapshot["required_qty"])), Decimal("19.800000"))
        self.assertIsNotNone(snapshot["checked_at"])

        detail_after_check = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_after_check.status_code, 200)
        detail_snapshot = detail_after_check.json()["data"]["material_snapshots"][0]
        self.assertEqual(detail_snapshot["material_item_code"], "MAT-A")
        self.assertEqual(detail_snapshot["material_name"], "主料 A")
        self.assertEqual(Decimal(str(detail_snapshot["qty_per_piece"])), Decimal("1.500000"))
        self.assertEqual(Decimal(str(detail_snapshot["loss_rate"])), Decimal("0.100000"))
        self.assertEqual(Decimal(str(detail_snapshot["required_qty"])), Decimal("19.800000"))

        outbox_response = self.client.post(
            f"/api/production/plans/{plan_id}/create-work-order",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._create_work_order_payload(
                plan_id=plan_id,
                idempotency_key="idem-create-wo-001",
            ),
        )
        self.assertEqual(outbox_response.status_code, 200)
        self.assertEqual(outbox_response.json()["code"], "0")
        self.assertGreater(int(outbox_response.json()["data"]["outbox_id"]), 0)
        self.assertEqual(outbox_response.json()["data"]["sync_status"], "pending")
        self.assertTrue(str(outbox_response.json()["data"]["event_key"]).startswith("pwo:"))

        with self.SessionLocal() as session:
            outbox_rows = (
                session.query(LyProductionWorkOrderOutbox)
                .filter(LyProductionWorkOrderOutbox.plan_id == plan_id)
                .all()
            )
            self.assertEqual(len(outbox_rows), 1)
            self.assertEqual(outbox_rows[0].status, "pending")
            snapshot = session.query(LyProductionPlanMaterial).filter_by(plan_id=plan_id).one()
            self.assertEqual(snapshot.uom, "Nos")

    def test_create_work_order_does_not_regress_completed_production_status(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-wo-no-regress", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = int(create_response.json()["data"]["plan_id"])
        self._set_plan_status(plan_id=plan_id, status="production_completed")

        outbox_response = self.client.post(
            f"/api/production/plans/{plan_id}/create-work-order",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._create_work_order_payload(
                plan_id=plan_id,
                idempotency_key="idem-create-wo-no-regress",
            ),
        )
        self.assertEqual(outbox_response.status_code, 200, outbox_response.text)

        with self.SessionLocal() as session:
            plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one()
            self.assertEqual(plan.status, "production_completed")

    def test_plan_detail_returns_work_order_link_fields(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-wo-link-detail", planned_qty="12"),
            )
        plan_id = int(create_response.json()["data"]["plan_id"])

        with self.SessionLocal() as session:
            session.add(
                LyProductionWorkOrderLink(
                    plan_id=plan_id,
                    work_order="WO-DETAIL-001",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    last_synced_at=datetime(2026, 4, 13, 9, 30, 0),
                    created_by="seed",
                )
            )
            session.commit()

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        data = detail_response.json()["data"]
        self.assertEqual(data["work_order"], "WO-DETAIL-001")
        self.assertEqual(data["erpnext_docstatus"], 1)
        self.assertEqual(data["erpnext_status"], "Submitted")
        self.assertEqual(data["sync_status"], "succeeded")
        self.assertIsNotNone(data["last_synced_at"])
        self.assertTrue(data["write_entry_frozen"])
        self.assertIn("受控写门禁", data["write_entry_frozen_reason"])
        self.assertIn("sync-job-cards", data["write_entry_frozen_reason"])
        self.assertIn("create-work-order", data["write_entry_frozen_reason"])
        self.assertNotIn("普通前端仍冻结 create-work-order / sync-job-cards", data["write_entry_frozen_reason"])

    def test_tracking_node_event_persists_idempotently_and_overlays_detail_nodes(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-node-event", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = int(create_response.json()["data"]["plan_id"])
        request_id = "PTR-NODE-20260620-001"
        payload = {
            "company": "COMP-A",
            "node_key": "work_order",
            "node_name": "生产工单",
            "owner": "生产跟单",
            "status": "in_progress",
            "progress": 60,
            "remark": "工单已排入车间",
            "operation": "tracking_node",
            "scenario_tag": "production_tracking_node",
            "idempotency_key": "node-event-idem-001",
            "plan_id": plan_id,
            "sales_order": "SO-TEST-001",
            "sales_order_item": "SOI-001",
            "item_code": "ITEM-A",
            "request_id": request_id,
        }

        response_1 = self.client.post(
            f"/api/production/plans/{plan_id}/tracking-nodes",
            headers={**self._headers(role="Production Manager"), "X-Request-ID": request_id},
            json=payload,
        )
        response_2 = self.client.post(
            f"/api/production/plans/{plan_id}/tracking-nodes",
            headers={**self._headers(role="Production Manager"), "X-Request-ID": request_id},
            json=payload,
        )
        conflict = self.client.post(
            f"/api/production/plans/{plan_id}/tracking-nodes",
            headers={**self._headers(role="Production Manager"), "X-Request-ID": request_id},
            json={**payload, "progress": 80},
        )

        self.assertEqual(response_1.status_code, 200, response_1.text)
        self.assertEqual(response_2.status_code, 200, response_2.text)
        self.assertEqual(response_1.json()["data"]["id"], response_2.json()["data"]["id"])
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            session.add(
                LyProductionPlanMaterial(
                    plan_id=plan_id,
                    bom_item_id=2001,
                    material_item_code="MAT-NODE-SHORT",
                    warehouse="WIP Warehouse - LY",
                    qty_per_piece=Decimal("1"),
                    loss_rate=Decimal("0"),
                    required_qty=Decimal("6"),
                    available_qty=Decimal("0"),
                    shortage_qty=Decimal("6"),
                    checked_at=datetime.utcnow(),
                )
            )
            session.commit()

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        nodes = {row["node_key"]: row for row in detail_response.json()["data"]["tracking_nodes"]}
        self.assertEqual(nodes["work_order"]["status"], "in_progress")
        self.assertEqual(nodes["work_order"]["progress"], 60)
        self.assertEqual(nodes["work_order"]["remark"], "工单已排入车间")
        self.assertEqual(nodes["work_order"]["source_type"], "production_tracking_node")

        list_response = self.client.get(
            "/api/production/plans?company=COMP-A&item_code=ITEM-A",
            headers=self._headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        listed_plan = next(row for row in list_response.json()["data"]["items"] if int(row["id"]) == plan_id)
        tracking_summary = listed_plan["tracking_summary"]
        self.assertEqual(tracking_summary["current_node_key"], "work_order")
        self.assertEqual(tracking_summary["current_node_name"], "生产工单")
        self.assertEqual(tracking_summary["current_node_status"], "in_progress")
        self.assertEqual(tracking_summary["current_node_progress"], 60)
        self.assertEqual(tracking_summary["open_exception_count"], 0)
        self.assertEqual(tracking_summary["blocker_count"], 0)
        self.assertIsNotNone(tracking_summary["latest_tracking_at"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionTrackingNodeEvent).count(), 1)

    def test_tracking_node_done_requires_started_production_and_dirty_nodes_are_visible(self) -> None:
        plan_id = self._seed_orphan_plan(status="material_checked", with_ready_snapshot=True)
        payload = {
            "company": "COMP-A",
            "node_key": "job_card",
            "node_name": "工票进度",
            "owner": "车间",
            "status": "done",
            "progress": 100,
            "remark": "误登记完成",
            "operation": "tracking_node",
            "scenario_tag": "production_tracking_node",
            "idempotency_key": "node-event-before-start",
            "plan_id": plan_id,
            "sales_order": "SO-TEST-001",
            "sales_order_item": "SOI-001",
            "item_code": "ITEM-A",
        }

        blocked = self.client.post(
            f"/api/production/plans/{plan_id}/tracking-nodes",
            headers=self._headers(role="Production Manager"),
            json=payload,
        )
        self.assertEqual(blocked.status_code, 400, blocked.text)
        self.assertEqual(blocked.json()["code"], "PRODUCTION_TRACKING_NODE_INVALID")
        self.assertIn("请先开始生产", blocked.json()["message"])

        direct_start = self.client.post(
            f"/api/production/plans/{plan_id}/tracking-nodes",
            headers=self._headers(role="Production Manager"),
            json={**payload, "node_key": "production_start", "node_name": "开始生产", "status": "in_progress", "progress": 20, "idempotency_key": "node-event-direct-start"},
        )
        self.assertEqual(direct_start.status_code, 400, direct_start.text)
        self.assertIn("不能用节点登记绕过齐料和通知单门禁", direct_start.json()["message"])

        with self.SessionLocal() as session:
            plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one()
            session.add(
                LyProductionTrackingNodeEvent(
                    event_no="PTN-DIRTY-001",
                    plan_id=plan_id,
                    company=str(plan.company),
                    plan_no=str(plan.plan_no),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    item_code=str(plan.item_code),
                    node_key="job_card",
                    node_name="工票进度",
                    owner="车间",
                    status="done",
                    progress=100,
                    remark="历史脏数据",
                    source_type="production_tracking_node",
                    source_ref=str(plan.plan_no),
                    idempotency_key="dirty-node-event",
                    created_by="seed",
                )
            )
            session.commit()

        detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers())
        self.assertEqual(detail.status_code, 200, detail.text)
        nodes = {row["node_key"]: row for row in detail.json()["data"]["tracking_nodes"]}
        self.assertEqual(nodes["job_card"]["status"], "blocked")
        self.assertIn("异常节点", nodes["job_card"]["node_name"])
        self.assertIn("生产开始前", nodes["job_card"]["remark"])

    def test_procurement_readiness_status_is_derived_from_requirement_quantities(self) -> None:
        plan_id = self._seed_orphan_plan(status="material_checked", with_ready_snapshot=True)
        with self.SessionLocal() as session:
            session.add(
                LyMaterialPurchaseRequirement(
                    company="COMP-A",
                    requirement_no="REQ-DERIVED-001",
                    source_type="production_plan",
                    source_id=str(plan_id),
                    source_no="PP-ORPHAN-001",
                    plan_id=plan_id,
                    sales_order="SO-TEST-001",
                    sales_order_item="SOI-001",
                    item_code="ITEM-A",
                    material_item_code="MAT-A",
                    material_name="面料A",
                    warehouse="WIP Warehouse - LY",
                    required_qty=Decimal("10"),
                    available_qty=Decimal("0"),
                    net_required_qty=Decimal("10"),
                    purchased_qty=Decimal("10"),
                    received_qty=Decimal("0"),
                    uom="米",
                    status="purchased",
                    purchase_no="PO-DERIVED-001",
                    created_by="seed",
                )
            )
            session.commit()

        detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers())
        self.assertEqual(detail.status_code, 200, detail.text)
        detail_data = detail.json()["data"]
        self.assertFalse(detail_data["material_ready"])
        self.assertEqual(detail_data["purchase_status"], "purchasing")
        self.assertEqual(detail_data["procurement_status"], "ordered_pending_inbound")
        self.assertEqual(detail_data["procurement_status_label"], "已下单待入库")

        listing = self.client.get("/api/production/plans?company=COMP-A&item_code=ITEM-A", headers=self._headers())
        self.assertEqual(listing.status_code, 200, listing.text)
        listed_plan = next(row for row in listing.json()["data"]["items"] if int(row["id"]) == plan_id)
        self.assertEqual(listed_plan["procurement_status"], "ordered_pending_inbound")

    def test_order_io_quantities_use_real_local_stock_and_delivery_facts(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-real-io", planned_qty="10"),
            )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = int(create_response.json()["data"]["plan_id"])

        with self.SessionLocal() as session:
            plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one()
            plan_no = str(plan.plan_no)
            receipt = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type="finished_goods_inbound",
                source_id=f"Z003-WAREHOUSE-20260616-301:finished-goods:{plan_no}",
                source_warehouse=None,
                target_warehouse="FG-WH-001",
                status="pending_outbox",
                created_by="seed",
                created_at=datetime.utcnow(),
                idempotency_key="idem-real-io-inbound",
                event_key="event-real-io-inbound",
            )
            session.add(receipt)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(receipt.id),
                    company="COMP-A",
                    item_code="ITEM-A",
                    qty=Decimal("6"),
                    uom="Nos",
                    source_warehouse=None,
                    target_warehouse="FG-WH-001",
                )
            )
            session.add(
                LyDeliveryInvoice(
                    company="COMP-A",
                    delivery_note="DN-REAL-IO-001",
                    sales_invoice="SI-REAL-IO-001",
                    sales_order="SO-TEST-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    item_name="ITEM-A",
                    warehouse="FG-WH-001",
                    delivered_qty=Decimal("4"),
                    uom="Nos",
                    rate=Decimal("1"),
                    grand_total=Decimal("4"),
                    paid_amount=Decimal("0"),
                    outstanding_amount=Decimal("4"),
                    posting_date=date(2026, 4, 13),
                    due_date=date(2026, 4, 30),
                    status="submitted",
                    docstatus=1,
                    source_ref="SRC-REAL-IO-001",
                    idempotency_key="idem-real-io-delivery",
                    request_hash="hash-real-io-delivery",
                    scenario_tag="REAL-IO",
                    warehouse_draft_id=None,
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

        response = self.client.get(
            "/api/production/order-io-quantities?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()["data"]["items"]
        matched = next(row for row in rows if int(row["plan_id"]) == plan_id)
        self.assertEqual(Decimal(str(matched["ordered_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(matched["inbound_qty"])), Decimal("6.000000"))
        self.assertEqual(Decimal(str(matched["outbound_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(matched["pending_inbound_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(matched["pending_outbound_qty"])), Decimal("6.000000"))
        self.assertEqual(Decimal(str(matched["inbound_progress"])), Decimal("60.00"))
        self.assertEqual(Decimal(str(matched["outbound_progress"])), Decimal("40.00"))
        self.assertEqual(matched["inbound_ref_count"], 1)
        self.assertEqual(matched["outbound_ref_count"], 1)
        self.assertEqual(matched["inbound_refs"], [plan_no])
        self.assertEqual(matched["outbound_refs"], ["DN-REAL-IO-001/SI-REAL-IO-001"])
        self.assertEqual(matched["io_status"], "in_progress")

    def test_finished_goods_inbound_trace_source_counts_full_and_updates_plan_status(self) -> None:
        plan_id = self._seed_orphan_plan(status="production_completed")
        source_id = (
            "Z003-WAREHOUSE-20260616-301:finished-goods:"
            "fg:so-SO-TEST-001:pn-PN-TRACE-001:pg-PP-ORPHAN-001:li-SOI-001:b-B1:0"
        )
        self._seed_stock_entry_draft(
            source_id=source_id,
            qty="10",
            sales_order_item="SOI-001",
            idempotency_key="idem-fg-trace-full",
        )

        io_response = self.client.get(
            "/api/production/order-io-quantities?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(io_response.status_code, 200, io_response.text)
        io_row = next(row for row in io_response.json()["data"]["items"] if int(row["plan_id"]) == plan_id)
        self.assertEqual(Decimal(str(io_row["inbound_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(io_row["pending_inbound_qty"])), Decimal("0.000000"))
        self.assertEqual(io_row["inbound_ref_count"], 1)

        plans_response = self.client.get(
            "/api/production/plans?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(plans_response.status_code, 200, plans_response.text)
        plan_row = next(row for row in plans_response.json()["data"]["items"] if int(row["id"]) == plan_id)
        self.assertEqual(Decimal(str(plan_row["finished_goods_inbound_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(plan_row["finished_goods_remaining_qty"])), Decimal("0.000000"))
        self.assertEqual(plan_row["finished_goods_inbound_status"], "completed")
        self.assertEqual(plan_row["finished_goods_inbound_ref_count"], 1)

    def test_finished_goods_inbound_partial_excludes_draft_cancelled_and_material_purchase(self) -> None:
        plan_id = self._seed_orphan_plan(status="production_completed")
        active_source = (
            "Z003-WAREHOUSE-20260616-301:finished-goods:"
            "fg:so-SO-TEST-001:pn-PN-TRACE-002:pg-PP-ORPHAN-001:li-SOI-001:b-B2:0"
        )
        draft_source = (
            "Z003-WAREHOUSE-20260616-301:finished-goods:"
            "fg:so-SO-TEST-001:pn-PN-TRACE-002:pg-PP-ORPHAN-001:li-SOI-001:b-B2:draft"
        )
        cancelled_source = (
            "Z003-WAREHOUSE-20260616-301:finished-goods:"
            "fg:so-SO-TEST-001:pn-PN-TRACE-002:pg-PP-ORPHAN-001:li-SOI-001:b-B2:cancelled"
        )
        self._seed_stock_entry_draft(
            source_id=active_source,
            qty="4",
            sales_order_item="SOI-001",
            idempotency_key="idem-fg-trace-partial-active",
        )
        self._seed_stock_entry_draft(
            source_id=draft_source,
            status="draft",
            qty="3",
            sales_order_item="SOI-001",
            idempotency_key="idem-fg-trace-partial-draft",
        )
        self._seed_stock_entry_draft(
            source_id=cancelled_source,
            status="cancelled",
            qty="2",
            sales_order_item="SOI-001",
            idempotency_key="idem-fg-trace-partial-cancelled",
        )
        self._seed_stock_entry_draft(
            source_id="Z003-WAREHOUSE-20260616-301:purchase:PO-SHOULD-NOT-COUNT",
            source_type="material_purchase_order",
            qty="10",
            sales_order_item="SOI-001",
            idempotency_key="idem-fg-trace-partial-material",
        )

        io_response = self.client.get(
            "/api/production/order-io-quantities?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(io_response.status_code, 200, io_response.text)
        io_row = next(row for row in io_response.json()["data"]["items"] if int(row["plan_id"]) == plan_id)
        self.assertEqual(Decimal(str(io_row["inbound_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(io_row["pending_inbound_qty"])), Decimal("6.000000"))
        self.assertEqual(io_row["inbound_ref_count"], 1)

        plans_response = self.client.get(
            "/api/production/plans?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(plans_response.status_code, 200, plans_response.text)
        plan_row = next(row for row in plans_response.json()["data"]["items"] if int(row["id"]) == plan_id)
        self.assertEqual(Decimal(str(plan_row["finished_goods_inbound_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(plan_row["finished_goods_remaining_qty"])), Decimal("6.000000"))
        self.assertEqual(plan_row["finished_goods_inbound_status"], "partial")
        self.assertEqual(plan_row["finished_goods_inbound_ref_count"], 1)

    def test_factory_packing_create_is_idempotent_and_feeds_order_io_quantities(self) -> None:
        plan_id = self._seed_orphan_plan(status="planned")

        payload = {
            "plan_id": plan_id,
            "company": "COMP-A",
            "inbound_qty": "3",
            "outbound_qty": "2",
            "carton_qty": "1",
            "box_spec": "1箱",
            "source_ref": "FP-SMOKE-001",
            "remark": "api smoke factory packing",
            "operation": "factory_packing_create",
            "idempotency_key": "idem-factory-packing-001",
        }

        response = self.client.post("/api/production/factory-packings", headers=self._headers(), json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["plan_id"], plan_id)
        self.assertEqual(data["source_ref"], "FP-SMOKE-001")
        self.assertEqual(Decimal(str(data["inbound_qty"])), Decimal("3.000000"))
        self.assertEqual(Decimal(str(data["outbound_qty"])), Decimal("2.000000"))

        replay_response = self.client.post("/api/production/factory-packings", headers=self._headers(), json=payload)
        self.assertEqual(replay_response.status_code, 200, replay_response.text)
        self.assertEqual(replay_response.json()["data"], data)

        conflict_payload = dict(payload)
        conflict_payload["inbound_qty"] = "4"
        conflict_response = self.client.post("/api/production/factory-packings", headers=self._headers(), json=conflict_payload)
        self.assertEqual(conflict_response.status_code, 409, conflict_response.text)
        self.assertEqual(conflict_response.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        list_response = self.client.get(
            "/api/production/order-io-quantities?keyword=SO-TEST-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        rows = list_response.json()["data"]["items"]
        matched = next(row for row in rows if int(row["plan_id"]) == plan_id)
        self.assertEqual(Decimal(str(matched["inbound_qty"])), Decimal("3.000000"))
        self.assertEqual(Decimal(str(matched["outbound_qty"])), Decimal("2.000000"))
        self.assertEqual(matched["inbound_refs"], ["FP-SMOKE-001"])
        self.assertEqual(matched["outbound_refs"], ["FP-SMOKE-001"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFactoryPacking).count(), 1)
            self.assertEqual(session.query(LyProductionPlanOperation).count(), 1)

    def test_material_check_without_warehouse_uses_default_simplified_mode(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="supplier",
                    company="COMP-A",
                    code="SUP-MAT-A",
                    name="默认物料供应商",
                    status="active",
                    payload={},
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code="MAT-A",
                    name="主料 A",
                    status="active",
                    payload={
                        "material_item_code": "MAT-A",
                        "material_name": "主料 A",
                        "supplier_code": "SUP-MAT-A",
                        "supplier_name": "默认物料供应商",
                    },
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-default-warehouse", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = create_response.json()["data"]["plan_id"]
        payload = self._material_check_payload(
            plan_id=plan_id,
            idempotency_key="idem-material-default-warehouse",
            warehouse=None,
        )
        payload.pop("warehouse", None)

        response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=payload,
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["snapshot_count"], 1)
        snapshot = data["items"][0]
        self.assertEqual(snapshot["warehouse"], "DEFAULT-MATERIAL-WH")
        self.assertEqual(Decimal(str(snapshot["required_qty"])), Decimal("19.800000"))
        self.assertEqual(Decimal(str(snapshot["available_qty"])), Decimal("0"))
        self.assertEqual(Decimal(str(snapshot["shortage_qty"])), Decimal("19.800000"))
        with self.SessionLocal() as session:
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.warehouse), "DEFAULT-MATERIAL-WH")
            self.assertEqual(str(requirement.status), "pending")
            self.assertEqual(Decimal(str(requirement.required_qty)), Decimal("19.800000"))
            self.assertEqual(Decimal(str(requirement.available_qty)), Decimal("0"))
            self.assertEqual(Decimal(str(requirement.net_required_qty)), Decimal("19.800000"))
            self.assertEqual(str(requirement.material_name), "主料 A")
            self.assertEqual(str(requirement.supplier_name), "默认物料供应商")

    def test_material_check_rejects_inactive_warehouse_master(self) -> None:
        warehouse = "WIP-OFFLINE-001"
        self._seed_warehouse_master(code=warehouse, status="inactive")
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-inactive-warehouse", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = create_response.json()["data"]["plan_id"]

        response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._material_check_payload(
                plan_id=plan_id,
                idempotency_key="idem-material-inactive-warehouse",
                warehouse=warehouse,
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_BOM_NOT_ACTIVE")
        self.assertIn("仓库主数据不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 0)

    def test_material_check_rejects_orphan_plan_without_requirements(self) -> None:
        self._clear_sales_orders()
        plan_id = self._seed_orphan_plan()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
                json=self._material_check_payload(
                    plan_id=plan_id,
                    idempotency_key="idem-material-orphan-plan",
                ),
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 0)

    def test_material_check_rejects_mismatched_sales_order_item_carrier(self) -> None:
        self._seed_sales_order(
            items=[
                {"sales_order_item": "SOI-001", "item_code": "ITEM-A", "qty": "100", "color": "黑", "size": "M"},
                {"sales_order_item": "SOI-002", "item_code": "ITEM-A", "qty": "50", "color": "黑", "size": "L"},
            ],
        )
        create_response = self.client.post(
            "/api/production/plans",
            headers=self._headers(),
            json=self._payload(idempotency_key="idem-pp-material-mismatch-carrier", planned_qty="12"),
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        plan_id = int(create_response.json()["data"]["plan_id"])

        payload = self._material_check_payload(
            plan_id=plan_id,
            idempotency_key="idem-material-mismatch-carrier",
        )
        payload["sales_order_item"] = "SOI-002"
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
                json=payload,
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")
        self.assertIn("mismatched_business_carrier", response.json()["message"])
        with self.SessionLocal() as session:
            plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one()
            self.assertEqual(plan.status, "planned")
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 0)

    def test_material_issue_rejects_orphan_plan_without_stock_outbox(self) -> None:
        self._clear_sales_orders()
        plan_id = self._seed_orphan_plan(status="material_checked", with_ready_snapshot=True)

        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            response = self.client.post(
                f"/api/production/plans/{plan_id}/material-issue",
                headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
                json=self._material_issue_payload(
                    plan_id=plan_id,
                    idempotency_key="idem-material-issue-orphan-plan",
                ),
            )
            adapter_lookup.assert_not_called()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 0)
            self.assertEqual(session.query(LyWarehouseStockEntryOutboxEvent).count(), 0)

    def test_material_check_replays_idempotently_without_recomputing(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-idem", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])
        payload = self._material_check_payload(
            plan_id=plan_id,
            idempotency_key="idem-material-check-replay",
        )

        first_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=payload,
        )
        self.assertEqual(first_response.status_code, 200, first_response.text)
        with self.SessionLocal() as session:
            operation = session.query(LyProductionPlanOperation).filter_by(plan_id=plan_id).one()
            legacy_response = dict(operation.response_json)
            for key in ("sales_order", "sales_order_item", "item_code", "color", "size", "planned_qty"):
                legacy_response.pop(key, None)
            operation.response_json = legacy_response
            session.commit()

        self._set_plan_status(plan_id=plan_id, status="cancelled")
        replay_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=payload,
        )
        self.assertEqual(replay_response.status_code, 200, replay_response.text)
        self.assertEqual(replay_response.json()["data"], first_response.json()["data"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlanOperation).count(), 1)
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 1)

    def test_material_check_same_key_different_warehouse_conflicts(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-conflict", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        first_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._material_check_payload(
                plan_id=plan_id,
                idempotency_key="idem-material-check-conflict",
                warehouse="WH-A",
            ),
        )
        conflict_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._material_check_payload(
                plan_id=plan_id,
                idempotency_key="idem-material-check-conflict",
                warehouse="WH-B",
            ),
        )
        self.assertEqual(first_response.status_code, 200, first_response.text)
        self.assertEqual(conflict_response.status_code, 409, conflict_response.text)
        self.assertEqual(conflict_response.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_material_check_allows_frozen_status_whitelist(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-status-whitelist", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        allowed_statuses = [
            "planned",
            "material_checked",
            "work_order_pending",
            "work_order_created",
        ]
        for status in allowed_statuses:
            self._set_plan_status(plan_id=plan_id, status=status)
            response = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
                json=self._material_check_payload(
                    plan_id=plan_id,
                    idempotency_key=f"idem-material-status-{status}",
                ),
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["code"], "0")
            self.assertEqual(response.json()["data"]["plan_id"], plan_id)

    def test_material_check_rejects_status_outside_whitelist(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-status-invalid", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        self._set_plan_status(plan_id=plan_id, status="cancelled")
        response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json=self._material_check_payload(
                plan_id=plan_id,
                idempotency_key="idem-material-status-invalid",
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_MATERIAL_CHECK_STATUS_INVALID")
        self.assertEqual(response.json()["message"], "当前生产计划状态不允许执行物料检查")

    def test_create_work_order_candidate_returns_unified_envelope(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-create-wo-required", planned_qty="12"),
            )
        plan_id = create_response.json()["data"]["plan_id"]

        frozen_response = self.client.post(
            f"/api/production/plans/{plan_id}/create-work-order",
            headers=self._headers(scenario_tag=self.DETAIL_SCENARIO_TAG),
            json={
                **self._create_work_order_payload(
                    plan_id=plan_id,
                    idempotency_key="idem-create-wo-frozen",
                ),
                "fg_warehouse": "FG-WH",
                "wip_warehouse": "WIP-WH",
                "start_date": "2026-04-13",
            },
        )
        self.assertEqual(frozen_response.status_code, 200)
        payload = frozen_response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["message"], "success")
        self.assertIn("data", payload)
        self.assertGreater(int(payload["data"]["outbox_id"]), 0)

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertTrue(detail["write_entry_frozen"])
        self.assertIn("受控写门禁", detail["write_entry_frozen_reason"])
        self.assertIn("sync-job-cards", detail["write_entry_frozen_reason"])
        self.assertIn("create-work-order", detail["write_entry_frozen_reason"])
        self.assertNotIn("普通前端仍冻结 create-work-order / sync-job-cards", detail["write_entry_frozen_reason"])


if __name__ == "__main__":
    unittest.main()
