"""Readonly finance analysis service."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.production import LyProductionPlan
from app.models.production import LyProductionQuote
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.schemas.finance import OrderProfitAnalysisItem
from app.schemas.finance import OrderProfitAnalysisListData
from app.schemas.finance import OrderProfitAnalysisSummary


CONFIRMED_QUOTE_STATUSES = {"quoted", "converted"}
PROFIT_STATUS_LABELS = {
    "normal": "正常",
    "low_profit": "低毛利",
    "negative_profit": "负毛利",
    "missing_cost": "缺成本",
    "missing_sales": "缺销售额",
}
PROFIT_STATUS_ALIASES = {
    "normal": "normal",
    "正常": "normal",
    "low": "low_profit",
    "low_profit": "low_profit",
    "低毛利": "low_profit",
    "negative": "negative_profit",
    "negative_profit": "negative_profit",
    "负毛利": "negative_profit",
    "missing_cost": "missing_cost",
    "缺成本": "missing_cost",
    "未核价": "missing_cost",
    "missing_sales": "missing_sales",
    "缺销售额": "missing_sales",
}


class FinanceAnalysisService:
    """Build readonly quoted gross-profit projection rows without financial posting."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_order_profit_analysis(
        self,
        *,
        company: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        customer: str | None = None,
        order_status: str | None = None,
        production_status: str | None = None,
        profit_status: str | None = None,
        keyword: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> OrderProfitAnalysisListData:
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 20), 1), 100)

        order_query = self.session.query(LySalesOrder)
        normalized_company = self._text(company)
        if normalized_company:
            order_query = order_query.filter(LySalesOrder.company == normalized_company)
        if from_date is not None:
            order_query = order_query.filter(LySalesOrder.transaction_date >= from_date)
        if to_date is not None:
            order_query = order_query.filter(LySalesOrder.transaction_date <= to_date)
        normalized_customer = self._text(customer)
        if normalized_customer:
            order_query = order_query.filter(LySalesOrder.customer.like(f"%{normalized_customer}%"))
        normalized_order_status = self._text(order_status)
        if normalized_order_status:
            order_query = order_query.filter(LySalesOrder.status == normalized_order_status)

        orders = order_query.order_by(LySalesOrder.transaction_date.desc(), LySalesOrder.id.desc()).all()
        order_ids = [int(order.id) for order in orders]
        item_map = self._sales_order_items(order_ids=order_ids)
        plan_status_map = self._production_statuses(orders=orders)
        quote_map = self._latest_confirmed_quotes(orders=orders)

        rows = [
            self._build_order_row(
                order=order,
                order_items=item_map.get(int(order.id), []),
                plan_statuses=plan_status_map.get((str(order.company), str(order.sales_order_no)), []),
                quote=quote_map.get((str(order.company), str(order.sales_order_no))),
            )
            for order in orders
        ]

        normalized_keyword = self._text(keyword).lower()
        if normalized_keyword:
            rows = [
                row
                for row in rows
                if normalized_keyword in row.sales_order.lower()
                or normalized_keyword in row.style_no.lower()
                or normalized_keyword in (row.customer or "").lower()
            ]

        normalized_production_status = self._text(production_status)
        if normalized_production_status:
            rows = [
                row
                for row in rows
                if row.production_status == normalized_production_status
                or row.production_status_label == normalized_production_status
            ]

        normalized_profit_status = self._normalize_profit_status_filter(profit_status)
        if normalized_profit_status:
            rows = [row for row in rows if row.profit_status_code == normalized_profit_status]

        rows = self._sort_rows(rows=rows, sort_by=sort_by, sort_order=sort_order)
        total = len(rows)
        start = (page - 1) * page_size
        paged = rows[start : start + page_size]
        return OrderProfitAnalysisListData(
            items=paged,
            total=total,
            page=page,
            page_size=page_size,
            summary=self._summary(rows),
        )

    def _sales_order_items(self, *, order_ids: list[int]) -> dict[int, list[LySalesOrderItem]]:
        if not order_ids:
            return {}
        rows = (
            self.session.query(LySalesOrderItem)
            .filter(LySalesOrderItem.sales_order_id.in_(order_ids))
            .order_by(LySalesOrderItem.sales_order_id.asc(), LySalesOrderItem.line_no.asc(), LySalesOrderItem.id.asc())
            .all()
        )
        grouped: dict[int, list[LySalesOrderItem]] = defaultdict(list)
        for row in rows:
            grouped[int(row.sales_order_id)].append(row)
        return grouped

    def _production_statuses(self, *, orders: list[LySalesOrder]) -> dict[tuple[str, str], list[str]]:
        if not orders:
            return {}
        companies = sorted({str(order.company) for order in orders})
        sales_orders = sorted({str(order.sales_order_no) for order in orders})
        rows = (
            self.session.query(LyProductionPlan.company, LyProductionPlan.sales_order, LyProductionPlan.status)
            .filter(LyProductionPlan.company.in_(companies), LyProductionPlan.sales_order.in_(sales_orders))
            .all()
        )
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for company, sales_order, status in rows:
            grouped[(str(company), str(sales_order))].append(str(status or ""))
        return grouped

    def _latest_confirmed_quotes(self, *, orders: list[LySalesOrder]) -> dict[tuple[str, str], LyProductionQuote]:
        if not orders:
            return {}
        companies = sorted({str(order.company) for order in orders})
        sales_orders = sorted({str(order.sales_order_no) for order in orders})
        rows = (
            self.session.query(LyProductionQuote)
            .filter(
                LyProductionQuote.company.in_(companies),
                LyProductionQuote.sales_order.in_(sales_orders),
                LyProductionQuote.status.in_(sorted(CONFIRMED_QUOTE_STATUSES)),
            )
            .order_by(LyProductionQuote.created_at.desc(), LyProductionQuote.id.desc())
            .all()
        )
        latest: dict[tuple[str, str], LyProductionQuote] = {}
        for row in rows:
            key = (str(row.company), str(row.sales_order))
            if key not in latest:
                latest[key] = row
        return latest

    def _build_order_row(
        self,
        *,
        order: LySalesOrder,
        order_items: list[LySalesOrderItem],
        plan_statuses: list[str],
        quote: LyProductionQuote | None,
    ) -> OrderProfitAnalysisItem:
        style_nos = self._unique_texts(item.item_code for item in order_items)
        style_names = self._unique_texts(item.item_name for item in order_items)
        order_qty = self._money(sum((self._dec(item.qty) for item in order_items), Decimal("0")))
        sales_amount = self._money(order.grand_total)
        production_status, production_status_label = self._production_status(plan_statuses)

        material_cost: Decimal | None = None
        labor_cost: Decimal | None = None
        management_fee: Decimal | None = None
        other_fee: Decimal | None = None
        total_cost: Decimal | None = None
        gross_profit: Decimal | None = None
        gross_margin_rate: Decimal | None = None
        quote_no: str | None = None
        cost_source = "missing_confirmed_quote"

        if quote is not None:
            material_cost = self._money(quote.material_cost)
            labor_cost = self._money(quote.labor_cost)
            management_fee = self._money(quote.management_fee)
            other_fee = self._money(quote.other_fee)
            total_cost = self._money(material_cost + labor_cost + management_fee + other_fee)
            gross_profit = self._money(sales_amount - total_cost)
            gross_margin_rate = None if sales_amount <= Decimal("0") else self._money((gross_profit / sales_amount) * Decimal("100"))
            quote_no = str(quote.quote_no)
            cost_source = "confirmed_internal_quote"

        profit_status_code = self._profit_status(
            has_confirmed_quote=quote is not None,
            sales_amount=sales_amount,
            gross_profit=gross_profit,
            gross_margin_rate=gross_margin_rate,
        )

        return OrderProfitAnalysisItem(
            id=int(order.id),
            company=str(order.company),
            sales_order=str(order.sales_order_no),
            customer=order.customer,
            style_no=" / ".join(style_nos) if style_nos else "-",
            style_name=" / ".join(style_names) if style_names else "-",
            order_qty=order_qty,
            order_date=order.transaction_date,
            delivery_date=order.delivery_date,
            order_status=str(order.status),
            production_status=production_status,
            production_status_label=production_status_label,
            sales_amount=sales_amount,
            material_cost=material_cost,
            labor_cost=labor_cost,
            management_fee=management_fee,
            other_fee=other_fee,
            total_cost=total_cost,
            gross_profit=gross_profit,
            gross_margin_rate=gross_margin_rate,
            profit_status=PROFIT_STATUS_LABELS[profit_status_code],
            profit_status_code=profit_status_code,
            quote_no=quote_no,
            cost_source=cost_source,
        )

    @classmethod
    def _profit_status(
        cls,
        *,
        has_confirmed_quote: bool,
        sales_amount: Decimal,
        gross_profit: Decimal | None,
        gross_margin_rate: Decimal | None,
    ) -> str:
        if not has_confirmed_quote:
            return "missing_cost"
        if sales_amount <= Decimal("0"):
            return "missing_sales"
        if gross_profit is not None and gross_profit < Decimal("0"):
            return "negative_profit"
        if gross_margin_rate is not None and gross_margin_rate < Decimal("15"):
            return "low_profit"
        return "normal"

    @classmethod
    def _production_status(cls, statuses: list[str]) -> tuple[str, str]:
        normalized = {status.strip() for status in statuses if status and status.strip()}
        if not normalized:
            return "not_planned", "未排产"
        if normalized == {"production_completed"}:
            return "production_completed", "生产完成"
        if "production_in_progress" in normalized:
            return "production_in_progress", "生产中"
        if "production_completed" in normalized:
            return "mixed", "部分完成"
        if "material_issued" in normalized:
            return "material_issued", "已领料"
        if "material_checked" in normalized:
            return "material_checked", "已齐料"
        if "job_cards_synced" in normalized:
            return "job_cards_synced", "已同步工票"
        if "work_order_created" in normalized or "work_order_pending" in normalized:
            return "work_order_created", "已生成工单"
        if "planned" in normalized:
            return "planned", "已排产"
        first = sorted(normalized)[0]
        return first, first

    @staticmethod
    def _unique_texts(values: Any) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = FinanceAnalysisService._text(value)
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @classmethod
    def _sort_rows(
        cls,
        *,
        rows: list[OrderProfitAnalysisItem],
        sort_by: str | None,
        sort_order: str | None,
    ) -> list[OrderProfitAnalysisItem]:
        field_map = {
            "order_date": "order_date",
            "sales_amount": "sales_amount",
            "total_cost": "total_cost",
            "gross_profit": "gross_profit",
            "gross_margin_rate": "gross_margin_rate",
        }
        attr = field_map.get(cls._text(sort_by) or "order_date", "order_date")
        descending = (cls._text(sort_order) or "desc").lower() != "asc"

        with_value = [row for row in rows if getattr(row, attr) is not None]
        missing = [row for row in rows if getattr(row, attr) is None]
        with_value.sort(key=lambda row: getattr(row, attr), reverse=descending)
        return with_value + missing

    @classmethod
    def _summary(cls, rows: list[OrderProfitAnalysisItem]) -> OrderProfitAnalysisSummary:
        return OrderProfitAnalysisSummary(
            order_count=len(rows),
            analyzed_count=sum(1 for row in rows if row.cost_source == "confirmed_internal_quote" and row.sales_amount > Decimal("0")),
            missing_cost_count=sum(1 for row in rows if row.profit_status_code == "missing_cost"),
            missing_sales_count=sum(1 for row in rows if row.profit_status_code == "missing_sales"),
            low_profit_count=sum(1 for row in rows if row.profit_status_code == "low_profit"),
            negative_profit_count=sum(1 for row in rows if row.profit_status_code == "negative_profit"),
            sales_amount=cls._money(sum((row.sales_amount for row in rows), Decimal("0"))),
            total_cost=cls._money(sum((row.total_cost or Decimal("0") for row in rows), Decimal("0"))),
            gross_profit=cls._money(sum((row.gross_profit or Decimal("0") for row in rows), Decimal("0"))),
        )

    @staticmethod
    def _normalize_profit_status_filter(value: str | None) -> str:
        text = FinanceAnalysisService._text(value)
        if not text:
            return ""
        return PROFIT_STATUS_ALIASES.get(text, PROFIT_STATUS_ALIASES.get(text.lower(), text.lower()))

    @staticmethod
    def _text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _dec(value: Any) -> Decimal:
        return Decimal(str(value or 0))

    @staticmethod
    def _money(value: Any) -> Decimal:
        return Decimal(str(value or 0)).quantize(Decimal("0.000001"))
