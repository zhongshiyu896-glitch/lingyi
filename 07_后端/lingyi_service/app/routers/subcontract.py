"""FastAPI router for subcontract module (TASK-002B baseline)."""

from __future__ import annotations

from collections.abc import Generator
import logging
from typing import Any

from fastapi import APIRouter
from fastapi import Body
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
from app.core.config import subcontract_enable_internal_stock_worker_api
from app.core.config import subcontract_enable_stock_worker_dry_run
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import SUBCONTRACT_COMPANY_AMBIGUOUS
from app.core.error_codes import SUBCONTRACT_COMPANY_REQUIRED
from app.core.error_codes import SUBCONTRACT_COMPANY_UNRESOLVED
from app.core.error_codes import SUBCONTRACT_DRY_RUN_DISABLED
from app.core.error_codes import SUBCONTRACT_RECEIPT_BATCH_REQUIRED
from app.core.error_codes import SUBCONTRACT_INTERNAL_ERROR
from app.core.error_codes import SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED
from app.core.error_codes import SUBCONTRACT_SCOPE_BLOCKED
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_CONFLICT
from app.core.error_codes import SUBCONTRACT_WORKER_DISABLED
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.exceptions import PermissionSourceUnavailable
from app.core.exceptions import ServiceAccountResourceForbiddenError
from app.core.exceptions import SubcontractInternalError
from app.core.logging import log_safe_error
from app.core.permissions import SUBCONTRACT_CREATE
from app.core.permissions import SUBCONTRACT_INSPECT
from app.core.permissions import SUBCONTRACT_ISSUE_MATERIAL
from app.core.permissions import SUBCONTRACT_READ
from app.core.permissions import SUBCONTRACT_RECEIVE
from app.core.permissions import SUBCONTRACT_SETTLEMENT_LOCK
from app.core.permissions import SUBCONTRACT_SETTLEMENT_READ
from app.core.permissions import SUBCONTRACT_SETTLEMENT_RELEASE
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_RETRY
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_WORKER
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.schemas.subcontract import IssueMaterialRequest
from app.schemas.subcontract import InspectRequest
from app.schemas.subcontract import ReceiveRequest
from app.schemas.subcontract import SubcontractCreateRequest
from app.schemas.subcontract import SubcontractDetailData
from app.schemas.subcontract import SubcontractListQuery
from app.schemas.subcontract import SubcontractSettlementLockRequest
from app.schemas.subcontract import SubcontractSettlementPreviewRequest
from app.schemas.subcontract import SubcontractSettlementReleaseRequest
from app.schemas.subcontract import SubcontractStockSyncRunOnceData
from app.schemas.subcontract import SubcontractStockSyncRetryRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService
from app.services.permission_service import PermissionService
from app.services.subcontract_service import SubcontractService
from app.services.subcontract_settlement_service import SubcontractSettlementService
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService
from app.services.subcontract_stock_outbox_service import SubcontractWorkerScope
from app.services.subcontract_stock_worker_service import SubcontractStockWorkerService

