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

        return DashboardOverviewData(
            company=company,
            from_date=from_date,
            to_date=to_date,
            generated_at=datetime.now(UTC),
            quality=quality,
            sales_inventory=sales_inventory,
            warehouse=warehouse_summary,
            source_status=source_status,
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
