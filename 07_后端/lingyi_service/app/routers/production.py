"""FastAPI router for production planning module (TASK-004A)."""

from __future__ import annotations

from collections.abc import Generator
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
from app.core.auth import is_internal_worker_principal
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import PRODUCTION_INTERNAL_ERROR
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ProductionInternalError
from app.core.logging import log_safe_error
from app.core.permissions import PRODUCTION_JOB_CARD_SYNC
from app.core.permissions import PRODUCTION_MATERIAL_CHECK
from app.core.permissions import PRODUCTION_PLAN_CREATE
from app.core.permissions import PRODUCTION_READ
from app.core.permissions import PRODUCTION_WORK_ORDER_CREATE
from app.core.permissions import PRODUCTION_WORK_ORDER_WORKER
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.schemas.production import ApiResponse
from app.schemas.production import ProductionCreateWorkOrderData
from app.schemas.production import ProductionCreateWorkOrderRequest
from app.schemas.production import ProductionMaterialCheckData
from app.schemas.production import ProductionMaterialCheckRequest
from app.schemas.production import ProductionPlanCreateData
from app.schemas.production import ProductionPlanCreateRequest
from app.schemas.production import ProductionPlanDetailData
from app.schemas.production import ProductionPlanListData
from app.schemas.production import ProductionPlanQuery
from app.schemas.production import ProductionSyncJobCardsData
from app.schemas.production import ProductionWorkerRunOnceData
from app.schemas.production import ProductionWorkerRunOnceRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.permission_service import PermissionService
from app.services.production_service import ProductionService
from app.services.production_work_order_worker import ProductionWorkOrderWorker

router = APIRouter(prefix="/api/production", tags=["production"])
logger = logging.getLogger(__name__)


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


def _http_exc_err(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or "请求失败")
        return _err(code, message, status_code=exc.status_code)
    if isinstance(detail, str):
        return _err("HTTP_ERROR", detail, status_code=exc.status_code)
    return _err("HTTP_ERROR", "请求失败", status_code=exc.status_code)


def _unknown_to_internal_error(request: Request, action: str, exc: Exception) -> ProductionInternalError:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "production_internal_error",
        exc,
        request_id=request_id,
        extra={
            "error_code": PRODUCTION_INTERNAL_ERROR,
            "module": "production",
            "action": action,
        },
    )
    return ProductionInternalError()


def _rollback_safely(session: Session, request: Request, action: str, origin: BaseException) -> None:
    try:
        session.rollback()
    except Exception as rollback_exc:  # pragma: no cover - rare branch
        request_id = get_request_id_from_request(request)
        error_code = origin.code if isinstance(origin, AppException) else ""
        log_safe_error(
            logger,
            "production_rollback_failed",
            rollback_exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "production",
                "action": action,
            },
        )


def _map_write_db_exception(request: Request, action: str, exc: BaseException) -> AppException:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "production_database_write_failed",
        exc,
        request_id=request_id,
        extra={
            "error_code": DATABASE_WRITE_FAILED,
            "module": "production",
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
            module="production",
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
            "production_operation_audit_write_failed",
            exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "production",
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id if resource_id is not None else "",
                "resource_no": resource_no or "",
                "user_id": current_user.username,
            },
        )
        raise AuditWriteFailed() from exc


def _service(session: Session, request: Request, *, use_service_account: bool = False) -> ProductionService:
    return ProductionService(
        session=session,
        erp_adapter=ERPNextProductionAdapter(request_obj=request, use_service_account=use_service_account),
    )


def _worker(session: Session, request: Request) -> ProductionWorkOrderWorker:
    return ProductionWorkOrderWorker(
        session=session,
        adapter=ERPNextProductionAdapter(request_obj=request, use_service_account=True),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)


def _deny_frozen_write(
    *,
    session: Session,
    permission_service: PermissionService,
    audit: AuditService,
    context: AuditContext,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    before_data: dict[str, Any] | None,
    deny_reason: str,
    response_message: str,
) -> JSONResponse:
    permission_service.record_security_denial(
        request_obj=request,
        current_user=current_user,
        action=action,
        module="production",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        deny_reason=deny_reason,
    )
    _record_failure_safely(
        session=session,
        audit=audit,
        context=context,
        request=request,
        action=action,
        current_user=current_user,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=before_data,
        after_data=None,
        error_code=AUTH_FORBIDDEN,
    )
    return _err(AUTH_FORBIDDEN, response_message)


