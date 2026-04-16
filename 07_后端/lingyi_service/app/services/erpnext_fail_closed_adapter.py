"""Shared fail-closed helpers for ERPNext integrations (TASK-008B)."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from json import JSONDecodeError
import re
import socket
from typing import Any
from typing import Mapping
from urllib import error as urllib_error

from app.core.error_codes import ERPNEXT_AUTH_FAILED
from app.core.error_codes import ERPNEXT_DOCSTATUS_INVALID
from app.core.error_codes import ERPNEXT_DOCSTATUS_REQUIRED
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.error_codes import ERPNEXT_RESPONSE_INVALID
from app.core.error_codes import ERPNEXT_TIMEOUT
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import sanitize_log_message

_DOCSTATUS_ALLOWED = {0, 1, 2}
_SENSITIVE_HINT_PATTERNS = (
    re.compile(r"\bapi[_\s-]?key\b", re.IGNORECASE),
    re.compile(r"\bprivate[_\s-]?key\b", re.IGNORECASE),
)
_RETRYABLE_CODES = {ERPNEXT_TIMEOUT, EXTERNAL_SERVICE_UNAVAILABLE}


@dataclass(frozen=True)
class ERPNextNormalizedResult:
    """Normalized ERPNext adapter payload."""

    doctype: str | None
    name: str | None
    docstatus: int | None
    status: str | None
    data: Any
    source: str = "erpnext"
    validated: bool = False


@dataclass
class ERPNextAdapterException(Exception):
    """Structured fail-closed ERPNext error."""

    error_code: str
    http_status: int | None = None
    doctype: str | None = None
    resource_name: str | None = None
    safe_message: str | None = None
    retryable: bool = False
    raw_detail: str | None = None

    def __post_init__(self) -> None:
        if self.http_status is None:
            self.http_status = status_of(self.error_code)
        if not self.safe_message:
            self.safe_message = message_of(self.error_code)
        Exception.__init__(self, self.safe_message)

    def to_http_detail(self) -> dict[str, Any]:
        return {
            "code": self.error_code,
            "message": self.safe_message,
            "data": None,
        }


def sanitize_erpnext_error(detail: Any) -> str:
    """Return safe error text that never leaks secrets."""
    text = sanitize_log_message(str(detail) if detail is not None else "")
    if not text:
        return REDACTED_MESSAGE
    if any(pattern.search(text) for pattern in _SENSITIVE_HINT_PATTERNS):
        return REDACTED_MESSAGE
    return text


def is_retryable_erpnext_error(error_code: str) -> bool:
    """Return whether ERPNext error should be retried."""
    return error_code in _RETRYABLE_CODES


def normalize_erpnext_response(
    response: Any,
    *,
    doctype: str | None = None,
    resource_name: str | None = None,
    allow_list: bool = False,
) -> ERPNextNormalizedResult:
    """Normalize ERPNext payload (`{data: ...}` or direct doc/list) into one shape."""
    payload: Any
    if isinstance(response, Mapping):
        payload = response.get("data", response)
    elif isinstance(response, list):
        payload = response
    else:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_RESPONSE_INVALID),
            retryable=False,
            raw_detail=str(type(response)),
        )

    if isinstance(payload, list):
        if not allow_list:
            raise ERPNextAdapterException(
                error_code=ERPNEXT_RESPONSE_INVALID,
                doctype=doctype,
                resource_name=resource_name,
                safe_message=f"{message_of(ERPNEXT_RESPONSE_INVALID)}: list payload not allowed",
                retryable=False,
                raw_detail="list payload",
            )
        return ERPNextNormalizedResult(
            doctype=_normalize_text(doctype),
            name=_normalize_text(resource_name),
            docstatus=None,
            status=None,
            data=payload,
            validated=False,
        )

    if not isinstance(payload, Mapping):
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_RESPONSE_INVALID),
            retryable=False,
            raw_detail=str(type(payload)),
        )

    merged_doctype = _normalize_text(doctype) or _normalize_text(payload.get("doctype"))
    name = _normalize_text(payload.get("name")) or _normalize_text(resource_name)
    status = _normalize_text(payload.get("status"))
    docstatus = None
    if "docstatus" in payload:
        docstatus = _coerce_docstatus(payload.get("docstatus"), doctype=merged_doctype, resource_name=name)

    return ERPNextNormalizedResult(
        doctype=merged_doctype,
        name=name,
        docstatus=docstatus,
        status=status,
        data=dict(payload),
        validated=False,
    )


def validate_docstatus(
    normalized: ERPNextNormalizedResult,
    *,
    require_submitted: bool = False,
    status_only_whitelist: Mapping[str, set[str]] | None = None,
) -> ERPNextNormalizedResult:
    """Validate ERPNext docstatus/status under fail-closed policy."""
    if not isinstance(normalized.data, Mapping):
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESPONSE_INVALID,
            doctype=normalized.doctype,
            resource_name=normalized.name,
            safe_message=message_of(ERPNEXT_RESPONSE_INVALID),
            retryable=False,
            raw_detail="non-dict normalized.data",
        )

    doctype = normalized.doctype or _normalize_text(normalized.data.get("doctype"))
    status = normalized.status or _normalize_text(normalized.data.get("status"))
    raw_docstatus = normalized.docstatus if normalized.docstatus is not None else normalized.data.get("docstatus")

    if raw_docstatus is None:
        if doctype and status_only_whitelist and doctype in status_only_whitelist:
            allowed = {item.strip().lower() for item in status_only_whitelist[doctype] if isinstance(item, str)}
            current_status = (status or "").strip().lower()
            if not current_status:
                raise ERPNextAdapterException(
                    error_code=ERPNEXT_DOCSTATUS_REQUIRED,
                    doctype=doctype,
                    resource_name=normalized.name,
                    safe_message=message_of(ERPNEXT_DOCSTATUS_REQUIRED),
                    retryable=False,
                    raw_detail="missing docstatus and status",
                )
            if current_status not in allowed:
                raise ERPNextAdapterException(
                    error_code=ERPNEXT_DOCSTATUS_INVALID,
                    doctype=doctype,
                    resource_name=normalized.name,
                    safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
                    retryable=False,
                    raw_detail=f"status={current_status!r} not in whitelist",
                )
            return replace(normalized, doctype=doctype, status=status, validated=True)

        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_REQUIRED,
            doctype=doctype,
            resource_name=normalized.name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_REQUIRED),
            retryable=False,
            raw_detail="missing docstatus",
        )

    docstatus = _coerce_docstatus(raw_docstatus, doctype=doctype, resource_name=normalized.name)
    if docstatus not in _DOCSTATUS_ALLOWED:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_INVALID,
            doctype=doctype,
            resource_name=normalized.name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
            retryable=False,
            raw_detail=f"unexpected docstatus={docstatus}",
        )

    if require_submitted and docstatus != 1:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_INVALID,
            doctype=doctype,
            resource_name=normalized.name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
            retryable=False,
            raw_detail=f"docstatus={docstatus} is not submitted",
        )

    return replace(normalized, doctype=doctype, docstatus=docstatus, status=status, validated=True)


def require_submitted_doc(
    normalized: ERPNextNormalizedResult,
    *,
    status_only_whitelist: Mapping[str, set[str]] | None = None,
) -> ERPNextNormalizedResult:
    """Validate ERPNext response as submitted document."""
    return validate_docstatus(
        normalized,
        require_submitted=True,
        status_only_whitelist=status_only_whitelist,
    )


def map_erpnext_exception(
    exc: BaseException,
    *,
    doctype: str | None = None,
    resource_name: str | None = None,
) -> ERPNextAdapterException:
    """Map raw network/HTTP/decoding failures to fail-closed ERPNext codes."""
    if isinstance(exc, ERPNextAdapterException):
        return exc

    safe_detail = sanitize_erpnext_error(exc)

    if isinstance(exc, urllib_error.HTTPError):
        if exc.code in {401, 403}:
            return _build_adapter_error(
                code=ERPNEXT_AUTH_FAILED,
                doctype=doctype,
                resource_name=resource_name,
                retryable=False,
                safe_detail=safe_detail,
                raw_detail=str(exc),
            )
        if exc.code == 404:
            return _build_adapter_error(
                code=ERPNEXT_RESOURCE_NOT_FOUND,
                doctype=doctype,
                resource_name=resource_name,
                retryable=False,
                safe_detail=safe_detail,
                raw_detail=str(exc),
            )
        if exc.code >= 500:
            return _build_adapter_error(
                code=EXTERNAL_SERVICE_UNAVAILABLE,
                doctype=doctype,
                resource_name=resource_name,
                retryable=True,
                safe_detail=safe_detail,
                raw_detail=str(exc),
            )
        return _build_adapter_error(
            code=EXTERNAL_SERVICE_UNAVAILABLE,
            doctype=doctype,
            resource_name=resource_name,
            retryable=False,
            safe_detail=safe_detail,
            raw_detail=str(exc),
        )

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return _build_adapter_error(
            code=ERPNEXT_TIMEOUT,
            doctype=doctype,
            resource_name=resource_name,
            retryable=True,
            safe_detail=safe_detail,
            raw_detail=str(exc),
        )

    if isinstance(exc, urllib_error.URLError):
        if _is_timeout_reason(exc.reason):
            return _build_adapter_error(
                code=ERPNEXT_TIMEOUT,
                doctype=doctype,
                resource_name=resource_name,
                retryable=True,
                safe_detail=safe_detail,
                raw_detail=str(exc),
            )
        return _build_adapter_error(
            code=EXTERNAL_SERVICE_UNAVAILABLE,
            doctype=doctype,
            resource_name=resource_name,
            retryable=True,
            safe_detail=safe_detail,
            raw_detail=str(exc),
        )

    if isinstance(exc, JSONDecodeError):
        return _build_adapter_error(
            code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            retryable=False,
            safe_detail=safe_detail,
            raw_detail=str(exc),
        )

    if isinstance(exc, (TypeError, ValueError, KeyError)):
        return _build_adapter_error(
            code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            retryable=False,
            safe_detail=safe_detail,
            raw_detail=str(exc),
        )

    return _build_adapter_error(
        code=EXTERNAL_SERVICE_UNAVAILABLE,
        doctype=doctype,
        resource_name=resource_name,
        retryable=False,
        safe_detail=safe_detail,
        raw_detail=str(exc),
    )


def _build_adapter_error(
    *,
    code: str,
    doctype: str | None,
    resource_name: str | None,
    retryable: bool,
    safe_detail: str,
    raw_detail: str,
) -> ERPNextAdapterException:
    message = message_of(code)
    if safe_detail and safe_detail != REDACTED_MESSAGE:
        message = f"{message}: {safe_detail}"
    return ERPNextAdapterException(
        error_code=code,
        http_status=status_of(code),
        doctype=_normalize_text(doctype),
        resource_name=_normalize_text(resource_name),
        safe_message=message,
        retryable=retryable,
        raw_detail=raw_detail,
    )


def _coerce_docstatus(
    raw_docstatus: Any,
    *,
    doctype: str | None,
    resource_name: str | None,
) -> int | None:
    if isinstance(raw_docstatus, bool):
        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
            retryable=False,
            raw_detail=str(raw_docstatus),
        )
    if isinstance(raw_docstatus, int):
        docstatus = raw_docstatus
    elif isinstance(raw_docstatus, str):
        text = raw_docstatus.strip()
        if text not in {"0", "1", "2"}:
            raise ERPNextAdapterException(
                error_code=ERPNEXT_DOCSTATUS_INVALID,
                doctype=doctype,
                resource_name=resource_name,
                safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
                retryable=False,
                raw_detail=raw_docstatus,
            )
        docstatus = int(text)
    else:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
            retryable=False,
            raw_detail=str(raw_docstatus),
        )

    if docstatus not in _DOCSTATUS_ALLOWED:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_DOCSTATUS_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_DOCSTATUS_INVALID),
            retryable=False,
            raw_detail=str(raw_docstatus),
        )
    return docstatus


def _is_timeout_reason(reason: Any) -> bool:
    if reason is None:
        return False
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(reason).lower()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "ERPNextAdapterException",
    "ERPNextNormalizedResult",
    "is_retryable_erpnext_error",
    "map_erpnext_exception",
    "normalize_erpnext_response",
    "require_submitted_doc",
    "sanitize_erpnext_error",
    "validate_docstatus",
]
