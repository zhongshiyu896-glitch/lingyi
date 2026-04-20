"""FastAPI router for permission governance readonly baseline (TASK-070A/TASK-070B)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
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
from app.core.error_codes import AUDIT_WRITE_FAILED
from app.core.permissions import PERMISSION_GOVERNANCE_AUDIT_READ
from app.core.permissions import PERMISSION_GOVERNANCE_DIAGNOSTIC
from app.core.permissions import PERMISSION_GOVERNANCE_EXPORT
from app.core.permissions import PERMISSION_READ
from app.core.exceptions import AuditWriteFailed
from app.schemas.permission_governance import ApiResponse
from app.schemas.permission_governance import PermissionGovernanceDiagnosticData
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_governance_diagnostic_service import PermissionGovernanceDiagnosticService
from app.services.permission_governance_export_service import PermissionGovernanceExportService
from app.services.permission_governance_service import PermissionGovernanceService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/permissions", tags=["permission_governance"])


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


def _invalid_query(message: str) -> None:
    raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_QUERY_PARAMETER", "message": message, "data": None},
    )


def _parse_optional_date(value: str | None, field_name: str) -> date | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        _invalid_query(f"{field_name} 日期格式非法，应为 YYYY-MM-DD")


def _validate_date_range(*, from_date: date | None, to_date: date | None) -> None:
    if from_date is not None and to_date is not None and from_date > to_date:
        _invalid_query("from_date 不得晚于 to_date")


def _validate_page_params(*, page: int, page_size: int) -> None:
    if page < 1:
        _invalid_query("page 必须大于等于 1")
    if page_size < 1 or page_size > 100:
        _invalid_query("page_size 必须在 1 到 100 之间")


def _validate_export_limit(limit: int) -> None:
    if limit < 1 or limit > 5000:
        _invalid_query("limit 必须在 1 到 5000 之间")


def _error_code_from_http_exception(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return str(detail.get("code") or "HTTP_ERROR")
    return "HTTP_ERROR"


def _record_export_audit(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    resource_type: str,
    limit: int,
    row_count: int,
    success: bool,
    error_code: str | None,
) -> None:
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    after_data = {
        "export_type": resource_type,
        "limit": limit,
        "row_count": row_count,
    }
    if success:
        audit.record_success_and_commit(
            module="permission",
            action=PERMISSION_GOVERNANCE_EXPORT,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type=resource_type,
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data=after_data,
            context=context,
        )
    else:
        audit.record_failure_and_commit(
            module="permission",
            action=PERMISSION_GOVERNANCE_EXPORT,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type=resource_type,
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data=after_data,
            error_code=error_code or "EXPORT_FAILED",
            context=context,
        )


@router.get("/actions/catalog")
def get_permission_action_catalog(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=PERMISSION_READ,
        module="permission",
        resource_type="permission_action_catalog",
    )
    return _ok(PermissionGovernanceService.get_actions_catalog())


@router.get("/roles/matrix")
def get_permission_roles_matrix(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=PERMISSION_READ,
        module="permission",
        resource_type="permission_roles_matrix",
    )
    return _ok(PermissionGovernanceService.get_roles_matrix())


@router.get("/diagnostic")
def get_permission_governance_diagnostic(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=PERMISSION_GOVERNANCE_DIAGNOSTIC,
        module="permission",
        resource_type="permission_diagnostic",
    )
    data: PermissionGovernanceDiagnosticData = PermissionGovernanceDiagnosticService.get_diagnostic_summary()
    return _ok(data)


@router.get("/audit/security/export")
def export_permission_security_audit(
    request: Request,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=1000),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        PermissionService(session=session).require_action(
            current_user=current_user,
            request_obj=request,
            action=PERMISSION_GOVERNANCE_EXPORT,
            module="permission",
            resource_type="permission_security_audit_export",
        )
        parsed_from_date = _parse_optional_date(from_date, "from_date")
        parsed_to_date = _parse_optional_date(to_date, "to_date")
        _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
        _validate_export_limit(limit)
        data = PermissionGovernanceService.list_security_audits(
            session=session,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            module=_scope_text(module),
            action=_scope_text(action),
            request_id=_scope_text(request_id),
            resource_type=_scope_text(resource_type),
            resource_id=_scope_text(resource_id),
            event_type=_scope_text(event_type),
            user_id=_scope_text(user_id),
            page=1,
            page_size=limit,
        )
        artifact = PermissionGovernanceExportService.build_security_audit_csv(items=data.items)
        _record_export_audit(
            session=session,
            request=request,
            current_user=current_user,
            resource_type="permission_security_audit_export",
            limit=limit,
            row_count=len(data.items),
            success=True,
            error_code=None,
        )
    except HTTPException as exc:
        try:
            _record_export_audit(
                session=session,
                request=request,
                current_user=current_user,
                resource_type="permission_security_audit_export",
                limit=limit,
                row_count=0,
                success=False,
                error_code=_error_code_from_http_exception(exc),
            )
        except AuditWriteFailed:
            raise HTTPException(
                status_code=500,
                detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
            ) from None
        raise
    except AuditWriteFailed:
        raise HTTPException(
            status_code=500,
            detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
        ) from None
    except Exception as exc:
        try:
            _record_export_audit(
                session=session,
                request=request,
                current_user=current_user,
                resource_type="permission_security_audit_export",
                limit=limit,
                row_count=0,
                success=False,
                error_code="EXPORT_FAILED",
            )
        except AuditWriteFailed:
            raise HTTPException(
                status_code=500,
                detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
            ) from None
        raise HTTPException(
            status_code=500,
            detail={"code": "EXPORT_FAILED", "message": "导出失败", "data": None},
        ) from exc

    headers = {"Content-Disposition": f'attachment; filename="{artifact.filename}"'}
    return StreamingResponse(iter([artifact.content]), media_type=artifact.content_type, headers=headers)


@router.get("/audit/operations/export")
def export_permission_operation_audit(
    request: Request,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: int | None = Query(default=None),
    operator: str | None = Query(default=None),
    result: str | None = Query(default=None),
    error_code: str | None = Query(default=None),
    limit: int = Query(default=1000),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        PermissionService(session=session).require_action(
            current_user=current_user,
            request_obj=request,
            action=PERMISSION_GOVERNANCE_EXPORT,
            module="permission",
            resource_type="permission_operation_audit_export",
        )
        parsed_from_date = _parse_optional_date(from_date, "from_date")
        parsed_to_date = _parse_optional_date(to_date, "to_date")
        _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
        _validate_export_limit(limit)
        normalized_result = _scope_text(result)
        if normalized_result is not None and normalized_result not in {"success", "failed"}:
            _invalid_query("result 仅支持 success 或 failed")
        data = PermissionGovernanceService.list_operation_audits(
            session=session,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            module=_scope_text(module),
            action=_scope_text(action),
            request_id=_scope_text(request_id),
            resource_type=_scope_text(resource_type),
            resource_id=resource_id,
            operator=_scope_text(operator),
            result=normalized_result,
            error_code=_scope_text(error_code),
            page=1,
            page_size=limit,
        )
        artifact = PermissionGovernanceExportService.build_operation_audit_csv(items=data.items)
        _record_export_audit(
            session=session,
            request=request,
            current_user=current_user,
            resource_type="permission_operation_audit_export",
            limit=limit,
            row_count=len(data.items),
            success=True,
            error_code=None,
        )
    except HTTPException as exc:
        try:
            _record_export_audit(
                session=session,
                request=request,
                current_user=current_user,
                resource_type="permission_operation_audit_export",
                limit=limit,
                row_count=0,
                success=False,
                error_code=_error_code_from_http_exception(exc),
            )
        except AuditWriteFailed:
            raise HTTPException(
                status_code=500,
                detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
            ) from None
        raise
    except AuditWriteFailed:
        raise HTTPException(
            status_code=500,
            detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
        ) from None
    except Exception as exc:
        try:
            _record_export_audit(
                session=session,
                request=request,
                current_user=current_user,
                resource_type="permission_operation_audit_export",
                limit=limit,
                row_count=0,
                success=False,
                error_code="EXPORT_FAILED",
            )
        except AuditWriteFailed:
            raise HTTPException(
                status_code=500,
                detail={"code": AUDIT_WRITE_FAILED, "message": "审计日志写入失败", "data": None},
            ) from None
        raise HTTPException(
            status_code=500,
            detail={"code": "EXPORT_FAILED", "message": "导出失败", "data": None},
        ) from exc

    headers = {"Content-Disposition": f'attachment; filename="{artifact.filename}"'}
    return StreamingResponse(iter([artifact.content]), media_type=artifact.content_type, headers=headers)


@router.get("/audit/security")
def get_permission_security_audit(
    request: Request,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=20),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=PERMISSION_GOVERNANCE_AUDIT_READ,
        module="permission",
        resource_type="permission_security_audit",
    )

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    _validate_page_params(page=page, page_size=page_size)

    data = PermissionGovernanceService.list_security_audits(
        session=session,
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        module=_scope_text(module),
        action=_scope_text(action),
        request_id=_scope_text(request_id),
        resource_type=_scope_text(resource_type),
        resource_id=_scope_text(resource_id),
        event_type=_scope_text(event_type),
        user_id=_scope_text(user_id),
        page=page,
        page_size=page_size,
    )
    return _ok(data)


@router.get("/audit/operations")
def get_permission_operation_audit(
    request: Request,
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: int | None = Query(default=None),
    operator: str | None = Query(default=None),
    result: str | None = Query(default=None),
    error_code: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=20),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=PERMISSION_GOVERNANCE_AUDIT_READ,
        module="permission",
        resource_type="permission_operation_audit",
    )

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    _validate_page_params(page=page, page_size=page_size)

    normalized_result = _scope_text(result)
    if normalized_result is not None and normalized_result not in {"success", "failed"}:
        _invalid_query("result 仅支持 success 或 failed")

    data = PermissionGovernanceService.list_operation_audits(
        session=session,
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        module=_scope_text(module),
        action=_scope_text(action),
        request_id=_scope_text(request_id),
        resource_type=_scope_text(resource_type),
        resource_id=resource_id,
        operator=_scope_text(operator),
        result=normalized_result,
        error_code=_scope_text(error_code),
        page=page,
        page_size=page_size,
    )
    return _ok(data)
