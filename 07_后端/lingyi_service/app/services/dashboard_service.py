"""Dashboard overview read-only aggregation service (TASK-060A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.schemas.dashboard import DashboardOverviewData
from app.schemas.dashboard import DashboardKanbanData
from app.schemas.dashboard import DashboardKanbanFlowLinkData
from app.schemas.dashboard import DashboardKanbanFlowNodeData
from app.schemas.dashboard import DashboardKanbanMessageRowData
from app.schemas.dashboard import DashboardQualityOverviewData
from app.schemas.dashboard import DashboardSalesInventoryOverviewData
from app.schemas.dashboard import DashboardSourceStatusData
from app.schemas.dashboard import DashboardWarehouseOverviewData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter
from app.services.quality_service import QualityService
from app.services.sales_inventory_service import SalesInventoryService
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
        self.sales_inventory_service = SalesInventoryService(adapter=ERPNextSalesInventoryAdapter(request_obj=request_obj))
        self.warehouse_service = WarehouseService(adapter=ERPNextWarehouseAdapter(request_obj=request_obj))

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
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
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
        )

    def _build_kanban_data(
        self,
        *,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
    ) -> DashboardKanbanData:
        messages = [
            DashboardKanbanMessageRowData(
                image=None,
                order_no="SO-240601-001",
                customer="华东客户A",
                style_no="L-1001",
                style_name="春夏T恤",
                ordered_qty=Decimal("1200"),
                overdue="否",
                sun="",
                mon="",
                tue="",
                wed="",
                thu="",
                fri="",
                sat="",
                title="订单已下发",
                sent_at=datetime(2026, 5, 3, 9, 30, tzinfo=UTC),
                status="已读",
                sender="跟单员A",
            ),
            DashboardKanbanMessageRowData(
                image=None,
                order_no="SO-240601-002",
                customer="华南客户B",
                style_no="D-2030",
                style_name="连衣裙",
                ordered_qty=Decimal("860"),
                overdue="是",
                sun="",
                mon="",
                tue="",
                wed="",
                thu="",
                fri="",
                sat="",
                title="请确认面料到仓",
                sent_at=datetime(2026, 5, 3, 10, 15, tzinfo=UTC),
                status="待处理",
                sender="跟单员B",
            ),
        ]

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
            aggregation = self.sales_inventory_service.get_inventory_aggregation(
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
            alerts = self.warehouse_service.get_alerts(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                alert_type=None,
            )
        except Exception as exc:  # noqa: BLE001 - fail-closed on any warehouse source failure.
            raise self._source_unavailable(module="warehouse", exc=exc) from exc

        rows = list(getattr(alerts, "items", []) or [])
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
    def _source_unavailable(*, module: str, exc: Exception) -> DashboardSourceUnavailableError:
        if isinstance(exc, DashboardSourceUnavailableError):
            return exc
        if isinstance(exc, ERPNextAdapterException):
            return DashboardSourceUnavailableError(
                module=module,
                message=f"{module} 来源不可用: {exc.safe_message or 'unknown'}",
                status_code=int(exc.http_status or 503),
            )
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
    def _safe_rate(*, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator <= Decimal("0"):
            return Decimal("0")
        rate = numerator / denominator
        if rate < Decimal("0"):
            return Decimal("0")
        if rate > Decimal("1"):
            return Decimal("1")
        return rate
