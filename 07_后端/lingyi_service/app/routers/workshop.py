"""FastAPI router for workshop module (TASK-003)."""

from __future__ import annotations

from collections.abc import Generator
import logging
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.auth import is_internal_worker_api_enabled
from app.core.config import workshop_dry_run_audit_required
from app.core.config import workshop_enable_forbidden_diagnostics
from app.core.config import workshop_enable_worker_dry_run
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import WORKSHOP_DRY_RUN_DISABLED
from app.core.error_codes import WORKSHOP_EMPLOYEE_NOT_FOUND
from app.core.error_codes import WORKSHOP_IDEMPOTENCY_CONFLICT
from app.core.error_codes import WORKSHOP_INVALID_QTY
from app.core.error_codes import WORKSHOP_JOB_CARD_NOT_FOUND
from app.core.error_codes import WORKSHOP_JOB_CARD_STATUS_INVALID
from app.core.error_codes import WORKSHOP_PROCESS_MISMATCH
from app.core.error_codes import WORKSHOP_REVERSAL_EXCEEDS_REGISTERED
from app.core.error_codes import WORKSHOP_WAGE_RATE_NOT_FOUND
from app.core.error_codes import WORKSHOP_WAGE_RATE_COMPANY_REQUIRED
from app.core.error_codes import WORKSHOP_WAGE_RATE_SCOPE_REQUIRED
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import WORKSHOP_ITEM_MISMATCH
from app.core.error_codes import WORKSHOP_INTERNAL_ERROR
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import PermissionSourceUnavailable
from app.core.exceptions import ServiceAccountResourceForbiddenError
from app.core.exceptions import WorkshopInternalError
from app.core.logging import log_safe_error
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC_WORKER
from app.core.permissions import WORKSHOP_READ
from app.core.permissions import WORKSHOP_TICKET_BATCH
from app.core.permissions import WORKSHOP_TICKET_REGISTER
from app.core.permissions import WORKSHOP_TICKET_REVERSAL
from app.core.permissions import WORKSHOP_WAGE_RATE_MANAGE
from app.core.permissions import WORKSHOP_WAGE_RATE_MANAGE_ALL
from app.core.permissions import WORKSHOP_WAGE_RATE_READ
from app.core.permissions import WORKSHOP_WAGE_RATE_READ_ALL
from app.core.permissions import WORKSHOP_WAGE_READ
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.schemas.workshop import ApiResponse
from app.schemas.workshop import OperationWageRateCreateRequest
from app.schemas.workshop import OperationWageRateDeactivateRequest
from app.schemas.workshop import OperationWageRateListData
from app.schemas.workshop import WorkshopDailyWageListData
from app.schemas.workshop import WorkshopDailyWageQuery
from app.schemas.workshop import WorkshopJobCardSummaryData
from app.schemas.workshop import WorkshopJobCardSyncData
from app.schemas.workshop import WorkshopJobCardSyncRunOnceData
from app.schemas.workshop import WorkshopTicketBatchRequest
from app.schemas.workshop import WorkshopBatchFailedItem
from app.schemas.workshop import WorkshopBatchResult
from app.schemas.workshop import WorkshopTicketData
from app.schemas.workshop import WorkshopTicketListData
from app.schemas.workshop import WorkshopTicketListQuery
from app.schemas.workshop import WorkshopTicketRegisterRequest
from app.schemas.workshop import WorkshopTicketReversalData
from app.schemas.workshop import WorkshopTicketReversalRequest
from app.schemas.workshop import OperationWageRateCreateData
from app.schemas.workshop import OperationWageRateDeactivateData
from app.schemas.workshop import OperationWageRateQuery
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.workshop_job_card_sync_worker import WorkshopJobCardSyncWorker
from app.services.permission_service import PermissionService
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.service_account_policy import ServiceAccountPolicyService
from app.services.workshop_service import WorkshopService

router = APIRouter(prefix="/api/workshop", tags=["workshop"])
logger = logging.getLogger(__name__)


