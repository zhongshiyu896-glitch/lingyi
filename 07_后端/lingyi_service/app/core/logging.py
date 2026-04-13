"""Logging sanitization utilities."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.request_id import normalize_request_id

REDACTED_MESSAGE = "internal error, detail redacted"

_SENSITIVE_PATTERNS = [
    re.compile(r"\[sql:.*?\]", re.IGNORECASE | re.DOTALL),
    re.compile(r"\[parameters:.*?\]", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(update|insert\s+into|delete\s+from|select)\b[\s\S]{0,200}\bly_schema\.", re.IGNORECASE),
    re.compile(r"\bauthorization\b", re.IGNORECASE),
    re.compile(r"\bcookie\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"\bservice[_-]?token\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\bpasswd\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"(postgres(?:ql)?|mysql|mariadb|oracle|sqlserver|sqlite)://", re.IGNORECASE),
]

_SAFE_EXTRA_KEYS = {
    "error_code",
    "module",
    "action",
    "resource_type",
    "resource_id",
    "resource_no",
    "user_id",
    "sqlstate",
    "db_driver_error_code",
}


def _contains_sensitive(message: str) -> bool:
    text = message or ""
    return any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS)


def sanitize_log_message(message: str | None) -> str:
    """Sanitize free-text log content and redact unsafe details."""
    if not message:
        return ""
    normalized = str(message).replace("\n", " ").replace("\r", " ").strip()
    if not normalized:
        return ""
    if _contains_sensitive(normalized):
        return REDACTED_MESSAGE
    if len(normalized) > 240:
        return normalized[:240]
    return normalized


def _safe_token(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 64:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        return None
    return text


def _extract_exception_text(exc: BaseException) -> str:
    for field in ("exception_message", "message"):
        value = getattr(exc, field, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(exc)


def _extract_sqlstate(exc: BaseException) -> str | None:
    for target in (getattr(exc, "orig", None), exc):
        if target is None:
            continue
        for field in ("pgcode", "sqlstate", "sql_state"):
            value = getattr(target, field, None)
            safe = _safe_token(value)
            if safe:
                return safe
    return None


def _extract_driver_code(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    args = getattr(orig, "args", None)
    if not args:
        return None
    first = args[0]
    if isinstance(first, int):
        return str(first)
    return _safe_token(first)


def sanitize_exception(exc: BaseException) -> dict[str, str | None]:
    """Return sanitized exception metadata for safe logs/audit."""
    return {
        "exception_type": type(exc).__name__,
        "sanitized_message": sanitize_log_message(_extract_exception_text(exc)) or REDACTED_MESSAGE,
        "sqlstate": _extract_sqlstate(exc),
        "db_driver_error_code": _extract_driver_code(exc),
    }


def log_safe_error(
    logger_obj: logging.Logger,
    message: str,
    exc: BaseException,
    *,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log safe error metadata without raw exception text."""
    safe_exc = sanitize_exception(exc)
    payload: dict[str, Any] = {
        "event": sanitize_log_message(message) or "error",
        "exception_type": safe_exc["exception_type"] or "Exception",
    }
    payload["request_id"] = normalize_request_id(request_id)
    if safe_exc.get("sqlstate"):
        payload["sqlstate"] = safe_exc["sqlstate"]
    if safe_exc.get("db_driver_error_code"):
        payload["db_driver_error_code"] = safe_exc["db_driver_error_code"]
    if extra:
        for key in _SAFE_EXTRA_KEYS:
            value = extra.get(key)
            if value is not None and str(value).strip() != "":
                payload[key] = sanitize_log_message(str(value)) or REDACTED_MESSAGE

    serialized = " ".join(f"{key}={str(value).replace(' ', '_')}" for key, value in payload.items())
    logger_obj.error("%s", serialized)
