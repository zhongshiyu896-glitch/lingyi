"""Auth and action permission APIs."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Response
from sqlalchemy.orm import Session

from app.core.auth import build_local_login_user
from app.core.auth import clear_auth_session_cache_for_request
from app.core.auth import clear_erpnext_session_cookie
from app.core.auth import clear_local_session_cookie
from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.auth import is_fastapi_session_auth_enabled
from app.core.auth import is_local_session_auth_enabled
from app.core.auth import login_fastapi_user
from app.core.auth import login_erpnext_user
from app.core.auth import set_erpnext_session_cookie
from app.core.auth import set_local_session_cookie
from app.schemas.auth import LocalLoginRequest
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/auth", tags=["auth"])
# Exposed endpoints:
# - POST /api/auth/login
# - POST /api/auth/logout
# - GET /api/auth/me
# - GET /api/auth/actions
# - GET /api/auth/actions/bom/{bom_id}


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _is_secure_cookie_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",", maxsplit=1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


@router.post("/login")
def login(payload: LocalLoginRequest, request: Request, response: Response):
    """Create an authenticated browser session.

    Local profile login is available only when development auth is explicitly enabled.
    Production uses the FastAPI native user source when permission source is fastapi.
    The legacy ERPNext session path is retained only for deployments that explicitly
    keep the ERPNext permission source.
    """
    if is_local_session_auth_enabled():
        current_user = build_local_login_user(username=payload.username, profile=payload.profile or "system_manager")
        set_local_session_cookie(response, current_user)
    elif is_fastapi_session_auth_enabled():
        current_user = login_fastapi_user(username=payload.username, password=payload.password or "")
        set_local_session_cookie(response, current_user, secure=_is_secure_cookie_request(request))
    else:
        erpnext_session = login_erpnext_user(username=payload.username, password=payload.password or "")
        current_user = erpnext_session.current_user
        set_erpnext_session_cookie(response, erpnext_session.sid, secure=_is_secure_cookie_request(request))
    return _ok(
        {
            "username": current_user.username,
            "roles": current_user.roles,
            "is_service_account": current_user.is_service_account,
            "source": current_user.source,
        }
    )


@router.post("/logout")
def logout(request: Request, response: Response):
    """Clear local and ERPNext browser sessions."""
    clear_auth_session_cache_for_request(request)
    clear_local_session_cookie(response)
    clear_erpnext_session_cookie(response)
    return _ok({"logged_out": True})


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
