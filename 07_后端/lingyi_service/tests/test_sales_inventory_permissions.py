"""Permission registry tests for sales/inventory read-only integration (TASK-011B)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import CurrentUser
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import SALES_INVENTORY_DIAGNOSTIC
from app.core.permissions import SALES_INVENTORY_EXPORT
from app.core.permissions import SALES_INVENTORY_READ
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
        "path": "/api/sales-inventory/sales-orders",
        "raw_path": b"/api/sales-inventory/sales-orders",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class SalesInventoryPermissionTest(unittest.TestCase):
    """Validate TASK-011B actions and customer resource scope."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        AuditBase.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

    def _service(self) -> PermissionService:
        return PermissionService(session=self.SessionLocal())

    def test_actions_registered(self) -> None:
        self.assertEqual(
            MODULE_ACTION_REGISTRY["sales_inventory"],
            {SALES_INVENTORY_READ, SALES_INVENTORY_EXPORT, SALES_INVENTORY_DIAGNOSTIC},
        )

    def test_sales_manager_gets_read_and_export_not_diagnostic(self) -> None:
        actions = get_static_actions_for_roles(["Sales Manager"])
        self.assertIn(SALES_INVENTORY_READ, actions)
        self.assertIn(SALES_INVENTORY_EXPORT, actions)
        self.assertNotIn(SALES_INVENTORY_DIAGNOSTIC, actions)

    def test_system_manager_gets_diagnostic(self) -> None:
        actions = get_static_actions_for_roles(["System Manager"])
        self.assertIn(SALES_INVENTORY_DIAGNOSTIC, actions)

    def test_customer_scope_denied_in_erpnext_mode(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
                allowed_customers={"CUST-A"},
            ),
        ):
            with self.assertRaises(Exception) as ctx:
                self._service().ensure_resource_scope_permission(
                    current_user=CurrentUser(
                        username="sales.scope",
                        roles=["Sales Manager"],
                        is_service_account=False,
                        source="dev_header",
                    ),
                    request_obj=_build_request(),
                    module="sales_inventory",
                    action=SALES_INVENTORY_READ,
                    resource_scope={"company": "COMP-A", "customer": "CUST-B"},
                    required_fields=("company",),
                    resource_type="sales_order",
                    resource_no="SO-001",
                    enforce_action=False,
                )
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertEqual(ctx.exception.detail.get("code"), "RESOURCE_ACCESS_DENIED")

    def test_empty_customer_permissions_fail_closed(self) -> None:
        permissions = UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items=set(),
            allowed_companies={"COMP-A"},
            allowed_customers=set(),
        )

        self.assertFalse(
            ERPNextPermissionAdapter.is_customer_permitted(customer="CUST-A", user_permissions=permissions)
        )
