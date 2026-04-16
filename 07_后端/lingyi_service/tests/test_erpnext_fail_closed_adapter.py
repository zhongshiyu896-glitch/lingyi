"""TASK-008B tests for ERPNext fail-closed adapter helpers."""

from __future__ import annotations

import socket
import urllib.error

from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_fail_closed_adapter import is_retryable_erpnext_error
from app.services.erpnext_fail_closed_adapter import map_erpnext_exception
from app.services.erpnext_fail_closed_adapter import normalize_erpnext_response
from app.services.erpnext_fail_closed_adapter import require_submitted_doc


def test_normalize_standard_data_wrapper() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": 1, "status": "Submitted"}},
    )
    assert normalized.doctype == "Sales Order"
    assert normalized.name == "SO-001"
    assert normalized.docstatus == 1
    assert normalized.status == "Submitted"
    assert normalized.source == "erpnext"
    assert normalized.validated is False


def test_normalize_direct_document_dict() -> None:
    normalized = normalize_erpnext_response(
        {"doctype": "Purchase Invoice", "name": "PINV-001", "docstatus": "0", "status": "Draft"},
    )
    assert normalized.doctype == "Purchase Invoice"
    assert normalized.docstatus == 0
    assert normalized.status == "Draft"


def test_normalize_accepts_exact_docstatus_literals() -> None:
    ok_values = (0, 1, 2, "0", "1", "2")
    for value in ok_values:
        normalized = normalize_erpnext_response(
            {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": value, "status": "Submitted"}},
        )
        assert normalized.docstatus in {0, 1, 2}


def test_normalize_rejects_malformed_docstatus_literals() -> None:
    bad_values = (
        True,
        False,
        1.2,
        0.0,
        "",
        " ",
        "01",
        "1.0",
        "submitted",
        None,
        [],
        {},
    )
    for value in bad_values:
        try:
            normalize_erpnext_response(
                {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": value, "status": "Submitted"}},
            )
        except ERPNextAdapterException as exc:
            assert exc.error_code == "ERPNEXT_DOCSTATUS_INVALID"
            assert exc.http_status == 409
        else:  # pragma: no cover
            raise AssertionError(f"expected ERPNEXT_DOCSTATUS_INVALID for value={value!r}")


def test_normalize_list_response_for_list_mode() -> None:
    normalized = normalize_erpnext_response(
        {"data": [{"name": "SE-001"}, {"name": "SE-002"}]},
        doctype="Stock Entry",
        allow_list=True,
    )
    assert normalized.doctype == "Stock Entry"
    assert isinstance(normalized.data, list)
    assert len(normalized.data) == 2


def test_normalize_malformed_response_fail_closed() -> None:
    try:
        normalize_erpnext_response({"data": "not-dict-and-not-list"})
    except ERPNextAdapterException as exc:
        assert exc.error_code == "ERPNEXT_RESPONSE_INVALID"
        assert exc.http_status == 502
    else:  # pragma: no cover
        raise AssertionError("expected ERPNEXT_RESPONSE_INVALID")


def test_require_submitted_doc_docstatus_1_passes() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": 1, "status": "Submitted"}},
    )
    validated = require_submitted_doc(normalized)
    assert validated.validated is True
    assert validated.docstatus == 1


def test_require_submitted_doc_docstatus_0_fails() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": 0, "status": "Draft"}},
    )
    try:
        require_submitted_doc(normalized)
    except ERPNextAdapterException as exc:
        assert exc.error_code == "ERPNEXT_DOCSTATUS_INVALID"
        assert exc.http_status == 409
    else:  # pragma: no cover
        raise AssertionError("expected ERPNEXT_DOCSTATUS_INVALID")


def test_require_submitted_doc_docstatus_2_fails() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "docstatus": 2, "status": "Cancelled"}},
    )
    try:
        require_submitted_doc(normalized)
    except ERPNextAdapterException as exc:
        assert exc.error_code == "ERPNEXT_DOCSTATUS_INVALID"
        assert exc.http_status == 409
    else:  # pragma: no cover
        raise AssertionError("expected ERPNEXT_DOCSTATUS_INVALID")


