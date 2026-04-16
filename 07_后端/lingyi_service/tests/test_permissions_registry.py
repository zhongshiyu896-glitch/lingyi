"""Registry and resource-scope baseline tests for TASK-007B."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import CurrentUser
from app.core.error_codes import RESOURCE_SCOPE_FIELD_UNKNOWN
from app.core.exceptions import PermissionSourceUnavailable
from app.core.permissions import BOM_READ
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import PERMISSION_AUDIT_DIAGNOSTIC
from app.core.permissions import PERMISSION_AUDIT_MANAGE
from app.core.permissions import PERMISSION_AUDIT_READ
from app.core.permissions import PRODUCTION_READ
from app.core.permissions import QUALITY_WORKER
from app.core.permissions import SUBCONTRACT_READ
from app.core.permissions import get_static_actions_for_roles
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
        "path": "/api/test/permissions",
        "raw_path": b"/api/test/permissions",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class PermissionRegistryBaselineTest(unittest.TestCase):
    """Validate TASK-007B registry and fail-closed scope behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._old_source = os.getenv("LINGYI_PERMISSION_SOURCE")
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        AuditBase.metadata.create_all(bind=engine)
        cls._SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._old_source is None:
            os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
        else:
            os.environ["LINGYI_PERMISSION_SOURCE"] = cls._old_source

    def _service(self) -> PermissionService:
        return PermissionService(session=self._SessionLocal())

    def test_sprint2_actions_registered(self) -> None:
        expected = {
            "permission_audit:read",
            "permission_audit:manage",
            "permission_audit:diagnostic",
            "erpnext_adapter:read",
            "erpnext_adapter:dry_run",
            "erpnext_adapter:diagnostic",
            "outbox:read",
            "outbox:retry",
            "outbox:manage",
            "outbox:dry_run",
            "outbox:diagnostic",
            "outbox:worker",
            "frontend_contract:read",
            "frontend_contract:manage",
            "frontend_contract:diagnostic",
            "sales:read",
            "sales:export",
            "inventory:read",
            "inventory:export",
            "quality:read",
            "quality:create",
            "quality:update",
            "quality:confirm",
            "quality:cancel",
            "quality:export",
            "quality:dry_run",
            "quality:diagnostic",
            "quality:worker",
            "dashboard:read",
        }
        flattened = {action for actions in MODULE_ACTION_REGISTRY.values() for action in actions}
        for action in expected:
            self.assertIn(action, flattened)

    def test_legacy_actions_not_lost(self) -> None:
        flattened = {action for actions in MODULE_ACTION_REGISTRY.values() for action in actions}
        self.assertIn(BOM_READ, flattened)
        self.assertIn(SUBCONTRACT_READ, flattened)
        self.assertIn(PRODUCTION_READ, flattened)

    def test_system_manager_gets_new_module_actions_in_static_mode(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="sys.manager",
                roles=["System Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="permission_audit",
        )
        self.assertIn(PERMISSION_AUDIT_READ, agg.actions)
        self.assertIn(PERMISSION_AUDIT_MANAGE, agg.actions)
        self.assertIn(PERMISSION_AUDIT_DIAGNOSTIC, agg.actions)

    def test_quality_module_filter_works(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        agg = self._service().get_actions(
            current_user=CurrentUser(
                username="sys.manager",
                roles=["System Manager"],
                is_service_account=False,
                source="dev_header",
            ),
            request_obj=_build_request(),
            module="quality",
        )
        self.assertIn(QUALITY_WORKER, agg.actions)
        self.assertTrue(all(action.startswith("quality:") for action in agg.actions))

    def test_missing_company_fails_closed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                self._service().ensure_resource_scope_permission(
                    current_user=CurrentUser(
                        username="scope.user",
                        roles=["Subcontract Manager"],
                        is_service_account=False,
                        source="dev_header",
                    ),
                    request_obj=_build_request(),
                    module="subcontract",
                    action=SUBCONTRACT_READ,
                    resource_scope={"item_code": "ITEM-A"},
                    required_fields=("company", "item_code"),
                    enforce_action=False,
                )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail.get("code"), "RESOURCE_ACCESS_DENIED")

    def test_unknown_required_field_fails_closed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.assertRaises(HTTPException) as ctx:
            self._service().ensure_resource_scope_permission(
                current_user=CurrentUser(
                    username="scope.user",
                    roles=["Subcontract Manager"],
                    is_service_account=False,
                    source="dev_header",
                ),
                request_obj=_build_request(),
                module="subcontract",
                action=SUBCONTRACT_READ,
                resource_scope={"company": "COMP-A", "item_code": "ITEM-A"},
                required_fields=("company_code",),
                enforce_action=False,
            )
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail.get("code"), RESOURCE_SCOPE_FIELD_UNKNOWN)

    def test_company_only_does_not_imply_item_permission(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                self._service().ensure_resource_scope_permission(
                    current_user=CurrentUser(
                        username="scope.user",
                        roles=["Subcontract Manager"],
                        is_service_account=False,
                        source="dev_header",
                    ),
                    request_obj=_build_request(),
                    module="subcontract",
                    action=SUBCONTRACT_READ,
                    resource_scope={"company": "COMP-A", "item_code": "ITEM-A"},
                    required_fields=("company", "item_code"),
                    enforce_action=False,
                )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail.get("code"), "RESOURCE_ACCESS_DENIED")

    def test_permission_source_unavailable_returns_503(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                self._service().ensure_resource_scope_permission(
                    current_user=CurrentUser(
                        username="scope.user",
                        roles=["Subcontract Manager"],
                        is_service_account=False,
                        source="dev_header",
                    ),
                    request_obj=_build_request(),
                    module="subcontract",
                    action=SUBCONTRACT_READ,
                    resource_scope={"company": "COMP-A"},
                    required_fields=("company",),
                    enforce_action=False,
                )
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail.get("code"), "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertIsNone(ctx.exception.detail.get("data"))

    def test_get_readable_item_codes_company_only_returns_empty_set(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
            ),
        ):
            readable = self._service().get_readable_item_codes(
                current_user=CurrentUser(
                    username="scope.user",
                    roles=["BOM Editor"],
                    is_service_account=False,
                    source="dev_header",
                ),
                request_obj=_build_request(),
            )
        self.assertEqual(readable, set())


if __name__ == "__main__":
    unittest.main()
