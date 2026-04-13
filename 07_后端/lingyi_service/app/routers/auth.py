"""Auth and action permission APIs."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/auth", tags=["auth"])
# Exposed endpoints:
# - GET /api/auth/me
# - GET /api/auth/actions
# - GET /api/auth/actions/bom/{bom_id}


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


@router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Return current authenticated user info."""
    return _ok(
        {
            "username": current_user.username,
            "roles": current_user.roles,
            "is_service_account": current_user.is_service_account,
            "source": current_user.source,
        }
    )


@router.get("/actions")
def get_actions(
    request: Request,
    module: str = Query(default="bom"),
    resource_type: str | None = Query(default=None),
    resource_id: int | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Return aggregated action permissions for current user."""
    service = PermissionService(session=session)
    agg = service.get_actions(
        current_user=current_user,
        request_obj=request,
        module=module,
        audit_module="auth",
        resource_type=resource_type,
        resource_id=resource_id,
        action_context="auth:actions",
    )
    return _ok(PermissionService.to_dict(agg))


@router.get("/actions/bom/{bom_id}")
def get_bom_actions(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Return resource-level action permissions for BOM detail page."""
    service = PermissionService(session=session)
    agg = service.get_actions(
        current_user=current_user,
        request_obj=request,
        module="bom",
        audit_module="auth",
        resource_type="bom",
        resource_id=bom_id,
        action_context="auth:actions",
    )
    return _ok(
        {
            "bom_id": bom_id,
            "status": agg.status,
            "actions": agg.actions,
            "button_permissions": agg.button_permissions,
        }
    )
