"""FastAPI router for production planning module (TASK-004A)."""

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
from app.core.auth import is_internal_worker_api_enabled
from app.core.auth import is_internal_worker_principal
from app.core.config import production_enable_work_order_worker_sync
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_CONFLICT
from app.core.error_codes import PRODUCTION_INTERNAL_ERROR
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ProductionInternalError
from app.core.logging import log_safe_error
from app.core.permissions import PRODUCTION_JOB_CARD_SYNC
from app.core.permissions import PRODUCTION_MATERIAL_CHECK
from app.core.permissions import PRODUCTION_MATERIAL_ISSUE
from app.core.permissions import PRODUCTION_PLAN_CREATE
from app.core.permissions import PRODUCTION_READ
from app.core.permissions import PRODUCTION_TRACKING_EXCEPTION
from app.core.permissions import PRODUCTION_WORK_ORDER_CREATE
from app.core.permissions import PRODUCTION_WORK_ORDER_WORKER
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.schemas.production import ApiResponse
from app.schemas.production import ProductionCreateWorkOrderData
from app.schemas.production import ProductionCreateWorkOrderRequest
from app.schemas.production import ProductionFollowupTemplateListData
from app.schemas.production import ProductionFollowupTemplateQuery
from app.schemas.production import ProductionMaterialCheckData
from app.schemas.production import ProductionMaterialCheckRequest
from app.schemas.production import ProductionMaterialIssueData
from app.schemas.production import ProductionMaterialIssueListData
from app.schemas.production import ProductionMaterialIssueQuery
from app.schemas.production import ProductionMaterialIssueRequest
from app.schemas.production import ProductionMaterialCostListData
from app.schemas.production import ProductionMaterialCostQuery
from app.schemas.production import ProductionOrderIOQuantityListData
from app.schemas.production import ProductionOrderIOQuantityQuery
from app.schemas.production import ProductionPlanCreateData
from app.schemas.production import ProductionPlanCreateRequest
from app.schemas.production import ProductionPlanDetailData
from app.schemas.production import ProductionPlanListData
from app.schemas.production import ProductionPlanQuery
from app.schemas.production import ProductionQuoteListData
from app.schemas.production import ProductionQuoteQuery
from app.schemas.production import ProductionReportSuiteData
from app.schemas.production import ProductionReportSuiteQuery
from app.schemas.production import ProductionSalesForecastListData
from app.schemas.production import ProductionSalesForecastQuery
from app.schemas.production import ProductionSalespersonPerformanceListData
from app.schemas.production import ProductionSalespersonPerformanceQuery
from app.schemas.production import ProductionSyncJobCardsData
from app.schemas.production import ProductionSyncJobCardsRequest
from app.schemas.production import ProductionTrackingReconcileGenerateData
from app.schemas.production import ProductionTrackingReconcileGenerateRequest
from app.schemas.production import ProductionTrackingReconcileListData
from app.schemas.production import ProductionTrackingReconcileQuery
from app.schemas.production import ProductionTrackingExceptionCreateRequest
from app.schemas.production import ProductionTrackingExceptionItem
from app.schemas.production import ProductionWorkOrderListData
from app.schemas.production import ProductionWorkOrderQuery
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
REPORT_SUITE_KEYS = {
    "orderQuantityReport",
    "productOrderSampleCompare",
    "orderTrackingReport",
    "productOrderProfitReport",
    "productionCostMaterialDetailReport",
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


def _http_exc_err(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or "请求失败")
        return _err(code, message, status_code=exc.status_code)
    if isinstance(detail, str):
        return _err("HTTP_ERROR", detail, status_code=exc.status_code)
    return _err("HTTP_ERROR", "请求失败", status_code=exc.status_code)


def _is_local_gate_failure(exc: AppException) -> bool:
    return exc.code == PRODUCTION_IDEMPOTENCY_CONFLICT and str(exc.message).startswith("LOCAL_GATE_FAIL_CLOSED:")


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
    raw_request_id = request.headers.get("X-Request-ID")
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
        scope_company, scope_item_code = service.resolve_create_scope(payload=payload, request_id=raw_request_id)
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

        data = service.create_plan(payload=payload, operator=current_user.username, request_id=raw_request_id)
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
        if _is_local_gate_failure(exc):
            return _app_err(exc)
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
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    company: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            keyword=keyword,
            turnover_no=turnover_no,
            item_code=item_code,
            company=company,
            from_date=from_date,
            to_date=to_date,
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


@router.get("/tracking-reconciliations", response_model=ApiResponse[ProductionTrackingReconcileListData])
def list_tracking_reconciliations(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    diff_status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            resource_type="production_tracking_reconcile",
            resource_id=None,
        )
        readable_companies, _readable_items = _resolve_read_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
        )
        query = ProductionTrackingReconcileQuery(
            company=company,
            keyword=keyword,
            customer=customer,
            diff_status=diff_status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_tracking_reconciliations(
            query=query,
            readable_companies=readable_companies,
        )
        return _ok(data)
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request=request, action=action, exc=exc))


