"""FastAPI-native material purchase routes for existing purchase pages."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.permissions import MATERIAL_PURCHASE_READ
from app.core.permissions import MATERIAL_PURCHASE_WRITE
from app.schemas.material_purchase import MaterialPurchaseOrderCreateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.material_purchase_service import MaterialPurchaseService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/material-purchase", tags=["material_purchase"])


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
        module="material_purchase",
        resource_type=resource_type,
        resource_id=resource_id,
    )


@router.get("/orders")
def list_material_purchase_orders(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
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
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_ORDER",
    )
    try:
        data = MaterialPurchaseService(session).list_orders(
            company=company,
            keyword=keyword,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/orders")
def create_material_purchase_order(
    payload: MaterialPurchaseOrderCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_ORDER",
    )
    audit = AuditService(session)
    try:
        result = MaterialPurchaseService(session).create_order(payload=payload, actor=current_user.username)
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=None,
            resource_no=payload.purchase_no,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)
