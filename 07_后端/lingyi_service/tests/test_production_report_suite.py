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
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionWorkOrderLink
from app.models.sample import Base as SampleBase
from app.models.sample import LySampleCostLine
from app.models.sample import LySampleOrder
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyStyleProfitSnapshot
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionReportSuiteApiTest(unittest.TestCase):
    """Validate A8 report-suite read model, permissions and cost/profit math."""

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
        for base in (AuditBase, BomBase, SalesOrderBase, ProductionBase, StyleProfitBase, MaterialPurchaseBase, SampleBase):
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
                LyProductionJobCardLink,
                LyProductionWorkOrderLink,
                LyProductionPlanMaterial,
                LyProductionPlan,
                LySampleCostLine,
                LySampleOrder,
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
            LyProductionWorkOrderLink(
                plan_id=int(plan.id),
                work_order="WO-RPT-001",
                erpnext_docstatus=1,
                erpnext_status="LocalSynced",
                sync_status="succeeded",
                created_by="seed",
            )
        )
        session.add(
            LyProductionJobCardLink(
                plan_id=int(plan.id),
                work_order="WO-RPT-001",
                job_card="JC-RPT-001-SEW",
                company="COMP-A",
                item_code="STYLE-A",
                operation="车缝",
                operation_sequence=20,
                expected_qty=Decimal("80"),
                completed_qty=Decimal("12"),
                erpnext_status="LocalSynced",
            )
        )
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
        self.assertGreater(int(row["planId"]), 0)
        self.assertEqual(row["planNo"], "PP-RPT-001")
        self.assertEqual(row["company"], "COMP-A")
        self.assertEqual(row["workOrder"], "WO-RPT-001")
        self.assertEqual(row["primaryJobCard"], "JC-RPT-001-SEW")
        self.assertEqual(row["jobCardCount"], 1)
        self.assertEqual(Decimal(str(row["amount"])), Decimal("2000"))
        self.assertEqual(Decimal(str(row["totalCost"])), Decimal("1140"))
        self.assertEqual(Decimal(str(row["profit"])), Decimal("860"))
        self.assertEqual(Decimal(str(row["grossMargin"])), Decimal("43.00"))
        self.assertEqual(row["risk"], "低风险")
        self.assertEqual(row["sourceType"], "style_profit_snapshot")
        self.assertEqual(row["sourceLabel"], "利润快照/估算收入")
        self.assertEqual(row["sourceStatus"], "mixed")
        self.assertTrue(row["hasSnapshot"])
        self.assertTrue(row["isEstimated"])
        self.assertEqual(row["snapshotNo"], "SP-RPT-001")
        self.assertEqual(row["revenueSourceStatus"], "estimated")
        self.assertEqual(row["costSourceStatus"], "actual")
        basis_text = "；".join(payload["data_basis"])
        pending_text = "；".join(payload["pending_b_phase_fields"])
        self.assertIn("sourceLabel/sourceStatus/hasSnapshot", basis_text)
        self.assertIn("可生成款式利润快照", basis_text)
        self.assertIn("已生成快照的行纳入实际工票工资", basis_text)
        self.assertIn("B期报表继续披露经营测算/快照", basis_text)
        self.assertIn("尚未在本报表合并为财务总账毛利闭环", basis_text)
        self.assertNotIn("真实毛利闭环已完成", basis_text)
        self.assertNotIn("已接本地 FastAPI 闭环", basis_text)
        self.assertNotIn("已建页面的成品入库、发货开票、回款", pending_text)
        self.assertIn("未生成利润快照的行仍按工序工价预测", pending_text)
        self.assertNotIn("成品入库/发货开票未建页面", pending_text)
        self.assertIn("生成利润快照后纳入实际工票工资", row["remark"])

    def test_profit_report_uses_snapshot_revenue_when_invoice_differs_from_order_amount(self) -> None:
        with self.SessionLocal() as session:
            snapshot = session.query(LyStyleProfitSnapshot).filter_by(snapshot_no="SP-RPT-001").one()
            snapshot.revenue_status = "actual"
            snapshot.actual_revenue_amount = Decimal("1800")
            snapshot.estimated_revenue_amount = Decimal("0")
            snapshot.revenue_amount = Decimal("1800")
            snapshot.profit_amount = Decimal("660")
            snapshot.profit_rate = Decimal("0.366667")
            session.commit()

        response = self.client.get(
            "/api/production/report-suite?report_key=productOrderProfitReport&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(row["amount"])), Decimal("1800"))
        self.assertEqual(Decimal(str(row["totalCost"])), Decimal("1140"))
        self.assertEqual(Decimal(str(row["profit"])), Decimal("660"))
        self.assertEqual(Decimal(str(row["grossMargin"])), Decimal("36.67"))
        self.assertEqual(row["sourceType"], "style_profit_snapshot")
        self.assertEqual(row["sourceLabel"], "利润快照")
        self.assertEqual(row["sourceStatus"], "actual")
        self.assertFalse(row["isEstimated"])
        self.assertEqual(row["revenueSourceStatus"], "actual")
        self.assertEqual(row["costSourceStatus"], "actual")

    def test_material_detail_report_uses_material_check_snapshot(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=orderTrackingReport&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["report_key"], "orderTrackingReport")
        self.assertEqual(payload["title"], "大货成本物料明细表")
        self.assertEqual([item["label"] for item in payload["composition"]], ["物料金额", "缺口数量", "可用数量"])
        row = payload["items"][0]
        self.assertEqual(row["item_code"], "FAB-A")
        self.assertEqual(Decimal(str(row["requiredQty"])), Decimal("176"))
        self.assertEqual(Decimal(str(row["availableQty"])), Decimal("150"))
        self.assertEqual(Decimal(str(row["gapQty"])), Decimal("-26"))
        self.assertEqual(Decimal(str(row["materialCost"])), Decimal("880"))
        self.assertEqual(row["status"], "缺口")

    def test_salesperson_performance_report_uses_salesperson_fields(self) -> None:
        response = self.client.get(
            "/api/production/report-suite?report_key=productionCostMaterialDetailReport&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["report_key"], "productionCostMaterialDetailReport")
        self.assertEqual(payload["title"], "业务员业绩分析报表")
        self.assertEqual([item["label"] for item in payload["composition"]], ["状态折算业绩", "预测待完成", "订单件数"])
        row = payload["items"][0]
        self.assertNotIn("requiredQty", row)
        self.assertNotIn("availableQty", row)
        self.assertNotIn("gapQty", row)
        self.assertNotIn("unitPrice", row)
        self.assertEqual(row["salesperson"], "merch.user")
        self.assertEqual(row["planNo"], "PP-RPT-001")
        self.assertEqual(Decimal(str(row["orderedQty"])), Decimal("80"))
        self.assertEqual(Decimal(str(row["completedQty"])), Decimal("28.000000"))
        self.assertEqual(Decimal(str(row["completionRate"])), Decimal("35.00"))
        self.assertEqual(Decimal(str(row["settledAmount"])), Decimal("2940.000000"))
        self.assertEqual(Decimal(str(row["pendingAmount"])), Decimal("5460.000000"))
        self.assertEqual(row["performanceStatus"], "attention")
        self.assertEqual(row["status"], "关注")

    def test_sample_compare_report_uses_converted_sample_costs(self) -> None:
        with self.SessionLocal() as session:
            sample = LySampleOrder(
                company="COMP-A",
                sample_no="SMP-RPT-COST",
                style_no="STYLE-A",
                style_name="通勤西装",
                style_master_id=None,
                customer="杭州云澜服饰",
                factory="样衣室",
                sample_type="初样",
                stage="已转大货",
                progress=100,
                pattern_maker="版师",
                sample_maker="样衣工",
                status="converted",
                image_tone="blue",
                owner_note="",
                bulk_handoff_no="SO-RPT-001",
                bulk_handoff_status="已生成 A4 销售订单草稿",
                created_by="sample.user",
                updated_by="sample.user",
            )
            session.add(sample)
            session.flush()
            session.add_all(
                [
                    LySampleCostLine(
                        company="COMP-A",
                        sample_order_id=int(sample.id),
                        cost_type="面辅料",
                        description="样衣面料",
                        qty=Decimal("1"),
                        unit_price=Decimal("80"),
                        amount=Decimal("80"),
                        created_by="sample.user",
                        updated_by="sample.user",
                    ),
                    LySampleCostLine(
                        company="COMP-A",
                        sample_order_id=int(sample.id),
                        cost_type="工费",
                        description="样衣工费",
                        qty=Decimal("1"),
                        unit_price=Decimal("30"),
                        amount=Decimal("30"),
                        created_by="sample.user",
                        updated_by="sample.user",
                    ),
                ]
            )
            session.commit()

        response = self.client.get(
            "/api/production/report-suite?report_key=productOrderSampleCompare&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        basis_text = "；".join(payload["data_basis"])
        pending_text = "；".join(payload["pending_b_phase_fields"])
        self.assertIn("样板单成本归集", basis_text)
        self.assertNotIn("样衣成本与样衣偏差等待", pending_text)
        row = payload["items"][0]
        self.assertEqual(Decimal(str(row["sampleCost"])), Decimal("110.000000"))
        self.assertEqual(row["sampleGap"], "大货低于样衣")
        self.assertEqual(Decimal(str(row["bulkUnitCost"])), Decimal("11.400000"))

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
                LyBomOperation(
                    id=4,
                    bom_id=int(bom.id),
                    process_name="外协压胶",
                    sequence_no=2,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("2"),
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
        profit_payload = profit_response.json()["data"]
        basis_text = "；".join(profit_payload["data_basis"])
        self.assertIn("BOM 用量", basis_text)
        self.assertIn("本地采购单价", basis_text)
        self.assertIn("工序工价预测", basis_text)
        profit_row = profit_payload["items"][0]
        self.assertEqual(profit_row["sourceType"], "bom_purchase_estimate")
        self.assertEqual(profit_row["sourceLabel"], "BOM/采购价估算")
        self.assertEqual(profit_row["sourceStatus"], "estimated")
        self.assertFalse(profit_row["hasSnapshot"])
        self.assertTrue(profit_row["isEstimated"])
        self.assertEqual(profit_row["snapshotNo"], "")
        self.assertEqual(profit_row["costSourceStatus"], "estimated")
        self.assertEqual(Decimal(str(profit_row["materialCost"])), Decimal("797.50000000"))
        self.assertEqual(Decimal(str(profit_row["laborCost"])), Decimal("50.000000000000"))
        self.assertEqual(Decimal(str(profit_row["outsourceCost"])), Decimal("100.000000000000"))
        self.assertEqual(Decimal(str(profit_row["totalCost"])), Decimal("947.500000000000"))
        self.assertEqual(
            Decimal(str(profit_row["totalCost"])),
            Decimal(str(profit_row["materialCost"]))
            + Decimal(str(profit_row["laborCost"]))
            + Decimal(str(profit_row["outsourceCost"])),
        )
        self.assertEqual(Decimal(str(profit_row["profit"])), Decimal("52.500000000000"))

        material_response = self.client.get(
            "/api/production/report-suite?report_key=orderTrackingReport&company=COMP-A&keyword=SO-RPT-PUR",
            headers=self._headers(),
        )
        self.assertEqual(material_response.status_code, 200, material_response.text)
        material_row = material_response.json()["data"]["items"][0]
        self.assertEqual(material_row["sourceType"], "bom_purchase_estimate")
        self.assertEqual(material_row["sourceLabel"], "BOM/采购价估算")
        self.assertEqual(material_row["sourceStatus"], "estimated")
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
