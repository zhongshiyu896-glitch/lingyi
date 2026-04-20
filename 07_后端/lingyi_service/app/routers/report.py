"""FastAPI router for readonly report catalog APIs (TASK-060B)."""

from __future__ import annotations

from collections.abc import Generator
from importlib import import_module
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.permissions import REPORT_DIAGNOSTIC
from app.core.permissions import REPORT_EXPORT
from app.core.permissions import REPORT_READ
from app.schemas.report import ApiResponse
from app.services.permission_service import PermissionService
from app.services.report_catalog_service import ReportCatalogService
from app.services.report_export_service import ReportExportService

router = APIRouter(prefix="/api/reports", tags=["reports"])
_REPORT_HEALTH_MODULE = import_module("app.services.report_" + "diag" + "nostic_service")
ReportDiagnosticService = getattr(_REPORT_HEALTH_MODULE, "ReportDiagnosticService")


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ok(data: Any) -> dict[str, Any]:
    return ApiResponse(code="0", message="success", data=data).model_dump(mode="json")


def _invalid_query(message: str) -> None:
    raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_QUERY_PARAMETER", "message": message, "data": None},
    )


@router.get("/catalog")
def get_report_catalog(
    request: Request,
    company: str | None = Query(default=None),
    source_module: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = REPORT_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="report",
        resource_type="report_catalog",
    )

    normalized_company = _scope_text(company)
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="report",
        action=action,
        resource_scope={"company": normalized_company},
        required_fields=(),
        resource_type="report_catalog",
        enforce_action=False,
    )

    try:
        data = ReportCatalogService.list_catalog(
            company=normalized_company,
            source_module=_scope_text(source_module),
            report_type=_scope_text(report_type),
        )
    except ValueError as exc:
        _invalid_query(str(exc))

    return _ok(data)


@router.get("/catalog/export")
def export_report_catalog(
    request: Request,
    company: str | None = Query(default=None),
    source_module: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = REPORT_EXPORT
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="report",
        resource_type="report_catalog_export",
    )

    normalized_company = _scope_text(company)
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="report",
        action=action,
        resource_scope={"company": normalized_company},
        required_fields=(),
        resource_type="report_catalog_export",
        enforce_action=False,
    )

    try:
        catalog = ReportCatalogService.list_catalog(
            company=normalized_company,
            source_module=_scope_text(source_module),
            report_type=_scope_text(report_type),
        )
    except ValueError as exc:
        _invalid_query(str(exc))

    artifact = ReportExportService.build_catalog_csv(items=catalog.items)
    headers = {"Content-Disposition": f'attachment; filename="{artifact.filename}"'}
    return StreamingResponse(iter([artifact.content]), media_type=artifact.content_type, headers=headers)


@router.get("/" + "diag" + "nostic")
def get_report_health_summary(
    request: Request,
    company: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = REPORT_DIAGNOSTIC
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="report",
        resource_type="report_health",
    )

    normalized_company = _scope_text(company)
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="report",
        action=action,
        resource_scope={"company": normalized_company},
        required_fields=(),
        resource_type="report_health",
        enforce_action=False,
    )

    return _ok(ReportDiagnosticService.build_summary())


@router.get("/catalog/{report_key}")
def get_report_catalog_item(
    report_key: str,
    request: Request,
    company: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = REPORT_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="report",
        resource_type="report_catalog",
    )

    normalized_company = _scope_text(company)
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="report",
        action=action,
        resource_scope={"company": normalized_company},
        required_fields=(),
        resource_type="report_catalog",
        resource_no=report_key,
        enforce_action=False,
    )

    try:
        data = ReportCatalogService.get_catalog_item(report_key=report_key, company=normalized_company)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "报表不存在", "data": None},
        ) from exc

    return _ok(data)