router = APIRouter(prefix="/api/subcontract", tags=["subcontract"])
logger = logging.getLogger(__name__)


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session.

    Note:
        Should be overridden by app main dependency wiring.
    """
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


def _unknown_to_internal_error(request: Request, action: str, exc: Exception) -> SubcontractInternalError:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "subcontract_internal_error",
        exc,
        request_id=request_id,
        extra={
            "error_code": SUBCONTRACT_INTERNAL_ERROR,
            "module": "subcontract",
            "action": action,
        },
    )
    return SubcontractInternalError()


def _rollback_safely(session: Session, request: Request, action: str, origin: BaseException) -> None:
    try:
        session.rollback()
    except Exception as rollback_exc:  # pragma: no cover
        request_id = get_request_id_from_request(request)
        error_code = origin.code if isinstance(origin, AppException) else ""
        log_safe_error(
            logger,
            "subcontract_rollback_failed",
            rollback_exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "subcontract",
                "action": action,
            },
        )


def _map_write_db_exception(request: Request, action: str, exc: BaseException) -> AppException:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "subcontract_database_write_failed",
        exc,
        request_id=request_id,
        extra={
            "error_code": DATABASE_WRITE_FAILED,
            "module": "subcontract",
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


def _resource_no(snapshot: dict[str, Any] | None) -> str | None:
    if not snapshot:
        return None
    value = snapshot.get("subcontract_no")
    return str(value) if value else None


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    request: Request,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
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
                "module": "subcontract",
                "action": action,
                "resource_type": "subcontract_order",
                "resource_id": resource_id if resource_id is not None else "",
                "resource_no": resource_no or "",
                "user_id": current_user.username,
            },
        )
        raise AuditWriteFailed() from exc


def _normalize_company(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _resolve_create_company(*, request: Request, payload: SubcontractCreateRequest) -> str:
    explicit = _normalize_company(payload.company)
    if explicit:
        return explicit

    if get_permission_source() != "erpnext":
        raise BusinessException(code=SUBCONTRACT_COMPANY_REQUIRED, message="外发单 company 不能为空")

    try:
        item_info = ERPNextJobCardAdapter(request_obj=request).get_item(item_code=payload.item_code.strip())
    except ERPNextServiceUnavailableError as exc:
        raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc

    if not item_info or not item_info.is_active:
        raise BusinessException(code=SUBCONTRACT_COMPANY_UNRESOLVED, message="无法解析外发单 company")

    companies = sorted({company.strip() for company in item_info.companies if company and company.strip()})
    if len(companies) == 1:
        return companies[0]
    if len(companies) > 1:
        raise BusinessException(code=SUBCONTRACT_COMPANY_AMBIGUOUS, message="外发单 company 存在多个候选，无法唯一确定")
    raise BusinessException(code=SUBCONTRACT_COMPANY_UNRESOLVED, message="无法解析外发单 company")


def _company_for_permission_check(company: str | None) -> str:
    normalized = _normalize_company(company)
    if normalized:
        return normalized
    raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单缺少 company 资源范围")


def _extract_required_warehouse(payload: dict[str, Any] | None) -> str:
    if isinstance(payload, dict):
        value = payload.get("receipt_warehouse")
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise BusinessException(code=SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED, message="回料仓不能为空")


def _parse_receive_payload(payload: dict[str, Any] | None) -> ReceiveRequest:
    if payload is None:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="回料请求不能为空")
    if not isinstance(payload, dict):
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="回料请求格式非法")
    try:
        return ReceiveRequest.model_validate(payload)
    except Exception:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="回料请求参数非法")


def _parse_stock_sync_retry_payload(payload: dict[str, Any] | None) -> SubcontractStockSyncRetryRequest:
    if payload is None:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="重试请求不能为空")
    if not isinstance(payload, dict):
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="重试请求格式非法")
    try:
        model = SubcontractStockSyncRetryRequest.model_validate(payload)
    except Exception:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="重试请求参数非法")
    normalized_action = model.stock_action.strip().lower()
    if normalized_action not in {
        SubcontractStockOutboxService.STOCK_ACTION_ISSUE,
        SubcontractStockOutboxService.STOCK_ACTION_RECEIPT,
    }:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="不支持的库存同步动作")
    model.stock_action = normalized_action
    model.idempotency_key = model.idempotency_key.strip()
    if not model.idempotency_key:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="重试请求参数非法")
    if model.reason is not None:
        model.reason = model.reason.strip()[:200] or None
    return model


def _parse_inspect_payload(payload: dict[str, Any] | None) -> InspectRequest:
    if payload is None:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="验货请求不能为空")
    if not isinstance(payload, dict):
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="验货请求格式非法")
    receipt_batch_no = str(payload.get("receipt_batch_no") or "").strip()
    if not receipt_batch_no:
        raise BusinessException(code=SUBCONTRACT_RECEIPT_BATCH_REQUIRED, message="验货必须指定回料批次")
    try:
        model = InspectRequest.model_validate(payload)
    except Exception:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="验货请求参数非法")
    model.receipt_batch_no = receipt_batch_no
    model.idempotency_key = model.idempotency_key.strip()
    if not model.idempotency_key:
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="验货幂等键不能为空")
    if model.remark is not None:
        model.remark = model.remark.strip()[:200] or None
    return model


def _bounded_batch_size(raw: int) -> int:
    return max(1, min(int(raw), 200))


def _resolve_subcontract_read_scope_sets(
    *,
    user_permissions,
) -> tuple[set[str] | None, set[str] | None, set[str] | None]:
    """Resolve query-level resource filters from ERPNext user permissions."""
    if user_permissions is None or user_permissions.unrestricted:
        return None, None, None

    readable_items = set(user_permissions.allowed_items) if user_permissions.allowed_items else set()
    readable_companies = set(user_permissions.allowed_companies) if user_permissions.allowed_companies else None
    readable_suppliers = set(user_permissions.allowed_suppliers) if user_permissions.allowed_suppliers else None
    return readable_items, readable_companies, readable_suppliers


def _resolve_subcontract_worker_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
) -> SubcontractWorkerScope:
    if get_permission_source() != "erpnext":
        raise ServiceAccountResourceForbiddenError("服务账号资源权限必须由 ERPNext User Permission 提供")

    user_permissions = permission_service.get_subcontract_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=action,
        resource_type="subcontract_stock_sync_worker",
        resource_id=None,
        resource_no=None,
    )
    if user_permissions is None or user_permissions.unrestricted:
        raise ServiceAccountResourceForbiddenError("服务账号必须显式配置 Company/Item/Supplier/Warehouse 权限")

    companies = {value.strip() for value in user_permissions.allowed_companies if value and value.strip()}
    items = {value.strip() for value in user_permissions.allowed_items if value and value.strip()}
    suppliers = {value.strip() for value in user_permissions.allowed_suppliers if value and value.strip()}
    warehouses = {value.strip() for value in user_permissions.allowed_warehouses if value and value.strip()}
    if not companies or not items or not suppliers or not warehouses:
        raise ServiceAccountResourceForbiddenError("服务账号缺少 Company/Item/Supplier/Warehouse 权限范围")

    return SubcontractWorkerScope(
        companies=companies,
        items=items,
        suppliers=suppliers,
        warehouses=warehouses,
    )


@router.post("/")
def create_subcontract_order(
    payload: SubcontractCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """创建外发单。"""
    service = SubcontractService(session=session)
    audit = AuditService(session=session)
    permission_service = PermissionService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_CREATE
    after_data = None
    resolved_company: str | None = None

    try:
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=SUBCONTRACT_CREATE,
            resource_type="subcontract_order",
            resource_id=None,
            resource_no=None,
        )
        resolved_company = _resolve_create_company(request=request, payload=payload)
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=SUBCONTRACT_CREATE,
            item_code=payload.item_code.strip(),
            company=resolved_company,
            supplier=payload.supplier.strip(),
            resource_type="subcontract_order",
            resource_id=None,
            resource_no=None,
            user_permissions=user_permissions,
        )
        create_payload = payload.model_copy(update={"company": resolved_company})
        result = service.create_order(payload=create_payload, operator=current_user.username)
        created_order = service.get_order_by_no(subcontract_no=result.name)
        if created_order is None:
            raise BusinessException(code=SUBCONTRACT_INTERNAL_ERROR, message="创建外发单后无法读取外发单快照")
        resource_id = int(created_order.id)
        after_data = service.get_order_snapshot(order_id=resource_id)
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
            resource_id=resource_id,
            resource_no=result.name,
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=f"{payload.supplier}:{payload.item_code}:{resolved_company or ''}".rstrip(":"),
                before_data=None,
                after_data=after_data,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=f"{payload.supplier}:{payload.item_code}:{resolved_company or ''}".rstrip(":"),
                before_data=None,
                after_data=after_data,
                error_code=SUBCONTRACT_INTERNAL_ERROR,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/")
def list_subcontract_order(
    request: Request,
    supplier: str | None = None,
    status: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询外发单。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SUBCONTRACT_READ,
        module="subcontract",
    )

    readable_item_codes: set[str] | None = None
    readable_companies: set[str] | None = None
    readable_suppliers: set[str] | None = None
    if get_permission_source() == "erpnext":
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=SUBCONTRACT_READ,
            resource_type="subcontract_order",
        )
        if user_permissions is not None and not user_permissions.unrestricted:
            readable_item_codes = set(user_permissions.allowed_items) if user_permissions.allowed_items else set()
            readable_companies = set(user_permissions.allowed_companies) if user_permissions.allowed_companies else None

            if user_permissions.allowed_suppliers:
                readable_suppliers = set(user_permissions.allowed_suppliers)

    service = SubcontractService(session=session)
    query = SubcontractListQuery(
        supplier=supplier,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    try:
        result = service.list_orders(
            query=query,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )
        return _ok(result.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, SUBCONTRACT_READ, exc))


@router.get("/settlement-candidates")
def list_subcontract_settlement_candidates(
    request: Request,
    company: str | None = None,
    supplier: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    item_code: str | None = None,
    process_name: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询可结算验货明细候选（TASK-002H）。"""
    permission_service = PermissionService(session=session)
    settlement_service = SubcontractSettlementService(session=session)
    action = SUBCONTRACT_SETTLEMENT_READ
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="subcontract_settlement",
        )
        readable_item_codes: set[str] | None = None
        readable_companies: set[str] | None = None
        readable_suppliers: set[str] | None = None
        if get_permission_source() == "erpnext":
            user_permissions = permission_service.get_subcontract_user_permissions(
                current_user=current_user,
                request_obj=request,
                action=action,
                resource_type="subcontract_settlement",
            )
            readable_item_codes, readable_companies, readable_suppliers = _resolve_subcontract_read_scope_sets(
                user_permissions=user_permissions,
            )

        result = settlement_service.list_candidates(
            company=company,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
            item_code=item_code,
            process_name=process_name,
            page=max(1, int(page)),
            page_size=max(1, min(int(page_size), 200)),
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )
        return _ok(result.model_dump())
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/settlement-preview")
def preview_subcontract_settlement(
    payload: SubcontractSettlementPreviewRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """对账候选预览汇总（TASK-002H）。"""
    permission_service = PermissionService(session=session)
    settlement_service = SubcontractSettlementService(session=session)
    action = SUBCONTRACT_SETTLEMENT_READ
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="subcontract_settlement",
        )

        user_permissions = None
        readable_item_codes: set[str] | None = None
        readable_companies: set[str] | None = None
        readable_suppliers: set[str] | None = None
        if get_permission_source() == "erpnext":
            user_permissions = permission_service.get_subcontract_user_permissions(
                current_user=current_user,
                request_obj=request,
                action=action,
                resource_type="subcontract_settlement",
            )
            readable_item_codes, readable_companies, readable_suppliers = _resolve_subcontract_read_scope_sets(
                user_permissions=user_permissions,
            )

        if payload.inspection_ids:
            for scope_row in settlement_service.list_scope_rows(inspection_ids=payload.inspection_ids):
                permission_service.ensure_subcontract_resource_permission(
                    current_user=current_user,
                    request_obj=request,
                    action=action,
                    item_code=scope_row.item_code,
                    company=_company_for_permission_check(scope_row.company),
                    supplier=scope_row.supplier,
                    resource_type="subcontract_settlement_line",
                    resource_id=scope_row.inspection_id,
                    resource_no=scope_row.subcontract_no,
                    enforce_action=False,
                    user_permissions=user_permissions,
                )

        result = settlement_service.preview(
            inspection_ids=payload.inspection_ids,
            company=payload.company,
            supplier=payload.supplier,
            from_date=payload.from_date,
            to_date=payload.to_date,
            item_code=payload.item_code,
            process_name=payload.process_name,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )
        return _ok(result.model_dump())
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/settlement-locks")
def lock_subcontract_settlement(
    payload: SubcontractSettlementLockRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """锁定结算明细（TASK-002H）。"""
    permission_service = PermissionService(session=session)
    settlement_service = SubcontractSettlementService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_SETTLEMENT_LOCK
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="subcontract_settlement",
        )
        user_permissions = None
        if get_permission_source() == "erpnext":
            user_permissions = permission_service.get_subcontract_user_permissions(
                current_user=current_user,
                request_obj=request,
                action=action,
                resource_type="subcontract_settlement",
            )

        for scope_row in settlement_service.list_scope_rows(inspection_ids=payload.inspection_ids):
            permission_service.ensure_subcontract_resource_permission(
                current_user=current_user,
                request_obj=request,
                action=action,
                item_code=scope_row.item_code,
                company=_company_for_permission_check(scope_row.company),
                supplier=scope_row.supplier,
                resource_type="subcontract_settlement_line",
                resource_id=scope_row.inspection_id,
                resource_no=scope_row.subcontract_no,
                enforce_action=False,
                user_permissions=user_permissions,
            )

        result = settlement_service.lock_inspections(
            statement_id=payload.statement_id,
            statement_no=payload.statement_no,
            inspection_ids=payload.inspection_ids,
            idempotency_key=payload.idempotency_key,
            operator=current_user.username,
            request_id=context.request_id,
        )
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_settlement",
            resource_id=payload.statement_id,
            resource_no=(payload.statement_no or f"statement:{payload.statement_id or ''}").rstrip(":"),
            before_data={
                "inspection_ids": payload.inspection_ids,
                "idempotency_key": payload.idempotency_key,
                "remark": payload.remark,
            },
            after_data=result.model_dump(),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/settlement-locks/release")
