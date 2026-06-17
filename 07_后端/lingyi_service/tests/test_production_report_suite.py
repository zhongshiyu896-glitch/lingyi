"""Existing frontend production report-suite API tests."""

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitSnapshot
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionReportSuiteApiTest(unittest.TestCase):
    """Validate A7 report-suite read model, permissions and cost/profit math."""

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
        for base in (AuditBase, BomBase, SalesOrderBase, ProductionBase, StyleProfitBase, MaterialPurchaseBase):
            base.metadata.create_all(bind=cls.engine)

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
        with self.SessionLocal() as session:
            for model in (
                LyStyleProfitSnapshot,
                LyMaterialPurchaseOrderItem,
                LyMaterialPurchaseOrder,
                LyProductionPlanMaterial,
                LyProductionPlan,
                LyBomOperation,
                LyApparelBomItem,
                LyApparelBom,
                LySalesOrderItem,
                LySalesOrder,
            ):
                session.query(model).delete()
            session.commit()
            self._seed(session)
            session.commit()

    @staticmethod
    def _headers(roles: str = "production:read") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "production.report.user",
            "X-LY-Dev-Roles": roles,
        }

    @staticmethod
    def _seed(session) -> None:
        order = LySalesOrder(
            sales_order_no="SO-RPT-001",
            source_order_ref="SO-RPT-001",
            company="COMP-A",
            customer="杭州云澜服饰",
            status="planned",
            docstatus=0,
            transaction_date=date(2026, 6, 1),
            delivery_date=date(2026, 6, 20),
            currency="CNY",
            grand_total=Decimal("2000"),
            idempotency_key="so-rpt-idem",
            request_hash="so-rpt-hash",
            created_by="sales.user",
        )
        session.add(order)
        session.flush()
        session.add(
            LySalesOrderItem(
                sales_order_id=int(order.id),
                company="COMP-A",
                line_no=1,
                sales_order_item="SO-RPT-001-001",
                item_code="STYLE-A",
                item_name="通勤西装",
                qty=Decimal("100"),
                planned_qty=Decimal("80"),
                delivered_qty=Decimal("12"),
                rate=Decimal("20"),
                amount=Decimal("2000"),
                uom="件",
                warehouse="FG-A",
                delivery_date=date(2026, 6, 20),
            )
        )

        bom = LyApparelBom(
            id=1,
            bom_no="BOM-RPT-001",
            company="COMP-RPT",
            item_code="STYLE-A",
            version_no="V1",
            is_default=True,
            status="active",
            effective_date=date(2026, 5, 20),
            created_by="bom.user",
            updated_by="bom.user",
        )
        session.add(bom)
        session.flush()
        material = LyApparelBomItem(
            id=1,
            bom_id=int(bom.id),
            material_item_code="FAB-A",
            qty_per_piece=Decimal("2"),
            loss_rate=Decimal("0.1"),
            uom="米",
            remark="单价:5 供应商:瑞兴纺织",
        )
        session.add(material)
        session.add(
            LyBomOperation(
                id=1,
                bom_id=int(bom.id),
                process_name="车缝",
                sequence_no=1,
                is_subcontract=False,
                wage_rate=Decimal("1"),
            )
        )
        session.add(
            LyBomOperation(
                id=2,
                bom_id=int(bom.id),
                process_name="压胶",
                sequence_no=2,
                is_subcontract=True,
                subcontract_cost_per_piece=Decimal("2"),
            )
        )
        session.flush()

        plan = LyProductionPlan(
            plan_no="PP-RPT-001",
            company="COMP-A",
            sales_order="SO-RPT-001",
            sales_order_item="SO-RPT-001-001",
            customer="杭州云澜服饰",
            item_code="STYLE-A",
            bom_id=int(bom.id),
            bom_version="V1",
            planned_qty=Decimal("80"),
            planned_start_date=date(2026, 6, 3),
            status="planned",
            idempotency_key="plan-rpt-idem",
            request_hash="plan-rpt-hash",
            created_by="merch.user",
        )
        session.add(plan)
        session.flush()
        session.add(
            LyProductionPlanMaterial(
                plan_id=int(plan.id),
                bom_item_id=int(material.id),
                material_item_code="FAB-A",
                warehouse="WH-A",
                qty_per_piece=Decimal("2"),
                loss_rate=Decimal("0.1"),
                required_qty=Decimal("176"),
                available_qty=Decimal("150"),
                shortage_qty=Decimal("26"),
            )
        )
        session.add(
            LyStyleProfitSnapshot(
                snapshot_no="SP-RPT-001",
                company="COMP-A",
                sales_order="SO-RPT-001",
                item_code="STYLE-A",
                revenue_status="estimated",
                estimated_revenue_amount=Decimal("2000"),
                actual_revenue_amount=Decimal("0"),
                revenue_amount=Decimal("2000"),
                from_date=date(2026, 6, 1),
                to_date=date(2026, 6, 30),
                revenue_mode="actual_first",
                standard_material_cost=Decimal("880"),
                standard_operation_cost=Decimal("240"),
                standard_total_cost=Decimal("1120"),
                actual_material_cost=Decimal("900"),
                actual_workshop_cost=Decimal("80"),
                actual_subcontract_cost=Decimal("160"),
                allocated_overhead_amount=Decimal("0"),
                actual_total_cost=Decimal("1140"),
                profit_amount=Decimal("860"),
                profit_rate=Decimal("0.43"),
                snapshot_status="complete",
                allocation_status="not_enabled",
                formula_version="STYLE_PROFIT_V1",
                include_provisional_subcontract=False,
                unresolved_count=0,
                idempotency_key="sp-rpt-idem",
                request_hash="sp-rpt-hash",
                created_by="profit.user",
            )
        )

    def test_profit_report_uses_latest_style_profit_snapshot(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=productOrderProfitReport&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["report_key"], "productOrderProfitReport")
        self.assertEqual(payload["total"], 1)
        row = payload["items"][0]
        self.assertEqual(row["sales_order"], "SO-RPT-001")
        self.assertEqual(Decimal(str(row["amount"])), Decimal("2000"))
        self.assertEqual(Decimal(str(row["totalCost"])), Decimal("1140"))
        self.assertEqual(Decimal(str(row["profit"])), Decimal("860"))
        self.assertEqual(Decimal(str(row["grossMargin"])), Decimal("43.00"))
        self.assertEqual(row["risk"], "低风险")
        pending_text = "；".join(payload["pending_b_phase_fields"])
        self.assertIn("已建页面的成品入库、发货开票、回款", pending_text)
        self.assertNotIn("成品入库/发货开票未建页面", pending_text)
        self.assertIn("成品入库、发货开票、回款已接本地闭环", row["remark"])

    def test_material_detail_report_uses_material_check_snapshot(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=productionCostMaterialDetailReport&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["data"]["items"][0]
        self.assertEqual(row["item_code"], "FAB-A")
        self.assertEqual(Decimal(str(row["requiredQty"])), Decimal("176"))
        self.assertEqual(Decimal(str(row["availableQty"])), Decimal("150"))
        self.assertEqual(Decimal(str(row["gapQty"])), Decimal("-26"))
        self.assertEqual(Decimal(str(row["materialCost"])), Decimal("880"))
        self.assertEqual(row["status"], "缺口")

    def test_missing_bom_price_uses_latest_purchase_unit_price_for_profit(self) -> None:
        with self.SessionLocal() as session:
            order = LySalesOrder(
                sales_order_no="SO-RPT-PUR",
                source_order_ref="SO-RPT-PUR",
                company="COMP-A",
                customer="杭州云澜服饰",
                status="planned",
                docstatus=0,
                transaction_date=date(2026, 6, 2),
                delivery_date=date(2026, 6, 22),
                currency="CNY",
                grand_total=Decimal("1000"),
                idempotency_key="so-rpt-pur-idem",
                request_hash="so-rpt-pur-hash",
                created_by="sales.user",
            )
            session.add(order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company="COMP-A",
                    line_no=1,
                    sales_order_item="SO-RPT-PUR-001",
                    item_code="STYLE-PUR",
                    item_name="采购价款式",
                    qty=Decimal("50"),
                    planned_qty=Decimal("50"),
                    delivered_qty=Decimal("0"),
                    rate=Decimal("20"),
                    amount=Decimal("1000"),
                    uom="件",
                    warehouse="FG-A",
                    delivery_date=date(2026, 6, 22),
                )
            )
            bom = LyApparelBom(
                id=2,
                bom_no="BOM-RPT-PUR",
                company="COMP-RPT",
                item_code="STYLE-PUR",
                version_no="V1",
                is_default=True,
                status="active",
                effective_date=date(2026, 5, 21),
                created_by="bom.user",
                updated_by="bom.user",
            )
            session.add(bom)
            session.flush()
            session.add(
                LyApparelBomItem(
                    id=2,
                    bom_id=int(bom.id),
                    material_item_code="MAT-PUR",
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0.1"),
                    uom="米",
                    remark="采购单价来自本地物料采购单",
                )
            )
            session.add(
                LyBomOperation(
                    id=3,
                    bom_id=int(bom.id),
                    process_name="车缝",
                    sequence_no=1,
                    is_subcontract=False,
                    wage_rate=Decimal("1"),
                )
            )
            session.add(
                LyProductionPlan(
                    plan_no="PP-RPT-PUR",
                    company="COMP-A",
                    sales_order="SO-RPT-PUR",
                    sales_order_item="SO-RPT-PUR-001",
                    customer="杭州云澜服饰",
                    item_code="STYLE-PUR",
                    bom_id=int(bom.id),
                    bom_version="V1",
                    planned_qty=Decimal("50"),
                    planned_start_date=date(2026, 6, 4),
                    status="planned",
                    idempotency_key="plan-rpt-pur-idem",
                    request_hash="plan-rpt-pur-hash",
                    created_by="merch.user",
                )
            )
            purchase = LyMaterialPurchaseOrder(
                company="COMP-A",
                purchase_no="PO-RPT-PUR",
                supplier_name="瑞兴纺织",
                transaction_date=date(2026, 6, 1),
                expected_delivery_date=date(2026, 6, 10),
                status="received",
                total_qty=Decimal("200"),
                received_qty=Decimal("200"),
                total_amount=Decimal("1450"),
                currency="CNY",
                created_by="purchase.user",
            )
            session.add(purchase)
            session.flush()
            session.add(
                LyMaterialPurchaseOrderItem(
                    order_id=int(purchase.id),
                    company="COMP-A",
                    item_code="STYLE-PUR",
                    material_item_code="MAT-PUR",
                    material_name="采购价面料",
                    qty=Decimal("200"),
                    received_qty=Decimal("200"),
                    uom="米",
                    unit_price=Decimal("7.25"),
                    amount=Decimal("1450"),
                    warehouse="WH-A",
                )
            )
            session.commit()

        profit_response = self.client.get(
            "/api/production/report-suite?report_key=productOrderProfitReport&company=COMP-A&keyword=SO-RPT-PUR",
            headers=self._headers(),
        )
        self.assertEqual(profit_response.status_code, 200, profit_response.text)
        profit_row = profit_response.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(profit_row["materialCost"])), Decimal("797.50000000"))
        self.assertEqual(Decimal(str(profit_row["laborCost"])), Decimal("50.000000000000"))
        self.assertEqual(Decimal(str(profit_row["totalCost"])), Decimal("847.500000000000"))
        self.assertEqual(Decimal(str(profit_row["profit"])), Decimal("152.500000000000"))

        material_response = self.client.get(
            "/api/production/report-suite?report_key=productionCostMaterialDetailReport&company=COMP-A&keyword=SO-RPT-PUR",
            headers=self._headers(),
        )
        self.assertEqual(material_response.status_code, 200, material_response.text)
        material_row = material_response.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(material_row["unitPrice"])), Decimal("7.25"))
        self.assertEqual(Decimal(str(material_row["requiredQty"])), Decimal("110.000000"))
        self.assertEqual(Decimal(str(material_row["materialCost"])), Decimal("797.50000000"))

    def test_report_suite_requires_production_read(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=productOrderProfitReport&company=COMP-A",
            headers=self._headers("sales_inventory:read"),
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_invalid_report_key_returns_standard_envelope(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=not_exists",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")
        self.assertEqual(response.json()["data"], {})
