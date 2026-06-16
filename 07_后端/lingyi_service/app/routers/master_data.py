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
        data = MasterDataService(session).list_records(
            entity_type=entity_type,
            company=company,
            keyword=keyword,
            disabled=disabled,
            page=page,
            page_size=page_size,
        )
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
        result = MasterDataService(session).update_record(
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
        result = MasterDataService(session).deactivate_record(
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
