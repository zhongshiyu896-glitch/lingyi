"""Authentication dependencies for Lingyi service."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import HTTPException
from fastapi import Request

from app.core.permissions import AUTH_UNAUTHORIZED_CODE


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated current user."""

    username: str
    roles: list[str]
    is_service_account: bool
    source: str


def _auth_error(message: str = "未登录或 Token 无效") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": AUTH_UNAUTHORIZED_CODE, "message": message, "data": {}},
    )


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_json(url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    req = request.Request(url=url, method="GET", headers=headers)
    try:
        with request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
    except (error.URLError, TimeoutError):
        return None
    except Exception:
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _service_account_users() -> set[str]:
    raw = os.getenv("LINGYI_SERVICE_ACCOUNT_USERS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _internal_worker_trusted_roles() -> set[str]:
    raw = os.getenv("LINGYI_INTERNAL_WORKER_TRUSTED_ROLES", "LY Integration Service,System Manager")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _extract_roles(user_payload: dict[str, Any]) -> list[str]:
    data = user_payload.get("data", {})
    if not isinstance(data, dict):
        return []
    roles_raw = data.get("roles", [])
    if not isinstance(roles_raw, list):
        return []

    roles: set[str] = set()
    for role_item in roles_raw:
        if isinstance(role_item, dict):
            role = role_item.get("role") or role_item.get("name")
            if isinstance(role, str) and role.strip():
                roles.add(role.strip())
        elif isinstance(role_item, str) and role_item.strip():
            roles.add(role_item.strip())
    return sorted(roles)


def _resolve_erpnext_user(
    *,
    base_url: str,
    authorization: str | None,
    cookie: str | None,
) -> CurrentUser | None:
    headers: dict[str, str] = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    if cookie:
        headers["Cookie"] = cookie

    user_payload = _load_json(f"{base_url}/api/method/frappe.auth.get_logged_user", headers=headers)
    if not user_payload:
        return None

    username = user_payload.get("message")
    if not isinstance(username, str) or not username.strip():
        return None

    encoded_username = parse.quote(username.strip(), safe="")
    fields = parse.quote('["name","roles"]', safe="")
    profile_payload = _load_json(
        f"{base_url}/api/resource/User/{encoded_username}?fields={fields}",
        headers=headers,
    )
    roles = _extract_roles(profile_payload or {})

    is_service_account = username in _service_account_users()
    source = "erpnext_token" if authorization else "erpnext_session"
    return CurrentUser(
        username=username.strip(),
        roles=roles,
        is_service_account=is_service_account,
        source=source,
    )


def _resolve_dev_user(request_obj: Request) -> CurrentUser | None:
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        return None
    if not _env_flag("LINGYI_ALLOW_DEV_AUTH", default=False):
        return None

    dev_user = request_obj.headers.get("X-LY-Dev-User", "").strip()
    if not dev_user:
        return None

    raw_roles = request_obj.headers.get("X-LY-Dev-Roles", "")
    roles = [item.strip() for item in raw_roles.split(",") if item.strip()]
    if not roles:
        roles = ["BOM Editor"]
    return CurrentUser(
        username=dev_user,
        roles=roles,
        is_service_account=dev_user in _service_account_users(),
        source="dev_header",
    )


def is_internal_worker_principal(current_user: CurrentUser) -> bool:
    """Whether user is allowed principal type for internal worker API.

    Requirements:
    - trusted service account user, OR
    - trusted system/integration role.
    """
    if current_user.is_service_account:
        return True
    trusted_roles = _internal_worker_trusted_roles()
    return bool(set(current_user.roles) & trusted_roles)


def is_internal_worker_api_enabled() -> bool:
    """Whether internal worker API is enabled under current environment.

    In production it is disabled by default and must be explicitly enabled.
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env != "production":
        return True
    return _env_flag("ENABLE_INTERNAL_WORKER_API", default=False)


def get_current_user(request_obj: Request) -> CurrentUser:
    """Resolve current user from ERPNext auth/session, with local dev fallback."""
    base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
    authorization = request_obj.headers.get("Authorization")
    cookie = request_obj.headers.get("Cookie")

    if base_url and (authorization or cookie):
        user = _resolve_erpnext_user(
            base_url=base_url,
            authorization=authorization,
            cookie=cookie,
        )
        if user:
            request_obj.state.current_user = user
            return user
        raise _auth_error()

    dev_user = _resolve_dev_user(request_obj)
    if dev_user:
        request_obj.state.current_user = dev_user
        return dev_user

    raise _auth_error()
