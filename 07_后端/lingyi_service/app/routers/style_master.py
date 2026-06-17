"""FastAPI-native style master routes for the A3 style base slice."""

from __future__ import annotations

from collections.abc import Callable
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
from app.core.permissions import STYLE_MASTER_MANAGE
from app.core.permissions import STYLE_MASTER_READ
from app.schemas.style_master import StyleDictionaryCreateRequest
from app.schemas.style_master import StyleDictionaryDeactivateRequest
from app.schemas.style_master import StyleDictionaryUpdateRequest
from app.schemas.style_master import StyleMasterCreateRequest
from app.schemas.style_master import StyleMasterDeactivateRequest
from app.schemas.style_master import StyleMasterUpdateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService
from app.services.style_master_service import StyleMasterMutationResult
from app.services.style_master_service import StyleMasterService

router = APIRouter(prefix="/api/style-master", tags=["style_master"])


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
    resource_type: str,
    resource_id: int | None = None,
) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="style_master",
        resource_type=resource_type,
        resource_id=resource_id,
    )


def _commit_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    result: StyleMasterMutationResult,
) -> None:
    AuditService(session).record_success(
        module="style_master",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=result.resource_type,
        resource_id=result.resource_id,
        resource_no=result.resource_no,
        before_data=result.before,
        after_data=result.after,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _record_failure_and_commit(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        session.rollback()
    except Exception:
        pass
    AuditService(session).record_failure(
        module="style_master",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _handle_internal_error(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    exc: Exception,
) -> None:
    error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
    _record_failure_and_commit(
        session=session,
        request=request,
        current_user=current_user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        error_code=error.code,
    )
    raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc


@router.get("/styles")
def list_styles(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=STYLE_MASTER_READ,
        resource_type="STYLE_MASTER",
    )
    try:
        data = StyleMasterService(session).list_styles(company=company, keyword=keyword, status=status, page=page, page_size=page_size)
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/styles")
def create_style(
    payload: StyleMasterCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="create",
            resource_type="STYLE_MASTER",
            resource_id=None,
            resource_no=payload.ys_style_no,
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.create_style(payload=payload, actor=current_user.username),
        )
    except AppException as exc:
        return _err(exc)
    return _created(result.item)


@router.patch("/styles/{style_id}")
def update_style(
    style_id: int,
    payload: StyleMasterUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="update",
            resource_type="STYLE_MASTER",
            resource_id=style_id,
            resource_no=payload.ys_style_no,
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.update_style(style_id=style_id, payload=payload, actor=current_user.username),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(result.item)


@router.post("/styles/{style_id}/deactivate")
def deactivate_style(
    style_id: int,
    payload: StyleMasterDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="deactivate",
            resource_type="STYLE_MASTER",
            resource_id=style_id,
            resource_no=None,
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.deactivate_style(
                style_id=style_id,
                company=payload.company,
                idempotency_key=payload.idempotency_key,
                reason=payload.reason,
                actor=current_user.username,
            ),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(result.item)


@router.get("/dictionaries")
def list_dictionaries(
    request: Request,
    company: str | None = Query(default=None),
    dict_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    disabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=STYLE_MASTER_READ,
        resource_type="STYLE_DICTIONARY",
    )
    try:
        data = StyleMasterService(session).list_dictionaries(
            company=company,
            dict_type=dict_type,
            keyword=keyword,
            disabled=disabled,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/dictionaries")
def create_dictionary(
    payload: StyleDictionaryCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="create_dictionary",
            resource_type="STYLE_DICTIONARY",
            resource_id=None,
            resource_no=f"{payload.dict_type}:{payload.code}",
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.create_dictionary(payload=payload, actor=current_user.username),
        )
    except AppException as exc:
        return _err(exc)
    return _created(result.item)


@router.patch("/dictionaries/{dictionary_id}")
def update_dictionary(
    dictionary_id: int,
    payload: StyleDictionaryUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="update_dictionary",
            resource_type="STYLE_DICTIONARY",
            resource_id=dictionary_id,
            resource_no=payload.code,
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.update_dictionary(dictionary_id=dictionary_id, payload=payload, actor=current_user.username),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(result.item)


@router.post("/dictionaries/{dictionary_id}/deactivate")
def deactivate_dictionary(
    dictionary_id: int,
    payload: StyleDictionaryDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        result = _mutate(
            action="deactivate_dictionary",
            resource_type="STYLE_DICTIONARY",
            resource_id=dictionary_id,
            resource_no=None,
            request=request,
            current_user=current_user,
            session=session,
            mutate=lambda service: service.deactivate_dictionary(
                dictionary_id=dictionary_id,
                company=payload.company,
                idempotency_key=payload.idempotency_key,
                reason=payload.reason,
                actor=current_user.username,
            ),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(result.item)


def _mutate(
    *,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    mutate: Callable[[StyleMasterService], StyleMasterMutationResult],
) -> StyleMasterMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=STYLE_MASTER_MANAGE,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    try:
        result = mutate(StyleMasterService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
        return result
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            error_code=exc.code,
        )
        raise
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            exc=exc,
        )
        raise
