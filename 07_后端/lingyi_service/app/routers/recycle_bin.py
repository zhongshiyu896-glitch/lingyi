"""Unified recycle-bin routes."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.permissions import RECYCLE_BIN_MANAGE
from app.core.permissions import RECYCLE_BIN_READ
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService
from app.services.recycle_bin_service import RecycleBinService

router = APIRouter(prefix="/api/recycle-bin", tags=["recycle_bin"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _err(exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "data": None})


def _require_action(*, session: Session, request: Request, current_user: CurrentUser, action: str, resource_id: int | None = None) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="recycle_bin",
        resource_type="RECYCLE_BIN_ITEM",
        resource_id=resource_id,
    )


@router.get("")
def list_recycle_bin_items(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    module: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=RECYCLE_BIN_READ)
    try:
        data = RecycleBinService(session).list_items(
            page=page,
            page_size=page_size,
            module=module,
            entity_type=entity_type,
            company=company,
            keyword=keyword,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/{item_id}/restore")
def restore_recycle_bin_item(
    item_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=RECYCLE_BIN_MANAGE, resource_id=item_id)
    try:
        item = RecycleBinService(session).restore(item_id=item_id, actor=current_user.username)
        AuditService(session).record_success(
            module="recycle_bin",
            action="restore",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="RECYCLE_BIN_ITEM",
            resource_id=item.id,
            resource_no=item.code,
            before_data=None,
            after_data=item.model_dump(mode="json"),
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        session.rollback()
        return _err(exc)
    return _ok(item)


@router.delete("/{item_id}")
def purge_recycle_bin_item(
    item_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(session=session, request=request, current_user=current_user, action=RECYCLE_BIN_MANAGE, resource_id=item_id)
    try:
        item = RecycleBinService(session).purge(item_id=item_id)
        AuditService(session).record_success(
            module="recycle_bin",
            action="purge",
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="RECYCLE_BIN_ITEM",
            resource_id=item.id,
            resource_no=item.code,
            before_data=item.model_dump(mode="json"),
            after_data={"purged": True},
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        session.rollback()
        return _err(exc)
    return _ok({**item.model_dump(mode="json"), "purged": True})