def test_missing_docstatus_fail_closed() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "status": "Submitted"}},
    )
    try:
        require_submitted_doc(normalized)
    except ERPNextAdapterException as exc:
        assert exc.error_code == "ERPNEXT_DOCSTATUS_REQUIRED"
        assert exc.http_status == 409
    else:  # pragma: no cover
        raise AssertionError("expected ERPNEXT_DOCSTATUS_REQUIRED")


def test_status_only_not_whitelisted_fails() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Sales Order", "name": "SO-001", "status": "Submitted"}},
    )
    try:
        require_submitted_doc(normalized, status_only_whitelist={"Delivery Note": {"submitted"}})
    except ERPNextAdapterException as exc:
        assert exc.error_code == "ERPNEXT_DOCSTATUS_REQUIRED"
    else:  # pragma: no cover
        raise AssertionError("expected fail-closed for missing whitelist")


def test_status_only_whitelisted_doctype_passes() -> None:
    normalized = normalize_erpnext_response(
        {"data": {"doctype": "Custom Doc", "name": "CD-001", "status": "Submitted"}},
    )
    validated = require_submitted_doc(
        normalized,
        status_only_whitelist={"Custom Doc": {"submitted"}},
    )
    assert validated.validated is True
    assert validated.status == "Submitted"


def test_map_timeout_to_erpnext_timeout() -> None:
    mapped = map_erpnext_exception(TimeoutError("operation timed out"), doctype="Item", resource_name="ITEM-001")
    assert mapped.error_code == "ERPNEXT_TIMEOUT"
    assert mapped.http_status == 503
    assert mapped.retryable is True
    assert is_retryable_erpnext_error(mapped.error_code) is True


def test_map_connection_error_to_external_unavailable() -> None:
    mapped = map_erpnext_exception(urllib.error.URLError("connection reset"))
    assert mapped.error_code == "EXTERNAL_SERVICE_UNAVAILABLE"
    assert mapped.http_status == 503
    assert mapped.retryable is True


def test_map_http_401_403_to_auth_failed() -> None:
    e401 = urllib.error.HTTPError(url="http://example.test", code=401, msg="unauthorized", hdrs=None, fp=None)
    e403 = urllib.error.HTTPError(url="http://example.test", code=403, msg="forbidden", hdrs=None, fp=None)
    m401 = map_erpnext_exception(e401)
    m403 = map_erpnext_exception(e403)
    assert m401.error_code == "ERPNEXT_AUTH_FAILED"
    assert m403.error_code == "ERPNEXT_AUTH_FAILED"
    assert m401.http_status == 503
    assert m403.http_status == 503


def test_map_http_404_to_resource_not_found() -> None:
    e404 = urllib.error.HTTPError(url="http://example.test", code=404, msg="missing", hdrs=None, fp=None)
    mapped = map_erpnext_exception(e404, doctype="Supplier", resource_name="SUP-001")
    assert mapped.error_code == "ERPNEXT_RESOURCE_NOT_FOUND"
    assert mapped.http_status == 404
    assert mapped.doctype == "Supplier"
    assert mapped.resource_name == "SUP-001"


def test_map_http_5xx_to_external_unavailable_retryable() -> None:
    e503 = urllib.error.HTTPError(url="http://example.test", code=503, msg="down", hdrs=None, fp=None)
    mapped = map_erpnext_exception(e503)
    assert mapped.error_code == "EXTERNAL_SERVICE_UNAVAILABLE"
    assert mapped.http_status == 503
    assert mapped.retryable is True


def test_sensitive_detail_is_redacted_in_safe_message() -> None:
    exc = RuntimeError(
        "Authorization=Bearer abc Cookie=sid=1 token=abc secret=xyz password=123 DSN=postgres://u:p@h/db"
    )
    mapped = map_erpnext_exception(exc)
    lowered = (mapped.safe_message or "").lower()
    assert "authorization" not in lowered
    assert "cookie" not in lowered
    assert "token" not in lowered
    assert "secret" not in lowered
    assert "password" not in lowered
    assert "dsn" not in lowered


def test_socket_timeout_maps_to_timeout_code() -> None:
    mapped = map_erpnext_exception(socket.timeout("timed out"))
    assert mapped.error_code == "ERPNEXT_TIMEOUT"
    assert mapped.retryable is True
