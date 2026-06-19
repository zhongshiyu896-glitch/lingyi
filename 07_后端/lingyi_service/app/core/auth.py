"""Authentication dependencies for Lingyi service."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import os
import secrets
import threading
import time
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import HTTPException
from fastapi import Request
from fastapi import Response

from app.core.error_codes import ERPNEXT_RESPONSE_INVALID
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import ERPNEXT_TIMEOUT
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.permissions import AUTH_FORBIDDEN_CODE
from app.core.permissions import AUTH_UNAUTHORIZED_CODE
from app.core.permissions import PERMISSION_SOURCE_UNAVAILABLE_CODE
from app.core.permissions import get_permission_source

DEV_AUTH_ALLOWED_ENVS = frozenset({"development", "test", "local"})
LOCAL_SESSION_COOKIE_NAME = "lingyi_local_session"
LOCAL_SESSION_SOURCE = "dev_session"
FASTAPI_SESSION_SOURCE = "fastapi_session"
LOCAL_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
ERPNEXT_SESSION_COOKIE_NAME = "sid"
AUTH_SESSION_CACHE_TTL_ENV = "LINGYI_AUTH_CACHE_TTL_SECONDS"
AUTH_SESSION_CACHE_DEFAULT_TTL_SECONDS = 45.0
AUTH_SESSION_CACHE_MAX_TTL_SECONDS = 60.0
ERPNEXT_API_KEY_ENV = "LINGYI_ERPNEXT_API_KEY"
ERPNEXT_API_SECRET_ENV = "LINGYI_ERPNEXT_API_SECRET"
FASTAPI_AUTH_USERS_ENV = "LINGYI_FASTAPI_AUTH_USERS_JSON"
FASTAPI_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
FASTAPI_PASSWORD_HASH_ITERATIONS = 260_000

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


@dataclass(frozen=True)
class ERPNextLoginSession:
    """ERPNext login result that can be mirrored into the browser session."""

    current_user: CurrentUser
    sid: str


_AuthSessionCacheValue = tuple[CurrentUser, float]
_auth_session_cache: dict[str, _AuthSessionCacheValue] = {}
_auth_session_cache_lock = threading.Lock()


def _clone_current_user(current_user: CurrentUser) -> CurrentUser:
    return CurrentUser(
        username=current_user.username,
        roles=list(current_user.roles),
        is_service_account=current_user.is_service_account,
        source=current_user.source,
    )


def _auth_cache_now() -> float:
    return time.monotonic()


def _auth_session_cache_ttl_seconds() -> float:
    raw = os.getenv(AUTH_SESSION_CACHE_TTL_ENV, str(AUTH_SESSION_CACHE_DEFAULT_TTL_SECONDS)).strip()
    try:
        ttl = float(raw)
    except ValueError:
        ttl = AUTH_SESSION_CACHE_DEFAULT_TTL_SECONDS
    if ttl <= 0:
        return 0.0
    return min(ttl, AUTH_SESSION_CACHE_MAX_TTL_SECONDS)


def _local_session_cache_key(token: str) -> str:
    return f"local_session:{token}"


def _erpnext_session_cache_key(sid: str) -> str:
    return f"erpnext_sid:{sid}"


def _erpnext_authorization_cache_key(authorization: str) -> str:
    return f"erpnext_authorization:{authorization}"


def _auth_session_cache_get(cache_key: str | None) -> CurrentUser | None:
    if not cache_key:
        return None
    now = _auth_cache_now()
    with _auth_session_cache_lock:
        cached = _auth_session_cache.get(cache_key)
        if cached is None:
            return None
        current_user, expires_at = cached
        if expires_at <= now:
            _auth_session_cache.pop(cache_key, None)
            return None
        return _clone_current_user(current_user)


def _auth_session_cache_set(cache_key: str | None, current_user: CurrentUser) -> None:
    if not cache_key:
        return
    ttl = _auth_session_cache_ttl_seconds()
    if ttl <= 0:
        return
    expires_at = _auth_cache_now() + ttl
    with _auth_session_cache_lock:
        _auth_session_cache[cache_key] = (_clone_current_user(current_user), expires_at)


def _auth_session_cache_delete(cache_key: str | None) -> None:
    if not cache_key:
        return
    with _auth_session_cache_lock:
        _auth_session_cache.pop(cache_key, None)


def clear_auth_session_cache_for_request(request_obj: Request) -> None:
    local_token = request_obj.cookies.get(LOCAL_SESSION_COOKIE_NAME, "").strip()
    if local_token:
        _auth_session_cache_delete(_local_session_cache_key(local_token))

    erpnext_sid = request_obj.cookies.get(ERPNEXT_SESSION_COOKIE_NAME, "").strip()
    if erpnext_sid:
        _auth_session_cache_delete(_erpnext_session_cache_key(erpnext_sid))

    authorization = request_obj.headers.get("Authorization", "").strip()
    if authorization:
        _auth_session_cache_delete(_erpnext_authorization_cache_key(authorization))


def _reset_auth_session_cache_for_tests() -> None:
    with _auth_session_cache_lock:
        _auth_session_cache.clear()


def _auth_error(message: str = "未登录或 Token 无效") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": AUTH_UNAUTHORIZED_CODE, "message": message, "data": {}},
    )


def _auth_forbidden_error(message: str = "无权执行该操作") -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": AUTH_FORBIDDEN_CODE, "message": message, "data": {}},
    )


def _local_auth_disabled_error(message: str = "本地登录仅在 local/development/test 且显式允许时可用") -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": INTERNAL_API_DISABLED, "message": message, "data": {}},
    )


def _auth_source_unavailable_error(message: str = "FastAPI 认证用户源暂时不可用") -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": PERMISSION_SOURCE_UNAVAILABLE_CODE, "message": message, "data": {}},
    )


def _erpnext_unavailable_error(
    message: str = "ERPNext 服务暂时不可用",
    *,
    code: str = ERPNEXT_SERVICE_UNAVAILABLE,
) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": code, "message": message, "data": {}},
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


def is_fastapi_session_auth_enabled() -> bool:
    return _normalized_app_env() == "production" and get_permission_source() == "fastapi"


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


def _load_json_strict(
    url: str,
    headers: dict[str, str],
    *,
    unavailable_message: str,
    invalid_message: str,
) -> dict[str, Any]:
    req = request.Request(url=url, method="GET", headers=headers)
    try:
        with request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
    except TimeoutError as exc:
        raise _erpnext_unavailable_error(unavailable_message, code=ERPNEXT_TIMEOUT) from exc
    except error.URLError as exc:
        raise _erpnext_unavailable_error(unavailable_message) from exc
    except Exception as exc:
        raise _erpnext_unavailable_error(unavailable_message) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise _erpnext_unavailable_error(invalid_message, code=ERPNEXT_RESPONSE_INVALID) from exc
    if not isinstance(payload, dict):
        raise _erpnext_unavailable_error(invalid_message, code=ERPNEXT_RESPONSE_INVALID)
    return payload


def _erpnext_service_headers() -> dict[str, str]:
    api_key = os.getenv(ERPNEXT_API_KEY_ENV, "").strip()
    api_secret = os.getenv(ERPNEXT_API_SECRET_ENV, "").strip()
    if not api_key or not api_secret:
        raise _erpnext_unavailable_error("ERPNext 服务凭据未配置")
    return {
        "Accept": "application/json",
        "Authorization": f"token {api_key}:{api_secret}",
    }


def _service_account_users() -> set[str]:
    raw = os.getenv("LINGYI_SERVICE_ACCOUNT_USERS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def make_fastapi_password_hash(
    password: str,
    *,
    salt: str | None = None,
    iterations: int = FASTAPI_PASSWORD_HASH_ITERATIONS,
) -> str:
    """Build a PBKDF2-SHA256 password hash for FastAPI-native auth config."""
    normalized_password = password or ""
    normalized_salt = salt or secrets.token_urlsafe(16)
    if "$" in normalized_salt:
        raise ValueError("salt must not contain '$'")
    safe_iterations = max(1_000, min(int(iterations), 1_000_000))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        normalized_password.encode("utf-8"),
        normalized_salt.encode("utf-8"),
        safe_iterations,
    ).hex()
    return f"{FASTAPI_PASSWORD_HASH_SCHEME}${safe_iterations}${normalized_salt}${digest}"


def _verify_fastapi_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4:
        return False
    scheme, iterations_raw, salt, expected_digest = parts
    if scheme != FASTAPI_PASSWORD_HASH_SCHEME or not salt or not expected_digest:
        return False
    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if iterations < 1_000 or iterations > 1_000_000:
        return False
    actual_hash = make_fastapi_password_hash(password, salt=salt, iterations=iterations)
    actual_digest = actual_hash.rsplit("$", maxsplit=1)[-1]
    return hmac.compare_digest(actual_digest, expected_digest)


def _load_fastapi_auth_users_config() -> dict[str, Any]:
    raw = os.getenv(FASTAPI_AUTH_USERS_ENV, "").strip()
    if not raw:
        raise _auth_source_unavailable_error("FastAPI 认证用户源未配置")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _auth_source_unavailable_error("FastAPI 认证用户源 JSON 非法") from exc
    if not isinstance(payload, dict):
        raise _auth_source_unavailable_error("FastAPI 认证用户源结构非法")
    users_payload = payload.get("users", payload)
    if not isinstance(users_payload, dict):
        raise _auth_source_unavailable_error("FastAPI 认证用户源 users 结构非法")
    return users_payload


def login_fastapi_user(*, username: str, password: str) -> CurrentUser:
    if not is_fastapi_session_auth_enabled():
        raise _local_auth_disabled_error("FastAPI 原生登录仅在 production 且权限源 fastapi 时可用")

    normalized_username = username.strip()
    if not normalized_username or not password:
        raise _auth_error("用户名或密码错误")

    users = _load_fastapi_auth_users_config()
    entry = users.get(normalized_username)
    if not isinstance(entry, dict) or bool(entry.get("disabled", False)):
        raise _auth_error("用户名或密码错误")

    password_hash = str(entry.get("password_hash") or "")
    if not password_hash or not _verify_fastapi_password(password, password_hash):
        raise _auth_error("用户名或密码错误")

    roles_raw = entry.get("roles")
    if not isinstance(roles_raw, list):
        raise _auth_source_unavailable_error("FastAPI 认证用户角色未配置")
    roles = sorted({role.strip() for role in roles_raw if isinstance(role, str) and role.strip()})
    if not roles:
        raise _auth_source_unavailable_error("FastAPI 认证用户角色未配置")

    return CurrentUser(
        username=normalized_username,
        roles=roles,
        is_service_account=bool(entry.get("is_service_account", False)) or normalized_username in _service_account_users(),
        source=FASTAPI_SESSION_SOURCE,
    )


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
        "source": current_user.source,
        "exp": int(time.time()) + LOCAL_SESSION_MAX_AGE_SECONDS,
    }
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = _sign_local_session_payload(raw_payload)
    return f"{_urlsafe_b64encode(raw_payload)}.{_urlsafe_b64encode(signature)}"


def set_local_session_cookie(response: Response, current_user: CurrentUser, *, secure: bool = False) -> None:
    response.set_cookie(
        key=LOCAL_SESSION_COOKIE_NAME,
        value=create_local_session_token(current_user),
        max_age=LOCAL_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_local_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=LOCAL_SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


def set_erpnext_session_cookie(response: Response, sid: str, *, secure: bool = False) -> None:
    response.set_cookie(
        key=ERPNEXT_SESSION_COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_erpnext_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ERPNEXT_SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


def _extract_sid_from_set_cookie(set_cookie_headers: list[str]) -> str | None:
    for header in set_cookie_headers:
        cookie = SimpleCookie()
        try:
            cookie.load(header)
        except Exception:
            continue
        sid = cookie.get(ERPNEXT_SESSION_COOKIE_NAME)
        if sid is not None and sid.value.strip():
            return sid.value.strip()
    return None


def _post_erpnext_login(*, base_url: str, username: str, password: str) -> tuple[dict[str, Any], list[str]]:
    body = parse.urlencode({"usr": username, "pwd": password}).encode("utf-8")
    req = request.Request(
        url=f"{base_url}/api/method/login",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            raw_body = response.read().decode("utf-8")
            response_info = response.info()
            set_cookie_headers = response_info.get_all("Set-Cookie", []) if response_info is not None else []
    except error.HTTPError as exc:
        if exc.code == 403:
            raise _auth_forbidden_error("ERPNext 拒绝登录") from exc
        if exc.code == 401:
            raise _auth_error("ERPNext 用户名或密码错误") from exc
        raise _erpnext_unavailable_error("ERPNext 登录服务暂时不可用") from exc
    except TimeoutError as exc:
        raise _erpnext_unavailable_error("ERPNext 登录请求超时", code=ERPNEXT_TIMEOUT) from exc
    except error.URLError as exc:
        raise _erpnext_unavailable_error("ERPNext 登录服务暂时不可用") from exc

    try:
        payload = json.loads(raw_body) if raw_body.strip() else {}
    except json.JSONDecodeError as exc:
        raise _erpnext_unavailable_error("ERPNext 登录响应格式非法", code=ERPNEXT_RESPONSE_INVALID) from exc
    if not isinstance(payload, dict):
        raise _erpnext_unavailable_error("ERPNext 登录响应格式非法", code=ERPNEXT_RESPONSE_INVALID)
    return payload, list(set_cookie_headers)


def login_erpnext_user(*, username: str, password: str) -> ERPNextLoginSession:
    normalized_username = username.strip()
    normalized_password = password.strip()
    if not normalized_username or not normalized_password:
        raise _auth_error("ERPNext 用户名或密码错误")

    base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise _erpnext_unavailable_error("LINGYI_ERPNEXT_BASE_URL 未配置")

    _, set_cookie_headers = _post_erpnext_login(
        base_url=base_url,
        username=normalized_username,
        password=normalized_password,
    )
    sid = _extract_sid_from_set_cookie(set_cookie_headers)
    if not sid:
        raise _auth_error("ERPNext 登录未返回有效会话")

    current_user = _resolve_erpnext_user(
        base_url=base_url,
        authorization=None,
        cookie=f"{ERPNEXT_SESSION_COOKIE_NAME}={sid}",
    )
    if current_user is None:
        raise _auth_error("ERPNext 会话校验失败")
    _auth_session_cache_set(_erpnext_session_cache_key(sid), current_user)
    return ERPNextLoginSession(current_user=current_user, sid=sid)


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


def _load_erpnext_user_roles_with_service_credentials(*, base_url: str, username: str) -> list[str]:
    """Read confirmed user's roles with ERPNext service credentials.

    The username must come from frappe.auth.get_logged_user; callers must not pass
    user-controlled identifiers into this helper.
    """
    encoded_username = parse.quote(username.strip(), safe="")
    fields = parse.quote('["name","roles"]', safe="")
    profile_payload = _load_json_strict(
        f"{base_url}/api/resource/User/{encoded_username}?fields={fields}",
        headers=_erpnext_service_headers(),
        unavailable_message="ERPNext 服务凭据读取用户角色失败",
        invalid_message="ERPNext 用户角色响应格式非法",
    )
    return _extract_roles(profile_payload)


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

    normalized_username = username.strip()
    roles = _load_erpnext_user_roles_with_service_credentials(base_url=base_url, username=normalized_username)

    is_service_account = username in _service_account_users()
    source = "erpnext_token" if authorization else "erpnext_session"
    return CurrentUser(
        username=normalized_username,
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


def _resolve_signed_session_user(request_obj: Request) -> CurrentUser | None:
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
    source = payload.get("source", LOCAL_SESSION_SOURCE)
    if not isinstance(username, str) or not username.strip():
        return None
    if not isinstance(roles, list) or not all(isinstance(role, str) and role.strip() for role in roles):
        return None
    if source not in {LOCAL_SESSION_SOURCE, FASTAPI_SESSION_SOURCE}:
        return None

    return CurrentUser(
        username=username.strip(),
        roles=[role.strip() for role in roles],
        is_service_account=is_service_account,
        source=source,
    )


def _resolve_local_session_user(request_obj: Request) -> CurrentUser | None:
    if not is_local_session_auth_enabled():
        return None
    user = _resolve_signed_session_user(request_obj)
    if user and user.source == LOCAL_SESSION_SOURCE:
        return user
    return None


def _resolve_fastapi_session_user(request_obj: Request) -> CurrentUser | None:
    if not is_fastapi_session_auth_enabled():
        return None
    user = _resolve_signed_session_user(request_obj)
    if user and user.source == FASTAPI_SESSION_SOURCE:
        return user
    return None


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
    """Resolve current user from FastAPI/local session or explicit ERPNext compatibility auth."""
    base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
    authorization = request_obj.headers.get("Authorization")

    local_session_token = request_obj.cookies.get(LOCAL_SESSION_COOKIE_NAME, "").strip()
    local_session_cache_key = _local_session_cache_key(local_session_token) if local_session_token else None
    cached_signed_user = _auth_session_cache_get(local_session_cache_key)
    if cached_signed_user:
        if cached_signed_user.source == LOCAL_SESSION_SOURCE and is_local_session_auth_enabled():
            request_obj.state.current_user = cached_signed_user
            return cached_signed_user
        if cached_signed_user.source == FASTAPI_SESSION_SOURCE and is_fastapi_session_auth_enabled():
            request_obj.state.current_user = cached_signed_user
            return cached_signed_user

    local_session_user = _resolve_local_session_user(request_obj)
    if local_session_user:
        _auth_session_cache_set(local_session_cache_key, local_session_user)
        request_obj.state.current_user = local_session_user
        return local_session_user

    fastapi_session_user = _resolve_fastapi_session_user(request_obj)
    if fastapi_session_user:
        _auth_session_cache_set(local_session_cache_key, fastapi_session_user)
        request_obj.state.current_user = fastapi_session_user
        return fastapi_session_user

    cookie = request_obj.headers.get("Cookie")
    erpnext_sid = request_obj.cookies.get(ERPNEXT_SESSION_COOKIE_NAME, "").strip()
    erpnext_cache_key = None
    if erpnext_sid:
        erpnext_cache_key = _erpnext_session_cache_key(erpnext_sid)
    elif authorization:
        erpnext_cache_key = _erpnext_authorization_cache_key(authorization)

    cached_erpnext_user = _auth_session_cache_get(erpnext_cache_key)
    if cached_erpnext_user and get_permission_source() != "fastapi" and base_url and (authorization or cookie):
        request_obj.state.current_user = cached_erpnext_user
        return cached_erpnext_user

    if get_permission_source() != "fastapi" and base_url and (authorization or cookie):
        user = _resolve_erpnext_user(
            base_url=base_url,
            authorization=authorization,
            cookie=cookie,
        )
        if user:
            _auth_session_cache_set(erpnext_cache_key, user)
            request_obj.state.current_user = user
            return user
        raise _auth_error()

    dev_user = _resolve_dev_user(request_obj)
    if dev_user:
        request_obj.state.current_user = dev_user
        return dev_user

    raise _auth_error()
