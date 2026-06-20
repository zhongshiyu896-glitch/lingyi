"""FastAPI-native finance approval task routes."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.permissions import FINANCE_APPROVAL_MANAGE
from app.core.permissions import FINANCE_APPROVAL_READ
from app.schemas.finance_approval import FinanceApprovalDecisionRequest
from app.schemas.finance_approval import FinanceApprovalTaskCreateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.finance_approval_service import FinanceApprovalService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/finance/approval-tasks", tags=["finance_approval"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _err(exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "data": None})


def _require_action(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_id: int | None = None,
) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="finance_approval",
        resource_type="FINANCE_APPROVAL_TASK",
        resource_id=resource_id,
    )


@router.get("")
@router.get("/")
def list_finance_approval_tasks(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=FINANCE_APPROVAL_READ)
    try:
        data = FinanceApprovalService(session).list_tasks(
            company=company,
            keyword=keyword,
            source_type=source_type,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.get("/templates")
def list_finance_approval_templates(
    request: Request,
    company: str | None = Query(default="默认公司"),
    source_type: str | None = Query(default=None),
    status: str | None = Query(default="active"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=FINANCE_APPROVAL_READ)
    try:
        data = FinanceApprovalService(session).list_templates(
            company=company,
            source_type=source_type,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("")
@router.post("/")
def create_finance_approval_task(
    payload: FinanceApprovalTaskCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=FINANCE_APPROVAL_MANAGE)
    audit = AuditService(session)
    try:
        result = FinanceApprovalService(session).create_task(payload=payload, actor=current_user.username)
        audit.record_success(
            module="finance_approval",
            action=FINANCE_APPROVAL_MANAGE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="finance_approval",
            action=FINANCE_APPROVAL_MANAGE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)


@router.post("/{task_id}/approve")
def approve_finance_approval_task(
    task_id: int,
    payload: FinanceApprovalDecisionRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=FINANCE_APPROVAL_MANAGE,
        resource_id=task_id,
    )
    audit = AuditService(session)
    try:
        result = FinanceApprovalService(session).approve_task(
            task_id=task_id,
            payload=payload,
            actor=current_user.username,
            actor_roles=current_user.roles,
        )
        audit.record_success(
            module="finance_approval",
            action="approve_task",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="finance_approval",
            action="approve_task",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=task_id,
            resource_no=None,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _ok(result.item)


@router.post("/{task_id}/reject")
def reject_finance_approval_task(
    task_id: int,
    payload: FinanceApprovalDecisionRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=FINANCE_APPROVAL_MANAGE,
        resource_id=task_id,
    )
    audit = AuditService(session)
    try:
        result = FinanceApprovalService(session).reject_task(
            task_id=task_id,
            payload=payload,
            actor=current_user.username,
            actor_roles=current_user.roles,
        )
        audit.record_success(
            module="finance_approval",
            action="reject_task",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="finance_approval",
            action="reject_task",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FINANCE_APPROVAL_TASK",
            resource_id=task_id,
            resource_no=None,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _ok(result.item)
