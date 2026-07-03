"""Tests for order quoted gross-profit projection analysis."""

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
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionQuote
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.finance import get_db_session as finance_db_dep


class FinanceOrderProfitAnalysisTest(unittest.TestCase):
    """Validate the boss-facing quoted gross-profit page data contract."""

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
        ProductionBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[finance_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(finance_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyProductionQuote).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.commit()
        self._seed_orders()

    @staticmethod
    def _headers(role: str = "Finance Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "finance.profit.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": "FIN-ORDER-PROFIT-REQ",
        }

    def _seed_order(
        self,
        *,
        order_id: int,
        sales_order: str,
        style_no: str,
        style_name: str,
        sales_amount: Decimal,
        plan_status: str,
        quote_status: str | None,
        material_cost: Decimal = Decimal("0"),
        labor_cost: Decimal = Decimal("0"),
        management_fee: Decimal = Decimal("0"),
        other_fee: Decimal = Decimal("0"),
        transaction_date: date = date(2026, 6, 20),
    ) -> None:
        plan_id = order_id + 1000
        with self.SessionLocal() as session:
            session.add(
                LySalesOrder(
                    id=order_id,
                    sales_order_no=sales_order,
                    source_order_ref=sales_order,
                    company="COMP-FIN",
                    customer=f"客户{style_no[-1]}",
                    status="planned",
                    docstatus=1,
                    transaction_date=transaction_date,
                    delivery_date=date(2026, 7, 20),
                    currency="CNY",
                    grand_total=sales_amount,
                    quote_status="已核价" if quote_status in {"quoted", "converted"} else "未核价",
                    idempotency_key=f"idem-{sales_order}",
                    request_hash=f"hash-{sales_order}",
                    created_by="seed",
                )
            )
            session.add(
                LySalesOrderItem(
                    id=order_id + 100,
                    sales_order_id=order_id,
                    company="COMP-FIN",
                    line_no=1,
                    sales_order_item=f"{sales_order}-001",
                    item_code=style_no,
                    item_name=style_name,
                    color="黑",
                    size="M",
                    qty=Decimal("100"),
                    planned_qty=Decimal("100"),
                    delivered_qty=Decimal("0"),
                    ys_material_calc_state="已算料",
                    rate=sales_amount / Decimal("100") if sales_amount else Decimal("0"),
                    amount=sales_amount,
                    uom="件",
                    delivery_date=date(2026, 7, 20),
                )
            )
            session.add(
                LyProductionPlan(
                    id=plan_id,
                    plan_no=f"PP-{sales_order}",
                    company="COMP-FIN",
                    sales_order=sales_order,
                    sales_order_item=f"{sales_order}-001",
                    customer=f"客户{style_no[-1]}",
                    item_code=style_no,
                    bom_id=order_id + 2000,
                    bom_version="V1",
                    planned_qty=Decimal("100"),
                    planned_start_date=date(2026, 6, 25),
                    status=plan_status,
                    idempotency_key=f"idem-plan-{sales_order}",
                    request_hash=f"hash-plan-{sales_order}",
                    created_by="seed",
                )
            )
            if quote_status:
                total_cost = material_cost + labor_cost + management_fee + other_fee
                gross_profit = sales_amount - total_cost
                gross_margin_rate = Decimal("0") if sales_amount == 0 else (gross_profit / sales_amount) * Decimal("100")
                session.add(
                    LyProductionQuote(
                        id=order_id + 200,
                        quote_no=f"QT-{sales_order}",
                        company="COMP-FIN",
                        sales_order_id=order_id,
                        plan_id=plan_id,
                        plan_no=f"PP-{sales_order}",
                        sales_order=sales_order,
                        sales_order_item="整单",
                        customer=f"客户{style_no[-1]}",
                        item_code=style_no,
                        quote_qty=Decimal("100"),
                        material_cost=material_cost,
                        labor_cost=labor_cost,
                        management_fee=management_fee,
                        other_fee=other_fee,
                        quote_unit_price=sales_amount / Decimal("100") if sales_amount else Decimal("0"),
                        quote_amount=sales_amount,
                        gross_profit=gross_profit,
                        gross_margin_rate=gross_margin_rate,
                        quote_items_json=[],
                        currency="CNY",
                        status=quote_status,
                        remark="seed quote",
                        created_by="seed",
                    )
                )
            session.commit()

    def _seed_orders(self) -> None:
        self._seed_order(
            order_id=1001,
            sales_order="SO-FIN-NORMAL",
            style_no="JACKET-NORMAL",
            style_name="常规夹克",
            sales_amount=Decimal("10000"),
            plan_status="production_in_progress",
            quote_status="quoted",
            material_cost=Decimal("5000"),
            labor_cost=Decimal("1500"),
            management_fee=Decimal("300"),
            other_fee=Decimal("200"),
            transaction_date=date(2026, 6, 25),
        )
        self._seed_order(
            order_id=1002,
            sales_order="SO-FIN-LOW",
            style_no="JACKET-LOW",
            style_name="低毛利夹克",
            sales_amount=Decimal("10000"),
            plan_status="planned",
            quote_status="quoted",
            material_cost=Decimal("7000"),
            labor_cost=Decimal("1500"),
            management_fee=Decimal("300"),
            other_fee=Decimal("200"),
            transaction_date=date(2026, 6, 24),
        )
        self._seed_order(
            order_id=1003,
            sales_order="SO-FIN-NEG",
            style_no="JACKET-NEG",
            style_name="负毛利夹克",
            sales_amount=Decimal("10000"),
            plan_status="production_completed",
            quote_status="quoted",
            material_cost=Decimal("9000"),
            labor_cost=Decimal("2500"),
            management_fee=Decimal("300"),
            other_fee=Decimal("200"),
            transaction_date=date(2026, 6, 23),
        )
        self._seed_order(
            order_id=1004,
            sales_order="SO-FIN-MISSING",
            style_no="JACKET-MISSING",
            style_name="未核价夹克",
            sales_amount=Decimal("10000"),
            plan_status="material_checked",
            quote_status=None,
            transaction_date=date(2026, 6, 22),
        )
        self._seed_order(
            order_id=1005,
            sales_order="SO-FIN-DRAFT",
            style_no="JACKET-DRAFT",
            style_name="草稿核价夹克",
            sales_amount=Decimal("10000"),
            plan_status="planned",
            quote_status="draft",
            material_cost=Decimal("1"),
            labor_cost=Decimal("1"),
            transaction_date=date(2026, 6, 21),
        )
        self._seed_order(
            order_id=1006,
            sales_order="SO-FIN-ZERO",
            style_no="JACKET-ZERO",
            style_name="零销售额夹克",
            sales_amount=Decimal("0"),
            plan_status="planned",
            quote_status="quoted",
            material_cost=Decimal("100"),
            transaction_date=date(2026, 6, 20),
        )

    def test_analysis_uses_confirmed_quote_and_marks_profit_statuses(self) -> None:
        response = self.client.get(
            "/api/finance/order-profit-analysis?company=COMP-FIN&page_size=100",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        rows = {item["sales_order"]: item for item in payload["items"]}

        normal = rows["SO-FIN-NORMAL"]
        self.assertEqual(Decimal(str(normal["sales_amount"])), Decimal("10000.000000"))
        self.assertEqual(Decimal(str(normal["total_cost"])), Decimal("7000.000000"))
        self.assertEqual(Decimal(str(normal["gross_profit"])), Decimal("3000.000000"))
        self.assertEqual(Decimal(str(normal["gross_margin_rate"])), Decimal("30.000000"))
        self.assertEqual(normal["profit_status"], "正常")

        self.assertEqual(rows["SO-FIN-LOW"]["profit_status"], "低毛利")
        self.assertEqual(Decimal(str(rows["SO-FIN-LOW"]["gross_margin_rate"])), Decimal("10.000000"))
        self.assertEqual(rows["SO-FIN-NEG"]["profit_status"], "负毛利")
        self.assertEqual(Decimal(str(rows["SO-FIN-NEG"]["gross_profit"])), Decimal("-2000.000000"))

        missing = rows["SO-FIN-MISSING"]
        self.assertEqual(missing["profit_status"], "缺成本")
        self.assertIsNone(missing["material_cost"])
        self.assertIsNone(missing["total_cost"])
        self.assertIsNone(missing["gross_profit"])

        draft = rows["SO-FIN-DRAFT"]
        self.assertEqual(draft["profit_status"], "缺成本")
        self.assertEqual(draft["cost_source"], "missing_confirmed_quote")
        self.assertIsNone(draft["material_cost"])

        zero = rows["SO-FIN-ZERO"]
        self.assertEqual(zero["profit_status"], "缺销售额")
        self.assertEqual(Decimal(str(zero["sales_amount"])), Decimal("0.000000"))
        self.assertIsNone(zero["gross_margin_rate"])

        self.assertEqual(payload["summary"]["order_count"], 6)
        self.assertEqual(payload["summary"]["missing_cost_count"], 2)
        self.assertEqual(payload["summary"]["missing_sales_count"], 1)
        self.assertEqual(payload["summary"]["low_profit_count"], 1)
        self.assertEqual(payload["summary"]["negative_profit_count"], 1)

    def test_filters_keyword_production_profit_status_and_sorts(self) -> None:
        low_response = self.client.get(
            "/api/finance/order-profit-analysis?company=COMP-FIN&profit_status=低毛利",
            headers=self._headers(),
        )
        self.assertEqual(low_response.status_code, 200, low_response.text)
        low_rows = low_response.json()["data"]["items"]
        self.assertEqual([row["sales_order"] for row in low_rows], ["SO-FIN-LOW"])

        keyword_response = self.client.get(
            "/api/finance/order-profit-analysis?company=COMP-FIN&keyword=JACKET-NEG",
            headers=self._headers(),
        )
        self.assertEqual(keyword_response.status_code, 200, keyword_response.text)
        self.assertEqual(keyword_response.json()["data"]["items"][0]["sales_order"], "SO-FIN-NEG")

        production_response = self.client.get(
            "/api/finance/order-profit-analysis?company=COMP-FIN&production_status=production_in_progress",
            headers=self._headers(),
        )
        self.assertEqual(production_response.status_code, 200, production_response.text)
        self.assertEqual(production_response.json()["data"]["items"][0]["sales_order"], "SO-FIN-NORMAL")

        sort_response = self.client.get(
            "/api/finance/order-profit-analysis?company=COMP-FIN&sort_by=gross_profit&sort_order=asc&page_size=100",
            headers=self._headers(),
        )
        self.assertEqual(sort_response.status_code, 200, sort_response.text)
        sorted_orders = [row["sales_order"] for row in sort_response.json()["data"]["items"]]
        self.assertEqual(sorted_orders[0], "SO-FIN-NEG")
        self.assertIn(sorted_orders[-1], {"SO-FIN-MISSING", "SO-FIN-DRAFT"})


if __name__ == "__main__":
    unittest.main()
