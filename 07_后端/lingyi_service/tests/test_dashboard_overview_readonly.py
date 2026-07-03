"""Dashboard overview read-only baseline tests (TASK-060A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import distinct
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import DASHBOARD_READ
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.sales_order import LySalesPaymentEntry
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.warehouse import Base as WarehouseBase
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.dashboard import get_db_session as dashboard_db_dep


class DashboardOverviewReadonlyApiTest(unittest.TestCase):
    """Validate dashboard overview contract, permissions and readonly boundary."""

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
        AuditBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        WarehouseBase.metadata.create_all(bind=cls.engine)
        StyleProfitBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[dashboard_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(dashboard_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.query(LySalesPaymentEntry).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LyMaterialPurchaseInvoice).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMasterDataRecord).delete()
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "dashboard.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_dashboard_read_can_access_overview(self) -> None:
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type="dashboard_seed",
                source_id="DASH-STOCK-READ",
                source_warehouse=None,
                target_warehouse="WH-DASH",
                status="draft",
                created_by="dash.seed",
                idempotency_key="idem-dash-stock-read",
                event_key="event-dash-stock-read",
            )
            session.add(draft)
            session.flush()
            session.add_all(
                [
                    LyWarehouseStockEntryDraftItem(
                        draft_id=int(draft.id),
                        company="COMP-A",
                        item_code="DASH-MAT-001",
                        qty=Decimal("10"),
                        uom="米",
                        target_warehouse="WH-DASH",
                    ),
                    LyWarehouseStockEntryDraftItem(
                        draft_id=int(draft.id),
                        company="COMP-A",
                        item_code="DASH-MAT-002",
                        qty=Decimal("20"),
                        uom="米",
                        target_warehouse="WH-DASH",
                    ),
                ]
            )
            session.commit()

        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=3,
                total_inspected_qty=Decimal("100"),
                total_accepted_qty=Decimal("95"),
                total_rejected_qty=Decimal("5"),
                total_defect_qty=Decimal("2"),
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A&from_date=2026-04-01&to_date=2026-04-20",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(payload["quality"]["inspection_count"], 3)
        self.assertEqual(payload["sales_inventory"]["item_count"], 2)
        self.assertEqual(Decimal(str(payload["sales_inventory"]["total_actual_qty"])), Decimal("30.000000"))
        self.assertEqual(payload["sales_inventory"]["below_safety_count"], 0)
        self.assertEqual(payload["sales_inventory"]["below_reorder_count"], 0)
        self.assertEqual(payload["warehouse"]["alert_count"], 0)
        self.assertEqual(payload["warehouse"]["critical_alert_count"], 0)
        self.assertEqual(payload["warehouse"]["warning_alert_count"], 0)
        self.assertEqual(
            [row["module"] for row in payload["source_status"]],
            ["quality", "sales_inventory", "warehouse", "dashboard_business", "dashboard_config"],
        )
        self.assertEqual([row["source_type"] for row in payload["source_status"][:3]], ["actual", "actual", "actual"])
        self.assertEqual(payload["source_status"][3]["source_type"], "actual")
        self.assertIn("只读聚合", payload["source_status"][3]["source_note"])
        self.assertEqual(payload["source_status"][4]["source_type"], "config")
        self.assertIn("配置项", payload["source_status"][4]["source_note"])
        self.assertIn("不代表业务闭环完成", payload["source_status"][4]["source_note"])
        self.assertNotIn("local_dev_static_fallback", response.text)
        self.assertIn("home_overview", payload)
        self.assertGreaterEqual(len(payload["home_overview"]["metric_cards"]), 4)
        self.assertGreaterEqual(len(payload["home_overview"]["todo_items"]), 3)
        self.assertEqual(payload["home_overview"]["warnings"], [])
        self.assertEqual(payload["home_overview"]["trend_points"], [])
        self.assertEqual(len(payload["home_overview"]["charts"]), 3)
        self.assertIn("查看动态", payload["home_overview"]["primary_actions"])
        self.assertEqual({row["source_type"] for row in payload["kanban"]["flow_nodes"]}, {"config"})
        self.assertTrue(
            all("不代表业务闭环完成" in row["status_note"] for row in payload["kanban"]["flow_nodes"])
        )
        self.assertNotIn("120000", response.text)
        self.assertNotIn("写入类动作", response.text)

    def test_dashboard_kanban_messages_are_built_from_local_orders_and_plans(self) -> None:
        with self.SessionLocal() as session:
            order = LySalesOrder(
                sales_order_no="SO-DASH-001",
                source_order_ref="SRC-DASH-001",
                company="COMP-A",
                customer="DASH-CUST",
                status="planned",
                docstatus=0,
                transaction_date=date(2026, 4, 1),
                delivery_date=date(2026, 4, 20),
                currency="CNY",
                grand_total=Decimal("100"),
                idempotency_key="idem-dash-so",
                request_hash="hash-dash-so",
                scenario_tag="DASH",
                payload={},
                created_by="dash.seed",
                created_at=datetime(2026, 4, 1, 8, 0, 0),
                updated_by="dash.seed",
                updated_at=datetime(2026, 4, 2, 8, 0, 0),
            )
            session.add(order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company="COMP-A",
                    line_no=1,
                    sales_order_item="SO-DASH-001-001",
                    item_code="DASH-STYLE-001",
                    item_name="Dashboard Style",
                    qty=Decimal("12"),
                    planned_qty=Decimal("12"),
                    delivered_qty=Decimal("0"),
                    ys_material_calc_state="待算料",
                    uom="件",
                    warehouse="FG-DASH",
                    delivery_date=date(2026, 4, 20),
                )
            )
            session.add(
                LyProductionPlan(
                    plan_no="PP-DASH-001",
                    company="COMP-A",
                    sales_order="SO-DASH-001",
                    sales_order_item="SO-DASH-001-001",
                    customer="DASH-CUST",
                    item_code="DASH-STYLE-001",
                    bom_id=1,
                    bom_version="V1",
                    planned_qty=Decimal("12"),
                    planned_start_date=date(2026, 4, 3),
                    status="planned",
                    idempotency_key="idem-dash-plan",
                    request_hash="hash-dash-plan",
                    created_by="dash.seed",
                    created_at=datetime(2026, 4, 3, 9, 0, 0),
                    updated_at=datetime(2026, 4, 3, 10, 0, 0),
                )
            )
            session.commit()

        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=0,
                total_inspected_qty=Decimal("0"),
                total_accepted_qty=Decimal("0"),
                total_rejected_qty=Decimal("0"),
                total_defect_qty=Decimal("0"),
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        messages = response.json()["data"]["kanban"]["messages"]
        joined = " ".join(f"{row['order_no']} {row['style_no']} {row['title']}" for row in messages)
        self.assertIn("SO-DASH-001", joined)
        self.assertIn("PP-DASH-001", joined)
        self.assertIn("DASH-STYLE-001", joined)
        self.assertNotIn("SO-240601-001", joined)

    def test_dashboard_home_business_metrics_and_charts_use_real_readonly_sources(self) -> None:
        with self.SessionLocal() as session:
            current_orders = [
                ("SO-DASH-BIZ-001", "DASH-BIZ-STYLE-001", Decimal("1000"), date(2026, 6, 5), date(2026, 6, 25)),
                ("SO-DASH-BIZ-002", "DASH-BIZ-STYLE-002", Decimal("1500"), date(2026, 6, 20), date(2026, 6, 10)),
            ]
            for index, (order_no, style_no, grand_total, transaction_date, delivery_date) in enumerate(current_orders, start=1):
                order = LySalesOrder(
                    sales_order_no=order_no,
                    source_order_ref=f"SRC-{order_no}",
                    company="COMP-A",
                    customer="DASH-BIZ-CUST",
                    status="draft",
                    docstatus=0,
                    transaction_date=transaction_date,
                    delivery_date=delivery_date,
                    currency="CNY",
                    grand_total=grand_total,
                    idempotency_key=f"idem-{order_no}",
                    request_hash=f"hash-{order_no}",
                    scenario_tag="DASH-BIZ",
                    payload={},
                    created_by="dash.seed",
                    created_at=datetime(2026, 6, index, 8, 0, 0),
                    updated_by="dash.seed",
                    updated_at=datetime(2026, 6, index, 9, 0, 0),
                )
                session.add(order)
                session.flush()
                session.add(
                    LySalesOrderItem(
                        sales_order_id=int(order.id),
                        company="COMP-A",
                        line_no=1,
                        sales_order_item=f"{order_no}-001",
                        item_code=style_no,
                        item_name=f"Dashboard Business Style {index}",
                        qty=Decimal("10"),
                        planned_qty=Decimal("0"),
                        delivered_qty=Decimal("0"),
                        ys_material_calc_state="待算料",
                        uom="件",
                        warehouse="FG-DASH",
                        delivery_date=delivery_date,
                        rate=grand_total / Decimal("10"),
                        amount=grand_total,
                    )
                )

            previous_order = LySalesOrder(
                sales_order_no="SO-DASH-BIZ-PREV",
                source_order_ref="SRC-SO-DASH-BIZ-PREV",
                company="COMP-A",
                customer="DASH-BIZ-CUST",
                status="draft",
                docstatus=0,
                transaction_date=date(2026, 5, 20),
                delivery_date=date(2026, 5, 30),
                currency="CNY",
                grand_total=Decimal("500"),
                idempotency_key="idem-SO-DASH-BIZ-PREV",
                request_hash="hash-SO-DASH-BIZ-PREV",
                scenario_tag="DASH-BIZ",
                payload={},
                created_by="dash.seed",
                created_at=datetime(2026, 5, 20, 8, 0, 0),
                updated_by="dash.seed",
                updated_at=datetime(2026, 5, 20, 9, 0, 0),
            )
            session.add(previous_order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(previous_order.id),
                    company="COMP-A",
                    line_no=1,
                    sales_order_item="SO-DASH-BIZ-PREV-001",
                    item_code="DASH-BIZ-STYLE-PREV",
                    item_name="Dashboard Business Previous Style",
                    qty=Decimal("5"),
                    planned_qty=Decimal("5"),
                    delivered_qty=Decimal("5"),
                    ys_material_calc_state="待算料",
                    uom="件",
                    warehouse="FG-DASH",
                    delivery_date=date(2026, 5, 30),
                    rate=Decimal("100"),
                    amount=Decimal("500"),
                )
            )

            session.add_all(
                [
                    LyDeliveryInvoice(
                        company="COMP-A",
                        delivery_note="DN-DASH-BIZ-001",
                        sales_invoice="SI-DASH-BIZ-001",
                        sales_order="SO-DASH-BIZ-001",
                        customer="DASH-BIZ-CUST",
                        item_code="DASH-BIZ-STYLE-001",
                        item_name="Dashboard Business Style 1",
                        warehouse="FG-DASH",
                        delivered_qty=Decimal("4"),
                        uom="件",
                        rate=Decimal("125"),
                        grand_total=Decimal("500"),
                        paid_amount=Decimal("200"),
                        outstanding_amount=Decimal("300"),
                        posting_date=date(2026, 6, 10),
                        due_date=date(2026, 6, 30),
                        status="partly_paid",
                        source_ref="SRC-DN-DASH-BIZ-001",
                        idempotency_key="idem-DN-DASH-BIZ-001",
                        request_hash="hash-DN-DASH-BIZ-001",
                        payload={},
                        created_by="dash.seed",
                    ),
                    LyWarehouseStockLedgerEntry(
                        company="COMP-A",
                        warehouse="WH-DASH",
                        item_code="DASH-BIZ-MAT",
                        uom="米",
                        posting_date=date(2026, 6, 11),
                        sort_at=datetime(2026, 6, 11, 8, 0, 0),
                        source_type="dashboard_seed",
                        source_id="LEDGER-IN-DASH-BIZ",
                        source_line_id="1",
                        voucher_type="Stock Entry",
                        voucher_no="STE-DASH-BIZ-IN",
                        actual_qty=Decimal("10"),
                        status="active",
                    ),
                    LyWarehouseStockLedgerEntry(
                        company="COMP-A",
                        warehouse="WH-DASH",
                        item_code="DASH-BIZ-MAT",
                        uom="米",
                        posting_date=date(2026, 6, 12),
                        sort_at=datetime(2026, 6, 12, 8, 0, 0),
                        source_type="dashboard_seed",
                        source_id="LEDGER-OUT-DASH-BIZ",
                        source_line_id="1",
                        voucher_type="Stock Entry",
                        voucher_no="STE-DASH-BIZ-OUT",
                        actual_qty=Decimal("-4"),
                        status="active",
                    ),
                    LyProductionPlan(
                        plan_no="PP-DASH-BIZ-001",
                        company="COMP-A",
                        sales_order="SO-DASH-BIZ-001",
                        sales_order_item="SO-DASH-BIZ-001-001",
                        customer="DASH-BIZ-CUST",
                        item_code="DASH-BIZ-STYLE-001",
                        bom_id=1,
                        bom_version="V1",
                        planned_qty=Decimal("10"),
                        planned_start_date=date(2026, 6, 6),
                        status="planned",
                        idempotency_key="idem-PP-DASH-BIZ-001",
                        request_hash="hash-PP-DASH-BIZ-001",
                        created_by="dash.seed",
                        created_at=datetime(2026, 6, 6, 8, 0, 0),
                        updated_at=datetime(2026, 6, 6, 9, 0, 0),
                    ),
                    LyStyleProfitSnapshot(
                        snapshot_no="SP-DASH-BIZ-001",
                        company="COMP-A",
                        sales_order="SO-DASH-BIZ-001",
                        item_code="DASH-BIZ-STYLE-001",
                        revenue_status="actual",
                        revenue_amount=Decimal("1000"),
                        from_date=date(2026, 6, 1),
                        to_date=date(2026, 6, 24),
                        standard_total_cost=Decimal("300"),
                        actual_total_cost=Decimal("300"),
                        profit_amount=Decimal("700"),
                        profit_rate=Decimal("0.7"),
                        snapshot_status="complete",
                        allocation_status="not_enabled",
                        formula_version="STYLE_PROFIT_V1",
                        unresolved_count=0,
                        idempotency_key="idem-SP-DASH-BIZ-001",
                        request_hash="hash-SP-DASH-BIZ-001",
                        created_by="dash.seed",
                        created_at=datetime(2026, 6, 20, 8, 0, 0),
                    ),
                    LyStyleProfitSnapshot(
                        snapshot_no="SP-DASH-BIZ-PREV",
                        company="COMP-A",
                        sales_order="SO-DASH-BIZ-PREV",
                        item_code="DASH-BIZ-STYLE-PREV",
                        revenue_status="actual",
                        revenue_amount=Decimal("500"),
                        from_date=date(2026, 5, 10),
                        to_date=date(2026, 5, 20),
                        standard_total_cost=Decimal("150"),
                        actual_total_cost=Decimal("150"),
                        profit_amount=Decimal("350"),
                        profit_rate=Decimal("0.7"),
                        snapshot_status="complete",
                        allocation_status="not_enabled",
                        formula_version="STYLE_PROFIT_V1",
                        unresolved_count=0,
                        idempotency_key="idem-SP-DASH-BIZ-PREV",
                        request_hash="hash-SP-DASH-BIZ-PREV",
                        created_by="dash.seed",
                        created_at=datetime(2026, 5, 20, 8, 0, 0),
                    ),
                ]
            )
            session.flush()
            delivery_invoice_id = int(
                session.query(LyDeliveryInvoice.id).filter(LyDeliveryInvoice.sales_invoice == "SI-DASH-BIZ-001").scalar()
            )
            purchase_order = LyMaterialPurchaseOrder(
                company="COMP-A",
                purchase_no="PO-DASH-BIZ-001",
                supplier_name="DASH-BIZ-SUP",
                transaction_date=date(2026, 6, 9),
                expected_delivery_date=date(2026, 6, 28),
                status="draft",
                total_qty=Decimal("20"),
                received_qty=Decimal("0"),
                total_amount=Decimal("600"),
                currency="CNY",
                created_by="dash.seed",
                updated_by="dash.seed",
            )
            session.add(purchase_order)
            session.flush()
            session.add_all(
                [
                    LySalesPaymentEntry(
                        company="COMP-A",
                        payment_entry="PE-DASH-BIZ-001",
                        delivery_invoice_id=delivery_invoice_id,
                        delivery_note="DN-DASH-BIZ-001",
                        sales_invoice="SI-DASH-BIZ-001",
                        sales_order="SO-DASH-BIZ-001",
                        customer="DASH-BIZ-CUST",
                        posting_date=date(2026, 6, 15),
                        paid_amount=Decimal("200"),
                        allocated_amount=Decimal("200"),
                        outstanding_before=Decimal("500"),
                        outstanding_after=Decimal("300"),
                        mode_of_payment="Bank Transfer",
                        reference_no="REF-DASH-BIZ-001",
                        reference_date=date(2026, 6, 15),
                        status="submitted",
                        source_ref="SRC-PE-DASH-BIZ-001",
                        idempotency_key="idem-PE-DASH-BIZ-001",
                        request_hash="hash-PE-DASH-BIZ-001",
                        payload={},
                        created_by="dash.seed",
                    ),
                    LyMaterialPurchaseInvoice(
                        company="COMP-A",
                        purchase_invoice="PI-DASH-BIZ-001",
                        purchase_order_id=int(purchase_order.id),
                        purchase_no="PO-DASH-BIZ-001",
                        supplier_name="DASH-BIZ-SUP",
                        material_item_code="DASH-BIZ-MAT",
                        material_name="Dashboard Material",
                        warehouse="WH-DASH",
                        qty=Decimal("20"),
                        uom="米",
                        rate=Decimal("30"),
                        grand_total=Decimal("600"),
                        paid_amount=Decimal("420"),
                        outstanding_amount=Decimal("180"),
                        posting_date=date(2026, 6, 12),
                        due_date=date(2026, 6, 30),
                        status="partly_paid",
                        source_ref="SRC-PI-DASH-BIZ-001",
                        idempotency_key="idem-PI-DASH-BIZ-001",
                        request_hash="hash-PI-DASH-BIZ-001",
                        payload={},
                        created_by="dash.seed",
                    ),
                ]
            )
            session.commit()

        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=2,
                total_inspected_qty=Decimal("10"),
                total_accepted_qty=Decimal("9"),
                total_rejected_qty=Decimal("1"),
                total_defect_qty=Decimal("1"),
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A&to_date=2026-06-24",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        home = response.json()["data"]["home_overview"]
        metrics = {row["key"]: row for row in home["metric_cards"]}
        self.assertEqual(metrics["monthly_order_count"]["value"], "2")
        self.assertEqual(metrics["monthly_order_count"]["trend"], "较上期 +100%")
        self.assertEqual(metrics["monthly_sales_amount"]["value"], "2500")
        self.assertEqual(metrics["monthly_sales_amount"]["trend"], "较上期 +400%")
        self.assertEqual(metrics["receivable_balance"]["value"], "300")
        self.assertEqual(metrics["payable_balance"]["value"], "180")
        self.assertEqual(metrics["in_production_order_count"]["value"], "1")
        self.assertEqual(metrics["delivery_warning_count"]["value"], "2")
        self.assertEqual(metrics["monthly_gross_profit"]["value"], "700")
        self.assertEqual(metrics["monthly_gross_profit"]["status"], "complete")
        self.assertEqual(metrics["monthly_gross_profit"]["trend"], "较上期 +100%")
        self.assertEqual({row["group"] for row in home["metric_cards"]}, {"business", "inventory", "quality"})
        self.assertTrue(all(row.get("route") for row in home["todo_items"]))

        blocked_trends = {"较昨日平稳", "按只读汇总更新", "来源于质检汇总", "高危优先处理"}
        self.assertTrue(blocked_trends.isdisjoint({row.get("trend") for row in home["metric_cards"]}))

        charts = {row["key"]: row for row in home["charts"]}
        self.assertEqual(set(charts), {"sales_amount_trend", "stock_movement_trend", "receivable_collection_trend"})
        sales_point = next(point for point in charts["sales_amount_trend"]["points"] if point["period"] == "2026-06-20")
        self.assertEqual(Decimal(str(sales_point["values"]["sales_amount"])), Decimal("1500.000000"))
        inbound_point = next(point for point in charts["stock_movement_trend"]["points"] if point["period"] == "2026-06-11")
        outbound_point = next(point for point in charts["stock_movement_trend"]["points"] if point["period"] == "2026-06-12")
        self.assertEqual(Decimal(str(inbound_point["values"]["inbound_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(outbound_point["values"]["outbound_qty"])), Decimal("4.000000"))
        payment_point = next(point for point in charts["receivable_collection_trend"]["points"] if point["period"] == "2026-06-15")
        self.assertEqual(Decimal(str(payment_point["values"]["paid_amount"])), Decimal("200.000000"))

        workbench = home["workbench"]
        alerts = {row["key"]: row for row in workbench["alerts"]}
        kpis = {row["key"]: row for row in workbench["kpis"]}
        stages = {row["key"]: row for row in workbench["stage_distribution"]}
        pipeline = {row["key"]: row for row in workbench["pipeline"]}

        self.assertEqual(alerts["overdue_orders"]["count"], 1)
        self.assertEqual(alerts["due_soon_orders"]["count"], 1)
        self.assertEqual(alerts["unpaid_customers_over_30d"]["count"], 0)
        self.assertEqual(kpis["monthly_gross_profit"]["label"], "核价毛利（预测）")
        self.assertEqual(Decimal(str(kpis["monthly_shipment"]["value"])), Decimal("4"))
        self.assertEqual(Decimal(str(kpis["monthly_collection"]["value"])), Decimal("200"))
        self.assertEqual(Decimal(str(kpis["receivable_balance_v1"]["value"])), Decimal("300"))
        self.assertEqual(Decimal(str(kpis["monthly_gross_profit"]["value"])), Decimal("700"))
        self.assertEqual(sum(row["count"] for row in workbench["stage_distribution"]), int(kpis["active_order_count"]["value"]))
        self.assertEqual(stages, pipeline)
        self.assertEqual(stages["quote"]["count"], 2)

        workbench_trend = {row["period"]: row for row in workbench["shipment_collection_trend"]}
        self.assertEqual(Decimal(str(workbench_trend["6月"]["shipment_amount"])), Decimal("500"))
        self.assertEqual(Decimal(str(workbench_trend["6月"]["collection_amount"])), Decimal("200"))
        self.assertEqual(workbench["due_orders"][0]["sales_order"], "SO-DASH-BIZ-001")
        self.assertEqual(Decimal(str(workbench["due_orders"][0]["completion_rate"])), Decimal("0.00"))
        self.assertEqual(workbench["customer_shares"][0]["customer"], "DASH-BIZ-CUST")
        self.assertEqual(Decimal(str(workbench["customer_shares"][0]["amount"])), Decimal("500"))
        self.assertTrue(any(row["sales_order"] == "SO-DASH-BIZ-001" for row in workbench["recent_orders"]))

        with self.SessionLocal() as session:
            delivery_date_expr = func.coalesce(LySalesOrderItem.delivery_date, LySalesOrder.delivery_date)
            direct_overdue = (
                session.query(func.count(distinct(LySalesOrder.id)))
                .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
                .filter(
                    LySalesOrder.company == "COMP-A",
                    LySalesOrder.status != "cancelled",
                    delivery_date_expr < date(2026, 6, 24),
                    LySalesOrderItem.delivered_qty < LySalesOrderItem.qty,
                )
                .scalar()
            )
            direct_due_soon = (
                session.query(func.count(distinct(LySalesOrder.id)))
                .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
                .filter(
                    LySalesOrder.company == "COMP-A",
                    LySalesOrder.status != "cancelled",
                    delivery_date_expr >= date(2026, 6, 24),
                    delivery_date_expr <= date(2026, 7, 1),
                    LySalesOrderItem.delivered_qty < LySalesOrderItem.qty,
                )
                .scalar()
            )
            direct_shipment_qty = (
                session.query(func.coalesce(func.sum(LyDeliveryInvoice.delivered_qty), 0))
                .filter(
                    LyDeliveryInvoice.company == "COMP-A",
                    LyDeliveryInvoice.status != "cancelled",
                    LyDeliveryInvoice.posting_date >= date(2026, 6, 1),
                    LyDeliveryInvoice.posting_date <= date(2026, 6, 24),
                )
                .scalar()
            )

        self.assertEqual(alerts["overdue_orders"]["count"], int(direct_overdue or 0))
        self.assertEqual(alerts["due_soon_orders"]["count"], int(direct_due_soon or 0))
        self.assertEqual(Decimal(str(kpis["monthly_shipment"]["value"])), Decimal(str(direct_shipment_qty)))

    def test_fastapi_dashboard_uses_local_stock_without_erpnext_adapters(self) -> None:
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type="dashboard_seed",
                source_id="DASH-STOCK-001",
                source_warehouse=None,
                target_warehouse="WH-DASH",
                status="draft",
                created_by="dash.seed",
                idempotency_key="idem-dash-stock",
                event_key="event-dash-stock",
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company="COMP-A",
                    item_code="DASH-MAT-001",
                    qty=Decimal("7"),
                    uom="米",
                    target_warehouse="WH-DASH",
                )
            )
            session.commit()

        with patch.dict(
            os.environ,
            {"LINGYI_PERMISSION_SOURCE": "fastapi", "LINGYI_ERPNEXT_BASE_URL": ""},
            clear=False,
        ), patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=0,
                total_inspected_qty=Decimal("0"),
                total_accepted_qty=Decimal("0"),
                total_rejected_qty=Decimal("0"),
                total_defect_qty=Decimal("0"),
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles("System Manager"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["sales_inventory"]["item_count"], 1)
        self.assertEqual(Decimal(str(payload["sales_inventory"]["total_actual_qty"])), Decimal("7.000000"))
        self.assertEqual(payload["warehouse"]["alert_count"], 0)
        self.assertEqual([row["status"] for row in payload["source_status"]], ["ok", "ok", "ok", "ok", "ok"])
        self.assertEqual(payload["source_status"][-1]["module"], "dashboard_config")
        self.assertEqual(payload["source_status"][-1]["source_type"], "config")

    def test_fastapi_dashboard_inventory_alerts_read_material_thresholds(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code="DASH-MAT-THRESHOLD",
                    name="Dashboard 阈值物料",
                    status="active",
                    payload={"reorder_level": "10", "safety_stock": "8"},
                    created_by="dash.seed",
                    updated_by="dash.seed",
                )
            )
            draft = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type="dashboard_seed",
                source_id="DASH-STOCK-THRESHOLD",
                source_warehouse=None,
                target_warehouse="WH-DASH",
                status="draft",
                created_by="dash.seed",
                idempotency_key="idem-dash-stock-threshold",
                event_key="event-dash-stock-threshold",
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company="COMP-A",
                    item_code="DASH-MAT-THRESHOLD",
                    qty=Decimal("7"),
                    uom="米",
                    target_warehouse="WH-DASH",
                )
            )
            session.commit()

        with patch.dict(
            os.environ,
            {"LINGYI_PERMISSION_SOURCE": "fastapi", "LINGYI_ERPNEXT_BASE_URL": ""},
            clear=False,
        ), patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=0,
                total_inspected_qty=Decimal("0"),
                total_accepted_qty=Decimal("0"),
                total_rejected_qty=Decimal("0"),
                total_defect_qty=Decimal("0"),
            ),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles("System Manager"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["sales_inventory"]["below_safety_count"], 1)
        self.assertEqual(payload["sales_inventory"]["below_reorder_count"], 1)
        self.assertEqual(payload["warehouse"]["alert_count"], 1)
        self.assertEqual(payload["warehouse"]["critical_alert_count"], 1)
        self.assertEqual(payload["home_overview"]["warnings"], ["低于补货线款号 1 个", "仓储高危预警 1 条"])

    def test_module_read_actions_cannot_replace_dashboard_read(self) -> None:
        for role in ("quality:read", "sales_inventory:read", "warehouse:read", "inventory:read"):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_company_missing_uses_dev_default_company(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["company"], "LY-FRONTEND-DEV")

    def test_company_empty_uses_dev_default_company(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["company"], "LY-FRONTEND-DEV")

    def test_invalid_date_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=COMP-A&from_date=2026/04/01",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_from_date_later_than_to_date_returns_400(self) -> None:
        response = self.client.get(
            "/api/dashboard/overview?company=COMP-A&from_date=2026-04-21&to_date=2026-04-20",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_source_unavailable_is_fail_closed(self) -> None:
        with patch(
            "app.services.quality_service.QualityService.statistics",
            return_value=SimpleNamespace(
                total_count=1,
                total_inspected_qty=Decimal("1"),
                total_accepted_qty=Decimal("1"),
                total_rejected_qty=Decimal("0"),
                total_defect_qty=Decimal("0"),
            ),
        ), patch(
            "app.services.warehouse_service.WarehouseService.get_local_stock_summary",
            side_effect=RuntimeError("local stock source unavailable"),
        ):
            response = self.client.get(
                "/api/dashboard/overview?company=COMP-A",
                headers=self._headers_with_roles("dashboard:read"),
            )

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["code"], "DASHBOARD_SOURCE_UNAVAILABLE")
        self.assertEqual(body["data"]["module"], "sales_inventory")

    def test_no_write_route_registered(self) -> None:
        dashboard_routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/dashboard")]
        self.assertTrue(dashboard_routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in dashboard_routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_main_route_mapping_for_dashboard_overview(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/dashboard/overview",
            "raw_path": b"/api/dashboard/overview",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "dashboard")
        self.assertEqual(action, DASHBOARD_READ)
        self.assertEqual(resource_type, "DashboardOverview")
        self.assertIsNone(resource_id)

    def test_dashboard_files_no_write_signatures(self) -> None:
        files = [
            Path("app/routers/dashboard.py"),
            Path("app/services/dashboard_service.py"),
            Path("app/schemas/dashboard.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "worker",
            "run-once",
            "internal",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)

    def test_dashboard_frontend_trend_readonly_files_guarded(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        files = [
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/components/DashboardTrendReadonlySection.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/composables/useDashboardTrendReadonly.ts",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/constants/dashboardTrendReadonlyFields.ts",
        ]
        for path in files:
            self.assertTrue(path.exists(), str(path))

        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        required = [
            "cand248-dashboard-trend-readonly",
            "latest_refresh=",
            "stale_indicator=",
            "审批",
            "导出",
            "跨模块执行",
        ]
        blocked = [
            ".post(",
            ".put(",
            ".patch(",
            ".delete(",
            "HomePage",
            "/home",
        ]

        for snippet in required:
            self.assertIn(snippet, combined)
        for snippet in blocked:
            self.assertNotIn(snippet, combined)

    def test_dashboard_frontend_todo_readonly_files_guarded(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        files = [
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/components/DashboardTodoReadonlySection.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/composables/useDashboardTodoReadonly.ts",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/constants/dashboardTodoReadonlyFields.ts",
        ]
        for path in files:
            self.assertTrue(path.exists(), str(path))

        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        required = [
            "cand254-dashboard-todo-readonly",
            "entry_source=",
            "source_route=",
            "overdue_bucket=",
            "blocked_reason=",
            "审批",
            "导出",
            "跨模块执行",
        ]

        for snippet in required:
            self.assertIn(snippet, combined)

    def test_dashboard_frontend_module_entry_readonly_files_guarded(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        files = [
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/components/DashboardModuleEntryReadonlySection.vue",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/composables/useDashboardModuleEntryReadonly.ts",
            repo_root / "06_前端/lingyi-pc/src/views/dashboard/constants/dashboardModuleEntryFields.ts",
        ]
        for path in files:
            self.assertTrue(path.exists(), str(path))

        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        required = [
            "cand260-dashboard-module-entry-readonly",
            "/sales-inventory/references",
            "/reports/style-profit",
            "/workshop/tickets",
            "/factory-statements/list",
            "/warehouse",
            "reachability=",
            "guard_state=",
            "blocked_reason=",
            "审批",
            "导出",
            "跨模块执行",
        ]
        blocked = [
            "HomePage",
            "/home",
        ]

        for snippet in required:
            self.assertIn(snippet, combined)
        for snippet in blocked:
            self.assertNotIn(snippet, combined)


if __name__ == "__main__":
    unittest.main()