def release_subcontract_settlement_locks(
    payload: SubcontractSettlementReleaseRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """释放结算锁定明细（TASK-002H）。"""
    permission_service = PermissionService(session=session)
    settlement_service = SubcontractSettlementService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_SETTLEMENT_RELEASE
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="subcontract_settlement",
        )
        user_permissions = None
        if get_permission_source() == "erpnext":
            user_permissions = permission_service.get_subcontract_user_permissions(
                current_user=current_user,
                request_obj=request,
                action=action,
                resource_type="subcontract_settlement",
            )

        for scope_row in settlement_service.list_scope_rows(inspection_ids=payload.inspection_ids):
            permission_service.ensure_subcontract_resource_permission(
                current_user=current_user,
                request_obj=request,
                action=action,
                item_code=scope_row.item_code,
                company=_company_for_permission_check(scope_row.company),
                supplier=scope_row.supplier,
                resource_type="subcontract_settlement_line",
                resource_id=scope_row.inspection_id,
                resource_no=scope_row.subcontract_no,
                enforce_action=False,
                user_permissions=user_permissions,
            )

        result = settlement_service.release_locks(
            statement_id=payload.statement_id,
            statement_no=payload.statement_no,
            inspection_ids=payload.inspection_ids,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason,
            operator=current_user.username,
            request_id=context.request_id,
        )
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_settlement",
            resource_id=payload.statement_id,
            resource_no=(payload.statement_no or f"statement:{payload.statement_id or ''}").rstrip(":"),
            before_data={
                "inspection_ids": payload.inspection_ids,
                "idempotency_key": payload.idempotency_key,
                "reason": payload.reason,
            },
            after_data=result.model_dump(),
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/{order_id}")
def get_subcontract_order_detail(
    order_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询单个外发单详情。"""
    service = SubcontractService(session=session)
    permission_service = PermissionService(session=session)
    try:
        order = service.get_order_or_raise(order_id)
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=SUBCONTRACT_READ,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
        )
        latest_issue_outbox = service.latest_issue_outbox(order_id=order_id)
        latest_receipt_outbox = service.latest_receipt_outbox(order_id=order_id)
        receipts = service.list_receipts(order_id=order_id)
        inspections = service.list_inspections(order_id=order_id)
        detail = SubcontractDetailData(
            id=int(order.id),
            subcontract_no=str(order.subcontract_no),
            supplier=str(order.supplier),
            item_code=str(order.item_code),
            company=_normalize_company(order.company),
            bom_id=int(order.bom_id),
            process_name=str(order.process_name),
            planned_qty=order.planned_qty,
            subcontract_rate=order.subcontract_rate,
            issued_qty=order.issued_qty,
            received_qty=order.received_qty,
            inspected_qty=order.inspected_qty,
            rejected_qty=order.rejected_qty,
            accepted_qty=order.accepted_qty,
            gross_amount=order.gross_amount,
            deduction_amount=order.deduction_amount,
            net_amount=order.net_amount,
            status=str(order.status),
            settlement_status=str(order.settlement_status or ""),
            resource_scope_status=str(order.resource_scope_status),
            scope_error_code=(str(order.scope_error_code) if order.scope_error_code else None),
            latest_issue_outbox_id=(int(latest_issue_outbox.id) if latest_issue_outbox else None),
            latest_issue_sync_status=(str(latest_issue_outbox.status) if latest_issue_outbox else None),
            latest_issue_stock_entry_name=(
                str(latest_issue_outbox.stock_entry_name)
                if latest_issue_outbox and latest_issue_outbox.stock_entry_name
                else None
            ),
            latest_issue_idempotency_key=(
                str(latest_issue_outbox.idempotency_key)
                if latest_issue_outbox and latest_issue_outbox.idempotency_key
                else None
            ),
            latest_receipt_outbox_id=(int(latest_receipt_outbox.id) if latest_receipt_outbox else None),
            latest_receipt_sync_status=(str(latest_receipt_outbox.status) if latest_receipt_outbox else None),
            latest_receipt_stock_entry_name=(
                str(latest_receipt_outbox.stock_entry_name)
                if latest_receipt_outbox and latest_receipt_outbox.stock_entry_name
                else None
            ),
            latest_receipt_idempotency_key=(
                str(latest_receipt_outbox.idempotency_key)
                if latest_receipt_outbox and latest_receipt_outbox.idempotency_key
                else None
            ),
            receipts=receipts,
            inspections=inspections,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        return _ok(detail.model_dump())
    except HTTPException as exc:
        return _http_exc_err(exc)
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, SUBCONTRACT_READ, exc))


@router.post("/{order_id}/issue-material")
def issue_material(
    order_id: int,
    payload: IssueMaterialRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """发料：写本地事实 + pending issue outbox，不在事务内调用 ERPNext。"""
    service = SubcontractService(session=session)
    audit = AuditService(session=session)
    permission_service = PermissionService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_ISSUE_MATERIAL
    before_data = None
    after_data = None

    try:
        order = service.get_order_or_raise(order_id)
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=action,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
        )
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            warehouse=payload.warehouse.strip(),
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            user_permissions=user_permissions,
        )
        result = service.issue_material(
            order_id=order_id,
            payload=payload,
            operator=current_user.username,
            request_id=context.request_id,
        )
        after_data = service.get_order_snapshot(order_id=order_id)
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=SUBCONTRACT_INTERNAL_ERROR,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{order_id}/stock-sync/retry")
def retry_subcontract_stock_sync(
    order_id: int,
    request: Request,
    payload: dict[str, Any] | None = Body(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """手动精确重试外发库存同步（issue/receipt）。"""
    service = SubcontractService(session=session)
    audit = AuditService(session=session)
    permission_service = PermissionService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_STOCK_SYNC_RETRY
    before_data = None
    after_data = None

    try:
        order = service.get_order_or_raise(order_id)
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=action,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
        )
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            user_permissions=user_permissions,
        )
        retry_payload = _parse_stock_sync_retry_payload(payload)
        target_outbox = service.get_stock_outbox_for_retry(
            order_id=order_id,
            outbox_id=retry_payload.outbox_id,
            stock_action=retry_payload.stock_action,
            idempotency_key=retry_payload.idempotency_key,
        )
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(target_outbox.item_code or ""),
            company=_company_for_permission_check(target_outbox.company),
            supplier=str(target_outbox.supplier or ""),
            warehouse=(str(target_outbox.warehouse or "") or None),
            resource_type="subcontract_stock_outbox",
            resource_id=int(target_outbox.id),
            resource_no=str(target_outbox.event_key or target_outbox.id),
            enforce_action=False,
            user_permissions=user_permissions,
        )
        result = service.retry_stock_sync(
            order_id=order_id,
            outbox_id=retry_payload.outbox_id,
            stock_action=retry_payload.stock_action,
            idempotency_key=retry_payload.idempotency_key,
            request_id=context.request_id,
            operator=current_user.username,
            reason=retry_payload.reason,
        )
        after_data = service.get_order_snapshot(order_id=order_id)
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            before_data={
                **(before_data or {}),
                "retry_target_outbox_id": retry_payload.outbox_id,
                "retry_target_stock_action": retry_payload.stock_action,
                "retry_reason": retry_payload.reason,
            },
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=SUBCONTRACT_INTERNAL_ERROR,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/internal/stock-sync/run-once")
def run_subcontract_stock_sync_once(
    request: Request,
    batch_size: int = 20,
    dry_run: bool = False,
    stock_action: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """运行外发库存同步 worker（内部接口，可按 action 分派 issue/receipt）。"""
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_STOCK_SYNC_WORKER

    if not subcontract_enable_internal_stock_worker_api():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="SubcontractStockSyncWorker",
            resource_no=None,
            deny_reason="外发库存同步内部接口未启用",
            event_type=SUBCONTRACT_WORKER_DISABLED,
            module="subcontract",
        )
        return _err(
            SUBCONTRACT_WORKER_DISABLED,
            "外发库存同步内部接口未启用",
            status_code=status_of(SUBCONTRACT_WORKER_DISABLED),
        )

    try:
        permission_service.require_action_from_roles_only(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="subcontract_stock_sync_worker",
        )
        permission_service.require_internal_worker_principal(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="subcontract",
            resource_type="SUBCONTRACTSTOCKWORKER",
        )

        if dry_run and not subcontract_enable_stock_worker_dry_run():
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="SubcontractStockSyncWorker",
                resource_no=None,
                deny_reason="生产环境未开启外发库存同步 worker dry-run",
                event_type=SUBCONTRACT_DRY_RUN_DISABLED,
                module="subcontract",
            )
            return _err(
                SUBCONTRACT_DRY_RUN_DISABLED,
                "生产环境未开启外发库存同步 worker dry-run",
                status_code=status_of(SUBCONTRACT_DRY_RUN_DISABLED),
            )

        try:
            worker_scope = _resolve_subcontract_worker_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
            )
        except PermissionSourceUnavailable:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="SubcontractStockSyncWorker",
                resource_no=None,
                deny_reason="ERPNext User Permission 查询失败",
                event_type=PERMISSION_SOURCE_UNAVAILABLE,
                module="subcontract",
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
                resource_type="SubcontractStockSyncWorker",
                resource_no=None,
                deny_reason=exc.message,
                event_type=AUTH_FORBIDDEN,
                module="subcontract",
            )
            return _app_err(exc)

        limit = _bounded_batch_size(batch_size)
        normalized_action: str | None = None
        if stock_action is not None and stock_action.strip():
            normalized_action = stock_action.strip().lower()
            if normalized_action not in {
                SubcontractStockOutboxService.STOCK_ACTION_ISSUE,
                SubcontractStockOutboxService.STOCK_ACTION_RECEIPT,
            }:
                raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="不支持的库存动作")
        worker = SubcontractStockWorkerService(
            session=session,
            erp_service=ERPNextStockEntryService(),
        )
        if dry_run:
            result = worker.preview_once(limit=limit, scope=worker_scope, stock_action=normalized_action)
        else:
            result = worker.run_once(limit=limit, scope=worker_scope, stock_action=normalized_action)

        data = SubcontractStockSyncRunOnceData(
            dry_run=result.dry_run,
            batch_size=result.batch_size,
            would_process_count=result.would_process_count,
            processed_count=result.processed_count,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            dead_count=result.dead_count,
        )
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_stock_sync_worker",
            resource_id=None,
            resource_no="run-once",
            before_data={
                "batch_size": limit,
                "dry_run": dry_run,
                "stock_action": normalized_action,
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
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{order_id}/receive")
def receive_subcontract(
    order_id: int,
    request: Request,
    payload: dict[str, Any] | None = Body(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """登记回料：写本地回料事实 + pending receipt outbox，不在事务内调用 ERPNext。"""
    service = SubcontractService(session=session)
    audit = AuditService(session=session)
    permission_service = PermissionService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_RECEIVE
    before_data = None
    after_data = None

    try:
        order = service.get_order_or_raise(order_id)
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=action,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
        )
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            user_permissions=user_permissions,
        )
        if str(getattr(order, "resource_scope_status", "") or "").strip().lower() == "blocked_scope":
            raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单缺少 company 资源范围")
        receipt_warehouse = _extract_required_warehouse(payload)
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            warehouse=receipt_warehouse,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            enforce_action=False,
            user_permissions=user_permissions,
        )
        receive_payload = _parse_receive_payload(payload)
        result = service.receive(
            order_id=order_id,
            payload=receive_payload,
            operator=current_user.username,
            request_id=context.request_id,
        )
        after_data = service.get_order_snapshot(order_id=order_id)
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=SUBCONTRACT_INTERNAL_ERROR,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{order_id}/inspect")
def inspect_subcontract(
    order_id: int,
    request: Request,
    payload: dict[str, Any] | None = Body(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """完成验货。"""
    service = SubcontractService(session=session)
    audit = AuditService(session=session)
    permission_service = PermissionService(session=session)
    context = AuditContext.from_request(request)
    action = SUBCONTRACT_INSPECT
    before_data = None
    after_data = None

    try:
        order = service.get_order_or_raise(order_id)
        user_permissions = permission_service.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request,
            action=action,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
        )
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(order.item_code),
            company=_company_for_permission_check(order.company),
            supplier=str(order.supplier),
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            user_permissions=user_permissions,
        )
        if str(getattr(order, "resource_scope_status", "") or "").strip().lower() == "blocked_scope":
            raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单缺少 company 资源范围")
        inspect_payload = _parse_inspect_payload(payload)
        receipt_scope = service.get_receipt_batch_scope(
            order_id=order_id,
            receipt_batch_no=inspect_payload.receipt_batch_no,
        )
        receipt_warehouse = receipt_scope.get("receipt_warehouse")
        if not receipt_warehouse:
            raise BusinessException(code=SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED, message="回料仓不能为空")
        permission_service.ensure_subcontract_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            item_code=str(receipt_scope.get("item_code") or ""),
            company=_company_for_permission_check(receipt_scope.get("company")),
            supplier=str(receipt_scope.get("supplier") or ""),
            warehouse=str(receipt_warehouse),
            resource_type="subcontract_receipt_batch",
            resource_id=order_id,
            resource_no=inspect_payload.receipt_batch_no,
            enforce_action=False,
            user_permissions=user_permissions,
        )
        before_data = service.get_order_snapshot(order_id=order_id)
        result = service.inspect(
            order_id=order_id,
            payload=inspect_payload,
            operator=current_user.username,
            request_id=context.request_id,
        )
        after_data = {
            **service.get_order_snapshot(order_id=order_id),
            "inspection": {
                "inspection_no": result.inspection_no,
                "receipt_batch_no": result.receipt_batch_no,
                "inspected_qty": str(result.inspected_qty),
                "rejected_qty": str(result.rejected_qty),
                "gross_amount": str(result.gross_amount),
                "deduction_amount": str(result.deduction_amount),
                "net_amount": str(result.net_amount),
            },
        }
        audit.record_success(
            module="subcontract",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="subcontract_order",
            resource_id=order_id,
            resource_no=str(order.subcontract_no),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except HTTPException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _http_exc_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=order_id,
                resource_no=_resource_no(before_data),
                before_data=before_data,
                after_data=after_data,
                error_code=SUBCONTRACT_INTERNAL_ERROR,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(_unknown_to_internal_error(request, action, exc))