ROW_LEVEL_BATCH_APP_CODES = {
    WORKSHOP_INVALID_QTY,
    WORKSHOP_JOB_CARD_NOT_FOUND,
    WORKSHOP_EMPLOYEE_NOT_FOUND,
    WORKSHOP_JOB_CARD_STATUS_INVALID,
    WORKSHOP_PROCESS_MISMATCH,
    WORKSHOP_ITEM_MISMATCH,
    WORKSHOP_WAGE_RATE_NOT_FOUND,
    WORKSHOP_WAGE_RATE_SCOPE_REQUIRED,
    WORKSHOP_IDEMPOTENCY_CONFLICT,
    WORKSHOP_REVERSAL_EXCEEDS_REGISTERED,
    AUTH_FORBIDDEN,
}


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
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
    return _err(exc.code, exc.message, status_code=exc.status_code)


def _unknown_to_internal_error(request: Request, action: str, exc: Exception) -> WorkshopInternalError:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "workshop_internal_error",
        exc,
        request_id=request_id,
        extra={
            "error_code": WORKSHOP_INTERNAL_ERROR,
            "module": "workshop",
            "action": action,
        },
    )
    return WorkshopInternalError()


def _rollback_safely(session: Session, request: Request, action: str, origin: BaseException) -> None:
    try:
        session.rollback()
    except Exception as rollback_exc:  # pragma: no cover - rare branch
        request_id = get_request_id_from_request(request)
        error_code = origin.code if isinstance(origin, AppException) else ""
        log_safe_error(
            logger,
            "workshop_rollback_failed",
            rollback_exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "workshop",
                "action": action,
            },
        )


def _map_write_db_exception(request: Request, action: str, exc: BaseException) -> AppException:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "workshop_database_write_failed",
        exc,
        request_id=request_id,
        extra={
            "error_code": DATABASE_WRITE_FAILED,
            "module": "workshop",
            "action": action,
        },
    )
    return DatabaseWriteFailed()


def _commit_or_raise_write_error(session: Session, request: Request, action: str) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise _map_write_db_exception(request=request, action=action, exc=exc) from exc


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    request: Request,
    action: str,
    current_user: CurrentUser,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=before_data,
            after_data=after_data,
            error_code=error_code,
            context=context,
        )
        session.commit()
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        request_id = get_request_id_from_request(request)
        log_safe_error(
            logger,
            "operation_audit_write_failed",
            exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "workshop",
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id if resource_id is not None else "",
                "resource_no": resource_no or "",
                "user_id": current_user.username,
            },
        )


def _service(session: Session, request: Request) -> WorkshopService:
    return WorkshopService(session=session, erp_adapter=ERPNextJobCardAdapter(request_obj=request))


def _http_error_payload(exc: HTTPException, *, default_code: str = "AUTH_FORBIDDEN", default_message: str = "无权限访问该资源") -> tuple[str, str]:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = str(detail.get("code") or default_code)
    message = str(detail.get("message") or default_message)
    return code, message


def _batch_row_fail(
    *,
    failed_items: list[WorkshopBatchFailedItem],
    row_index: int,
    ticket_key: str,
    code: str,
    message: str,
) -> None:
    failed_items.append(
        WorkshopBatchFailedItem(
            row_index=row_index,
            index=row_index,
            code=code,
            error_code=code,
            message=message,
            ticket_key=ticket_key,
        )
    )


def _record_batch_security_denial_strict(
    *,
    audit: AuditService,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_no: str | None,
    deny_reason: str,
) -> None:
    audit.record_security_audit(
        event_type=AUTH_FORBIDDEN,
        module="workshop",
        action=action,
        resource_type=resource_type,
        resource_id=None,
        resource_no=resource_no,
        user=current_user,
        deny_reason=deny_reason,
        permission_source=get_permission_source(),
        request_obj=request,
    )