def _resolve_read_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
) -> tuple[set[str] | None, set[str] | None]:
    if get_permission_source() != "erpnext":
        return None, None

    user_permissions = permission_service.get_production_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=action,
        resource_type="production_plan",
        resource_id=None,
        resource_no=None,
    )
    if user_permissions is None or user_permissions.unrestricted:
        return None, None

    companies = {item.strip() for item in user_permissions.allowed_companies if item and item.strip()}
    items = {item.strip() for item in user_permissions.allowed_items if item and item.strip()}
    return companies, items


@router.post("/plans", response_model=ApiResponse[ProductionPlanCreateData])
def create_production_plan(
    payload: ProductionPlanCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_PLAN_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_plan",
            resource_id=None,
        )
        service = _service(session=session, request=request)
        scope_company, scope_item_code = service.resolve_create_scope(payload=payload)
        permission_service.ensure_production_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=scope_item_code,
            company=scope_company,
            resource_type="production_plan",
            resource_id=None,
            resource_no=payload.sales_order,
            enforce_action=False,
        )

        data = service.create_plan(payload=payload, operator=current_user.username)
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_plan",
            resource_id=int(data.plan_id),
            resource_no=str(data.plan_no),
            before_data=None,
            after_data=_as_dict(data),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=None,
            resource_no=payload.sales_order,
            before_data=None,
            after_data={"item_code": payload.item_code},
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        app_exc = _unknown_to_internal_error(request=request, action=action, exc=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=None,
            resource_no=payload.sales_order,
            before_data=None,
            after_data={"item_code": payload.item_code},
            error_code=app_exc.code,
        )
        return _app_err(app_exc)


@router.get("/plans", response_model=ApiResponse[ProductionPlanListData])
def list_production_plans(
    request: Request,
    sales_order: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    company: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_READ
    permission_service = PermissionService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_plan",
            resource_id=None,
        )

        readable_companies, readable_items = _resolve_read_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
        )
        query = ProductionPlanQuery(
            sales_order=sales_order,
            item_code=item_code,
            company=company,
            status=status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_plans(
            query=query,
            readable_companies=readable_companies,
            readable_item_codes=readable_items,
        )
        return _ok(data)
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request=request, action=action, exc=exc))


@router.get("/plans/{plan_id}", response_model=ApiResponse[ProductionPlanDetailData])
def get_production_plan_detail(
    plan_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_READ
    permission_service = PermissionService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_plan",
            resource_id=plan_id,
        )
        service = _service(session=session, request=request)
        company, item = service.get_plan_resource(plan_id=plan_id)
        permission_service.ensure_production_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=item,
            company=company,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            enforce_action=False,
        )
        data = service.get_plan_detail(plan_id=plan_id)
        return _ok(data)
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request=request, action=action, exc=exc))


@router.post("/plans/{plan_id}/material-check", response_model=ApiResponse[ProductionMaterialCheckData])
def material_check_plan(
    plan_id: int,
    request: Request,
    payload: ProductionMaterialCheckRequest = Body(default=ProductionMaterialCheckRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_MATERIAL_CHECK
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    before_data: dict[str, Any] | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_plan",
            resource_id=plan_id,
        )
        service = _service(session=session, request=request)
        company, item = service.get_plan_resource(plan_id=plan_id)
        permission_service.ensure_production_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=item,
            company=company,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            enforce_action=False,
        )
        status = service.ensure_material_check_status_allowed(plan_id=plan_id)
        before_data = {"plan_id": plan_id, "warehouse": payload.warehouse, "status": status}
        data = service.material_check(plan_id=plan_id, operator=current_user.username, payload=payload)
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=_as_dict(data),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        app_exc = _unknown_to_internal_error(request=request, action=action, exc=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=None,
            error_code=app_exc.code,
        )
        return _app_err(app_exc)


