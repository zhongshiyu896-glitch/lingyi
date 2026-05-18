"""FastAPI router for dashboard overview read-only baseline (TASK-060A)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from datetime import datetime
from datetime import UTC
from decimal import Decimal
import os
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.permissions import DASHBOARD_READ
from app.core.permissions import get_permission_source
from app.schemas.dashboard import ApiResponse
from app.services.dashboard_service import DashboardService
from app.services.dashboard_service import DashboardSourceUnavailableError
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return ApiResponse(code="0", message="success", data=data).model_dump(mode="json")


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_optional_date(value: str | None, field_name: str) -> date | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_QUERY_PARAMETER",
                "message": f"{field_name} 日期格式非法，应为 YYYY-MM-DD",
                "data": None,
            },
        ) from exc


def _validate_date_range(*, from_date: date | None, to_date: date | None) -> None:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_QUERY_PARAMETER",
                "message": "from_date 不得晚于 to_date",
                "data": None,
            },
        )


def _require_company(company: str | None) -> str:
    normalized = _scope_text(company)
    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_QUERY_PARAMETER",
                "message": "company 不能为空",
                "data": None,
            },
        )
    return normalized


def _local_dashboard_read_fallback_enabled() -> bool:
    env = os.getenv("APP_ENV", "").strip().lower()
    allow_dev_auth = os.getenv("LINGYI_ALLOW_DEV_AUTH", "").strip().lower()
    return env in {"development", "dev", "local"} and allow_dev_auth == "true" and get_permission_source() == "static"


def _build_local_dashboard_read_fallback(
    *,
    company: str,
    from_date: date | None,
    to_date: date | None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "generated_at": now,
        "quality": {
            "inspection_count": 0,
            "accepted_qty": Decimal("0"),
            "rejected_qty": Decimal("0"),
            "defect_count": 0,
            "pass_rate": Decimal("0"),
        },
        "sales_inventory": {
            "item_count": 0,
            "total_actual_qty": Decimal("0"),
            "below_safety_count": 0,
            "below_reorder_count": 0,
        },
        "warehouse": {
            "alert_count": 0,
            "critical_alert_count": 0,
            "warning_alert_count": 0,
        },
        "source_status": [
            {"module": "quality", "status": "local_dev_static_fallback"},
            {"module": "sales_inventory", "status": "local_dev_static_fallback"},
            {"module": "warehouse", "status": "local_dev_static_fallback"},
        ],
        "kanban": {
            "board_name": "大货看板",
            "quick_filters": [],
            "flow_nodes": [],
            "flow_links": [],
            "messages": [],
        },
        "home_overview": {
            "summary_title": "首页经营总览",
            "metric_cards": [
                {"key": "inspection_count", "label": "质检单量", "value": "0", "unit": "单", "trend": "local_dev_static_fallback"},
                {"key": "inventory_qty", "label": "库存总量", "value": "0", "unit": "件", "trend": "local_dev_static_fallback"},
                {"key": "quality_pass_rate", "label": "质检通过率", "value": "0", "unit": "%", "trend": "local_dev_static_fallback"},
                {"key": "warehouse_alerts", "label": "仓储预警", "value": "0", "unit": "条", "trend": "local_dev_static_fallback"},
            ],
            "todo_items": [],
            "warnings": [],
            "business_summary": [],
            "recent_activities": [],
            "trend_points": [],
            "primary_actions": [],
        },
    }


@router.get("/overview")
def get_dashboard_overview(
    request: Request,
    company: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    action = DASHBOARD_READ
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="dashboard",
        resource_type="dashboard_overview",
    )

    normalized_company = _require_company(company)
    normalized_item_code = _scope_text(item_code)
    normalized_warehouse = _scope_text(warehouse)

    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="dashboard",
        action=action,
        resource_scope={
            "company": normalized_company,
            "warehouse": normalized_warehouse,
            "item_code": normalized_item_code,
        },
        required_fields=("company",),
        resource_type="dashboard_overview",
        enforce_action=False,
    )

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)

    try:
        data = DashboardService(session=session, request_obj=request).get_overview(
            company=normalized_company,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            item_code=normalized_item_code,
            warehouse=normalized_warehouse,
            keyword=_scope_text(keyword),
        )
    except DashboardSourceUnavailableError as exc:
        if _local_dashboard_read_fallback_enabled():
            data = _build_local_dashboard_read_fallback(
                company=normalized_company,
                from_date=parsed_from_date,
                to_date=parsed_to_date,
            )
            return _ok(data)
        raise HTTPException(
            status_code=int(exc.status_code),
            detail={
                "code": "DASHBOARD_SOURCE_UNAVAILABLE",
                "message": "报表来源服务暂时不可用",
                "data": {"module": exc.module},
            },
        ) from exc

    return _ok(data)