@router.post("/tickets/register")
def register_ticket(
    payload: WorkshopTicketRegisterRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Register workshop ticket."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_TICKET_REGISTER
    request_id = get_request_id_from_request(request)
    resource = None

    try:
        resource = service.resolve_job_card_resource(
            job_card=payload.job_card,
            process_name=payload.process_name,
            request_item_code=payload.item_code,
            enforce_status=True,
        )
        permission_service.ensure_workshop_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_TICKET_REGISTER,
            item_code=resource.item_code,
            company=resource.company,
            job_card=resource.job_card,
            resource_type="JobCard",
            resource_no=resource.job_card,
            enforce_action=True,
        )
        data: WorkshopTicketData = service.register_ticket(
            payload=payload,
            operator=current_user.username,
            request_id=request_id,
            resolved_resource=resource,
        )
        after_data = service.get_ticket_snapshot(ticket_id=data.ticket_id)
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="workshop_ticket",
            resource_id=data.ticket_id,
            resource_no=data.ticket_no,
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if exc.code in {WORKSHOP_ITEM_MISMATCH, WORKSHOP_WAGE_RATE_SCOPE_REQUIRED}:
            resource_no = payload.item_code
            if resource is not None and getattr(resource, "item_code", None):
                resource_no = resource.item_code
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=WORKSHOP_TICKET_REGISTER,
                resource_type="WageRate" if exc.code == WORKSHOP_WAGE_RATE_SCOPE_REQUIRED else "Item",
                resource_no=resource_no,
                deny_reason=exc.message,
            )
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=None,
            resource_no=payload.ticket_key,
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=None,
            resource_no=payload.ticket_key,
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/tickets/reversal")
def reverse_ticket(
    payload: WorkshopTicketReversalRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Reverse workshop ticket."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_TICKET_REVERSAL
    request_id = get_request_id_from_request(request)

    try:
        resource = service.resolve_job_card_resource(
            job_card=payload.job_card,
            process_name=payload.process_name,
            request_item_code=payload.item_code,
            enforce_status=True,
        )
        permission_service.ensure_workshop_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_TICKET_REVERSAL,
            item_code=resource.item_code,
            company=resource.company,
            job_card=resource.job_card,
            resource_type="JobCard",
            resource_no=resource.job_card,
            enforce_action=True,
        )
        if payload.original_ticket_id:
            original_resource = service.get_ticket_resource_context(payload.original_ticket_id)
            permission_service.ensure_workshop_resource_permission(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_TICKET_REVERSAL,
                item_code=original_resource.item_code,
                company=original_resource.company,
                job_card=original_resource.job_card,
                resource_type="WorkshopTicket",
                resource_id=payload.original_ticket_id,
                resource_no=original_resource.item_code,
                enforce_action=False,
            )
        data: WorkshopTicketReversalData = service.reverse_ticket(
            payload=payload,
            operator=current_user.username,
            request_id=request_id,
            resolved_resource=resource,
        )
        after_data = service.get_ticket_snapshot(ticket_id=data.ticket_id)
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="workshop_ticket",
            resource_id=data.ticket_id,
            resource_no=data.ticket_no,
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if exc.code == WORKSHOP_ITEM_MISMATCH:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=WORKSHOP_TICKET_REVERSAL,
                resource_type="Item",
                resource_no=payload.item_code,
                deny_reason=exc.message,
            )
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=payload.original_ticket_id,
            resource_no=payload.ticket_key,
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=payload.original_ticket_id,
            resource_no=payload.ticket_key,
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/tickets/batch")
def batch_tickets(
    payload: WorkshopTicketBatchRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Batch import workshop tickets."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_TICKET_BATCH
    request_id = get_request_id_from_request(request)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_TICKET_BATCH,
            module="workshop",
            raise_on_audit_failure=True,
        )
        user_permissions = permission_service.get_workshop_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_TICKET_BATCH,
            resource_type="WorkshopTicket",
            resource_no="batch",
        )
        success_items: list[WorkshopTicketData] = []
        failed_items: list[WorkshopBatchFailedItem] = []
        permission_adapter = ERPNextPermissionAdapter(request_obj=request)

        for row_index, row in enumerate(payload.tickets, start=1):
            try:
                row_resource = service.resolve_job_card_resource(
                    job_card=row.job_card,
                    process_name=row.process_name,
                    request_item_code=row.item_code,
                    enforce_status=True,
                )

                if user_permissions is not None:
                    if not permission_adapter.is_item_permitted(item_code=row_resource.item_code, user_permissions=user_permissions):
                        _record_batch_security_denial_strict(
                            audit=audit,
                            request=request,
                            current_user=current_user,
                            action=WORKSHOP_TICKET_BATCH,
                            resource_type="Item",
                            resource_no=row_resource.item_code,
                            deny_reason="资源权限不足：无权访问该 item_code",
                        )
                        _batch_row_fail(
                            failed_items=failed_items,
                            row_index=row_index,
                            ticket_key=row.ticket_key,
                            code=AUTH_FORBIDDEN,
                            message="无权限访问该资源",
                        )
                        continue
                    if row_resource.company and not permission_adapter.is_company_permitted(
                        company=row_resource.company,
                        user_permissions=user_permissions,
                    ):
                        _record_batch_security_denial_strict(
                            audit=audit,
                            request=request,
                            current_user=current_user,
                            action=WORKSHOP_TICKET_BATCH,
                            resource_type="Company",
                            resource_no=row_resource.company,
                            deny_reason="资源权限不足：无权访问该 company",
                        )
                        _batch_row_fail(
                            failed_items=failed_items,
                            row_index=row_index,
                            ticket_key=row.ticket_key,
                            code=AUTH_FORBIDDEN,
                            message="无权限访问该资源",
                        )
                        continue

                if row.operation_type.strip().lower() == "reversal" and row.original_ticket_id:
                    original_resource = service.get_ticket_resource_context(row.original_ticket_id)
                    if user_permissions is not None:
                        if not permission_adapter.is_item_permitted(
                            item_code=original_resource.item_code,
                            user_permissions=user_permissions,
                        ):
                            _record_batch_security_denial_strict(
                                audit=audit,
                                request=request,
                                current_user=current_user,
                                action=WORKSHOP_TICKET_BATCH,
                                resource_type="Item",
                                resource_no=original_resource.item_code,
                                deny_reason="资源权限不足：无权访问原工票 item_code",
                            )
                            _batch_row_fail(
                                failed_items=failed_items,
                                row_index=row_index,
                                ticket_key=row.ticket_key,
                                code=AUTH_FORBIDDEN,
                                message="无权限访问该资源",
                            )
                            continue
                        if original_resource.company and not permission_adapter.is_company_permitted(
                            company=original_resource.company,
                            user_permissions=user_permissions,
                        ):
                            _record_batch_security_denial_strict(
                                audit=audit,
                                request=request,
                                current_user=current_user,
                                action=WORKSHOP_TICKET_BATCH,
                                resource_type="Company",
                                resource_no=original_resource.company,
                                deny_reason="资源权限不足：无权访问原工票 company",
                            )
                            _batch_row_fail(
                                failed_items=failed_items,
                                row_index=row_index,
                                ticket_key=row.ticket_key,
                                code=AUTH_FORBIDDEN,
                                message="无权限访问该资源",
                            )
                            continue

                with session.begin_nested():
                    success_items.append(
                        service.process_batch_row(
                            row=row,
                            operator=current_user.username,
                            request_id=request_id,
                            resolved_resource=row_resource,
                        )
                    )
            except HTTPException as exc:
                code, message = _http_error_payload(exc)
                if code == AUTH_FORBIDDEN:
                    _batch_row_fail(
                        failed_items=failed_items,
                        row_index=row_index,
                        ticket_key=row.ticket_key,
                        code=code,
                        message=message,
                    )
                    continue
                raise
            except AppException as exc:
                if exc.code == WORKSHOP_ITEM_MISMATCH:
                    _record_batch_security_denial_strict(
                        audit=audit,
                        request=request,
                        current_user=current_user,
                        action=WORKSHOP_TICKET_BATCH,
                        resource_type="Item",
                        resource_no=row.item_code,
                        deny_reason=exc.message,
                    )
                if exc.code in ROW_LEVEL_BATCH_APP_CODES:
                    _batch_row_fail(
                        failed_items=failed_items,
                        row_index=row_index,
                        ticket_key=row.ticket_key,
                        code=exc.code,
                        message=exc.message,
                    )
                    continue
                raise
            except Exception as exc:
                raise WorkshopInternalError() from exc

        data = WorkshopBatchResult(
            success_count=len(success_items),
            failed_count=len(failed_items),
            success_items=success_items,
            failed_items=failed_items,
        )
        after_data = {
            "success_count": data.success_count,
            "failed_count": data.failed_count,
        }
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="workshop_ticket",
            resource_id=None,
            resource_no=f"batch:{data.success_count}/{data.failed_count}",
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=None,
            resource_no="batch",
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="workshop_ticket",
            resource_id=None,
            resource_no="batch",
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/tickets")
def list_tickets(
    request: Request,
    employee: str | None = None,
    job_card: str | None = None,
    item_code: str | None = None,
    process_name: str | None = None,
    operation_type: str | None = None,
    work_date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """List workshop tickets."""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=WORKSHOP_READ,
        module="workshop",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="workshop",
        action_context=WORKSHOP_READ,
        resource_type="workshop",
    )
    query = WorkshopTicketListQuery(
        employee=employee,
        job_card=job_card,
        item_code=item_code,
        process_name=process_name,
        operation_type=operation_type,
        work_date=work_date,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    service = _service(session=session, request=request)
    try:
        data: WorkshopTicketListData = service.list_tickets(query=query, allowed_item_codes=allowed_item_codes)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, WORKSHOP_READ, exc))


