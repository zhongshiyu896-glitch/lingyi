"""FastAPI-native master data routes for existing frontend pages."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import INTERNAL_ERROR
from app.core.error_codes import message_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.permissions import MASTER_DATA_MANAGE
from app.core.permissions import MASTER_DATA_READ
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.master_data_service import MasterDataMutationResult
from app.services.master_data_service import MasterDataService
from app.services.permission_service import PermissionService
from app.schemas.master_data import MasterDataCreateRequest
from app.schemas.master_data import MasterDataDeactivateRequest
from app.schemas.master_data import MasterDataUpdateRequest

router = APIRouter(prefix="/api/master-data", tags=["master_data"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _err(exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


def _record_failure_and_commit(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    entity_type: str,
    action: str,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        session.rollback()
    except Exception:
        pass
    audit = AuditService(session)
    audit.record_failure(
        module="master_data",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=entity_type.upper(),
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _commit_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    entity_type: str,
    action: str,
    result: MasterDataMutationResult,
) -> None:
    audit = AuditService(session)
    audit.record_success(
        module="master_data",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=entity_type.upper(),
        resource_id=result.item.id,
        resource_no=result.item.code,
        before_data=result.before,
        after_data=result.after,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _require_action(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    entity_type: str,
    resource_id: int | None = None,
) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="master_data",
        resource_type=entity_type,
        resource_id=resource_id,
    )


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _payload_text(payload: dict[str, Any] | None, *keys: str) -> str | None:
    source = payload or {}
    for key in keys:
        value = _scope_text(source.get(key))
        if value:
            return value
    return None


def _master_data_scope_target(
    *,
    entity_type: str,
    company: str | None,
    code: str | None,
    payload: dict[str, Any] | None,
) -> dict[str, str | None] | None:
    normalized_company = _scope_text(company)
    if entity_type == "customer":
        return {
            "company": normalized_company,
            "customer": _scope_text(code),
        }
    if entity_type == "material":
        item_code = _payload_text(payload, "material_item_code", "materialItemCode", "item_code", "itemCode") or _scope_text(code)
        return {
            "company": normalized_company,
            "item_code": item_code,
        }
    return None


def _scope_filters_for_list(
    *,
    permissions: UserPermissionResult | None,
    entity_type: str,
) -> dict[str, set[str] | None]:
    if permissions is None or permissions.unrestricted or entity_type not in {"customer", "material"}:
        return {
            "allowed_companies": None,
            "allowed_customers": None,
            "allowed_items": None,
        }
    return {
        "allowed_companies": set(permissions.allowed_companies),
        "allowed_customers": set(permissions.allowed_customers) if entity_type == "customer" else None,
        "allowed_items": set(permissions.allowed_items) if entity_type == "material" else None,
    }


def _master_data_scope_permissions(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    entity_type: str,
    resource_id: int | None = None,
    resource_no: str | None = None,
) -> UserPermissionResult | None:
    if entity_type not in {"customer", "material"}:
        return None
    return PermissionService(session=session).get_resource_scope_permissions(
        current_user=current_user,
        request_obj=request,
        module="master_data",
        action=action,
        resource_type=entity_type,
        resource_id=resource_id,
        resource_no=resource_no,
    )


def _ensure_master_data_scope(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    entity_type: str,
    resource_id: int | None,
    resource_no: str | None,
    scope: dict[str, str | None] | None,
    permissions: UserPermissionResult | None,
) -> None:
    if scope is None or permissions is None or permissions.unrestricted:
        return
    required_fields = ("company", "customer") if entity_type == "customer" else ("company", "item_code")
    PermissionService(session=session).ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="master_data",
        action=action,
        resource_scope=scope,
        required_fields=required_fields,
        resource_type=entity_type,
        resource_id=resource_id,
        resource_no=resource_no,
        enforce_action=False,
        user_permissions=permissions,
    )


@router.get("/{entity_path}")
def list_master_data(
    entity_path: str,
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    disabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    entity_type = MasterDataService.entity_type_from_path(entity_path)
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MASTER_DATA_READ,
        entity_type=entity_type,
    )
    try:
        permissions = _master_data_scope_permissions(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_READ,
            entity_type=entity_type,
        )
        scope_filters = _scope_filters_for_list(permissions=permissions, entity_type=entity_type)
        data = MasterDataService(session).list_records(
            entity_type=entity_type,
            company=company,
            keyword=keyword,
            disabled=disabled,
            page=page,
            page_size=page_size,
            **scope_filters,
        )
    except HTTPException:
        raise
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/{entity_path}")
def create_master_data(
    entity_path: str,
    payload: MasterDataCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    entity_type = MasterDataService.entity_type_from_path(entity_path)
    action = "create"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MASTER_DATA_MANAGE,
        entity_type=entity_type,
    )
    try:
        scope = _master_data_scope_target(
            entity_type=entity_type,
            company=payload.company,
            code=payload.code,
            payload=payload.payload,
        )
        permissions = _master_data_scope_permissions(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_no=payload.code,
        )
        _ensure_master_data_scope(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=None,
            resource_no=payload.code,
            scope=scope,
            permissions=permissions,
        )
        result = MasterDataService(session).create_record(
            entity_type=entity_type,
            payload=payload,
            actor=current_user.username,
        )
        _commit_success(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            result=result,
        )
    except HTTPException:
        raise
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=None,
            resource_no=payload.code,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=None,
            resource_no=payload.code,
            error_code=error.code,
        )
        raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc
    return _created(result.item)


@router.patch("/{entity_path}/{record_id}")
def update_master_data(
    entity_path: str,
    record_id: int,
    payload: MasterDataUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    entity_type = MasterDataService.entity_type_from_path(entity_path)
    action = "update"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MASTER_DATA_MANAGE,
        entity_type=entity_type,
        resource_id=record_id,
    )
    try:
        service = MasterDataService(session)
        existing = service.get_record_for_permission(entity_type=entity_type, record_id=record_id, company=payload.company)
        scope = _master_data_scope_target(
            entity_type=entity_type,
            company=payload.company,
            code=payload.code or existing.code,
            payload=payload.payload or existing.payload,
        )
        permissions = _master_data_scope_permissions(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
        )
        _ensure_master_data_scope(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
            scope=scope,
            permissions=permissions,
        )
        result = service.update_record(
            entity_type=entity_type,
            record_id=record_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_success(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            result=result,
        )
    except HTTPException:
        raise
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=payload.code,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=payload.code,
            error_code=error.code,
        )
        raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc
    return _ok(result.item)


@router.post("/{entity_path}/{record_id}/deactivate")
def deactivate_master_data(
    entity_path: str,
    record_id: int,
    payload: MasterDataDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    entity_type = MasterDataService.entity_type_from_path(entity_path)
    action = "deactivate"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MASTER_DATA_MANAGE,
        entity_type=entity_type,
        resource_id=record_id,
    )
    try:
        service = MasterDataService(session)
        existing = service.get_record_for_permission(entity_type=entity_type, record_id=record_id, company=payload.company)
        scope = _master_data_scope_target(
            entity_type=entity_type,
            company=payload.company,
            code=existing.code,
            payload=existing.payload,
        )
        permissions = _master_data_scope_permissions(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
        )
        _ensure_master_data_scope(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
            scope=scope,
            permissions=permissions,
        )
        result = service.deactivate_record(
            entity_type=entity_type,
            record_id=record_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_success(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            result=result,
        )
    except HTTPException:
        raise
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=None,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=None,
            error_code=error.code,
        )
        raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc
    return _ok(result.item)


@router.delete("/{entity_path}/{record_id}")
def delete_master_data(
    entity_path: str,
    record_id: int,
    request: Request,
    company: str = Query(..., min_length=1, max_length=140),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    entity_type = MasterDataService.entity_type_from_path(entity_path)
    action = "delete"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MASTER_DATA_MANAGE,
        entity_type=entity_type,
        resource_id=record_id,
    )
    resource_no: str | None = None
    try:
        service = MasterDataService(session)
        existing = service.get_record_for_permission(entity_type=entity_type, record_id=record_id, company=company)
        resource_no = existing.code
        scope = _master_data_scope_target(
            entity_type=entity_type,
            company=company,
            code=existing.code,
            payload=existing.payload,
        )
        permissions = _master_data_scope_permissions(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
        )
        _ensure_master_data_scope(
            session=session,
            request=request,
            current_user=current_user,
            action=MASTER_DATA_MANAGE,
            entity_type=entity_type,
            resource_id=record_id,
            resource_no=existing.code,
            scope=scope,
            permissions=permissions,
        )
        result = service.delete_record(
            entity_type=entity_type,
            record_id=record_id,
            company=company,
            actor=current_user.username,
        )
        _commit_success(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            result=result,
        )
    except HTTPException:
        raise
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=resource_no,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            entity_type=entity_type,
            action=action,
            resource_id=record_id,
            resource_no=resource_no,
            error_code=error.code,
        )
        raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc
    return _ok(result.item)
