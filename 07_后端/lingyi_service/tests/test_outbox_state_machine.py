"""TASK-009B tests for shared outbox state machine helpers."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal

import pytest

from app.services.outbox_state_machine import DiagnosticWindow
from app.services.outbox_state_machine import OUTBOX_ACTION_GENERIC
from app.services.outbox_state_machine import OUTBOX_EVENT_KEY_INVALID
from app.services.outbox_state_machine import OUTBOX_PAYLOAD_INVALID
from app.services.outbox_state_machine import OUTBOX_STATUS_CANCELLED
from app.services.outbox_state_machine import OUTBOX_STATUS_DEAD
from app.services.outbox_state_machine import OUTBOX_STATUS_FAILED
from app.services.outbox_state_machine import OUTBOX_STATUS_PENDING
from app.services.outbox_state_machine import OUTBOX_STATUS_PROCESSING
from app.services.outbox_state_machine import OUTBOX_STATUS_SUCCEEDED
from app.services.outbox_state_machine import OUTBOX_TRANSITION_INVALID
from app.services.outbox_state_machine import OutboxStateMachineError
from app.services.outbox_state_machine import build_claim_update_guard
from app.services.outbox_state_machine import build_dry_run_preview
from app.services.outbox_state_machine import build_event_key
from app.services.outbox_state_machine import build_payload_hash
from app.services.outbox_state_machine import can_claim
from app.services.outbox_state_machine import can_transition
from app.services.outbox_state_machine import compute_next_retry_at
from app.services.outbox_state_machine import decide_retry_transition
from app.services.outbox_state_machine import evaluate_claim_lease
from app.services.outbox_state_machine import evaluate_diagnostic_window
from app.services.outbox_state_machine import is_due
from app.services.outbox_state_machine import is_lease_expired
from app.services.outbox_state_machine import is_retryable_error
from app.services.outbox_state_machine import normalize_event_key_parts
from app.services.outbox_state_machine import validate_transition


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_event_key_is_stable_for_same_business_facts() -> None:
    parts_a = {
        "aggregate_type": "factory_statement",
        "aggregate_id": "123",
        "action": "purchase_invoice_draft",
        "net_amount": "4700.00",
    }
    parts_b = {
        "action": "purchase_invoice_draft",
        "net_amount": "4700.00",
        "aggregate_id": "123",
        "aggregate_type": "factory_statement",
    }
    key_a = build_event_key(parts_a, prefix="fspo")
    key_b = build_event_key(parts_b, prefix="fspo")
    assert key_a == key_b


def test_event_key_changes_when_business_facts_change() -> None:
    key_a = build_event_key({"aggregate_id": "123", "action": "stock_issue"}, prefix="obx")
    key_b = build_event_key({"aggregate_id": "124", "action": "stock_issue"}, prefix="obx")
    assert key_a != key_b


@pytest.mark.parametrize(
    "forbidden_field",
    ["idempotency_key", "request_id", "outbox_id", "created_at", "operator", "created_by"],
)
def test_event_key_rejects_forbidden_mutable_fields(forbidden_field: str) -> None:
    payload = {"aggregate_id": "123", forbidden_field: "x"}
    with pytest.raises(OutboxStateMachineError) as exc_info:
        build_event_key(payload)
    assert exc_info.value.code == OUTBOX_EVENT_KEY_INVALID


@pytest.mark.parametrize(
    "forbidden_field",
    [
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
    ],
)
def test_build_event_key_rejects_runtime_fields(forbidden_field: str) -> None:
    payload = {
        "aggregate_id": "123",
        "aggregate_type": "factory_statement",
        forbidden_field: "runtime-state-should-not-participate",
    }
    with pytest.raises(OutboxStateMachineError) as exc_info:
        build_event_key(payload)
    assert exc_info.value.code == OUTBOX_EVENT_KEY_INVALID
    # Fail closed without leaking runtime value content.
    assert "runtime-state-should-not-participate" not in str(exc_info.value)


def test_event_key_hashes_long_fields_before_concat() -> None:
    long_supplier = "SUP-" + ("A" * 256)
    normalized = normalize_event_key_parts(
        {
            "supplier": long_supplier,
            "aggregate_id": "123",
        },
        max_inline_length=32,
    )
    assert normalized["supplier"].startswith("sha256:")
    assert long_supplier not in normalized["supplier"]
    event_key = build_event_key(
        {
            "supplier": long_supplier,
            "aggregate_id": "123",
        },
        max_inline_length=32,
    )
    assert event_key.startswith("outbox:")


def test_event_key_rejects_empty_business_facts() -> None:
    with pytest.raises(OutboxStateMachineError) as exc_info:
        build_event_key({})
    assert exc_info.value.code == OUTBOX_EVENT_KEY_INVALID


def test_payload_hash_is_order_insensitive_for_dict_keys() -> None:
    payload_a = {"a": 1, "b": {"x": 2, "y": 3}}
    payload_b = {"b": {"y": 3, "x": 2}, "a": 1}
    assert build_payload_hash(payload_a) == build_payload_hash(payload_b)


def test_payload_hash_decimal_date_datetime_stable() -> None:
    payload = {
        "amount": Decimal("4700.00"),
        "posting_date": date(2026, 4, 16),
        "confirmed_at": _utc("2026-04-16T08:30:00Z"),
    }
    assert build_payload_hash(payload) == build_payload_hash(payload)


def test_payload_hash_distinguishes_decimal_vs_float_vs_string() -> None:
    decimal_hash = build_payload_hash({"amount": Decimal("1.20")})
    float_hash = build_payload_hash({"amount": 1.2})
    string_hash = build_payload_hash({"amount": "1.20"})
    assert decimal_hash != float_hash
    assert decimal_hash != string_hash
    assert float_hash != string_hash


def test_payload_hash_distinguishes_none_and_missing_field() -> None:
    with_none = build_payload_hash({"remark": None, "id": 1})
    without_field = build_payload_hash({"id": 1})
    assert with_none != without_field


def test_payload_hash_changes_when_payload_changes() -> None:
    hash_a = build_payload_hash({"net_amount": "4700.00"})
    hash_b = build_payload_hash({"net_amount": "4700.01"})
    assert hash_a != hash_b


def test_payload_hash_rejects_unsupported_types_fail_closed() -> None:
    with pytest.raises(OutboxStateMachineError) as exc_info:
        build_payload_hash({"obj": object()})
    assert exc_info.value.code == OUTBOX_PAYLOAD_INVALID


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (OUTBOX_STATUS_PENDING, OUTBOX_STATUS_PROCESSING),
        (OUTBOX_STATUS_PROCESSING, OUTBOX_STATUS_SUCCEEDED),
        (OUTBOX_STATUS_PROCESSING, OUTBOX_STATUS_FAILED),
        (OUTBOX_STATUS_FAILED, OUTBOX_STATUS_PENDING),
        (OUTBOX_STATUS_FAILED, OUTBOX_STATUS_DEAD),
        (OUTBOX_STATUS_PENDING, OUTBOX_STATUS_CANCELLED),
        (OUTBOX_STATUS_FAILED, OUTBOX_STATUS_CANCELLED),
    ],
)
def test_legal_state_transitions_pass(from_status: str, to_status: str) -> None:
    assert can_transition(from_status, to_status) is True
    validate_transition(from_status, to_status)


def test_succeeded_is_terminal_state() -> None:
    assert can_transition(OUTBOX_STATUS_SUCCEEDED, OUTBOX_STATUS_PROCESSING) is False
    with pytest.raises(OutboxStateMachineError) as exc_info:
        validate_transition(OUTBOX_STATUS_SUCCEEDED, OUTBOX_STATUS_PROCESSING)
    assert exc_info.value.code == OUTBOX_TRANSITION_INVALID


def test_cancelled_is_terminal_state() -> None:
    assert can_transition(OUTBOX_STATUS_CANCELLED, OUTBOX_STATUS_PENDING) is False
    with pytest.raises(OutboxStateMachineError) as exc_info:
        validate_transition(OUTBOX_STATUS_CANCELLED, OUTBOX_STATUS_PENDING)
    assert exc_info.value.code == OUTBOX_TRANSITION_INVALID


def test_dead_state_is_not_auto_retryable_transition() -> None:
    assert can_transition(OUTBOX_STATUS_DEAD, OUTBOX_STATUS_PENDING) is False


def test_pending_due_can_be_claimed() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    assert is_due(OUTBOX_STATUS_PENDING, now, now=now) is True
    assert can_claim(OUTBOX_STATUS_PENDING, now, None, now=now) is True


def test_failed_due_can_be_claimed() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    assert is_due(OUTBOX_STATUS_FAILED, now - timedelta(seconds=1), now=now) is True
    assert can_claim(OUTBOX_STATUS_FAILED, now - timedelta(seconds=1), None, now=now) is True


def test_pending_not_due_cannot_be_claimed() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    assert is_due(OUTBOX_STATUS_PENDING, now + timedelta(minutes=5), now=now) is False
    assert can_claim(OUTBOX_STATUS_PENDING, now + timedelta(minutes=5), None, now=now) is False


def test_processing_lease_expired_can_be_claimed() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    assert is_lease_expired(OUTBOX_STATUS_PROCESSING, now - timedelta(seconds=1), now=now) is True
    assert can_claim(
        OUTBOX_STATUS_PROCESSING,
        next_retry_at=None,
        locked_until=now - timedelta(seconds=1),
        now=now,
    ) is True


def test_processing_unexpired_lease_cannot_be_claimed_stale_guard() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    assert is_lease_expired(OUTBOX_STATUS_PROCESSING, now + timedelta(seconds=30), now=now) is False
    assert can_claim(
        OUTBOX_STATUS_PROCESSING,
        next_retry_at=None,
        locked_until=now + timedelta(seconds=30),
        now=now,
    ) is False
    guard = build_claim_update_guard(
        OUTBOX_STATUS_PROCESSING,
        next_retry_at=None,
        locked_until=now + timedelta(seconds=30),
        now=now,
    )
    assert guard["can_claim"] is False


def test_claim_lease_evaluation_contains_all_flags() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    evaluation = evaluate_claim_lease(
        OUTBOX_STATUS_FAILED,
        next_retry_at=now - timedelta(minutes=1),
        locked_until=None,
        now=now,
    )
    assert evaluation.is_due is True
    assert evaluation.lease_expired is False
    assert evaluation.can_claim is True


def test_retryable_external_error_schedules_retry() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    decision = decide_retry_transition(
        error_code="EXTERNAL_SERVICE_UNAVAILABLE",
        attempts=1,
        max_attempts=5,
        now=now,
        base_backoff_seconds=60,
        max_backoff_seconds=3600,
    )
    assert decision.retryable is True
    assert decision.next_status == OUTBOX_STATUS_FAILED
    assert decision.next_retry_at is not None
    assert decision.next_retry_at > now


def test_non_retryable_error_goes_dead() -> None:
    decision = decide_retry_transition(
        error_code="ERPNEXT_AUTH_FAILED",
        attempts=1,
        max_attempts=5,
    )
    assert decision.retryable is False
    assert decision.next_status == OUTBOX_STATUS_DEAD
    assert decision.next_retry_at is None


def test_retryable_error_reaches_dead_at_max_attempts() -> None:
    decision = decide_retry_transition(
        error_code="ERPNEXT_TIMEOUT",
        attempts=5,
        max_attempts=5,
    )
    assert decision.retryable is True
    assert decision.next_status == OUTBOX_STATUS_DEAD
    assert decision.next_retry_at is None


def test_retry_classifier_auth_permission_resource_are_non_retryable() -> None:
    assert is_retryable_error("ERPNEXT_AUTH_FAILED") is False
    assert is_retryable_error("PERMISSION_SOURCE_UNAVAILABLE") is False
    assert is_retryable_error("RESOURCE_ACCESS_DENIED") is False


def test_retry_classifier_external_unavailable_is_retryable() -> None:
    assert is_retryable_error("EXTERNAL_SERVICE_UNAVAILABLE") is True
    assert is_retryable_error("ERPNEXT_TIMEOUT") is True


def test_compute_next_retry_at_uses_backoff() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    first = compute_next_retry_at(attempts=1, now=now, base_backoff_seconds=30, max_backoff_seconds=120)
    third = compute_next_retry_at(attempts=3, now=now, base_backoff_seconds=30, max_backoff_seconds=120)
    assert first == now + timedelta(seconds=30)
    assert third == now + timedelta(seconds=120)


def test_dry_run_preview_never_mutates_state() -> None:
    preview = build_dry_run_preview(
        action=OUTBOX_ACTION_GENERIC,
        event_key="outbox:abc",
        current_status=OUTBOX_STATUS_PENDING,
        target_status=OUTBOX_STATUS_PROCESSING,
        note="dry-run only",
    )
    assert preview.will_mutate is False
    assert preview.current_status == OUTBOX_STATUS_PENDING


def test_diagnostic_window_cooldown_blocks_repeated_emit() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    window = DiagnosticWindow(seen_count=0, cooldown_seconds=60, last_seen_at=now)
    should_emit, next_window = evaluate_diagnostic_window(window, now=now + timedelta(seconds=10))
    assert should_emit is False
    assert next_window.seen_count == 1
    assert next_window.last_seen_at == now


def test_diagnostic_window_emits_after_cooldown() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    window = DiagnosticWindow(seen_count=3, cooldown_seconds=60, last_seen_at=now)
    should_emit, next_window = evaluate_diagnostic_window(window, now=now + timedelta(seconds=61))
    assert should_emit is True
    assert next_window.seen_count == 4
    assert next_window.last_seen_at == now + timedelta(seconds=61)


def test_diagnostic_window_seen_count_increments() -> None:
    now = _utc("2026-04-16T10:00:00Z")
    window = DiagnosticWindow(seen_count=5, cooldown_seconds=0, last_seen_at=None)
    should_emit, next_window = evaluate_diagnostic_window(window, now=now)
    assert should_emit is True
    assert next_window.seen_count == 6
    assert next_window.last_seen_at == now
