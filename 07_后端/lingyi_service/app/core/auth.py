"""Authentication dependencies for Lingyi service."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import HTTPException
from fastapi import Request
from fastapi import Response

from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.permissions import AUTH_UNAUTHORIZED_CODE

DEV_AUTH_ALLOWED_ENVS = frozenset({"development", "test", "local"})
LOCAL_SESSION_COOKIE_NAME = "lingyi_local_session"
LOCAL_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60

LOCAL_LOGIN_ROLE_PROFILES: dict[str, list[str]] = {
    "system_manager": ["System Manager"],
    "bom_editor": ["BOM Editor"],
    "production_manager": ["Production Manager"],
    "subcontract_manager": ["Subcontract Manager"],
    "quality_manager": ["Quality Manager"],
    "warehouse_manager": ["Warehouse Manager"],
    "sales_manager": ["Sales Manager"],
}


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


def _local_auth_disabled_error(message: str = "本地登录仅在 local/development/test 且显式允许时可用") -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": INTERNAL_API_DISABLED, "message": message, "data": {}},
    )


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalized_app_env(default: str = "development") -> str:
    return os.getenv("APP_ENV", default).strip().lower() or default


def is_local_session_auth_enabled() -> bool:
    return _normalized_app_env() in DEV_AUTH_ALLOWED_ENVS and _env_flag("LINGYI_ALLOW_DEV_AUTH", default=False)


def ensure_local_session_auth_enabled() -> None:
    if not is_local_session_auth_enabled():
        raise _local_auth_disabled_error()


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


def _session_secret() -> bytes:
    raw = os.getenv("LINGYI_LOCAL_SESSION_SECRET", "lingyi-local-session-secret").strip()
    if not raw:
        raw = "lingyi-local-session-secret"
    return raw.encode("utf-8")


def _urlsafe_b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _urlsafe_b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(f"{payload}{padding}")


def _sign_local_session_payload(payload: bytes) -> bytes:
    return hmac.new(_session_secret(), payload, hashlib.sha256).digest()


def build_local_login_user(*, username: str, profile: str) -> CurrentUser:
    ensure_local_session_auth_enabled()

    normalized_username = username.strip()
    roles = LOCAL_LOGIN_ROLE_PROFILES.get(profile)
    if not normalized_username or roles is None:
        raise _auth_error("本地登录信息无效")

    return CurrentUser(
        username=normalized_username,
        roles=list(roles),
        is_service_account=normalized_username in _service_account_users(),
        source="dev_session",
    )


def create_local_session_token(current_user: CurrentUser) -> str:
    payload = {
        "username": current_user.username,
        "roles": current_user.roles,
        "is_service_account": current_user.is_service_account,
        "source": "dev_session",
        "exp": int(time.time()) + LOCAL_SESSION_MAX_AGE_SECONDS,
    }
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = _sign_local_session_payload(raw_payload)
    return f"{_urlsafe_b64encode(raw_payload)}.{_urlsafe_b64encode(signature)}"


def set_local_session_cookie(response: Response, current_user: CurrentUser) -> None:
    response.set_cookie(
        key=LOCAL_SESSION_COOKIE_NAME,
        value=create_local_session_token(current_user),
        max_age=LOCAL_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_local_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=LOCAL_SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


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
    if not is_local_session_auth_enabled():
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


def _resolve_local_session_user(request_obj: Request) -> CurrentUser | None:
    if not is_local_session_auth_enabled():
        return None

    token = request_obj.cookies.get(LOCAL_SESSION_COOKIE_NAME, "").strip()
    if not token:
        return None

    payload_segment, separator, signature_segment = token.partition(".")
    if not payload_segment or not separator or not signature_segment:
        return None

    try:
        raw_payload = _urlsafe_b64decode(payload_segment)
        raw_signature = _urlsafe_b64decode(signature_segment)
    except Exception:
        return None

    expected_signature = _sign_local_session_payload(raw_payload)
    if not hmac.compare_digest(raw_signature, expected_signature):
        return None

    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    if int(payload.get("exp", 0) or 0) <= int(time.time()):
        return None

    username = payload.get("username")
    roles = payload.get("roles")
    is_service_account = bool(payload.get("is_service_account", False))
    if not isinstance(username, str) or not username.strip():
        return None
    if not isinstance(roles, list) or not all(isinstance(role, str) and role.strip() for role in roles):
        return None

    return CurrentUser(
        username=username.strip(),
        roles=[role.strip() for role in roles],
        is_service_account=is_service_account,
        source="dev_session",
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
    app_env = _normalized_app_env()
    if app_env in DEV_AUTH_ALLOWED_ENVS:
        return True
    if app_env != "production":
        return False
    return _env_flag("ENABLE_INTERNAL_WORKER_API", default=False)


def get_current_user(request_obj: Request) -> CurrentUser:
    """Resolve current user from ERPNext auth/session, with local dev fallback."""
    base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
    authorization = request_obj.headers.get("Authorization")

    local_session_user = _resolve_local_session_user(request_obj)
    if local_session_user:
        request_obj.state.current_user = local_session_user
        return local_session_user

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
