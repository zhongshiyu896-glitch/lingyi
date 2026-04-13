"""Request ID normalization helpers."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import Request

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SENSITIVE_REQUEST_ID_KEYWORDS = (
    "authorization",
    "bearer",
    "token",
    "cookie",
    "set-cookie",
    "password",
    "passwd",
    "secret",
    "session",
    "sessionid",
    "api-key",
    "api_key",
    "access-key",
    "access_key",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
)


def generate_request_id() -> str:
    """Generate safe request id."""
    while True:
        generated = uuid4().hex
        if REQUEST_ID_PATTERN.fullmatch(generated) and not _contains_sensitive_keyword(generated):
            return generated


def _contains_sensitive_keyword(request_id: str) -> bool:
    lowered = request_id.lower()
    return any(keyword in lowered for keyword in SENSITIVE_REQUEST_ID_KEYWORDS)


def normalize_request_id(raw_request_id: str | None) -> str:
    """Validate request id by whitelist and return safe id.

    Invalid value will be fully discarded and replaced by generated id.
    """
    if not raw_request_id:
        return generate_request_id()
    if not REQUEST_ID_PATTERN.fullmatch(raw_request_id):
        return generate_request_id()
    if _contains_sensitive_keyword(raw_request_id):
        return generate_request_id()
    return raw_request_id


def is_sensitive_request_id(raw_request_id: str | None) -> bool:
    """Return whether request_id should be replaced for semantic safety."""
    if not raw_request_id:
        return False
    return _contains_sensitive_keyword(raw_request_id)


def is_request_id_valid(raw_request_id: str | None) -> bool:
    """Return whether request_id matches strict whitelist and semantic rules."""
    if not raw_request_id:
        return False
    if not REQUEST_ID_PATTERN.fullmatch(raw_request_id):
        return False
    return not _contains_sensitive_keyword(raw_request_id)


def request_id_replacement_reason(raw_request_id: str | None) -> str | None:
    """Return safe reason enum when request_id must be replaced."""
    if not raw_request_id:
        return "missing"
    if not REQUEST_ID_PATTERN.fullmatch(raw_request_id):
        return "invalid_format"
    if _contains_sensitive_keyword(raw_request_id):
        return "sensitive_keyword"
    return None


def normalize_request_id_with_meta(raw_request_id: str | None) -> tuple[str, bool, str | None]:
    """Normalize request_id and return replacement metadata."""
    normalized = normalize_request_id(raw_request_id)
    was_invalid = normalized != raw_request_id
    reason = request_id_replacement_reason(raw_request_id) if was_invalid else None
    return normalized, was_invalid, reason


def make_request_id_security_meta(raw_request_id: str | None) -> dict[str, str | bool]:
    """Build safe metadata for logs/audit without keeping raw request_id."""
    normalized, was_invalid, reason = normalize_request_id_with_meta(raw_request_id)
    meta: dict[str, str | bool] = {
        "request_id": normalized,
        "request_id_source": "generated" if was_invalid else "header",
    }
    if was_invalid:
        meta["request_id_was_invalid"] = True
        meta["request_id_invalid_reason"] = reason or "invalid"
    return meta


def get_request_id_from_request(request_obj: Request) -> str:
    """Get normalized request id from request state or generate new one."""
    raw_value = getattr(getattr(request_obj, "state", None), "request_id", None)
    normalized = normalize_request_id(raw_value)
    if getattr(getattr(request_obj, "state", None), "request_id", None) != normalized:
        request_obj.state.request_id = normalized
    return normalized
