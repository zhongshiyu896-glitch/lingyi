"""Readonly permission governance diagnostic tests (TASK-070D)."""

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
from app.core.permissions import PERMISSION_AUDIT_DIAGNOSTIC
from app.core.permissions import PERMISSION_GOVERNANCE_AUDIT_READ
from app.core.permissions import PERMISSION_GOVERNANCE_DIAGNOSTIC
from app.core.permissions import PERMISSION_GOVERNANCE_EXPORT
from app.core.permissions import PERMISSION_READ
from app.core.permissions import get_static_actions_for_roles
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.permission_governance import get_db_session as permission_governance_db_dep


class PermissionGovernanceDiagnosticApiTest(unittest.TestCase):
    """Validate diagnostic readonly contract, permission isolation and safety boundary."""

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
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "permission.diagnostic.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_permission_diagnostic_registered_and_role_boundary(self) -> None:
        actions = MODULE_ACTION_REGISTRY.get("permission")
        self.assertIsNotNone(actions)
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, actions or set())

        system_actions = get_static_actions_for_roles(["System Manager"])
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, system_actions)
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, DEFAULT_STATIC_ROLE_ACTIONS.get("System Manager", set()))
        self.assertNotIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, get_static_actions_for_roles(["Viewer"]))

    def test_diagnostic_requires_exact_permission(self) -> None:
        denied_roles = [
            PERMISSION_READ,
            PERMISSION_GOVERNANCE_AUDIT_READ,
            PERMISSION_GOVERNANCE_EXPORT,
            PERMISSION_AUDIT_DIAGNOSTIC,
            "dashboard:read",
            "report:diagnostic",
            "warehouse:diagnostic",
            "inventory:read",
        ]
        for role in denied_roles:
            response = self.client.get(
                "/api/permissions/diagnostic",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

        allowed = self.client.get(
            "/api/permissions/diagnostic",
            headers=self._headers_with_roles(PERMISSION_GOVERNANCE_DIAGNOSTIC),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_diagnostic_response_contract_and_safety(self) -> None:
        response = self.client.get(
            "/api/permissions/diagnostic",
            headers=self._headers_with_roles(PERMISSION_GOVERNANCE_DIAGNOSTIC),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        data = payload["data"]

        required_fields = {
            "module",
            "status",
            "registered_actions",
            "legacy_permission_audit_actions",
            "high_risk_actions",
            "ui_hidden_actions",
            "roles_with_permission_actions_count",
            "checks",
            "catalog_enabled",
            "roles_matrix_enabled",
            "audit_read_enabled",
            "export_enabled",
            "diagnostic_enabled",
            "generated_at",
        }
        self.assertTrue(required_fields.issubset(set(data.keys())))
        self.assertEqual(data["module"], "permission")
        self.assertIn(PERMISSION_READ, data["registered_actions"])
        self.assertIn(PERMISSION_GOVERNANCE_AUDIT_READ, data["registered_actions"])
        self.assertIn(PERMISSION_GOVERNANCE_EXPORT, data["registered_actions"])
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, data["registered_actions"])
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, data["high_risk_actions"])
        self.assertIn(PERMISSION_GOVERNANCE_DIAGNOSTIC, data["ui_hidden_actions"])
        self.assertTrue(bool(data["catalog_enabled"]))
        self.assertTrue(bool(data["roles_matrix_enabled"]))
        self.assertTrue(bool(data["audit_read_enabled"]))
        self.assertTrue(bool(data["export_enabled"]))
        self.assertTrue(bool(data["diagnostic_enabled"]))

        check_names = {item["name"] for item in data["checks"]}
        expected_checks = {
            "permission:read_registered",
            "permission:audit_read_registered",
            "permission:export_registered",
            "permission:diagnostic_registered",
            "permission_diagnostic_hidden",
            "permission_diagnostic_high_risk",
            "permission_audit_legacy_kept",
            "no_wildcard_permission_action",
        }
        self.assertTrue(expected_checks.issubset(check_names))
        self.assertTrue(all(item["status"] == "pass" for item in data["checks"]))

        # UTC ISO string
        datetime.fromisoformat(data["generated_at"])

        forbidden_field_names = {
            "authorization",
            "cookie",
            "token",
            "secret",
            "password",
            "dsn",
            "database_url",
            "headers",
            "payload",
            "before_data",
            "after_data",
        }
        lowered_keys = {str(key).lower() for key in data.keys()}
        self.assertTrue(forbidden_field_names.isdisjoint(lowered_keys))

    def test_main_route_mapping_for_permission_diagnostic(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/permissions/diagnostic",
            "raw_path": b"/api/permissions/diagnostic",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_GOVERNANCE_DIAGNOSTIC)
        self.assertEqual(resource_type, "PermissionDiagnostic")
        self.assertIsNone(resource_id)

    def test_permission_diagnostic_files_have_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/permission_governance.py"),
            Path("app/services/permission_governance_service.py"),
            Path("app/services/permission_governance_export_service.py"),
            Path("app/services/permission_governance_diagnostic_service.py"),
            Path("app/schemas/permission_governance.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
        blocked = [
            "@router.post(",
            "@router.put(",
            "@router.patch(",
            "@router.delete(",
            "session.add(",
            "session.delete(",
            "session.commit(",
            "session.rollback(",
            "requests.",
            "httpx.",
            "/api/resource",
            "erpnext",
            "stock entry",
            "stock reconciliation",
            "payment entry",
            "purchase invoice",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)


if __name__ == "__main__":
    unittest.main()