@router.post("/tracking-reconciliations/generate", response_model=ApiResponse[ProductionTrackingReconcileGenerateData])
def generate_tracking_reconciliations(
    payload: ProductionTrackingReconcileGenerateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_PLAN_CREATE
    resource_type = "production_tracking_reconcile"
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type=resource_type,
            resource_id=None,
        )
        data = _service(session=session, request=request).generate_tracking_reconciliations(
            payload=payload,
            operator=current_user.username,
        )
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type=resource_type,
            resource_id=None,
            resource_no=data.batch_no,
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
            resource_type=resource_type,
            resource_id=None,
            resource_no=payload.idempotency_key,
            before_data=None,
            after_data={"company": payload.company, "keyword": payload.keyword},
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
            resource_type=resource_type,
            resource_id=None,
            resource_no=payload.idempotency_key,
            before_data=None,
            after_data={"company": payload.company, "keyword": payload.keyword},
            error_code=app_exc.code,
        )
        return _app_err(app_exc)


@router.get("/work-orders", response_model=ApiResponse[ProductionWorkOrderListData])
def list_production_work_orders(
    request: Request,
    sales_order: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    company: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sync_status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            resource_type="production_work_order",
            resource_id=None,
        )

        readable_companies, readable_items = _resolve_read_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
        )
        query = ProductionWorkOrderQuery(
            sales_order=sales_order,
            keyword=keyword,
            turnover_no=turnover_no,
            item_code=item_code,
            company=company,
            status=status,
            sync_status=sync_status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_work_orders(
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


@router.get("/material-cost-details", response_model=ApiResponse[ProductionMaterialCostListData])
def list_production_material_cost_details(
    request: Request,
    sales_order: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    material_item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
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
        query = ProductionMaterialCostQuery(
            sales_order=sales_order,
            keyword=keyword,
            turnover_no=turnover_no,
            material_item_code=material_item_code,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
            status=status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_material_cost_details(
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


@router.get("/sales-forecast-details", response_model=ApiResponse[ProductionSalesForecastListData])
def list_production_sales_forecast_details(
    request: Request,
    sales_order: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
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
        query = ProductionSalesForecastQuery(
            sales_order=sales_order,
            keyword=keyword,
            turnover_no=turnover_no,
            item_code=item_code,
            customer=customer,
            from_date=from_date,
            to_date=to_date,
            status=status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_sales_forecast_details(
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


@router.get("/quotes", response_model=ApiResponse[ProductionQuoteListData])
def list_production_quotes(
    request: Request,
    quote_no: str | None = Query(default=None),
    sales_order: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
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
        query = ProductionQuoteQuery(
            quote_no=quote_no,
            sales_order=sales_order,
            keyword=keyword,
            turnover_no=turnover_no,
            item_code=item_code,
            customer=customer,
            from_date=from_date,
            to_date=to_date,
            status=status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_quotes(
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


@router.get("/followup-templates", response_model=ApiResponse[ProductionFollowupTemplateListData])
def list_production_followup_templates(
    request: Request,
    template_no: str | None = Query(default=None),
    template_name: str | None = Query(default=None),
    template_type: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
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
        query = ProductionFollowupTemplateQuery(
            template_no=template_no,
            template_name=template_name,
            template_type=template_type,
            item_code=item_code,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            status=status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_followup_templates(
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


@router.get("/order-io-quantities", response_model=ApiResponse[ProductionOrderIOQuantityListData])
def list_production_order_io_quantities(
    request: Request,
    sales_order: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    turnover_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    io_status: str | None = Query(default=None),
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
        query = ProductionOrderIOQuantityQuery(
            sales_order=sales_order,
            keyword=keyword,
            turnover_no=turnover_no,
            item_code=item_code,
            customer=customer,
            from_date=from_date,
            to_date=to_date,
            status=status,
            io_status=io_status,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_order_io_quantities(
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


@router.get("/salesperson-performance", response_model=ApiResponse[ProductionSalespersonPerformanceListData])
def list_production_salesperson_performance(
    request: Request,
    salesperson: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    status: str | None = Query(default=None),
    performance_status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
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
        query = ProductionSalespersonPerformanceQuery(
            salesperson=salesperson,
            keyword=keyword,
            item_code=item_code,
            customer=customer,
            status=status,
            performance_status=performance_status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_salesperson_performance(
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


@router.get("/report-suite", response_model=ApiResponse[ProductionReportSuiteData])
def get_production_report_suite(
    request: Request,
    report_key: str = Query(..., min_length=1, max_length=80),
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_READ
    permission_service = PermissionService(session=session)

    if report_key not in REPORT_SUITE_KEYS:
        return _err("INVALID_QUERY_PARAMETER", "report_key 不合法", 400)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="production",
            resource_type="production_report_suite",
            resource_id=None,
        )

        readable_companies, readable_items = _resolve_read_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
        )
        query = ProductionReportSuiteQuery(
            report_key=report_key,
            company=company,
            keyword=keyword,
            customer=customer,
            owner=owner,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).get_report_suite(
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


@router.get("/material-issues", response_model=ApiResponse[ProductionMaterialIssueListData])
def list_production_material_issues(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    sales_order: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    material_item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            resource_type="production_material_issue",
            resource_id=None,
        )
        readable_companies, readable_items = _resolve_read_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
        )
        query = ProductionMaterialIssueQuery(
            company=company,
            keyword=keyword,
            sales_order=sales_order,
            item_code=item_code,
            material_item_code=material_item_code,
            warehouse=warehouse,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        data = _service(session=session, request=request).list_material_issues(
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


@router.post("/plans/{plan_id}/tracking-exceptions", response_model=ApiResponse[ProductionTrackingExceptionItem])
def register_production_tracking_exception(
    plan_id: int,
    payload: ProductionTrackingExceptionCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_TRACKING_EXCEPTION
    raw_request_id = request.headers.get("X-Request-ID")
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
        before_data = {
            "plan_id": plan_id,
            "company": company,
            "item_code": item,
            "description": payload.description,
        }
        data = service.register_tracking_exception(
            plan_id=plan_id,
            payload=payload,
            operator=current_user.username,
            request_id=raw_request_id,
        )
        audit.record_success(
            module="production",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="production_tracking_exception",
            resource_id=int(data.id),
            resource_no=str(data.exception_no),
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


@router.post("/plans/{plan_id}/material-check", response_model=ApiResponse[ProductionMaterialCheckData])
def material_check_plan(
    plan_id: int,
    request: Request,
    payload: ProductionMaterialCheckRequest = Body(default=ProductionMaterialCheckRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_MATERIAL_CHECK
    raw_request_id = request.headers.get("X-Request-ID")
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
        before_data = {"plan_id": plan_id, "warehouse": payload.warehouse}
        data = service.material_check(plan_id=plan_id, operator=current_user.username, payload=payload, request_id=raw_request_id)
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
        if _is_local_gate_failure(exc):
            return _app_err(exc)
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


@router.post("/plans/{plan_id}/material-issue", response_model=ApiResponse[ProductionMaterialIssueData])
def create_material_issue_draft(
    plan_id: int,
    request: Request,
    payload: ProductionMaterialIssueRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_MATERIAL_ISSUE
    raw_request_id = request.headers.get("X-Request-ID")
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
        for scope in service.get_material_issue_resource_scopes(plan_id=plan_id, warehouse=payload.warehouse):
            permission_service.ensure_resource_scope_permission(
                current_user=current_user,
                request_obj=request,
                module="production",
                action=action,
                resource_scope=scope,
                required_fields=("company", "warehouse", "item_code"),
                resource_type="production_material_issue",
                resource_id=plan_id,
                resource_no=str(plan_id),
                enforce_action=False,
            )
        before_data = {
            "plan_id": plan_id,
            "warehouse": payload.warehouse,
            "business_date": payload.business_date.isoformat(),
        }
        data = service.create_material_issue_draft(
            plan_id=plan_id,
            operator=current_user.username,
            payload=payload,
            request_id=raw_request_id,
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
    raw_request_id = request.headers.get("X-Request-ID")

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
            request_id=raw_request_id,
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
        if _is_local_gate_failure(exc):
            return _app_err(exc)
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
    payload: ProductionSyncJobCardsRequest = Body(default=ProductionSyncJobCardsRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = PRODUCTION_JOB_CARD_SYNC
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    raw_request_id = request.headers.get("X-Request-ID")

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
        before_data = {
            "plan_id": plan_id,
            "work_order": work_order,
            "scenario_tag": payload.scenario_tag,
            "idempotency_key": payload.idempotency_key,
            "operation": payload.operation,
            "source_ref": payload.source_ref,
        }
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
            payload=payload,
            request_id=raw_request_id,
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
        if _is_local_gate_failure(exc):
            return _app_err(exc)
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
        if not is_internal_worker_api_enabled():
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                module="production",
                resource_type="production_work_order_worker",
                resource_no=current_user.username,
                deny_reason="生产工单同步内部接口未启用",
                event_type=INTERNAL_API_DISABLED,
            )
            return _err(INTERNAL_API_DISABLED, "内部接口未启用", status_code=status_of(INTERNAL_API_DISABLED))
        if not payload.dry_run and not production_enable_work_order_worker_sync():
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                module="production",
                resource_type="production_work_order_worker",
                resource_no=current_user.username,
                deny_reason="生产工单 ERP 同步未启用",
                event_type=INTERNAL_API_DISABLED,
            )
            return _err(INTERNAL_API_DISABLED, "生产工单 ERP 同步未启用", status_code=status_of(INTERNAL_API_DISABLED))
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