@router.get("/daily-wages")
def list_daily_wages(
    request: Request,
    employee: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    process_name: str | None = None,
    item_code: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """List daily wages."""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=WORKSHOP_WAGE_READ,
        module="workshop",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="workshop",
        action_context=WORKSHOP_WAGE_READ,
        resource_type="workshop",
    )
    query = WorkshopDailyWageQuery(
        employee=employee,
        from_date=from_date,
        to_date=to_date,
        process_name=process_name,
        item_code=item_code,
        page=page,
        page_size=page_size,
    )
    service = _service(session=session, request=request)
    try:
        data: WorkshopDailyWageListData = service.list_daily_wages(query=query, allowed_item_codes=allowed_item_codes)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, WORKSHOP_WAGE_READ, exc))


@router.get("/job-cards/{job_card}/summary")
def get_job_card_summary(
    job_card: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Get local ticket summary by job card."""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=WORKSHOP_READ,
        module="workshop",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="workshop",
        action_context=WORKSHOP_READ,
        resource_type="workshop",
    )
    service = _service(session=session, request=request)
    try:
        data: WorkshopJobCardSummaryData = service.get_job_card_summary(
            job_card=job_card,
            allowed_item_codes=allowed_item_codes,
        )
        if data.net_qty and allowed_item_codes is not None and data.job_card and data.job_card not in {"", None}:
            # 仅做显式 item 资源校验（list 已做过滤）。
            item_row = service.list_tickets(
                query=WorkshopTicketListQuery(job_card=job_card, page=1, page_size=1),
                allowed_item_codes=None,
            )
            if item_row.items:
                permission_service.require_item_access(
                    current_user=current_user,
                    request_obj=request,
                    module="workshop",
                    action=WORKSHOP_READ,
                    item_code=item_row.items[0].item_code,
                    resource_type="item",
                    resource_no=item_row.items[0].item_code,
                )
        return _ok(data.model_dump())
    except BusinessException as exc:
        if exc.code == "AUTH_FORBIDDEN":
            return _err("AUTH_FORBIDDEN", "无权限访问该资源", status_code=403)
        return _app_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, WORKSHOP_READ, exc))


@router.post("/job-cards/{job_card}/sync")
def retry_job_card_sync(
    job_card: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Manual retry ERPNext Job Card sync."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_JOB_CARD_SYNC
    request_id = get_request_id_from_request(request)

    try:
        resource = service.resolve_job_card_resource(
            job_card=job_card,
            process_name=None,
            request_item_code=None,
            enforce_status=False,
        )
        permission_service.ensure_workshop_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_JOB_CARD_SYNC,
            item_code=resource.item_code,
            company=resource.company,
            job_card=resource.job_card,
            resource_type="JobCard",
            resource_no=resource.job_card,
            enforce_action=True,
        )
        before_data = service.get_job_card_summary(job_card=job_card).model_dump()
        data: WorkshopJobCardSyncData = service.retry_job_card_sync(
            job_card=job_card,
            request_id=request_id,
            operator=current_user.username,
        )
        after_data = service.get_job_card_summary(job_card=job_card).model_dump()
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="job_card",
            resource_id=None,
            resource_no=job_card,
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="job_card",
            resource_id=None,
            resource_no=job_card,
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="job_card",
            resource_id=None,
            resource_no=job_card,
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post(
    "/internal/job-card-sync/run-once",
    response_model=ApiResponse[WorkshopJobCardSyncRunOnceData],
)
def run_job_card_sync_once(
    request: Request,
    batch_size: int = 20,
    dry_run: bool = False,
    include_forbidden_diagnostics: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Run workshop Job Card sync worker once (internal/admin only)."""
    permission_service = PermissionService(session=session)
    policy_service = ServiceAccountPolicyService(request_obj=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_JOB_CARD_SYNC_WORKER
    if not is_internal_worker_api_enabled():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="JobCardSyncWorker",
            resource_no=None,
            deny_reason="内部 Worker 接口未启用",
            event_type=INTERNAL_API_DISABLED,
            module="workshop",
        )
        return _err(INTERNAL_API_DISABLED, "内部接口未启用", status_code=status_of(INTERNAL_API_DISABLED))

    try:
        permission_service.require_action_from_roles_only(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="workshop",
            resource_type="job_card_sync_worker",
        )
        permission_service.require_internal_worker_principal(
            current_user=current_user,
            request_obj=request,
            action=action,
        )
        if dry_run and not workshop_enable_worker_dry_run():
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="JobCardSyncWorker",
                resource_no=None,
                deny_reason="生产环境未开启内部 Worker dry-run",
                event_type=WORKSHOP_DRY_RUN_DISABLED,
                module="workshop",
            )
            return _err(
                WORKSHOP_DRY_RUN_DISABLED,
                "生产环境未开启内部 Worker dry-run",
                status_code=status_of(WORKSHOP_DRY_RUN_DISABLED),
            )
        try:
            worker_policy = policy_service.get_worker_policy(current_user=current_user)
        except PermissionSourceUnavailable:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="JobCardSyncWorker",
                resource_no=None,
                deny_reason="ERPNext User Permission 查询失败",
                event_type=PERMISSION_SOURCE_UNAVAILABLE,
                module="workshop",
            )
            return _err(
                PERMISSION_SOURCE_UNAVAILABLE,
                "权限来源暂时不可用",
                status_code=status_of(PERMISSION_SOURCE_UNAVAILABLE),
            )
        except ServiceAccountResourceForbiddenError as exc:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="JobCardSyncWorker",
                resource_no=None,
                deny_reason=exc.message,
                event_type=AUTH_FORBIDDEN,
                module="workshop",
            )
            return _app_err(exc)

        diagnostics_enabled = include_forbidden_diagnostics or workshop_enable_forbidden_diagnostics()

        if dry_run:
            worker = WorkshopJobCardSyncWorker(
                session=session,
                erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
            )
            preview = worker.preview_once(
                limit=max(1, min(batch_size, 200)),
                service_account_policy=worker_policy,
                include_forbidden_diagnostics=include_forbidden_diagnostics,
                request_obj=request,
                current_user=current_user,
                audit_service=audit,
            )
            data = WorkshopJobCardSyncRunOnceData(
                dry_run=True,
                forbidden_diagnostics_enabled=diagnostics_enabled,
                would_process_count=preview.would_process,
                processed_count=0,
                succeeded_count=0,
                failed_count=0,
                forbidden_diagnostic_count=preview.forbidden_diagnostic,
                skipped_forbidden_count=preview.forbidden_diagnostic,
                blocked_scope_count=preview.blocked_scope,
                dead_count=0,
                would_process=preview.would_process,
                processed=0,
                succeeded=0,
                failed=0,
                forbidden_diagnostic=preview.forbidden_diagnostic,
                skipped_forbidden=preview.forbidden_diagnostic,
                blocked_scope=preview.blocked_scope,
                dead=0,
            )
            if workshop_dry_run_audit_required():
                audit.record_success(
                    module="workshop",
                    action=action,
                    operator=current_user.username,
                    operator_roles=current_user.roles,
                    resource_type="job_card_sync_worker",
                    resource_id=None,
                    resource_no="run-once",
                    before_data={
                        "batch_size": max(1, min(batch_size, 200)),
                        "dry_run": True,
                        "include_forbidden_diagnostics": include_forbidden_diagnostics,
                        "forbidden_diagnostics_enabled": diagnostics_enabled,
                    },
                    after_data=data.model_dump(),
                    context=context,
                )
            _commit_or_raise_write_error(session=session, request=request, action=action)
            return _ok(data.model_dump())

        worker = WorkshopJobCardSyncWorker(
            session=session,
            erp_adapter=ERPNextJobCardAdapter(request_obj=None, use_service_account=True),
        )
        result = worker.run_once(
            limit=max(1, min(batch_size, 200)),
            service_account_policy=worker_policy,
            include_forbidden_diagnostics=include_forbidden_diagnostics,
            request_obj=request,
            current_user=current_user,
            audit_service=audit,
        )
        data = WorkshopJobCardSyncRunOnceData(
            dry_run=False,
            forbidden_diagnostics_enabled=diagnostics_enabled,
            would_process_count=result.would_process,
            processed_count=result.processed,
            succeeded_count=result.succeeded,
            failed_count=result.failed,
            forbidden_diagnostic_count=result.forbidden_diagnostic,
            skipped_forbidden_count=result.forbidden_diagnostic,
            blocked_scope_count=result.blocked_scope,
            dead_count=result.dead,
            would_process=result.would_process,
            processed=result.processed,
            succeeded=result.succeeded,
            failed=result.failed,
            forbidden_diagnostic=result.forbidden_diagnostic,
            skipped_forbidden=result.forbidden_diagnostic,
            blocked_scope=result.blocked_scope,
            dead=result.dead,
        )
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="job_card_sync_worker",
            resource_id=None,
            resource_no="run-once",
            before_data={
                "batch_size": max(1, min(batch_size, 200)),
                "dry_run": dry_run,
                "include_forbidden_diagnostics": include_forbidden_diagnostics,
                "forbidden_diagnostics_enabled": diagnostics_enabled,
            },
            after_data=data.model_dump(),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/wage-rates")
