"""Readonly permission governance audit query tests (TASK-070B)."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import unittest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import DEFAULT_STATIC_ROLE_ACTIONS
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import PERMISSION_GOVERNANCE_AUDIT_READ
from app.core.permissions import get_static_actions_for_roles
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.permission_governance import get_db_session as permission_governance_db_dep


class PermissionGovernanceAuditReadonlyApiTest(unittest.TestCase):
    """Validate permission audit readonly contract and sensitive-field boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[permission_governance_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(permission_governance_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.add_all(
                [
                    LySecurityAuditLog(
                        event_type="AUTH_FORBIDDEN",
                        module="report",
                        action="report:read",
                        resource_type="REPORT",
                        resource_id="R-1",
                        resource_no="RP-001",
                        user_id="viewer.user",
                        user_roles=["Viewer"],
                        permission_source="static",
                        deny_reason="forbidden",
                        dedupe_key="D-1",
                        request_method="GET",
                        request_path="/api/reports/catalog",
                        request_id="SEC-REQ-1",
                        created_at=datetime(2026, 4, 20, 9, 0, 0),
                    ),
                    LySecurityAuditLog(
                        event_type="AUTH_FORBIDDEN",
                        module="permission",
                        action="permission:audit_read",
                        resource_type="PERMISSION",
                        resource_id="P-1",
                        resource_no="PM-001",
                        user_id="sys.manager",
                        user_roles=["System Manager"],
                        permission_source="static",
                        deny_reason="forbidden",
                        dedupe_key="D-2",
                        request_method="GET",
                        request_path="/api/permissions/audit/security",
                        request_id="SEC-REQ-2",
                        created_at=datetime(2026, 4, 21, 9, 0, 0),
                    ),
                    LySecurityAuditLog(
                        event_type="PERMISSION_SOURCE_UNAVAILABLE",
                        module="warehouse",
                        action="warehouse:read",
                        resource_type="WAREHOUSE",
                        resource_id="W-1",
                        resource_no="WH-001",
                        user_id="ops.user",
                        user_roles=["Warehouse Manager"],
                        permission_source="erpnext",
                        deny_reason="source unavailable",
                        dedupe_key="D-3",
                        request_method="GET",
                        request_path="/api/warehouse/stock-summary",
                        request_id="SEC-REQ-3",
                        created_at=datetime(2026, 4, 21, 10, 0, 0),
                    ),
                ]
            )
            session.add_all(
                [
                    LyOperationAuditLog(
                        module="permission",
                        action="permission:read",
                        operator="sys.manager",
                        operator_roles=["System Manager"],
                        resource_type="ROLE",
                        resource_id=101,
                        resource_no="ROLE-101",
                        before_data={"token": "abc", "name": "role-a"},
                        after_data={"password": "123", "name": "role-b"},
                        result="success",
                        error_code=None,
                        request_id="OP-REQ-1",
                        created_at=datetime(2026, 4, 20, 11, 0, 0),
                    ),
                    LyOperationAuditLog(
                        module="permission",
                        action="permission:audit_read",
                        operator="sys.manager",
                        operator_roles=["System Manager"],
                        resource_type="ROLE",
                        resource_id=102,
                        resource_no="ROLE-102",
                        before_data=None,
                        after_data=None,
                        result="failed",
                        error_code="AUTH_FORBIDDEN",
                        request_id="OP-REQ-2",
                        created_at=datetime(2026, 4, 21, 11, 0, 0),
                    ),
                    LyOperationAuditLog(
                        module="quality",
                        action="quality:update",
                        operator="qa.user",
                        operator_roles=["Quality Manager"],
                        resource_type="QUALITY_INSPECTION",
                        resource_id=201,
                        resource_no="QI-201",
                        before_data={"status": "draft"},
                        after_data={"status": "confirmed"},
                        result="success",
                        error_code=None,
                        request_id="OP-REQ-3",
                        created_at=datetime(2026, 4, 21, 12, 0, 0),
                    ),
                ]
            )
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "permission.audit.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_permission_audit_read_registered_and_role_matrix(self) -> None:
        self.assertIn(PERMISSION_GOVERNANCE_AUDIT_READ, MODULE_ACTION_REGISTRY.get("permission", set()))
        self.assertIn(PERMISSION_GOVERNANCE_AUDIT_READ, get_static_actions_for_roles(["System Manager"]))
        self.assertIn(PERMISSION_GOVERNANCE_AUDIT_READ, DEFAULT_STATIC_ROLE_ACTIONS.get("System Manager", set()))
        self.assertNotIn(PERMISSION_GOVERNANCE_AUDIT_READ, get_static_actions_for_roles(["Viewer"]))

    def test_security_audit_requires_permission_audit_read(self) -> None:
        denied_read = self.client.get(
            "/api/permissions/audit/security",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(denied_read.status_code, 403)

        denied_other = self.client.get(
            "/api/permissions/audit/security",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(denied_other.status_code, 403)

        allowed = self.client.get(
            "/api/permissions/audit/security",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_operation_audit_requires_permission_audit_read(self) -> None:
        denied_read = self.client.get(
            "/api/permissions/audit/operations",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(denied_read.status_code, 403)

        denied_other = self.client.get(
            "/api/permissions/audit/operations",
            headers=self._headers_with_roles("quality:read"),
        )
        self.assertEqual(denied_other.status_code, 403)

        allowed = self.client.get(
            "/api/permissions/audit/operations",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_security_filters_and_pagination_work(self) -> None:
        response = self.client.get(
            "/api/permissions/audit/security?module=permission&event_type=AUTH_FORBIDDEN&request_id=SEC-REQ-2&page=1&page_size=20",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(item["module"], "permission")
        self.assertEqual(item["request_id"], "SEC-REQ-2")

        date_response = self.client.get(
            "/api/permissions/audit/security?from_date=2026-04-21&to_date=2026-04-21&page=1&page_size=1",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(date_response.status_code, 200, date_response.text)
        date_data = date_response.json()["data"]
        self.assertEqual(date_data["total"], 2)
        self.assertEqual(len(date_data["items"]), 1)

    def test_operation_filters_work(self) -> None:
        response = self.client.get(
            "/api/permissions/audit/operations?module=permission&result=failed&operator=sys.manager&error_code=AUTH_FORBIDDEN",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(item["action"], "permission:audit_read")
        self.assertEqual(item["result"], "failed")

    def test_invalid_query_parameters_fail_closed(self) -> None:
        invalid_date = self.client.get(
            "/api/permissions/audit/security?from_date=2026-99-01",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(invalid_date.status_code, 400)
        self.assertEqual(invalid_date.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_range = self.client.get(
            "/api/permissions/audit/security?from_date=2026-04-22&to_date=2026-04-21",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(invalid_range.status_code, 400)
        self.assertEqual(invalid_range.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_page_size = self.client.get(
            "/api/permissions/audit/security?page_size=101",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(invalid_page_size.status_code, 400)
        self.assertEqual(invalid_page_size.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_result = self.client.get(
            "/api/permissions/audit/operations?result=partial_success",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(invalid_result.status_code, 400)
        self.assertEqual(invalid_result.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_sensitive_fields_not_exposed_in_response(self) -> None:
        security_response = self.client.get(
            "/api/permissions/audit/security",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(security_response.status_code, 200, security_response.text)
        security_item = security_response.json()["data"]["items"][0]
        forbidden_fields = {
            "authorization",
            "cookie",
            "token",
            "secret",
            "password",
            "dsn",
            "DATABASE_URL",
            "raw headers",
            "raw payload",
        }
        for field in forbidden_fields:
            self.assertNotIn(field, security_item)

        operation_response = self.client.get(
            "/api/permissions/audit/operations?module=permission&action=permission:read",
            headers=self._headers_with_roles("permission:audit_read"),
        )
        self.assertEqual(operation_response.status_code, 200, operation_response.text)
        op_item = operation_response.json()["data"]["items"][0]
        self.assertNotIn("before_data", op_item)
        self.assertNotIn("after_data", op_item)
        self.assertNotIn("token", op_item.get("before_keys", []))
        self.assertNotIn("password", op_item.get("after_keys", []))

    def test_main_route_mapping_for_permission_audit_endpoints(self) -> None:
        security_scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/permissions/audit/security",
            "raw_path": b"/api/permissions/audit/security",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        security_request = Request(security_scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(security_request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_GOVERNANCE_AUDIT_READ)
        self.assertEqual(resource_type, "PermissionSecurityAudit")
        self.assertIsNone(resource_id)

        operation_scope = dict(security_scope)
        operation_scope["path"] = "/api/permissions/audit/operations"
        operation_scope["raw_path"] = b"/api/permissions/audit/operations"
        operation_request = Request(operation_scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(operation_request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_GOVERNANCE_AUDIT_READ)
        self.assertEqual(resource_type, "PermissionOperationAudit")
        self.assertIsNone(resource_id)

    def test_permission_governance_files_have_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/permission_governance.py"),
            Path("app/schemas/permission_governance.py"),
            Path("app/services/permission_governance_service.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "requests.post(",
            "requests.put(",
            "requests.patch(",
            "requests.delete(",
            "httpx.post(",
            "httpx.put(",
            "httpx.patch(",
            "httpx.delete(",
            "/api/resource",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)


if __name__ == "__main__":
    unittest.main()
