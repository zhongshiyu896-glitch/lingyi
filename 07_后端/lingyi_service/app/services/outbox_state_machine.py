"""Shared Outbox state machine helpers (TASK-009B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
import hashlib
import json
from typing import Any
from typing import Mapping


OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_PROCESSING = "processing"
OUTBOX_STATUS_SUCCEEDED = "succeeded"
OUTBOX_STATUS_FAILED = "failed"
OUTBOX_STATUS_DEAD = "dead"
OUTBOX_STATUS_CANCELLED = "cancelled"

OUTBOX_STATUSES = frozenset(
    {
        OUTBOX_STATUS_PENDING,
        OUTBOX_STATUS_PROCESSING,
        OUTBOX_STATUS_SUCCEEDED,
        OUTBOX_STATUS_FAILED,
        OUTBOX_STATUS_DEAD,
        OUTBOX_STATUS_CANCELLED,
    }
)

OUTBOX_TERMINAL_STATUSES = frozenset(
    {
        OUTBOX_STATUS_SUCCEEDED,
        OUTBOX_STATUS_CANCELLED,
        OUTBOX_STATUS_DEAD,
    }
)

OUTBOX_ACTION_STOCK_ISSUE = "stock_issue"
OUTBOX_ACTION_STOCK_RECEIPT = "stock_receipt"
OUTBOX_ACTION_JOB_CARD_SYNC = "job_card_sync"
OUTBOX_ACTION_WORK_ORDER_CREATE = "work_order_create"
OUTBOX_ACTION_PURCHASE_INVOICE_DRAFT = "purchase_invoice_draft"
OUTBOX_ACTION_GENERIC = "generic"

OUTBOX_ACTIONS = frozenset(
    {
        OUTBOX_ACTION_STOCK_ISSUE,
        OUTBOX_ACTION_STOCK_RECEIPT,
        OUTBOX_ACTION_JOB_CARD_SYNC,
        OUTBOX_ACTION_WORK_ORDER_CREATE,
        OUTBOX_ACTION_PURCHASE_INVOICE_DRAFT,
        OUTBOX_ACTION_GENERIC,
    }
)

OUTBOX_EVENT_KEY_INVALID = "OUTBOX_EVENT_KEY_INVALID"
OUTBOX_PAYLOAD_INVALID = "OUTBOX_PAYLOAD_INVALID"
OUTBOX_STATUS_INVALID = "OUTBOX_STATUS_INVALID"
OUTBOX_TRANSITION_INVALID = "OUTBOX_TRANSITION_INVALID"

FORBIDDEN_EVENT_KEY_FIELDS = frozenset(
    {
        "idempotency_key",
        "request_id",
        "outbox_id",
        "created_at",
        "updated_at",
        "operator",
        "created_by",
        "attempts",
        "locked_by",
        "locked_until",
        "next_retry_at",
        "status",
        "error_code",
        "error_message",
        "last_error",
        "last_error_at",
        "retry_after",
        "processing_started_at",
        "succeeded_at",
        "failed_at",
        "dead_at",
        "cancelled_at",
        "external_docname",
        "external_docstatus",
    }
)

RETRYABLE_EXTERNAL_ERROR_CODES = frozenset(
    {
        "EXTERNAL_SERVICE_UNAVAILABLE",
        "ERPNEXT_SERVICE_UNAVAILABLE",
        "ERPNEXT_TIMEOUT",
        "DATABASE_WRITE_FAILED",
        "DATABASE_READ_FAILED",
    }
)

NON_RETRYABLE_ERROR_CODES = frozenset(
    {
        "AUTH_UNAUTHORIZED",
        "AUTH_UNAUTHENTICATED",
        "AUTH_FORBIDDEN",
        "PERMISSION_SOURCE_UNAVAILABLE",
        "RESOURCE_ACCESS_DENIED",
        "RESOURCE_NOT_FOUND",
        "ERPNEXT_AUTH_FAILED",
        "ERPNEXT_RESOURCE_NOT_FOUND",
        "ERPNEXT_DOCSTATUS_INVALID",
        "ERPNEXT_DOCSTATUS_REQUIRED",
        "ERPNEXT_RESPONSE_INVALID",
    }
)

_TRANSITIONS: dict[str, frozenset[str]] = {
    OUTBOX_STATUS_PENDING: frozenset({OUTBOX_STATUS_PROCESSING, OUTBOX_STATUS_CANCELLED}),
    OUTBOX_STATUS_PROCESSING: frozenset({OUTBOX_STATUS_SUCCEEDED, OUTBOX_STATUS_FAILED}),
    OUTBOX_STATUS_FAILED: frozenset({OUTBOX_STATUS_PENDING, OUTBOX_STATUS_DEAD, OUTBOX_STATUS_CANCELLED}),
    OUTBOX_STATUS_SUCCEEDED: frozenset(),
    OUTBOX_STATUS_DEAD: frozenset(),
    OUTBOX_STATUS_CANCELLED: frozenset(),
}


class OutboxStateMachineError(ValueError):
    """Outbox template error with explicit fail-closed code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ClaimLeaseEvaluation:
    """Pure claim/lease evaluation snapshot."""

    is_due: bool
    lease_expired: bool
    can_claim: bool