def list_wage_rates(
    request: Request,
    item_code: str | None = None,
    company: str | None = None,
    is_global: bool | None = None,
    process_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """List wage rates."""
    normalized_company = company.strip() if company is not None else None
    if company is not None and not normalized_company:
        return _err(WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, "company 不能为空", status_code=status_of(WORKSHOP_WAGE_RATE_COMPANY_REQUIRED))
    normalized_item_code = item_code.strip() if item_code is not None else None

    permission_service = PermissionService(session=session)
    agg = permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=WORKSHOP_WAGE_RATE_READ,
        module="workshop",
    )
    allow_global_read = WORKSHOP_WAGE_RATE_READ_ALL in set(agg.actions)
    if is_global is True and not allow_global_read:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_WAGE_RATE_READ_ALL,
            module="workshop",
            resource_type="wage_rate",
        )

    user_permissions = permission_service.get_workshop_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=WORKSHOP_WAGE_RATE_READ,
        resource_type="WageRate",
        resource_no=normalized_item_code,
    )
    if normalized_item_code and user_permissions is not None:
        permission_service.ensure_workshop_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=WORKSHOP_WAGE_RATE_READ,
            item_code=normalized_item_code,
            company=normalized_company,
            resource_type="Item",
            resource_no=normalized_item_code,
            enforce_action=False,
            user_permissions=user_permissions,
        )

    query = OperationWageRateQuery(
        item_code=normalized_item_code,
        company=normalized_company,
        is_global=is_global,
        process_name=process_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = _service(session=session, request=request)
    try:
        data: OperationWageRateListData = service.list_wage_rates(
            query=query,
            user_permissions=user_permissions,
            allow_global_read=allow_global_read,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, WORKSHOP_WAGE_RATE_READ, exc))


