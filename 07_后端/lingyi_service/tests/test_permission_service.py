"""Unit tests for permission aggregation logic."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

# Ensure env-dependent settings are stable for both pytest and unittest discover.
os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi import HTTPException
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import CurrentUser
from app.core.exceptions import PermissionSourceUnavailable
from app.core.permissions import PERMISSION_SOURCE_UNAVAILABLE_CODE
from app.models.audit import Base as AuditBase
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.permission_service import PermissionService


def _build_request() -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class PermissionAggregationTest(unittest.TestCase):
    """Cover role-based aggregation for Sprint 1 static source."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._old_source = os.getenv("LINGYI_PERMISSION_SOURCE")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        engine = create_engine(
            "sqlite://",
            future=True,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        AuditBase.metadata.create_all(bind=engine)
        cls._SessionLocal = sessionmaker(bind=engine, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._old_source is None:
            os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
        else:
            os.environ["LINGYI_PERMISSION_SOURCE"] = cls._old_source

    def _service(self) -> PermissionService:
        return PermissionService(session=self._SessionLocal())

    def test_system_manager_actions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="sys.manager",
                roles=["System Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="bom",
        )
        expected = {
            "bom:read",
            "bom:create",
            "bom:update",
            "bom:publish",
            "bom:submit",
            "bom:deactivate",
            "bom:cancel",
            "bom:set_default",
        }
        self.assertEqual(set(agg.actions), expected)

    def test_bom_editor_actions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="bom.editor",
                roles=["BOM Editor"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="bom",
        )
        self.assertEqual(set(agg.actions), {"bom:read", "bom:create", "bom:update"})

    def test_bom_publisher_actions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="bom.publisher",
                roles=["BOM Publisher"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="bom",
        )
        self.assertEqual(
            set(agg.actions),
            {"bom:read", "bom:publish", "bom:submit", "bom:deactivate", "bom:cancel", "bom:set_default"},
        )

    def test_no_permission_user_actions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="anonymous",
                roles=[],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="bom",
        )
        self.assertEqual(set(agg.actions), set())


class PermissionServiceFailClosedTest(unittest.TestCase):
    """Cover fail-closed behavior for ERPNext permission source."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._old_source = os.getenv("LINGYI_PERMISSION_SOURCE")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        engine = create_engine(
            "sqlite://",
            future=True,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        AuditBase.metadata.create_all(bind=engine)
        cls._SessionLocal = sessionmaker(bind=engine, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._old_source is None:
            os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
        else:
            os.environ["LINGYI_PERMISSION_SOURCE"] = cls._old_source

    def _service(self) -> PermissionService:
        return PermissionService(session=self._SessionLocal())

    def test_get_actions_fail_closed_on_permission_source_unavailable(self) -> None:
        current_user = CurrentUser(
            username="reader.user",
            roles=["BOM Editor"],
            is_service_account=False,
            source="dev_header",
        )
        request_obj = _build_request()
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="request timeout",
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                self._service().get_actions(current_user=current_user, request_obj=request_obj, module="bom")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail["code"], PERMISSION_SOURCE_UNAVAILABLE_CODE)

    def test_get_readable_item_codes_unrestricted_when_query_succeeds_with_zero_rows(self) -> None:
        current_user = CurrentUser(
            username="reader.user",
            roles=["BOM Editor"],
            is_service_account=False,
            source="dev_header",
        )
        request_obj = _build_request()
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=True,
                allowed_items=set(),
                allowed_companies=set(),
            ),
        ):
            readable = self._service().get_readable_item_codes(current_user=current_user, request_obj=request_obj)
        self.assertIsNone(readable)


if __name__ == "__main__":
    unittest.main()
