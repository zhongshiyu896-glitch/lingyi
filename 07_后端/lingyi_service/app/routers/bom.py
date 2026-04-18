"""FastAPI router for BOM module (TASK-001/TASK-001A)."""

from __future__ import annotations

from collections.abc import Generator
import logging
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import BOM_DEFAULT_CONFLICT
from app.core.error_codes import BOM_INTERNAL_ERROR
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BomInternalError
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import is_default_bom_unique_conflict
from app.core.logging import log_safe_error
from app.core.request_id import get_request_id_from_request
from app.core.permissions import BOM_CREATE
from app.core.permissions import BOM_DEACTIVATE
from app.core.permissions import BOM_PUBLISH
from app.core.permissions import BOM_READ
from app.core.permissions import BOM_SET_DEFAULT
from app.core.permissions import BOM_UPDATE
from app.schemas.bom import BomActivateData
from app.schemas.bom import BomCreateRequest
from app.schemas.bom import BomDeactivateData
from app.schemas.bom import BomDeactivateRequest
from app.schemas.bom import BomDetailData
from app.schemas.bom import BomExplodeData
from app.schemas.bom import BomExplodeRequest
from app.schemas.bom import BomListData
from app.schemas.bom import BomListQuery
from app.schemas.bom import BomSetDefaultData
from app.schemas.bom import BomUpdateData
from app.schemas.bom import BomUpdateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.bom_service import BomService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/bom", tags=["bom"])
logger = logging.getLogger(__name__)

BOM_ACTIVATE_ACTION = "bom:activate"
BOM_EXPLODE_ACTION = "bom:explode"


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message, "data": None},
    )


def _app_err(exc: AppException) -> JSONResponse:
    return _err(exc.code, exc.message, status_code=exc.status_code)


def _unknown_to_internal_error(request: Request, action: str, exc: Exception) -> BomInternalError:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "bom_internal_error",
        exc,
        request_id=request_id,
        extra={
            "error_code": BOM_INTERNAL_ERROR,
            "module": "bom",
            "action": action,
        },
    )
    return BomInternalError()


def _rollback_safely(session: Session, request: Request, action: str, origin: BaseException) -> None:
    try:
        session.rollback()
    except Exception as rollback_exc:  # pragma: no cover - hard to reproduce with sqlite
        request_id = get_request_id_from_request(request)
        error_code = origin.code if isinstance(origin, AppException) else ""
        log_safe_error(
            logger,
            "bom_rollback_failed",
            rollback_exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "bom",
                "action": action,
            },
        )


def _map_write_db_exception(request: Request, action: str, exc: BaseException) -> AppException:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "bom_database_write_failed",
        exc,
        request_id=request_id,
        extra={
            "error_code": DATABASE_WRITE_FAILED,
            "module": "bom",
            "action": action,
        },
    )
    if isinstance(exc, IntegrityError) and is_default_bom_unique_conflict(exc):
        return BusinessException(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试")
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
    bom_info = snapshot.get("bom", {})
    if not isinstance(bom_info, dict):
        return None
    value = bom_info.get("bom_no")
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
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
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
                "module": "bom",
                "action": action,
                "resource_type": "bom",
                "resource_id": resource_id if resource_id is not None else "",
                "resource_no": resource_no or "",
                "user_id": current_user.username,
            },
        )


def _require_any_action(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request_obj: Request,
    actions: tuple[str, ...],
    module: str = "bom",
    resource_type: str | None = None,
    resource_id: int | None = None,
    resource_item_code: str | None = None,
) -> None:
    """Require one action from a primary+fallback set.

    Notes:
    - `actions[0]` is the canonical action frozen by design.
    - subsequent actions are compatibility aliases kept for historical role sets.
    """
    if not actions:
        raise ValueError("actions must not be empty")

    agg = permission_service.get_actions(
        current_user=current_user,
        request_obj=request_obj,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_item_code=resource_item_code,
        action_context=actions[0],
    )
    if any(action in set(agg.actions) for action in actions):
        return

    # Reuse baseline denied-path auditing and response envelope.
    permission_service.require_action(
        current_user=current_user,
        request_obj=request_obj,
        action=actions[0],
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_item_code=resource_item_code,
    )


@router.post("/")
def create_bom(
    payload: BomCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """创建 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_CREATE,
        module="bom",
        resource_type="bom",
        resource_id=None,
        resource_item_code=payload.item_code,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_CREATE
    result = None
    after_data = None

    try:
        result = service.create_bom(payload=payload, operator=current_user.username)
        created_bom = service.get_bom_by_no(result.name)
        resource_id = int(created_bom.id) if created_bom else None
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=resource_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
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
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=f"{payload.item_code}:{payload.version_no}",
            before_data=None,
            after_data=after_data,
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
            resource_id=None,
            resource_no=f"{payload.item_code}:{payload.version_no}",
            before_data=None,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/")
def list_bom(
    request: Request,
    item_code: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 列表。"""
    # 读权限动作：bom:read
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )
    service = BomService(session=session)
    query = BomListQuery(item_code=item_code, status=status, page=page, page_size=page_size)
    try:
        data: BomListData = service.list_bom(query=query, allowed_item_codes=allowed_item_codes)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/{bom_id}")
def get_bom_detail(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """获取 BOM 详情。"""
    # 读权限动作：bom:read（含资源级校验）
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )
    service = BomService(session=session)
    try:
        data: BomDetailData = service.get_bom_detail(bom_id=bom_id)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.put("/{bom_id}")
def update_bom_draft(
    bom_id: int,
    payload: BomUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """更新 BOM 草稿。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_UPDATE,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_UPDATE
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        data: BomUpdateData = service.update_bom_draft(
            bom_id=bom_id,
            payload=payload,
            operator=current_user.username,
        )
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/set-default")
def set_default_bom(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """设置默认 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_SET_DEFAULT,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_SET_DEFAULT
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        data: BomSetDefaultData = service.set_default(bom_id=bom_id, operator=current_user.username)
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/activate")
def activate_bom(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """发布 BOM。"""
    permission_service = PermissionService(session=session)
    _require_any_action(
        permission_service=permission_service,
        current_user=current_user,
        request_obj=request,
        actions=(BOM_ACTIVATE_ACTION, BOM_PUBLISH),
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_ACTIVATE_ACTION
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        data: BomActivateData = service.activate(bom_id=bom_id, operator=current_user.username)
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/deactivate")
def deactivate_bom(
    bom_id: int,
    payload: BomDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """停用 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_DEACTIVATE,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_DEACTIVATE
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        data: BomDeactivateData = service.deactivate(
            bom_id=bom_id,
            reason=payload.reason,
            operator=current_user.username,
        )
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
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
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/explode")
def explode_bom(
    bom_id: int,
    payload: BomExplodeRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """展开 BOM。"""
    permission_service = PermissionService(session=session)
    _require_any_action(
        permission_service=permission_service,
        current_user=current_user,
        request_obj=request,
        actions=(BOM_EXPLODE_ACTION, BOM_READ),
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )
    service = BomService(session=session)
    try:
        data: BomExplodeData = service.explode(bom_id=bom_id, payload=payload)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_EXPLODE_ACTION, exc))