@router.post("/wage-rates")
def create_wage_rate(
    payload: OperationWageRateCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Create wage rate record."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_WAGE_RATE_MANAGE

    try:
        resource = service.resolve_wage_rate_resource(item_code=payload.item_code, company=payload.company)
        if resource.is_global:
            permission_service.require_action(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE,
                module="workshop",
            )
            permission_service.require_action(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE_ALL,
                module="workshop",
                resource_type="wage_rate",
            )
            if resource.company:
                permission_service.ensure_workshop_company_permission(
                    current_user=current_user,
                    request_obj=request,
                    action=WORKSHOP_WAGE_RATE_MANAGE,
                    company=resource.company,
                    resource_type="Company",
                    resource_no=resource.company,
                    enforce_action=False,
                )
        else:
            permission_service.ensure_workshop_resource_permission(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE,
                item_code=str(resource.item_code),
                company=resource.company,
                resource_type="Item",
                resource_no=str(resource.item_code),
                enforce_action=True,
            )

        data: OperationWageRateCreateData = service.create_wage_rate(
            payload=payload,
            operator=current_user.username,
            resolved_resource=resource,
        )
        after_data = service.get_wage_rate_snapshot(rate_id=data.id)
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="wage_rate",
            resource_id=data.id,
            resource_no=f"{after_data.get('item_code') or '*'}@{after_data.get('company') or '*'}:{after_data.get('process_name')}",
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="wage_rate",
            resource_id=None,
            resource_no=f"{payload.item_code or '*'}@{payload.company or '*'}:{payload.process_name}",
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="wage_rate",
            resource_id=None,
            resource_no=f"{payload.item_code or '*'}@{payload.company or '*'}:{payload.process_name}",
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/wage-rates/{rate_id}/deactivate")
def deactivate_wage_rate(
    rate_id: int,
    payload: OperationWageRateDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Deactivate wage rate."""
    permission_service = PermissionService(session=session)
    service = _service(session=session, request=request)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = WORKSHOP_WAGE_RATE_MANAGE

    try:
        before_data = service.get_wage_rate_snapshot(rate_id=rate_id)
        target_item_code = before_data.get("item_code")
        target_company = before_data.get("company")

        if target_item_code:
            permission_service.ensure_workshop_resource_permission(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE,
                item_code=str(target_item_code),
                company=str(target_company) if target_company else None,
                resource_type="WageRate",
                resource_id=rate_id,
                resource_no=str(target_item_code),
                enforce_action=True,
            )
        else:
            permission_service.require_action(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE,
                module="workshop",
                resource_type="wage_rate",
                resource_id=rate_id,
            )
            permission_service.require_action(
                current_user=current_user,
                request_obj=request,
                action=WORKSHOP_WAGE_RATE_MANAGE_ALL,
                module="workshop",
                resource_type="wage_rate",
                resource_id=rate_id,
            )
            if target_company:
                permission_service.ensure_workshop_company_permission(
                    current_user=current_user,
                    request_obj=request,
                    action=WORKSHOP_WAGE_RATE_MANAGE,
                    company=str(target_company),
                    resource_type="Company",
                    resource_id=rate_id,
                    resource_no=str(target_company),
                    enforce_action=False,
                )

        data: OperationWageRateDeactivateData = service.deactivate_wage_rate(
            rate_id=rate_id,
            operator=current_user.username,
            reason=payload.reason,
        )
        after_data = service.get_wage_rate_snapshot(rate_id=rate_id)
        audit.record_success(
            module="workshop",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="wage_rate",
            resource_id=rate_id,
            resource_no=f"{before_data.get('item_code') or '*'}@{before_data.get('company') or '*'}:{before_data.get('process_name')}",
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise exc
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="wage_rate",
            resource_id=rate_id,
            resource_no=None,
            before_data=None,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="wage_rate",
            resource_id=rate_id,
            resource_no=None,
            before_data=None,
            after_data=None,
            error_code=WORKSHOP_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))