@dataclass(frozen=True)
class RetryDecision:
    """Retry decision after worker failure."""

    retryable: bool
    next_status: str
    next_retry_at: datetime | None
    reason: str


@dataclass(frozen=True)
class DryRunPreview:
    """Dry-run output contract; never mutates outbox state."""

    action: str
    event_key: str
    current_status: str
    target_status: str | None
    will_mutate: bool
    note: str | None


@dataclass(frozen=True)
class DiagnosticWindow:
    """Diagnostic cooldown tracking snapshot."""

    seen_count: int
    cooldown_seconds: int
    last_seen_at: datetime | None


def normalize_event_key_parts(
    parts: Mapping[str, Any],
    *,
    forbidden_fields: set[str] | frozenset[str] = FORBIDDEN_EVENT_KEY_FIELDS,
    max_inline_length: int = 96,
) -> dict[str, str]:
    """Normalize business facts for stable event_key hashing."""
    if not isinstance(parts, Mapping) or not parts:
        raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "event_key business facts are required")
    if max_inline_length < 16:
        raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "max_inline_length is too small")

    normalized: dict[str, str] = {}
    forbidden_lower = {str(key).strip().lower() for key in forbidden_fields}

    for raw_key, raw_value in parts.items():
        key = str(raw_key or "").strip()
        if not key:
            raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "event_key contains blank field name")
        if key.lower() in forbidden_lower:
            raise OutboxStateMachineError(
                OUTBOX_EVENT_KEY_INVALID,
                f"event_key contains forbidden mutable field: {key}",
            )
        rendered = _render_event_value(raw_value)
        if not rendered:
            raise OutboxStateMachineError(
                OUTBOX_EVENT_KEY_INVALID,
                f"event_key field '{key}' has empty value",
            )
        if len(rendered) > max_inline_length:
            rendered = f"sha256:{_sha256_hex(rendered)}"
        normalized[key] = rendered

    if not normalized:
        raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "event_key business facts are empty")

    return {key: normalized[key] for key in sorted(normalized)}


def build_event_key(
    parts: Mapping[str, Any],
    *,
    prefix: str = "outbox",
    forbidden_fields: set[str] | frozenset[str] = FORBIDDEN_EVENT_KEY_FIELDS,
    max_inline_length: int = 96,
) -> str:
    """Build deterministic event_key from stable business facts."""
    normalized = normalize_event_key_parts(
        parts,
        forbidden_fields=forbidden_fields,
        max_inline_length=max_inline_length,
    )
    canonical = "|".join(f"{key}={value}" for key, value in normalized.items())
    key_prefix = str(prefix or "").strip()
    if not key_prefix:
        raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "event_key prefix is required")
    return f"{key_prefix}:{_sha256_hex(canonical)}"


