"""FastAPI router for quality management APIs (TASK-012B)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
import logging
from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import QUALITY_DATABASE_WRITE_FAILED
from app.core.error_codes import QUALITY_INTERNAL_ERROR
from app.core.error_codes import QUALITY_NOT_FOUND
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.logging import log_safe_error
from app.core.permissions import QUALITY_CANCEL
from app.core.permissions import QUALITY_CONFIRM
from app.core.permissions import QUALITY_CREATE
from app.core.permissions import QUALITY_DIAGNOSTIC
from app.core.permissions import QUALITY_EXPORT
from app.core.permissions import QUALITY_READ
from app.core.permissions import QUALITY_UPDATE
from app.core.request_id import get_request_id_from_request
from app.models.quality import LyQualityInspection
from app.schemas.quality import QualityInspectionCancelRequest
from app.schemas.quality import QualityInspectionConfirmRequest
from app.schemas.quality import QualityInspectionCreateRequest
from app.schemas.quality import QualityInspectionUpdateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.quality_service import QualityService
from app.services.quality_service import QualitySourceValidator
from app.services.quality_service import _text as _scope_text
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/quality", tags=["quality"])
logger = logging.getLogger(__name__)


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str | None = None, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message or message_of(code), "data": None},
    )


def _app_err(exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": getattr(exc, "data", None)},
    )


def _rollback_safely(session: Session) -> None:
    try:
        session.rollback()
    except Exception:  # pragma: no cover
        return


def _commit_or_raise_write_error(session: Session) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session)
        raise BusinessException(code=QUALITY_DATABASE_WRITE_FAILED) from exc


def _permission_error_code(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        if code == AUTH_FORBIDDEN:
            return AUTH_FORBIDDEN
        if code == PERMISSION_SOURCE_UNAVAILABLE:
            return PERMISSION_SOURCE_UNAVAILABLE
        return code
    return "HTTP_ERROR"


def _map_permission_error(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        return _err(str(detail.get("code") or "HTTP_ERROR"), str(detail.get("message") or "请求失败"), exc.status_code)
    return _err("HTTP_ERROR", str(detail), exc.status_code)


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="quality",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="QUALITY_INSPECTION",
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=None,
            after_data=None,
            error_code=error_code,
            context=context,
        )
        session.commit()
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        raise AuditWriteFailed() from exc


def _record_success(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    after_data: dict[str, Any] | None,
) -> None:
    audit.record_success(
        module="quality",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type="QUALITY_INSPECTION",
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=after_data,
        context=context,
    )
    _commit_or_raise_write_error(session)


def _ensure_quality_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    row_or_scope: LyQualityInspection | dict[str, Any],
    resource_id: int | None = None,
    resource_no: str | None = None,
    enforce_action: bool = False,
) -> None:
    if isinstance(row_or_scope, LyQualityInspection):
        scope = {
            "company": row_or_scope.company,
            "item_code": row_or_scope.item_code,
            "supplier": row_or_scope.supplier,
            "warehouse": row_or_scope.warehouse,
            "work_order": row_or_scope.work_order,
            "sales_order": row_or_scope.sales_order,
            "source_type": row_or_scope.source_type,
            "source_id": row_or_scope.source_id,
        }
    else:
        scope = row_or_scope
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="quality",
        action=action,
        resource_scope=scope,
        required_fields=("company", "item_code"),
        resource_type="quality_inspection",
        resource_id=resource_id,
        resource_no=resource_no,
        enforce_action=enforce_action,
    )


def _quality_service(session: Session, request: Request) -> QualityService:
    return QualityService(session=session, source_validator=QualitySourceValidator(request_obj=request))


def _handle_write_exception(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    exc: Exception,
    request: Request,
) -> JSONResponse:
    _rollback_safely(session)
    if isinstance(exc, HTTPException):
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=resource_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    if isinstance(exc, AppException):
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=resource_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    log_safe_error(
        logger_obj=logger,
        message="quality_internal_error",
        exc=exc,
        request_id=get_request_id_from_request(request),
        extra={"module": "quality", "action": action, "error_code": QUALITY_INTERNAL_ERROR},
    )
    error = BusinessException(code=QUALITY_INTERNAL_ERROR)
    try:
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=resource_id,
            resource_no=resource_no,
            error_code=error.code,
        )
    except AuditWriteFailed as audit_exc:
        return _app_err(audit_exc)
    return _app_err(error)


def _hide_not_found() -> None:
    raise HTTPException(
        status_code=404,
        detail={"code": ERPNEXT_RESOURCE_NOT_FOUND, "message": message_of(ERPNEXT_RESOURCE_NOT_FOUND), "data": None},
    )


@router.post("/inspections")
def create_quality_inspection(
    request: Request,
    payload: QualityInspectionCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_inspection",
        )
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=payload.model_dump(),
            enforce_action=False,
        )
        data = _quality_service(session, request).create_inspection(
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=data.id,
            resource_no=data.inspection_no,
            after_data={"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status},
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )


@router.get("/inspections")
def list_quality_inspections(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_inspection",
    )
    _ensure_quality_scope(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        row_or_scope={
            "company": company,
            "item_code": item_code,
            "supplier": supplier,
            "warehouse": warehouse,
            "source_type": source_type,
            "source_id": source_id,
        },
        enforce_action=False,
    ) if company and item_code else None
    data = QualityService(session=session).list_inspections(
        company=company,
        item_code=item_code,
        supplier=supplier,
        warehouse=warehouse,
        source_type=source_type,
        source_id=source_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    filtered = []
    for row in data.items:
        db_row = session.query(LyQualityInspection).filter(LyQualityInspection.id == row.id).one()
        try:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope=db_row,
                resource_id=row.id,
                resource_no=row.inspection_no,
                enforce_action=False,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if detail.get("code") == "RESOURCE_ACCESS_DENIED":
                continue
            raise
        filtered.append(row)
    data.items = filtered
    data.total = len(filtered)
    return _ok(data.model_dump(mode="json"))


@router.get("/inspections/{inspection_id}")
def get_quality_inspection(
    inspection_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_inspection",
        resource_id=inspection_id,
    )
    row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
    if row is None:
        return _err(QUALITY_NOT_FOUND, status_code=status_of(QUALITY_NOT_FOUND))
    try:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=row,
            resource_id=inspection_id,
            resource_no=str(row.inspection_no),
            enforce_action=False,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "RESOURCE_ACCESS_DENIED":
            _hide_not_found()
        raise
    data = QualityService(session=session).get_detail_data(inspection_id)
    return _ok(data.model_dump(mode="json"))


@router.patch("/inspections/{inspection_id}")
def update_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionUpdateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_UPDATE,
        operation="update",
    )


@router.post("/inspections/{inspection_id}/confirm")
def confirm_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_CONFIRM,
        operation="confirm",
    )


@router.post("/inspections/{inspection_id}/cancel")
def cancel_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_CANCEL,
        operation="cancel",
    )


def _write_existing(
    *,
    inspection_id: int,
    request: Request,
    payload: Any,
    current_user: CurrentUser,
    session: Session,
    action: str,
    operation: str,
):
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_inspection",
            resource_id=inspection_id,
        )
        row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
        if row is None:
            raise BusinessException(code=QUALITY_NOT_FOUND)
        resource_no = str(row.inspection_no)
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=row,
            resource_id=inspection_id,
            resource_no=resource_no,
            enforce_action=False,
        )
        service = _quality_service(session, request)
        if operation == "update":
            data = service.update_inspection(
                inspection_id=inspection_id,
                payload=payload,
                operator=current_user.username,
                request_id=get_request_id_from_request(request),
            )
            after_data = {"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status}
        elif operation == "confirm":
            data = service.confirm_inspection(
                inspection_id=inspection_id,
                operator=current_user.username,
                request_id=get_request_id_from_request(request),
                remark=payload.remark,
            )
            after_data = data.model_dump(mode="json")
        else:
            data = service.cancel_inspection(
                inspection_id=inspection_id,
                operator=current_user.username,
                request_id=get_request_id_from_request(request),
                reason=payload.reason,
            )
            after_data = data.model_dump(mode="json")
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=inspection_id,
            resource_no=resource_no,
            after_data=after_data,
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=inspection_id,
            resource_no=resource_no,
            exc=exc,
            request=request,
        )


@router.get("/statistics")
def get_quality_statistics(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_statistics",
    )
    if company and item_code:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope={
                "company": company,
                "item_code": item_code,
                "supplier": supplier,
                "warehouse": warehouse,
                "source_type": source_type,
                "source_id": source_id,
            },
            enforce_action=False,
        )
    data = QualityService(session=session).statistics(
        company=company,
        item_code=item_code,
        supplier=supplier,
        warehouse=warehouse,
        source_type=source_type,
        source_id=source_id,
        from_date=from_date,
        to_date=to_date,
    )
    return _ok(data.model_dump(mode="json"))


@router.get("/export")
def export_quality_inspections(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_EXPORT
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_export",
        )
        if company and item_code:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope={
                    "company": company,
                    "item_code": item_code,
                    "supplier": supplier,
                    "warehouse": warehouse,
                    "source_type": source_type,
                    "source_id": source_id,
                },
                enforce_action=False,
            )
        data = QualityService(session=session).export_rows(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            after_data={"total": data.total},
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )


@router.get("/diagnostic")
def diagnostic_quality_inspections(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_DIAGNOSTIC
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_diagnostic",
        )
        if company and item_code:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope={
                    "company": company,
                    "item_code": item_code,
                    "supplier": supplier,
                    "warehouse": warehouse,
                    "source_type": source_type,
                    "source_id": source_id,
                },
                enforce_action=False,
            )
        data = QualityService(session=session).diagnostic(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            from_date=from_date,
            to_date=to_date,
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            after_data=data.model_dump(mode="json"),
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )
