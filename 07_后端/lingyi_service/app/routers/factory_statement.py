"""FastAPI router for factory statement APIs (TASK-006D)."""

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
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_INTERNAL_ERROR
from app.core.error_codes import FACTORY_STATEMENT_PERMISSION_DENIED
from app.core.error_codes import FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import FACTORY_STATEMENT_SOURCE_NOT_FOUND
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.logging import log_safe_error
from app.core.permissions import FACTORY_STATEMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_CONFIRM
from app.core.permissions import FACTORY_STATEMENT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
from app.core.permissions import FACTORY_STATEMENT_READ
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.models.factory_statement import LyFactoryStatement
from app.schemas.factory_statement import FactoryStatementCancelRequest
from app.schemas.factory_statement import FactoryStatementConfirmRequest
from app.schemas.factory_statement import FactoryStatementCreateRequest
from app.schemas.factory_statement import FactoryStatementPayableDraftRequest
from app.schemas.factory_statement import FactoryStatementPayableWorkerRunOnceRequest
from app.schemas.factory_statement import FactoryStatementPayableWorkerRunOnceData
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.factory_statement_payable_worker import FactoryStatementPayableWorker
from app.services.factory_statement_service import FactoryStatementService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/factory-statements", tags=["factory_statement"])
logger = logging.getLogger(__name__)


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message, "data": {}},
    )


def _app_err(exc: AppException) -> JSONResponse:
    data = getattr(exc, "data", {}) or {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": data,
        },
    )


def _map_permission_error(exc: HTTPException) -> JSONResponse:
    code = _permission_error_code(exc)
    detail = exc.detail
    if isinstance(detail, dict):
        if code == FACTORY_STATEMENT_PERMISSION_DENIED:
            return _err(
                FACTORY_STATEMENT_PERMISSION_DENIED,
                message_of(FACTORY_STATEMENT_PERMISSION_DENIED),
                status_of(FACTORY_STATEMENT_PERMISSION_DENIED),
            )
        if code == FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE:
            return _err(
                FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE,
                message_of(FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE),
                status_of(FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE),
            )
        return _err(code, str(detail.get("message") or "请求失败"), exc.status_code)
    if isinstance(detail, str):
        return _err("HTTP_ERROR", detail, exc.status_code)
    return _err("HTTP_ERROR", "请求失败", exc.status_code)


def _permission_error_code(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        if code == AUTH_FORBIDDEN:
            return FACTORY_STATEMENT_PERMISSION_DENIED
        if code == PERMISSION_SOURCE_UNAVAILABLE:
            return FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE
        return code
    return "HTTP_ERROR"


def _rollback_safely(session: Session) -> None:
    try:
        session.rollback()
    except Exception:  # pragma: no cover
        return


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
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
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


def _commit_or_raise_write_error(session: Session) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session)
        raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc


def _resolve_readable_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
) -> tuple[set[str] | None, set[str] | None]:
    if get_permission_source() != "erpnext":
        return None, None

    permissions = permission_service.get_factory_statement_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=FACTORY_STATEMENT_READ,
        resource_type="factory_statement",
        resource_id=None,
        resource_no=None,
    )
    if permissions is None or permissions.unrestricted:
        return None, None

    readable_companies = set(permissions.allowed_companies) if permissions.allowed_companies else None
    readable_suppliers = set(permissions.allowed_suppliers) if permissions.allowed_suppliers else None
    return readable_companies, readable_suppliers


def _resolve_worker_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
) -> tuple[set[str] | None, set[str] | None]:
    if get_permission_source() != "erpnext":
        return None, None

    permissions = permission_service.get_factory_statement_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
        resource_type="factory_statement_payable_worker",
        resource_id=None,
        resource_no=current_user.username,
    )
    if permissions is None:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE)
    # Worker must run under explicit supplier+company scope, never unrestricted.
    if permissions.unrestricted:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_DENIED)

    allowed_companies = {item.strip() for item in permissions.allowed_companies if item and item.strip()}
    allowed_suppliers = {item.strip() for item in permissions.allowed_suppliers if item and item.strip()}
    if not allowed_companies or not allowed_suppliers:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_DENIED)
    return allowed_companies, allowed_suppliers


@router.post("/")
def create_factory_statement(
    request: Request,
    payload: FactoryStatementCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(payload.company or "").strip() or None,
            supplier=str(payload.supplier or "").strip() or None,
            resource_type="factory_statement",
            resource_id=None,
            resource_no=None,
            enforce_action=True,
        )

        result = service.create_draft(
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )
        resource_no = result.statement_no

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=result.statement_id,
            resource_no=result.statement_no,
            before_data=None,
            after_data={
                "statement_id": result.statement_id,
                "statement_no": result.statement_no,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        exc_data = getattr(exc, "data", {}) or {}
        conflict_statement_no = str(exc_data.get("statement_no") or "").strip() or None
        conflict_statement_id = exc_data.get("statement_id")
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=int(conflict_statement_id) if conflict_statement_id is not None else None,
                resource_no=resource_no or conflict_statement_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR, message="加工厂对账单处理失败")
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return JSONResponse(
            status_code=error.status_code,
            content={
                "code": error.code,
                "message": error.message,
                "data": None,
            },
        )


@router.post("/{statement_id}/confirm")
def confirm_factory_statement(
    statement_id: int,
    request: Request,
    payload: FactoryStatementConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CONFIRM
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.confirm_statement(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.id,
                "statement_no": result.statement_no,
                "status": result.status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/cancel")
def cancel_factory_statement(
    statement_id: int,
    request: Request,
    payload: FactoryStatementCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CANCEL
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.cancel_statement(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.id,
                "statement_no": result.statement_no,
                "status": result.status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/payable-draft")
def create_factory_statement_payable_draft(
    statement_id: int,
    request: Request,
    payload: FactoryStatementPayableDraftRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.create_payable_draft_outbox(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
            erp_adapter=ERPNextPurchaseInvoiceAdapter(request_obj=request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.statement_id,
                "statement_no": result.statement_no,
                "status": result.status,
                "payable_outbox_id": result.payable_outbox_id,
                "payable_outbox_status": result.payable_outbox_status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/internal/payable-draft-sync/run-once")
def run_factory_statement_payable_worker_once(
    request: Request,
    payload: FactoryStatementPayableWorkerRunOnceRequest = Body(default=FactoryStatementPayableWorkerRunOnceRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action_from_roles_only(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement_payable_worker",
            resource_id=None,
        )
        if not current_user.is_service_account:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="FactoryStatementPayableWorker",
                resource_no=current_user.username,
                deny_reason="内部 payable worker 仅允许服务账号调用",
                module="factory_statement",
            )
            return _err(
                FACTORY_STATEMENT_PERMISSION_DENIED,
                message_of(FACTORY_STATEMENT_PERMISSION_DENIED),
                status_of(FACTORY_STATEMENT_PERMISSION_DENIED),
            )

        allowed_companies, allowed_suppliers = _resolve_worker_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        worker = FactoryStatementPayableWorker(
            session=session,
            adapter=ERPNextPurchaseInvoiceAdapter(request_obj=None, use_service_account=True),
        )
        result = worker.run_once(
            batch_size=payload.batch_size,
            worker_id=f"factory-statement-payable-worker:{current_user.username}",
            dry_run=payload.dry_run,
            allowed_companies=allowed_companies,
            allowed_suppliers=allowed_suppliers,
        )
        data = FactoryStatementPayableWorkerRunOnceData(
            dry_run=result.dry_run,
            processed_count=result.processed_count,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            dead_count=result.dead_count,
        )
        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT_PAYABLE_WORKER",
            resource_id=None,
            resource_no=current_user.username,
            before_data={"dry_run": payload.dry_run, "batch_size": payload.batch_size},
            after_data=data.model_dump(mode="json"),
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=current_user.username,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=current_user.username,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/")
def list_factory_statements(
    request: Request,
    company: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    statement_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data = service.list_statements(
            company=company,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
            statement_status=statement_status,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/{statement_id}")
def get_factory_statement_detail(
    statement_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=str(header.statement_no),
            enforce_action=False,
        )

        data = service.get_statement_detail(statement_id=statement_id)

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=str(header.statement_no),
            before_data=None,
            after_data={"statement_id": statement_id, "statement_no": str(header.statement_no)},
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)
