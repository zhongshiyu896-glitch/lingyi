"""Dashboard overview read-only aggregation service (TASK-060A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.production import LyProductionPlan
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.schemas.dashboard import DashboardOverviewData
from app.schemas.dashboard import DashboardKanbanData
from app.schemas.dashboard import DashboardKanbanFlowLinkData
from app.schemas.dashboard import DashboardKanbanFlowNodeData
from app.schemas.dashboard import DashboardHomeMetricCardData
from app.schemas.dashboard import DashboardHomeOverviewData
from app.schemas.dashboard import DashboardHomeTodoItemData
from app.schemas.dashboard import DashboardHomeTrendPointData
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


class DashboardService:
    """Compose quality/sales-inventory/warehouse summaries under fail-closed policy."""

    def __init__(self, *, session: Session, request_obj: Request):
        self.session = session
        self.request_obj = request_obj
        self.quality_service = QualityService(session=session)
        self.warehouse_service = WarehouseService(session=session)

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
            quality=quality,
            sales_inventory=sales_inventory,
            warehouse=warehouse_summary,
            kanban=kanban,
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

    @staticmethod
    def _build_home_overview(
        *,
        quality: DashboardQualityOverviewData,
        sales_inventory: DashboardSalesInventoryOverviewData,
        warehouse: DashboardWarehouseOverviewData,
        kanban: DashboardKanbanData,
    ) -> DashboardHomeOverviewData:
        pass_rate_percent = (quality.pass_rate * Decimal("100")).quantize(Decimal("0.01"))
        sales_total = DashboardService._decimal_or_zero(sales_inventory.total_actual_qty)
        warning_total = int(warehouse.warning_alert_count) + int(warehouse.critical_alert_count)
        pending_count = sum(1 for row in kanban.messages if row.status != "已读")
        overdue_count = sum(1 for row in kanban.messages if row.overdue == "是")

        metric_cards = [
            DashboardHomeMetricCardData(
                key="inspection_count",
                label="质检单量",
                value=str(int(quality.inspection_count)),
                unit="单",
                trend="较昨日平稳",
            ),
            DashboardHomeMetricCardData(
                key="inventory_qty",
                label="库存总量",
                value=str(sales_total),
                unit="件",
                trend="按只读汇总更新",
            ),
            DashboardHomeMetricCardData(
                key="quality_pass_rate",
                label="质检通过率",
                value=str(pass_rate_percent),
                unit="%",
                trend="来源于质检汇总",
            ),
            DashboardHomeMetricCardData(
                key="warehouse_alerts",
                label="仓储预警",
                value=str(int(warehouse.alert_count)),
                unit="条",
                trend="高危优先处理",
            ),
        ]

        todo_items = [
            DashboardHomeTodoItemData(
                key="pending_messages",
                title="待处理动态",
                count=pending_count,
                status="normal" if pending_count == 0 else "warning",
                action_label="查看动态",
            ),
            DashboardHomeTodoItemData(
                key="overdue_orders",
                title="超期订单",
                count=overdue_count,
                status="normal" if overdue_count == 0 else "urgent",
                action_label="查看跟进",
            ),
            DashboardHomeTodoItemData(
                key="warehouse_warning",
                title="仓储预警",
                count=warning_total,
                status="normal" if warning_total == 0 else "warning",
                action_label="查看仓储",
            ),
        ]

        business_summary = [
            f"质检通过率 {pass_rate_percent}%",
            f"低于安全库存款号 {int(sales_inventory.below_safety_count)} 个",
            f"低于补货线款号 {int(sales_inventory.below_reorder_count)} 个",
            f"仓储高危预警 {int(warehouse.critical_alert_count)} 条",
        ]

        recent_activities = [
            f"{row.sent_at.astimezone(UTC).strftime('%m-%d %H:%M')} {row.title}（{row.order_no}）"
            for row in kanban.messages[:5]
        ]

        trend_points = [
            DashboardHomeTrendPointData(
                period="W1",
                forecast_sales=Decimal("120000"),
                forecast_cost=Decimal("86000"),
                forecast_profit=Decimal("34000"),
            ),
            DashboardHomeTrendPointData(
                period="W2",
                forecast_sales=Decimal("132000"),
                forecast_cost=Decimal("93000"),
                forecast_profit=Decimal("39000"),
            ),
            DashboardHomeTrendPointData(
                period="W3",
                forecast_sales=Decimal("126000"),
                forecast_cost=Decimal("90500"),
                forecast_profit=Decimal("35500"),
            ),
            DashboardHomeTrendPointData(
                period="W4",
                forecast_sales=Decimal("138000"),
                forecast_cost=Decimal("96400"),
                forecast_profit=Decimal("41600"),
            ),
        ]

        return DashboardHomeOverviewData(
            summary_title="首页经营总览（P1）",
            metric_cards=metric_cards,
            todo_items=todo_items,
            warnings=[
                "写入类动作在本地首版保持受控，不触发真实提交。",
                "导出/下载/打印在本页仅提供语义按钮。",
            ],
            business_summary=business_summary,
            recent_activities=recent_activities,
            trend_points=trend_points,
            primary_actions=["查看动态", "刷新指标", "导出概览"],
        )

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
                    route="/sales-inventory/sales-orders",
                ),
                DashboardKanbanFlowNodeData(
                    key="order",
                    label="订单",
                    status="active",
                    route="/sales-inventory/sales-orders",
                ),
                DashboardKanbanFlowNodeData(
                    key="production_order",
                    label="生产制单",
                    status="active",
                    route="/production/plans",
                ),
                DashboardKanbanFlowNodeData(
                    key="material",
                    label="面料",
                    status="normal",
                    route="/production/plans",
                ),
                DashboardKanbanFlowNodeData(
                    key="bulk_followup",
                    label="大货跟进",
                    status="active",
                    route="/production/plans",
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
                    route="/production/plans",
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
