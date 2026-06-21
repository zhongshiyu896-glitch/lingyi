"""Unit tests for permission aggregation logic."""

from __future__ import annotations

import os
import json
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
from app.services.permission_service import FASTAPI_ROLE_ACTIONS_ENV


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

    def test_warehouse_manager_button_permissions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="warehouse.manager",
                roles=["Warehouse Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="warehouse",
        )
        self.assertIn("warehouse:stock_entry_draft", agg.actions)
        self.assertIn("warehouse:stock_entry_cancel", agg.actions)
        self.assertTrue(agg.button_permissions["read"])
        self.assertTrue(agg.button_permissions["create"])
        self.assertTrue(agg.button_permissions["cancel"])
        self.assertTrue(agg.button_permissions["export"])
        self.assertTrue(agg.button_permissions["diagnostic"])
        self.assertTrue(agg.button_permissions["worker"])
        self.assertTrue(agg.button_permissions["stock_entry_draft"])
        self.assertTrue(agg.button_permissions["stock_entry_cancel"])
        self.assertTrue(agg.button_permissions["inventory_count"])

    def test_subcontract_manager_can_open_factory_return_material_stock_actions(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="subcontract.manager",
                roles=["Subcontract Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="warehouse",
        )
        self.assertIn("warehouse:read", agg.actions)
        self.assertIn("warehouse:stock_entry_draft", agg.actions)
        self.assertTrue(agg.button_permissions["read"])
        self.assertTrue(agg.button_permissions["stock_entry_draft"])
        self.assertFalse(agg.button_permissions["stock_entry_cancel"])

    def test_business_module_button_permissions_are_projected(self) -> None:
        cases = [
            (
                "sales_inventory",
                "Sales Manager",
                {
                    "read": True,
                    "write": True,
                    "create": True,
                    "update": True,
                    "export": True,
                    "sales_inventory_write": True,
                },
            ),
            (
                "master_data",
                "Master Data Manager",
                {"read": True, "manage": True, "create": True, "update": True, "master_data_manage": True},
            ),
            (
                "sample",
                "Sample Manager",
                {"read": True, "manage": True, "create": True, "update": True, "sample_manage": True},
            ),
            (
                "style_master",
                "Style Manager",
                {"read": True, "manage": True, "create": True, "update": True, "deactivate": True, "write": True},
            ),
            (
                "material_purchase",
                "Purchasing Manager",
                {"read": True, "write": True, "create": True, "update": True, "material_purchase_write": True},
            ),
            (
                "report",
                "System Manager",
                {"read": True, "export": True, "diagnostic": True, "report_export": True},
            ),
        ]
        for module, role, expected_permissions in cases:
            with self.subTest(module=module):
                agg = self._service().get_actions(
                    current_user=CurrentUser(
                        username=f"{module}.user",
                        roles=[role],
                        is_service_account=False,
                        source="dev_header",
                    ),
                    request_obj=_build_request(),
                    module=module,
                )
                for key, expected in expected_permissions.items():
                    self.assertIs(agg.button_permissions[key], expected)

    def test_factory_statement_payment_button_permission(self) -> None:
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="finance.manager",
                roles=["Finance Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="factory_statement",
        )
        self.assertIn("factory_statement:payment_create", agg.actions)
        self.assertTrue(agg.button_permissions["payment_create"])
        self.assertTrue(agg.button_permissions["factory_statement_payment_create"])


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


class PermissionServiceFastApiActionsTest(unittest.TestCase):
    """Cover FastAPI-native action aggregation without static fallback."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._old_source = os.getenv("LINGYI_PERMISSION_SOURCE")
        cls._old_role_actions = os.getenv(FASTAPI_ROLE_ACTIONS_ENV)
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
        if cls._old_role_actions is None:
            os.environ.pop(FASTAPI_ROLE_ACTIONS_ENV, None)
        else:
            os.environ[FASTAPI_ROLE_ACTIONS_ENV] = cls._old_role_actions

    def _service(self) -> PermissionService:
        return PermissionService(session=self._SessionLocal())

    @staticmethod
    def _current_user(*, username: str = "fastapi.user", roles: list[str] | None = None) -> CurrentUser:
        return CurrentUser(
            username=username,
            roles=roles or [],
            is_service_account=False,
            source="dev_header",
        )

    def test_fastapi_actions_use_native_role_config_without_erpnext(self) -> None:
        payload = {
            "roles": {
                "BOM Editor": ["bom:read", "bom:submit"],
                "Style Viewer": {"actions": ["style_master:read"]},
            },
            "users": {
                "fastapi.user": ["bom:update"],
            },
        }
        with patch.dict(
            os.environ,
            {
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                FASTAPI_ROLE_ACTIONS_ENV: json.dumps(payload),
            },
            clear=False,
        ):
            with (
                patch.object(
                    ERPNextPermissionAdapter,
                    "get_user_roles",
                    side_effect=AssertionError("ERPNext must not be used"),
                ),
                patch.object(
                    ERPNextPermissionAdapter,
                    "get_user_permissions",
                    side_effect=AssertionError("ERPNext must not be used"),
                ),
            ):
                agg = self._service().get_actions(
                    current_user=self._current_user(roles=["BOM Editor", "Style Viewer"]),
                    request_obj=_build_request(),
                    module="bom",
                )
        self.assertEqual(set(agg.actions), {"bom:read", "bom:publish", "bom:submit", "bom:update"})

    def test_fastapi_actions_missing_native_config_fails_closed_without_static_fallback(self) -> None:
        with patch.dict(os.environ, {"LINGYI_PERMISSION_SOURCE": "fastapi"}, clear=False):
            os.environ.pop(FASTAPI_ROLE_ACTIONS_ENV, None)
            agg = self._service().get_actions(
                current_user=self._current_user(roles=["BOM Editor", "System Manager"]),
                request_obj=_build_request(),
                module="bom",
            )
        self.assertEqual(set(agg.actions), set())
        self.assertFalse(agg.button_permissions["read"])
        self.assertFalse(agg.button_permissions["create"])

    def test_fastapi_actions_invalid_native_config_returns_503(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                FASTAPI_ROLE_ACTIONS_ENV: "{not-json",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                self._service().get_actions(
                    current_user=self._current_user(roles=["BOM Editor"]),
                    request_obj=_build_request(),
                    module="bom",
                )
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail["code"], PERMISSION_SOURCE_UNAVAILABLE_CODE)


if __name__ == "__main__":
    unittest.main()
