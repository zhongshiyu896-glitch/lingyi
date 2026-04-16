"""TASK-007B error-code baseline tests."""

from __future__ import annotations

import unittest

from app.core.error_codes import AUDIT_WRITE_FAILED
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import INTERNAL_API_FORBIDDEN
from app.core.error_codes import REQUEST_ID_REJECTED
from app.core.error_codes import INTERNAL_ERROR
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import RESOURCE_NOT_FOUND
from app.core.error_codes import RESOURCE_SCOPE_FIELD_UNKNOWN
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AuthUnauthenticatedError
from app.core.exceptions import ExternalServiceUnavailableError
from app.core.exceptions import InternalError
from app.core.exceptions import ResourceAccessDeniedError
from app.core.exceptions import ResourceNotFoundError


class ErrorEnvelopeBaselineTest(unittest.TestCase):
    """Validate core fail-closed status/code mapping for TASK-007B."""

    def test_core_fail_closed_status_mapping(self) -> None:
        self.assertEqual(status_of("AUTH_UNAUTHENTICATED"), 401)
        self.assertEqual(status_of("AUTH_FORBIDDEN"), 403)
        self.assertEqual(status_of(RESOURCE_ACCESS_DENIED), 403)
        self.assertEqual(status_of(PERMISSION_SOURCE_UNAVAILABLE), 503)
        self.assertEqual(status_of(RESOURCE_NOT_FOUND), 404)
        self.assertEqual(status_of(RESOURCE_SCOPE_FIELD_UNKNOWN), 500)
        self.assertEqual(status_of(EXTERNAL_SERVICE_UNAVAILABLE), 503)
        self.assertEqual(status_of(INTERNAL_API_FORBIDDEN), 403)
        self.assertEqual(status_of(REQUEST_ID_REJECTED), 400)
        self.assertEqual(status_of(DATABASE_READ_FAILED), 500)
        self.assertEqual(status_of(DATABASE_WRITE_FAILED), 500)
        self.assertEqual(status_of(AUDIT_WRITE_FAILED), 500)
        self.assertEqual(status_of(INTERNAL_ERROR), 500)

    def test_failures_never_map_to_http_200(self) -> None:
        codes = {
            "AUTH_UNAUTHENTICATED",
            "AUTH_FORBIDDEN",
            RESOURCE_ACCESS_DENIED,
            PERMISSION_SOURCE_UNAVAILABLE,
            RESOURCE_NOT_FOUND,
            RESOURCE_SCOPE_FIELD_UNKNOWN,
            EXTERNAL_SERVICE_UNAVAILABLE,
            INTERNAL_API_FORBIDDEN,
            REQUEST_ID_REJECTED,
            DATABASE_READ_FAILED,
            DATABASE_WRITE_FAILED,
            AUDIT_WRITE_FAILED,
            INTERNAL_ERROR,
        }
        for code in codes:
            self.assertNotEqual(status_of(code), 200, msg=f"{code} must not map to 200")

    def test_new_exception_classes_bind_code_and_status(self) -> None:
        unauth = AuthUnauthenticatedError()
        denied = ResourceAccessDeniedError()
        not_found = ResourceNotFoundError()
        ext_unavailable = ExternalServiceUnavailableError()
        internal = InternalError()

        self.assertEqual(unauth.code, "AUTH_UNAUTHENTICATED")
        self.assertEqual(unauth.status_code, 401)
        self.assertEqual(denied.code, RESOURCE_ACCESS_DENIED)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(not_found.code, RESOURCE_NOT_FOUND)
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(ext_unavailable.code, EXTERNAL_SERVICE_UNAVAILABLE)
        self.assertEqual(ext_unavailable.status_code, 503)
        self.assertEqual(internal.code, INTERNAL_ERROR)
        self.assertEqual(internal.status_code, 500)

    def test_default_messages_present(self) -> None:
        self.assertEqual(message_of("AUTH_UNAUTHENTICATED"), "未认证或登录已过期")
        self.assertEqual(message_of(RESOURCE_ACCESS_DENIED), "资源权限不足，禁止访问")
        self.assertEqual(message_of(PERMISSION_SOURCE_UNAVAILABLE), "权限来源暂时不可用")


if __name__ == "__main__":
    unittest.main()
