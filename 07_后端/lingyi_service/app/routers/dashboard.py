"""FastAPI router for dashboard overview read-only baseline (TASK-060A)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
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


@router.get("/overview")
def get_dashboard_overview(
    request: Request,
    company: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
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
        )
    except DashboardSourceUnavailableError as exc:
        raise HTTPException(
            status_code=int(exc.status_code),
            detail={
                "code": "DASHBOARD_SOURCE_UNAVAILABLE",
                "message": "报表来源服务暂时不可用",
                "data": {"module": exc.module},
            },
        ) from exc

    return _ok(data)
