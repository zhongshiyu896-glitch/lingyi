"""Dashboard overview read-only aggregation service (TASK-060A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import os
from threading import RLock
from time import monotonic
from typing import Any

from fastapi import Request
from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import distinct
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.production import LyProductionPlan
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.sales_order import LySalesPaymentEntry
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.schemas.dashboard import DashboardHomeChartData
from app.schemas.dashboard import DashboardHomeChartPointData
from app.schemas.dashboard import DashboardHomeChartSeriesData
from app.schemas.dashboard import DashboardOverviewData
from app.schemas.dashboard import DashboardKanbanData
from app.schemas.dashboard import DashboardKanbanFlowLinkData
from app.schemas.dashboard import DashboardKanbanFlowNodeData
from app.schemas.dashboard import DashboardHomeMetricCardData
from app.schemas.dashboard import DashboardHomeOverviewData
from app.schemas.dashboard import DashboardHomeTodoItemData
from app.schemas.dashboard import DashboardKanbanMessageRowData
from app.schemas.dashboard import DashboardQualityOverviewData
from app.schemas.dashboard import DashboardSalesInventoryOverviewData
from app.schemas.dashboard import DashboardSourceStatusData
from app.schemas.dashboard import DashboardWarehouseOverviewData
from app.services.quality_service import QualityService
from app.services.warehouse_service import WarehouseService


@dataclass(slots=True)
class DashboardSourceUnavailableError(Exception):
    """Raised when one required dashboard source cannot provide data."""

    module: str
    message: str
    status_code: int = 503


@dataclass(slots=True)
class DashboardOverviewCacheResult:
    """Result wrapper used by the router to expose cache evidence headers."""

    data: DashboardOverviewData
    cache_status: str
    ttl_seconds: int


@dataclass(slots=True)
class _DashboardOverviewCacheEntry:
    """Short-lived in-process dashboard cache entry."""

    expires_at: float
    data: DashboardOverviewData


_DASHBOARD_OVERVIEW_CACHE_LOCK = RLock()
_DASHBOARD_OVERVIEW_CACHE: dict[
    tuple[str, str | None, str | None, str | None, str | None, str | None],
    _DashboardOverviewCacheEntry,
] = {}


class DashboardService:
    """Compose quality/sales-inventory/warehouse summaries under fail-closed policy."""

    def __init__(self, *, session: Session, request_obj: Request):
        self.session = session
        self.request_obj = request_obj
        self.quality_service = QualityService(session=session)
        self.warehouse_service = WarehouseService(session=session)

    @classmethod
    def get_cached_overview(
        cls,
        *,
        session: Session,
        request_obj: Request,
        company: str,
        from_date: date | None,
        to_date: date | None,
        item_code: str | None,
        warehouse: str | None,
        keyword: str | None = None,
    ) -> DashboardOverviewCacheResult:
        ttl_seconds = cls._overview_cache_ttl_seconds()
        cache_key = cls._overview_cache_key(
            company=company,
            from_date=from_date,
            to_date=to_date,
            item_code=item_code,
            warehouse=warehouse,
            keyword=keyword,
        )
        if cls._overview_cache_enabled():
            now = monotonic()
            with _DASHBOARD_OVERVIEW_CACHE_LOCK:
                entry = _DASHBOARD_OVERVIEW_CACHE.get(cache_key)
                if entry is not None and entry.expires_at > now:
                    return DashboardOverviewCacheResult(data=entry.data, cache_status="hit", ttl_seconds=ttl_seconds)
                if entry is not None:
                    _DASHBOARD_OVERVIEW_CACHE.pop(cache_key, None)

        data = cls(session=session, request_obj=request_obj).get_overview(
            company=company,
            from_date=from_date,
            to_date=to_date,
            item_code=item_code,
            warehouse=warehouse,
            keyword=keyword,
        )
        if cls._overview_cache_enabled():
            with _DASHBOARD_OVERVIEW_CACHE_LOCK:
                _DASHBOARD_OVERVIEW_CACHE[cache_key] = _DashboardOverviewCacheEntry(
                    expires_at=monotonic() + ttl_seconds,
                    data=data,
                )
        return DashboardOverviewCacheResult(data=data, cache_status="miss", ttl_seconds=ttl_seconds)

    @staticmethod
    def clear_overview_cache() -> None:
        with _DASHBOARD_OVERVIEW_CACHE_LOCK:
            _DASHBOARD_OVERVIEW_CACHE.clear()

    @staticmethod
    def _overview_cache_enabled() -> bool:
        if os.getenv("APP_ENV", "").strip().lower() == "test":
            return False
        return os.getenv("LINGYI_DASHBOARD_OVERVIEW_CACHE_DISABLED", "").strip().lower() not in {"1", "true", "yes"}

    @staticmethod
    def _overview_cache_ttl_seconds() -> int:
        raw_value = os.getenv("LINGYI_DASHBOARD_OVERVIEW_CACHE_TTL_SECONDS", "45")
        try:
            ttl_seconds = int(raw_value)
        except ValueError:
            ttl_seconds = 45
        return min(60, max(30, ttl_seconds))

    @staticmethod
    def _overview_cache_key(
        *,
        company: str,
        from_date: date | None,
        to_date: date | None,
        item_code: str | None,
        warehouse: str | None,
        keyword: str | None,
    ) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
        return (
            company,
            from_date.isoformat() if from_date else None,
            to_date.isoformat() if to_date else None,
            item_code,
            warehouse,
            keyword,
        )

    def get_overview(
        self,
        *,
        company: str,
        from_date: date | None,
        to_date: date | None,
        item_code: str | None,
        warehouse: str | None,
        keyword: str | None = None,
    ) -> DashboardOverviewData:
        source_status: list[DashboardSourceStatusData] = []

        quality = self._build_quality_summary(
            company=company,
            from_date=from_date,
            to_date=to_date,
            item_code=item_code,
            warehouse=warehouse,
        )
        source_status.append(DashboardSourceStatusData(module="quality", status="ok"))

        sales_inventory = self._build_sales_inventory_summary(
            company=company,
            item_code=item_code,
            warehouse=warehouse,
        )
        source_status.append(DashboardSourceStatusData(module="sales_inventory", status="ok"))

        warehouse_summary = self._build_warehouse_summary(
            company=company,
            item_code=item_code,
            warehouse=warehouse,
        )
        source_status.append(DashboardSourceStatusData(module="warehouse", status="ok"))

        kanban = self._build_kanban_data(
            company=company,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
        )
        home_overview = self._build_home_overview(
            company=company,
            from_date=from_date,
            to_date=to_date,
            quality=quality,
            sales_inventory=sales_inventory,
            warehouse=warehouse_summary,
            kanban=kanban,
        )
        source_status.append(
            DashboardSourceStatusData(
                module="dashboard_business",
                status="ok",
                source_note="经营指标、环比和趋势图来自本地只读聚合表。",
            )
        )
        source_status.append(
            DashboardSourceStatusData(
                module="dashboard_config",
                status="ok",
                source_type="config",
                source_note="看板流程节点、快捷筛选、按钮文案为系统配置项，不代表业务闭环完成。",
            )
        )

        return DashboardOverviewData(
            company=company,
            from_date=from_date,
            to_date=to_date,
            generated_at=datetime.now(UTC),
            quality=quality,
            sales_inventory=sales_inventory,
            warehouse=warehouse_summary,
            source_status=source_status,
            kanban=kanban,
            home_overview=home_overview,
        )

    def _build_home_overview(
        self,
        *,
        company: str,
        from_date: date | None,
        to_date: date | None,
        quality: DashboardQualityOverviewData,
        sales_inventory: DashboardSalesInventoryOverviewData,
        warehouse: DashboardWarehouseOverviewData,
        kanban: DashboardKanbanData,
    ) -> DashboardHomeOverviewData:
        period_start, period_end = self._home_period(from_date=from_date, to_date=to_date)
        previous_start, previous_end = self._previous_period(period_start=period_start, period_end=period_end)
        try:
            current_totals, previous_totals = self._build_business_metric_totals_pair(
                company=company,
                period_start=period_start,
                period_end=period_end,
                previous_start=previous_start,
                previous_end=previous_end,
            )
            charts = self._build_home_charts(company=company, end_date=period_end)
        except SQLAlchemyError as exc:
            raise self._source_unavailable(module="dashboard_business", exc=exc) from exc

        pass_rate_percent = (quality.pass_rate * Decimal("100")).quantize(Decimal("0.01"))
        sales_total = DashboardService._decimal_or_zero(sales_inventory.total_actual_qty)
        warning_total = int(warehouse.warning_alert_count) + int(warehouse.critical_alert_count)
        pending_count = sum(1 for row in kanban.messages if row.status != "已读")
        overdue_count = sum(1 for row in kanban.messages if row.overdue == "是")

        metric_cards = [
            DashboardHomeMetricCardData(
                key="monthly_order_count",
                label="本月订单数",
                value=str(int(current_totals["order_count"])),
                unit="单",
                trend=self._period_trend(current_totals["order_count"], previous_totals["order_count"]),
                group="business",
                route="/production/productOrder",
            ),
            DashboardHomeMetricCardData(
                key="monthly_sales_amount",
                label="本月销售额",
                value=self._format_decimal(current_totals["sales_amount"]),
                unit="元",
                trend=self._period_trend(current_totals["sales_amount"], previous_totals["sales_amount"]),
                group="business",
                route="/production/productOrder",
            ),
            DashboardHomeMetricCardData(
                key="receivable_balance",
                label="应收余额",
                value=self._format_decimal(current_totals["receivable_balance"]),
                unit="元",
                trend="—",
                group="business",
                route="/production/receivablePayment",
                source_note="余额来自未取消发货开票的 outstanding_amount 当前值。",
            ),
            DashboardHomeMetricCardData(
                key="payable_balance",
                label="应付余额",
                value=self._format_decimal(current_totals["payable_balance"]),
                unit="元",
                trend="—",
                group="business",
                route="/materialPurchase/purchaseInvoicePayable",
                source_note="余额来自未取消采购发票的 outstanding_amount 当前值。",
            ),
            DashboardHomeMetricCardData(
                key="in_production_order_count",
                label="在产订单数",
                value=str(int(current_totals["in_production_order_count"])),
                unit="单",
                trend="—",
                group="business",
                route="/production/orderTrackingV2",
            ),
            DashboardHomeMetricCardData(
                key="delivery_warning_count",
                label="交期预警",
                value=str(int(current_totals["delivery_warning_count"])),
                unit="单",
                trend="—",
                group="business",
                route="/production/productOrder",
                source_note="统计临近 7 天或已超期且未完全交付的订单。",
            ),
            DashboardHomeMetricCardData(
                key="monthly_gross_profit",
                label="本月毛利",
                value=self._format_decimal(current_totals["gross_profit"])
                if current_totals["gross_profit_status"] == "complete"
                else "—",
                unit="元",
                trend=self._period_trend(current_totals["gross_profit"], previous_totals["gross_profit"])
                if current_totals["gross_profit_status"] == "complete"
                else "—",
                group="business",
                route="/reports/style-profit",
                status=str(current_totals["gross_profit_status"]),
                source_note="仅当本期存在 complete 利润快照时展示。",
            ),
            DashboardHomeMetricCardData(
                key="inspection_count",
                label="质检单量",
                value=str(int(quality.inspection_count)),
                unit="单",
                trend="—",
                group="quality",
                route="/quality/inspections",
            ),
            DashboardHomeMetricCardData(
                key="inventory_qty",
                label="库存总量",
                value=self._format_decimal(sales_total),
                unit="件",
                trend="—",
                group="inventory",
                route="/materialStock/materialTypeStock",
            ),
            DashboardHomeMetricCardData(
                key="quality_pass_rate",
                label="质检通过率",
                value=self._format_decimal(pass_rate_percent),
                unit="%",
                trend="—",
                group="quality",
                route="/quality/inspections",
            ),
            DashboardHomeMetricCardData(
                key="warehouse_alerts",
                label="仓储预警",
                value=str(int(warehouse.alert_count)),
                unit="条",
                trend="—",
                group="inventory",
                route="/materialStock/materialTypeStock",
            ),
        ]

        todo_items = [
            DashboardHomeTodoItemData(
                key="pending_messages",
                title="待处理动态",
                count=pending_count,
                status="normal" if pending_count == 0 else "warning",
                action_label="查看动态",
                route="/production/home",
            ),
            DashboardHomeTodoItemData(
                key="overdue_orders",
                title="超期订单",
                count=overdue_count,
                status="normal" if overdue_count == 0 else "urgent",
                action_label="查看跟进",
                route="/production/productOrder",
            ),
            DashboardHomeTodoItemData(
                key="warehouse_warning",
                title="仓储预警",
                count=warning_total,
                status="normal" if warning_total == 0 else "warning",
                action_label="查看仓储",
                route="/materialStock/materialTypeStock",
            ),
        ]

        business_summary = [
            f"{period_start.strftime('%m-%d')} 至 {period_end.strftime('%m-%d')} 订单 {int(current_totals['order_count'])} 单",
            f"本期销售额 {self._format_decimal(current_totals['sales_amount'])} 元",
            f"应收余额 {self._format_decimal(current_totals['receivable_balance'])} 元",
            f"应付余额 {self._format_decimal(current_totals['payable_balance'])} 元",
            f"在产订单 {int(current_totals['in_production_order_count'])} 单",
            f"交期预警 {int(current_totals['delivery_warning_count'])} 单",
            f"质检通过率 {pass_rate_percent}%",
            f"低于安全库存款号 {int(sales_inventory.below_safety_count)} 个",
            f"低于补货线款号 {int(sales_inventory.below_reorder_count)} 个",
            f"仓储高危预警 {int(warehouse.critical_alert_count)} 条",
        ]

        recent_activities = [
            f"{row.sent_at.astimezone(UTC).strftime('%m-%d %H:%M')} {row.title}（{row.order_no}）"
            for row in kanban.messages[:5]
        ]

        warnings: list[str] = []
        if overdue_count > 0:
            warnings.append(f"存在 {overdue_count} 条超期订单动态")
        if int(current_totals["delivery_warning_count"]) > 0:
            warnings.append(f"交期临近或超期订单 {int(current_totals['delivery_warning_count'])} 单")
        if int(sales_inventory.below_reorder_count) > 0:
            warnings.append(f"低于补货线款号 {int(sales_inventory.below_reorder_count)} 个")
        if int(warehouse.critical_alert_count) > 0:
            warnings.append(f"仓储高危预警 {int(warehouse.critical_alert_count)} 条")
        elif warning_total > 0:
            warnings.append(f"仓储预警 {warning_total} 条")

        return DashboardHomeOverviewData(
            summary_title="首页经营总览（P1）",
            metric_cards=metric_cards,
            todo_items=todo_items,
            warnings=warnings,
            business_summary=business_summary,
            recent_activities=recent_activities,
            trend_points=[],
            charts=charts,
            primary_actions=["查看动态", "刷新指标", "导出概览"],
        )

    @staticmethod
    def _home_period(*, from_date: date | None, to_date: date | None) -> tuple[date, date]:
        period_end = to_date or datetime.now(UTC).date()
        period_start = from_date or period_end.replace(day=1)
        return period_start, period_end

    @staticmethod
    def _previous_period(*, period_start: date, period_end: date) -> tuple[date, date]:
        span_days = max((period_end - period_start).days, 0)
        previous_end = period_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=span_days)
        return previous_start, previous_end

    @staticmethod
    def _empty_business_metric_totals() -> dict[str, Decimal | str]:
        return {
            "order_count": Decimal("0"),
            "sales_amount": Decimal("0"),
            "receivable_balance": Decimal("0"),
            "payable_balance": Decimal("0"),
            "in_production_order_count": Decimal("0"),
            "delivery_warning_count": Decimal("0"),
            "gross_profit": Decimal("0"),
            "gross_profit_status": "incomplete",
        }

    def _build_business_metric_totals_pair(
        self,
        *,
        company: str,
        period_start: date,
        period_end: date,
        previous_start: date,
        previous_end: date,
    ) -> tuple[dict[str, Decimal | str], dict[str, Decimal | str]]:
        current_totals = self._empty_business_metric_totals()
        previous_totals = self._empty_business_metric_totals()

        if self._has_tables({LySalesOrder.__tablename__}):
            current_order_window = and_(
                LySalesOrder.transaction_date >= period_start,
                LySalesOrder.transaction_date <= period_end,
            )
            previous_order_window = and_(
                LySalesOrder.transaction_date >= previous_start,
                LySalesOrder.transaction_date <= previous_end,
            )
            sales_row = (
                self.session.query(
                    func.coalesce(func.sum(case((current_order_window, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((current_order_window, LySalesOrder.grand_total), else_=0)), 0),
                    func.coalesce(func.sum(case((previous_order_window, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((previous_order_window, LySalesOrder.grand_total), else_=0)), 0),
                )
                .filter(
                    LySalesOrder.company == company,
                    LySalesOrder.status != "cancelled",
                    LySalesOrder.transaction_date.isnot(None),
                    LySalesOrder.transaction_date >= previous_start,
                    LySalesOrder.transaction_date <= period_end,
                )
                .one()
            )
            current_totals["order_count"] = self._decimal_or_zero(sales_row[0])
            current_totals["sales_amount"] = self._decimal_or_zero(sales_row[1])
            previous_totals["order_count"] = self._decimal_or_zero(sales_row[2])
            previous_totals["sales_amount"] = self._decimal_or_zero(sales_row[3])

        if self._has_tables({LyDeliveryInvoice.__tablename__}):
            receivable = (
                self.session.query(func.coalesce(func.sum(LyDeliveryInvoice.outstanding_amount), 0))
                .filter(LyDeliveryInvoice.company == company, LyDeliveryInvoice.status != "cancelled")
                .scalar()
            )
            current_totals["receivable_balance"] = self._decimal_or_zero(receivable)

        if self._has_tables({LyMaterialPurchaseInvoice.__tablename__}):
            payable = (
                self.session.query(func.coalesce(func.sum(LyMaterialPurchaseInvoice.outstanding_amount), 0))
                .filter(LyMaterialPurchaseInvoice.company == company, LyMaterialPurchaseInvoice.status != "cancelled")
                .scalar()
            )
            current_totals["payable_balance"] = self._decimal_or_zero(payable)

        if self._has_tables({LyProductionPlan.__tablename__}):
            in_production = (
                self.session.query(func.count(distinct(LyProductionPlan.sales_order)))
                .filter(
                    LyProductionPlan.company == company,
                    LyProductionPlan.status.notin_(
                        [
                            "cancelled",
                            "completed",
                            "finished",
                            "closed",
                            "done",
                        ]
                    ),
                )
                .scalar()
            )
            current_totals["in_production_order_count"] = self._decimal_or_zero(in_production)

        if self._has_tables({LySalesOrder.__tablename__, LySalesOrderItem.__tablename__}):
            delivery_date_expr = func.coalesce(LySalesOrderItem.delivery_date, LySalesOrder.delivery_date)
            warning_deadline = period_end + timedelta(days=7)
            delivery_warnings = (
                self.session.query(func.count(distinct(LySalesOrder.id)))
                .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
                .filter(
                    LySalesOrder.company == company,
                    LySalesOrder.status != "cancelled",
                    delivery_date_expr.isnot(None),
                    delivery_date_expr <= warning_deadline,
                    LySalesOrderItem.delivered_qty < LySalesOrderItem.qty,
                )
                .scalar()
            )
            current_totals["delivery_warning_count"] = self._decimal_or_zero(delivery_warnings)

        if self._has_tables({LyStyleProfitSnapshot.__tablename__}):
            current_profit_overlap = and_(
                or_(LyStyleProfitSnapshot.to_date.is_(None), LyStyleProfitSnapshot.to_date >= period_start),
                or_(LyStyleProfitSnapshot.from_date.is_(None), LyStyleProfitSnapshot.from_date <= period_end),
            )
            previous_profit_overlap = and_(
                or_(LyStyleProfitSnapshot.to_date.is_(None), LyStyleProfitSnapshot.to_date >= previous_start),
                or_(LyStyleProfitSnapshot.from_date.is_(None), LyStyleProfitSnapshot.from_date <= previous_end),
            )
            profit_row = (
                self.session.query(
                    func.coalesce(func.sum(case((current_profit_overlap, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((current_profit_overlap, LyStyleProfitSnapshot.profit_amount), else_=0)), 0),
                    func.coalesce(func.sum(case((previous_profit_overlap, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((previous_profit_overlap, LyStyleProfitSnapshot.profit_amount), else_=0)), 0),
                )
                .filter(
                    LyStyleProfitSnapshot.company == company,
                    LyStyleProfitSnapshot.snapshot_status == "complete",
                    or_(current_profit_overlap, previous_profit_overlap),
                )
                .one()
            )
            if int(profit_row[0] or 0) > 0:
                current_totals["gross_profit"] = self._decimal_or_zero(profit_row[1])
                current_totals["gross_profit_status"] = "complete"
            if int(profit_row[2] or 0) > 0:
                previous_totals["gross_profit"] = self._decimal_or_zero(profit_row[3])
                previous_totals["gross_profit_status"] = "complete"

        return current_totals, previous_totals

    def _build_home_charts(self, *, company: str, end_date: date) -> list[DashboardHomeChartData]:
        start_date = end_date - timedelta(days=29)
        charts: list[DashboardHomeChartData] = []

        if self._has_tables({LySalesOrder.__tablename__}):
            sales_points = self._empty_daily_points(start_date=start_date, end_date=end_date, keys=["sales_amount"])
            rows = (
                self.session.query(
                    LySalesOrder.transaction_date,
                    func.coalesce(func.sum(LySalesOrder.grand_total), 0),
                )
                .filter(
                    LySalesOrder.company == company,
                    LySalesOrder.status != "cancelled",
                    LySalesOrder.transaction_date.isnot(None),
                    LySalesOrder.transaction_date >= start_date,
                    LySalesOrder.transaction_date <= end_date,
                )
                .group_by(LySalesOrder.transaction_date)
                .all()
            )
            for bucket_date, amount in rows:
                self._put_chart_value(sales_points, bucket_date, "sales_amount", self._decimal_or_zero(amount))
            charts.append(
                DashboardHomeChartData(
                    key="sales_amount_trend",
                    title="近30天销售额",
                    chart_type="line",
                    unit="元",
                    source_note="销售订单 grand_total 按 transaction_date 汇总。",
                    series=[DashboardHomeChartSeriesData(key="sales_amount", label="销售额", unit="元")],
                    points=self._chart_points_from_daily_map(sales_points),
                )
            )

        if self._has_tables({LyWarehouseStockLedgerEntry.__tablename__}):
            stock_points = self._empty_daily_points(start_date=start_date, end_date=end_date, keys=["inbound_qty", "outbound_qty"])
            rows = (
                self.session.query(
                    LyWarehouseStockLedgerEntry.posting_date,
                    func.coalesce(
                        func.sum(
                            case(
                                (LyWarehouseStockLedgerEntry.actual_qty > 0, LyWarehouseStockLedgerEntry.actual_qty),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (LyWarehouseStockLedgerEntry.actual_qty < 0, -LyWarehouseStockLedgerEntry.actual_qty),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                )
                .filter(
                    LyWarehouseStockLedgerEntry.company == company,
                    LyWarehouseStockLedgerEntry.status == "active",
                    LyWarehouseStockLedgerEntry.posting_date >= start_date,
                    LyWarehouseStockLedgerEntry.posting_date <= end_date,
                )
                .group_by(LyWarehouseStockLedgerEntry.posting_date)
                .all()
            )
            for bucket_date, inbound_qty, outbound_qty in rows:
                self._put_chart_value(stock_points, bucket_date, "inbound_qty", self._decimal_or_zero(inbound_qty))
                self._put_chart_value(stock_points, bucket_date, "outbound_qty", self._decimal_or_zero(outbound_qty))
            charts.append(
                DashboardHomeChartData(
                    key="stock_movement_trend",
                    title="近30天入库/出库量",
                    chart_type="line",
                    unit="件",
                    source_note="库存流水 actual_qty 按 posting_date 汇总，正数为入库，负数取绝对值为出库。",
                    series=[
                        DashboardHomeChartSeriesData(key="inbound_qty", label="入库量", unit="件"),
                        DashboardHomeChartSeriesData(key="outbound_qty", label="出库量", unit="件"),
                    ],
                    points=self._chart_points_from_daily_map(stock_points),
                )
            )

        if self._has_tables({LySalesPaymentEntry.__tablename__}):
            payment_points = self._empty_daily_points(start_date=start_date, end_date=end_date, keys=["paid_amount"])
            rows = (
                self.session.query(
                    LySalesPaymentEntry.posting_date,
                    func.coalesce(func.sum(LySalesPaymentEntry.paid_amount), 0),
                )
                .filter(
                    LySalesPaymentEntry.company == company,
                    LySalesPaymentEntry.status == "submitted",
                    LySalesPaymentEntry.posting_date >= start_date,
                    LySalesPaymentEntry.posting_date <= end_date,
                )
                .group_by(LySalesPaymentEntry.posting_date)
                .all()
            )
            for bucket_date, paid_amount in rows:
                self._put_chart_value(payment_points, bucket_date, "paid_amount", self._decimal_or_zero(paid_amount))
            charts.append(
                DashboardHomeChartData(
                    key="receivable_collection_trend",
                    title="近30天回款",
                    chart_type="line",
                    unit="元",
                    source_note="销售回款 paid_amount 按 posting_date 汇总。",
                    series=[DashboardHomeChartSeriesData(key="paid_amount", label="回款", unit="元")],
                    points=self._chart_points_from_daily_map(payment_points),
                )
            )

        return charts

    @staticmethod
    def _empty_daily_points(*, start_date: date, end_date: date, keys: list[str]) -> dict[date, dict[str, Decimal]]:
        span_days = max((end_date - start_date).days, 0)
        return {
            start_date + timedelta(days=offset): {key: Decimal("0") for key in keys}
            for offset in range(span_days + 1)
        }

    @staticmethod
    def _put_chart_value(points: dict[date, dict[str, Decimal]], bucket_date: date | None, key: str, value: Decimal) -> None:
        if bucket_date is None or bucket_date not in points:
            return
        points[bucket_date][key] = value

    @staticmethod
    def _chart_points_from_daily_map(points: dict[date, dict[str, Decimal]]) -> list[DashboardHomeChartPointData]:
        return [
            DashboardHomeChartPointData(period=bucket_date.isoformat(), values=values)
            for bucket_date, values in sorted(points.items())
        ]

    @classmethod
    def _period_trend(cls, current: Decimal | int | str, previous: Decimal | int | str) -> str:
        current_value = cls._decimal_or_zero(current)
        previous_value = cls._decimal_or_zero(previous)
        if previous_value <= Decimal("0"):
            return "—"
        delta = ((current_value - previous_value) / previous_value * Decimal("100")).quantize(Decimal("0.01"))
        sign = "+" if delta > Decimal("0") else ""
        return f"较上期 {sign}{cls._format_decimal(delta)}%"

    @staticmethod
    def _format_decimal(value: Decimal | int | str) -> str:
        decimal_value = DashboardService._decimal_or_zero(value)
        text = format(decimal_value, "f")
        if "." not in text:
            return text
        return text.rstrip("0").rstrip(".") or "0"

    def _build_kanban_data(
        self,
        *,
        company: str,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
    ) -> DashboardKanbanData:
        messages = self._build_local_kanban_messages(company=company)

        if from_date is not None:
            messages = [row for row in messages if row.sent_at.date() >= from_date]
        if to_date is not None:
            messages = [row for row in messages if row.sent_at.date() <= to_date]

        normalized_keyword = (keyword or "").strip().lower()
        if normalized_keyword:
            messages = [
                row
                for row in messages
                if normalized_keyword in (
                    f"{row.order_no}|{row.customer}|{row.style_no}|{row.style_name}|{row.title}".lower()
                )
            ]

        return DashboardKanbanData(
            board_name="大货看板",
            quick_filters=[
                "物料类型",
                "物料单位",
                "客户画像",
                "加工厂画像",
                "供应商画像",
                "样板单",
                "设计打样",
                "跟进模板",
                "大货看板",
            ],
            flow_nodes=[
                DashboardKanbanFlowNodeData(
                    key="quote",
                    label="报价单",
                    status="completed",
                    route="/production/productOrder",
                ),
                DashboardKanbanFlowNodeData(
                    key="order",
                    label="订单",
                    status="active",
                    route="/production/productOrder",
                ),
                DashboardKanbanFlowNodeData(
                    key="production_order",
                    label="生产制单",
                    status="active",
                    route="/production/orderTrackingV2",
                ),
                DashboardKanbanFlowNodeData(
                    key="material",
                    label="面料",
                    status="normal",
                    route="/materialPurchase/materialPurchaseProcess",
                ),
                DashboardKanbanFlowNodeData(
                    key="bulk_followup",
                    label="大货跟进",
                    status="active",
                    route="/production/orderTrackingV2",
                ),
                DashboardKanbanFlowNodeData(
                    key="factory_contract",
                    label="工厂合同",
                    status="normal",
                    route="/subcontract/list",
                ),
                DashboardKanbanFlowNodeData(
                    key="qc",
                    label="工厂合同质检",
                    status="normal",
                    route="/quality/inspections",
                ),
                DashboardKanbanFlowNodeData(
                    key="accessory",
                    label="辅料/包材",
                    status="normal",
                    route="/materialPurchase/materialPurchaseProcess",
                ),
                DashboardKanbanFlowNodeData(
                    key="cost",
                    label="大货成本核算",
                    status="normal",
                    route="/reports/style-profit",
                ),
            ],
            flow_links=[
                DashboardKanbanFlowLinkData(from_key="quote", to_key="order"),
                DashboardKanbanFlowLinkData(from_key="order", to_key="production_order"),
                DashboardKanbanFlowLinkData(from_key="production_order", to_key="factory_contract"),
                DashboardKanbanFlowLinkData(from_key="factory_contract", to_key="qc"),
                DashboardKanbanFlowLinkData(from_key="material", to_key="bulk_followup"),
                DashboardKanbanFlowLinkData(from_key="accessory", to_key="cost"),
            ],
            messages=messages,
        )

    def _build_local_kanban_messages(self, *, company: str) -> list[DashboardKanbanMessageRowData]:
        messages: list[DashboardKanbanMessageRowData] = []
        today = datetime.now(UTC).date()

        try:
            if self._has_tables({LySalesOrder.__tablename__, LySalesOrderItem.__tablename__}):
                sales_rows = (
                    self.session.query(LySalesOrder, LySalesOrderItem)
                    .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
                    .filter(LySalesOrder.company == company)
                    .order_by(LySalesOrder.updated_at.desc(), LySalesOrder.id.desc(), LySalesOrderItem.line_no.asc())
                    .limit(40)
                    .all()
                )
                for order, line in sales_rows:
                    qty = self._decimal_or_zero(getattr(line, "qty", None))
                    delivered_qty = self._decimal_or_zero(getattr(line, "delivered_qty", None))
                    planned_qty = self._decimal_or_zero(getattr(line, "planned_qty", None))
                    delivery_date = getattr(line, "delivery_date", None)
                    is_overdue = bool(delivery_date and delivery_date < today and delivered_qty < qty)
                    if str(order.status) == "cancelled":
                        row_status = "已取消"
                        title = "销售订单已取消"
                    elif delivered_qty >= qty and qty > Decimal("0"):
                        row_status = "已读"
                        title = "销售订单已交付"
                    elif planned_qty > Decimal("0") or str(order.status) == "planned":
                        row_status = "已读"
                        title = "销售订单已排产"
                    else:
                        row_status = "待处理"
                        title = "销售订单待排产"
                    messages.append(
                        DashboardKanbanMessageRowData(
                            image=None,
                            order_no=str(order.sales_order_no),
                            customer=str(order.customer or ""),
                            style_no=str(line.item_code),
                            style_name=str(line.item_name or line.item_code),
                            ordered_qty=qty,
                            overdue="是" if is_overdue else "否",
                            sun="",
                            mon="",
                            tue="",
                            wed="",
                            thu="",
                            fri="",
                            sat="",
                            title=title,
                            sent_at=self._as_utc_datetime(order.updated_at or order.created_at),
                            status=row_status,
                            sender=str(order.updated_by or order.created_by),
                        )
                    )

            if self._has_tables({LyProductionPlan.__tablename__}):
                plan_rows = (
                    self.session.query(LyProductionPlan)
                    .filter(LyProductionPlan.company == company)
                    .order_by(LyProductionPlan.updated_at.desc(), LyProductionPlan.id.desc())
                    .limit(40)
                    .all()
                )
                for plan in plan_rows:
                    status = str(plan.status or "")
                    messages.append(
                        DashboardKanbanMessageRowData(
                            image=None,
                            order_no=str(plan.sales_order),
                            customer=str(plan.customer or ""),
                            style_no=str(plan.item_code),
                            style_name=str(plan.sales_order_item or plan.item_code),
                            ordered_qty=self._decimal_or_zero(plan.planned_qty),
                            overdue="否",
                            sun="",
                            mon="",
                            tue="",
                            wed="",
                            thu="",
                            fri="",
                            sat="",
                            title=f"生产计划 {plan.plan_no}：{status or '未定'}",
                            sent_at=self._as_utc_datetime(plan.updated_at or plan.created_at),
                            status="待处理" if status not in {"cancelled", "job_cards_synced", "material_issued"} else "已读",
                            sender=str(getattr(plan, "updated_by", None) or plan.created_by),
                        )
                    )
        except SQLAlchemyError as exc:
            raise self._source_unavailable(module="dashboard_kanban", exc=exc) from exc

        messages.sort(key=lambda row: row.sent_at, reverse=True)
        return messages[:40]

    def _has_tables(self, table_names: set[str]) -> bool:
        bind = self.session.get_bind()
        if bind.dialect.name != "sqlite":
            return True
        existing_tables = set(inspect(bind).get_table_names())
        return table_names.issubset(existing_tables)

    def _build_quality_summary(
        self,
        *,
        company: str,
        from_date: date | None,
        to_date: date | None,
        item_code: str | None,
        warehouse: str | None,
    ) -> DashboardQualityOverviewData:
        try:
            stats = self.quality_service.statistics(
                company=company,
                item_code=item_code,
                warehouse=warehouse,
                from_date=from_date,
                to_date=to_date,
            )
        except Exception as exc:  # noqa: BLE001 - fail-closed on any quality source failure.
            raise self._source_unavailable(module="quality", exc=exc) from exc

        inspected_qty = self._decimal_or_zero(getattr(stats, "total_inspected_qty", None))
        accepted_qty = self._decimal_or_zero(getattr(stats, "total_accepted_qty", None))
        rejected_qty = self._decimal_or_zero(getattr(stats, "total_rejected_qty", None))
        return DashboardQualityOverviewData(
            inspection_count=int(getattr(stats, "total_count", 0) or 0),
            accepted_qty=accepted_qty,
            rejected_qty=rejected_qty,
            defect_count=int(self._decimal_or_zero(getattr(stats, "total_defect_qty", None))),
            pass_rate=self._safe_rate(numerator=accepted_qty, denominator=inspected_qty),
        )

    def _build_sales_inventory_summary(
        self,
        *,
        company: str,
        item_code: str | None,
        warehouse: str | None,
    ) -> DashboardSalesInventoryOverviewData:
        try:
            aggregation = self.warehouse_service.get_local_stock_summary(
                company=company,
                item_code=item_code,
                warehouse=warehouse,
            )
        except Exception as exc:  # noqa: BLE001 - fail-closed on any sales-inventory source failure.
            raise self._source_unavailable(module="sales_inventory", exc=exc) from exc

        rows = list(getattr(aggregation, "items", []) or [])
        total_actual_qty = sum((self._decimal_or_zero(getattr(row, "actual_qty", None)) for row in rows), Decimal("0"))
        below_safety_count = sum(1 for row in rows if bool(getattr(row, "is_below_safety", False)))
        below_reorder_count = sum(1 for row in rows if bool(getattr(row, "is_below_reorder", False)))
        return DashboardSalesInventoryOverviewData(
            item_count=len(rows),
            total_actual_qty=total_actual_qty,
            below_safety_count=below_safety_count,
            below_reorder_count=below_reorder_count,
        )

    def _build_warehouse_summary(
        self,
        *,
        company: str,
        item_code: str | None,
        warehouse: str | None,
    ) -> DashboardWarehouseOverviewData:
        try:
            summary = self.warehouse_service.get_local_stock_summary(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
            )
            rows = [
                self._local_stock_alert_proxy(row)
                for row in summary.items
                if bool(getattr(row, "is_below_reorder", False)) or bool(getattr(row, "is_below_safety", False))
            ]
        except Exception as exc:  # noqa: BLE001 - fail-closed on any warehouse source failure.
            raise self._source_unavailable(module="warehouse", exc=exc) from exc

        critical_count = 0
        warning_count = 0
        for row in rows:
            severity = str(getattr(row, "severity", "")).strip().lower()
            if severity in {"high", "critical"}:
                critical_count += 1
            elif severity in {"medium", "warning"}:
                warning_count += 1

        return DashboardWarehouseOverviewData(
            alert_count=len(rows),
            critical_alert_count=critical_count,
            warning_alert_count=warning_count,
        )

    @staticmethod
    def _local_stock_alert_proxy(row: Any) -> Any:
        severity = "high" if bool(getattr(row, "is_below_reorder", False)) else "medium"
        return type("DashboardLocalStockAlert", (), {"severity": severity})()

    @staticmethod
    def _source_unavailable(*, module: str, exc: Exception) -> DashboardSourceUnavailableError:
        if isinstance(exc, DashboardSourceUnavailableError):
            return exc
        return DashboardSourceUnavailableError(
            module=module,
            message=f"{module} 来源不可用",
            status_code=503,
        )

    @staticmethod
    def _decimal_or_zero(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        text = str(value).strip()
        if not text:
            return Decimal("0")
        return Decimal(text)

    @staticmethod
    def _as_utc_datetime(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(UTC)
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _safe_rate(*, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator <= Decimal("0"):
            return Decimal("0")
        rate = numerator / denominator
        if rate < Decimal("0"):
            return Decimal("0")
        if rate > Decimal("1"):
            return Decimal("1")
        return rate