@router.post("/plans/{plan_id}/create-work-order", response_model=ApiResponse[ProductionCreateWorkOrderData])
def create_work_order_outbox(
    plan_id: int,
    request: Request,
    payload: ProductionCreateWorkOrderRequest = Body(default=ProductionCreateWorkOrderRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_WORK_ORDER_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    request_id = get_request_id_from_request(request)

    before_data: dict[str, Any] | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_plan",
            resource_id=plan_id,
        )
        service = _service(session=session, request=request)
        company, item = service.get_plan_resource(plan_id=plan_id)
        before_data = {
            "plan_id": plan_id,
            "fg_warehouse": payload.fg_warehouse,
            "wip_warehouse": payload.wip_warehouse,
            "start_date": payload.start_date.isoformat() if payload.start_date else None,
            "idempotency_key": payload.idempotency_key,
        }
        permission_service.ensure_production_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=item,
            company=company,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            enforce_action=False,
        )
        data = service.create_work_order_outbox(
            plan_id=plan_id,
            payload=payload,
            operator=current_user.username,
            request_id=request_id,
        )
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=_as_dict(data),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        app_exc = _unknown_to_internal_error(request=request, action=action, exc=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_plan",
            resource_id=plan_id,
            resource_no=str(plan_id),
            before_data=before_data,
            after_data=None,
            error_code=app_exc.code,
        )
        return _app_err(app_exc)


@router.post("/work-orders/{work_order}/sync-job-cards", response_model=ApiResponse[ProductionSyncJobCardsData])
def sync_job_cards(
    work_order: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_JOB_CARD_SYNC
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    request_id = get_request_id_from_request(request)

    before_data: dict[str, Any] | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_work_order",
            resource_id=None,
        )
        service = _service(session=session, request=request)
        plan_id, company, item = service.get_work_order_resource(work_order=work_order)
        before_data = {"plan_id": plan_id, "work_order": work_order}
        permission_service.ensure_production_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=item,
            company=company,
            resource_type="production_work_order",
            resource_id=plan_id,
            resource_no=work_order,
            enforce_action=False,
        )
        data = service.sync_job_cards(
            work_order=work_order,
            operator=current_user.username,
            request_id=request_id,
        )
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_work_order",
            resource_id=plan_id,
            resource_no=work_order,
            before_data=before_data,
            after_data=_as_dict(data),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_work_order",
            resource_id=None,
            resource_no=work_order,
            before_data=before_data,
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        app_exc = _unknown_to_internal_error(request=request, action=action, exc=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_work_order",
            resource_id=None,
            resource_no=work_order,
            before_data=before_data,
            after_data=None,
            error_code=app_exc.code,
        )
        return _app_err(app_exc)


@router.post("/internal/work-order-sync/run-once", response_model=ApiResponse[ProductionWorkerRunOnceData])
def run_work_order_sync_once(
    request: Request,
    payload: ProductionWorkerRunOnceRequest = Body(default=ProductionWorkerRunOnceRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_WORK_ORDER_WORKER
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_work_order_worker",
            resource_id=None,
        )
        if not is_internal_worker_principal(current_user):
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                module="production",
                resource_type="production_work_order_worker",
                resource_no=current_user.username,
                deny_reason="调用主体不是服务账号或系统级主体",
            )
            return _err(AUTH_FORBIDDEN, "无权限访问该资源")

        allowed_companies: set[str] | None = None
        allowed_items: set[str] | None = None
        if get_permission_source() == "erpnext":
            user_permissions = permission_service.get_production_user_permissions(
                current_user=current_user,
                request_obj=request,
                action=action,
                resource_type="production_work_order_worker",
                resource_id=None,
                resource_no=current_user.username,
            )
            if user_permissions is not None and not user_permissions.unrestricted:
                allowed_companies = {value.strip() for value in user_permissions.allowed_companies if value and value.strip()}
                allowed_items = {value.strip() for value in user_permissions.allowed_items if value and value.strip()}

        result = _worker(session=session, request=request).run_once(
            batch_size=payload.batch_size,
            worker_id=f"production-worker:{current_user.username}",
            dry_run=payload.dry_run,
            allowed_companies=allowed_companies,
            allowed_items=allowed_items,
        )
        data = ProductionWorkerRunOnceData(
            dry_run=result.dry_run,
            processed_count=result.processed_count,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            dead_count=result.dead_count,
        )
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_work_order_worker",
            resource_id=None,
            resource_no=current_user.username,
            before_data={"dry_run": payload.dry_run, "batch_size": payload.batch_size},
            after_data=_as_dict(data),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_work_order_worker",
            resource_id=None,
            resource_no=current_user.username,
            before_data={"dry_run": payload.dry_run, "batch_size": payload.batch_size},
            after_data=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        app_exc = _unknown_to_internal_error(request=request, action=action, exc=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_type="production_work_order_worker",
            resource_id=None,
            resource_no=current_user.username,
            before_data={"dry_run": payload.dry_run, "batch_size": payload.batch_size},
            after_data=None,
            error_code=app_exc.code,
        )
        return _app_err(app_exc)