def canonical_payload_json(payload: Any) -> str:
    """Canonical JSON string for stable payload hashing."""
    canonical_value = _canonicalize_payload(payload)
    try:
        return json.dumps(
            canonical_value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OutboxStateMachineError(
            OUTBOX_PAYLOAD_INVALID,
            f"payload cannot be canonicalized: {exc}",
        ) from exc


def build_payload_hash(payload: Any) -> str:
    """Return sha256 over canonical payload JSON."""
    return _sha256_hex(canonical_payload_json(payload))


def is_terminal_status(status: str) -> bool:
    """Return whether status is terminal."""
    normalized = _normalize_status(status)
    return normalized in OUTBOX_TERMINAL_STATUSES


def can_transition(from_status: str, to_status: str) -> bool:
    """Return whether transition is allowed."""
    current = _normalize_status(from_status)
    target = _normalize_status(to_status)
    return target in _TRANSITIONS[current]


def validate_transition(from_status: str, to_status: str) -> None:
    """Fail closed if transition is invalid."""
    current = _normalize_status(from_status)
    target = _normalize_status(to_status)
    if target not in _TRANSITIONS[current]:
        raise OutboxStateMachineError(
            OUTBOX_TRANSITION_INVALID,
            f"invalid outbox transition: {current} -> {target}",
        )


def is_due(status: str, next_retry_at: datetime | None, *, now: datetime | None = None) -> bool:
    """True when pending/failed row is due."""
    current = _normalize_status(status)
    if current not in {OUTBOX_STATUS_PENDING, OUTBOX_STATUS_FAILED}:
        return False
    moment = now or datetime.now(timezone.utc)
    if next_retry_at is None:
        return True
    return _to_aware(next_retry_at) <= _to_aware(moment)


def is_lease_expired(status: str, locked_until: datetime | None, *, now: datetime | None = None) -> bool:
    """True when processing row lease has expired."""
    current = _normalize_status(status)
    if current != OUTBOX_STATUS_PROCESSING:
        return False
    if locked_until is None:
        return False
    moment = now or datetime.now(timezone.utc)
    return _to_aware(locked_until) < _to_aware(moment)


def can_claim(
    status: str,
    next_retry_at: datetime | None,
    locked_until: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """True when row can be claimed by worker."""
    moment = now or datetime.now(timezone.utc)
    return is_due(status, next_retry_at, now=moment) or is_lease_expired(status, locked_until, now=moment)


def evaluate_claim_lease(
    status: str,
    next_retry_at: datetime | None,
    locked_until: datetime | None,
    *,
    now: datetime | None = None,
) -> ClaimLeaseEvaluation:
    """Return detailed claim/lease evaluation snapshot."""
    moment = now or datetime.now(timezone.utc)
    due = is_due(status, next_retry_at, now=moment)
    expired = is_lease_expired(status, locked_until, now=moment)
    return ClaimLeaseEvaluation(is_due=due, lease_expired=expired, can_claim=(due or expired))


def build_claim_update_guard(
    status: str,
    next_retry_at: datetime | None,
    locked_until: datetime | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build second-phase update guard snapshot for claim_due."""
    evaluation = evaluate_claim_lease(status, next_retry_at, locked_until, now=now)
    return {
        "status": _normalize_status(status),
        "next_retry_at": next_retry_at,
        "locked_until": locked_until,
        "is_due": evaluation.is_due,
        "lease_expired": evaluation.lease_expired,
        "can_claim": evaluation.can_claim,
    }


def is_retryable_error(error_code: str | None) -> bool:
    """Return retryability under fail-closed defaults."""
    code = str(error_code or "").strip()
    if not code:
        return False
    if code in NON_RETRYABLE_ERROR_CODES:
        return False
    return code in RETRYABLE_EXTERNAL_ERROR_CODES


def compute_next_retry_at(
    *,
    attempts: int,
    now: datetime | None = None,
    base_backoff_seconds: int = 60,
    max_backoff_seconds: int = 3600,
) -> datetime:
    """Compute exponential backoff timestamp."""
    if attempts < 1:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, "attempts must be >= 1")
    if base_backoff_seconds < 1 or max_backoff_seconds < 1:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, "backoff seconds must be >= 1")
    if base_backoff_seconds > max_backoff_seconds:
        raise OutboxStateMachineError(
            OUTBOX_STATUS_INVALID,
            "base_backoff_seconds cannot exceed max_backoff_seconds",
        )
    moment = _to_aware(now or datetime.now(timezone.utc))
    delay = min(max_backoff_seconds, base_backoff_seconds * (2 ** max(0, attempts - 1)))
    return moment + timedelta(seconds=delay)


def decide_retry_transition(
    *,
    error_code: str | None,
    attempts: int,
    max_attempts: int,
    now: datetime | None = None,
    base_backoff_seconds: int = 60,
    max_backoff_seconds: int = 3600,
) -> RetryDecision:
    """Decide failed/dead transition after processing error."""
    if attempts < 1 or max_attempts < 1:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, "attempts and max_attempts must be >= 1")
    retryable = is_retryable_error(error_code)
    if not retryable:
        return RetryDecision(
            retryable=False,
            next_status=OUTBOX_STATUS_DEAD,
            next_retry_at=None,
            reason="non_retryable_error",
        )
    if attempts >= max_attempts:
        return RetryDecision(
            retryable=True,
            next_status=OUTBOX_STATUS_DEAD,
            next_retry_at=None,
            reason="max_attempts_reached",
        )
    next_retry_at = compute_next_retry_at(
        attempts=attempts,
        now=now,
        base_backoff_seconds=base_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
    )
    return RetryDecision(
        retryable=True,
        next_status=OUTBOX_STATUS_FAILED,
        next_retry_at=next_retry_at,
        reason="retry_scheduled",
    )


def build_dry_run_preview(
    *,
    action: str,
    event_key: str,
    current_status: str,
    target_status: str | None = None,
    note: str | None = None,
) -> DryRunPreview:
    """Return dry-run preview contract with explicit no-mutation flag."""
    if action not in OUTBOX_ACTIONS:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, f"unknown outbox action: {action}")
    _normalize_status(current_status)
    if target_status is not None:
        _normalize_status(target_status)
    if not str(event_key or "").strip():
        raise OutboxStateMachineError(OUTBOX_EVENT_KEY_INVALID, "event_key is required")
    return DryRunPreview(
        action=action,
        event_key=str(event_key).strip(),
        current_status=current_status,
        target_status=target_status,
        will_mutate=False,
        note=note,
    )


def evaluate_diagnostic_window(
    window: DiagnosticWindow,
    *,
    now: datetime | None = None,
) -> tuple[bool, DiagnosticWindow]:
    """Evaluate diagnostic cooldown and return (should_emit, next_window)."""
    if window.cooldown_seconds < 0:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, "cooldown_seconds cannot be negative")
    moment = _to_aware(now or datetime.now(timezone.utc))
    last_seen = _to_aware(window.last_seen_at) if window.last_seen_at else None
    next_seen_count = max(0, int(window.seen_count)) + 1

    if window.cooldown_seconds == 0:
        next_window = DiagnosticWindow(
            seen_count=next_seen_count,
            cooldown_seconds=window.cooldown_seconds,
            last_seen_at=moment,
        )
        return True, next_window

    if last_seen is None:
        next_window = DiagnosticWindow(
            seen_count=next_seen_count,
            cooldown_seconds=window.cooldown_seconds,
            last_seen_at=moment,
        )
        return True, next_window

    elapsed = (moment - last_seen).total_seconds()
    should_emit = elapsed >= window.cooldown_seconds
    next_window = DiagnosticWindow(
        seen_count=next_seen_count,
        cooldown_seconds=window.cooldown_seconds,
        last_seen_at=(moment if should_emit else last_seen),
    )
    return should_emit, next_window


def _normalize_status(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized not in OUTBOX_STATUSES:
        raise OutboxStateMachineError(OUTBOX_STATUS_INVALID, f"unknown outbox status: {status}")
    return normalized


def _render_event_value(value: Any) -> str:
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).strip()


def _canonicalize_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize_payload(value[key]) for key in sorted(value.keys(), key=lambda x: str(x))}
    if isinstance(value, list):
        return [_canonicalize_payload(item) for item in value]
    if isinstance(value, tuple):
        return {"__ly_type__": "tuple", "value": [_canonicalize_payload(item) for item in value]}
    if isinstance(value, set):
        canonical_items = [_canonicalize_payload(item) for item in value]
        return {"__ly_type__": "set", "value": sorted(canonical_items, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))}
    if isinstance(value, Decimal):
        return {"__ly_type__": "decimal", "value": format(value, "f")}
    if isinstance(value, datetime):
        return {"__ly_type__": "datetime", "value": _format_datetime(value)}
    if isinstance(value, date):
        return {"__ly_type__": "date", "value": value.isoformat()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise OutboxStateMachineError(
        OUTBOX_PAYLOAD_INVALID,
        f"unsupported payload type: {type(value).__name__}",
    )


def _format_datetime(value: datetime) -> str:
    aware = _to_aware(value)
    if aware.tzinfo == timezone.utc:
        return aware.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return aware.isoformat(timespec="microseconds")


def _to_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = [
    "ClaimLeaseEvaluation",
    "DiagnosticWindow",
    "DryRunPreview",
    "FORBIDDEN_EVENT_KEY_FIELDS",
    "NON_RETRYABLE_ERROR_CODES",
    "OUTBOX_ACTIONS",
    "OUTBOX_ACTION_GENERIC",
    "OUTBOX_ACTION_JOB_CARD_SYNC",
    "OUTBOX_ACTION_PURCHASE_INVOICE_DRAFT",
    "OUTBOX_ACTION_STOCK_ISSUE",
    "OUTBOX_ACTION_STOCK_RECEIPT",
    "OUTBOX_ACTION_WORK_ORDER_CREATE",
    "OUTBOX_EVENT_KEY_INVALID",
    "OUTBOX_PAYLOAD_INVALID",
    "RETRYABLE_EXTERNAL_ERROR_CODES",
    "OUTBOX_STATUSES",
    "OUTBOX_STATUS_CANCELLED",
    "OUTBOX_STATUS_DEAD",
    "OUTBOX_STATUS_FAILED",
    "OUTBOX_STATUS_INVALID",
    "OUTBOX_STATUS_PENDING",
    "OUTBOX_STATUS_PROCESSING",
    "OUTBOX_STATUS_SUCCEEDED",
    "OUTBOX_TERMINAL_STATUSES",
    "OUTBOX_TRANSITION_INVALID",
    "OutboxStateMachineError",
    "RetryDecision",
    "build_claim_update_guard",
    "build_dry_run_preview",
    "build_event_key",
    "build_payload_hash",
    "can_claim",
    "can_transition",
    "canonical_payload_json",
    "compute_next_retry_at",
    "decide_retry_transition",
    "evaluate_claim_lease",
    "evaluate_diagnostic_window",
    "is_due",
    "is_lease_expired",
    "is_retryable_error",
    "is_terminal_status",
    "normalize_event_key_parts",
    "validate_transition",
]
