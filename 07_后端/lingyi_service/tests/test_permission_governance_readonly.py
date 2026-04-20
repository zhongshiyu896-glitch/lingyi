"""Readonly permission governance baseline tests (TASK-070A)."""

from __future__ import annotations

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
from app.core.permissions import PERMISSION_READ
from app.core.permissions import get_static_actions_for_roles
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.permission_governance import get_db_session as permission_governance_db_dep


class PermissionGovernanceReadonlyApiTest(unittest.TestCase):
    """Validate permission governance readonly contract and boundaries."""

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
            "X-LY-Dev-User": "permission.governance.user",
            "X-LY-Dev-Roles": roles,
        }

    def test_permission_read_registered_under_permission_module(self) -> None:
        permission_actions = MODULE_ACTION_REGISTRY.get("permission")
        self.assertIsNotNone(permission_actions)
        self.assertIn(PERMISSION_READ, permission_actions or set())

    def test_system_manager_has_permission_read(self) -> None:
        self.assertIn(PERMISSION_READ, get_static_actions_for_roles(["System Manager"]))
        self.assertIn(PERMISSION_READ, DEFAULT_STATIC_ROLE_ACTIONS.get("System Manager", set()))

    def test_viewer_does_not_have_permission_read(self) -> None:
        self.assertNotIn(PERMISSION_READ, get_static_actions_for_roles(["Viewer"]))

    def test_actions_catalog_requires_permission_read(self) -> None:
        denied = self.client.get(
            "/api/permissions/actions/catalog",
            headers=self._headers_with_roles("report:read"),
        )
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get(
            "/api/permissions/actions/catalog",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_roles_matrix_requires_permission_read(self) -> None:
        denied = self.client.get(
            "/api/permissions/roles/matrix",
            headers=self._headers_with_roles("dashboard:read"),
        )
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get(
            "/api/permissions/roles/matrix",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_only_other_module_read_actions_still_forbidden(self) -> None:
        for role in ("dashboard:read", "report:read", "warehouse:read", "quality:read"):
            response = self.client.get(
                "/api/permissions/roles/matrix",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_actions_catalog_covers_required_modules(self) -> None:
        response = self.client.get(
            "/api/permissions/actions/catalog",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        modules = {entry["module"] for entry in response.json()["data"]["modules"]}
        expected = {"dashboard", "report", "warehouse", "quality", "permission"}
        self.assertTrue(expected.issubset(modules))

    def test_diagnostic_worker_internal_actions_are_high_risk_or_hidden(self) -> None:
        response = self.client.get(
            "/api/permissions/actions/catalog",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        flagged_rows: list[dict[str, object]] = []
        for module_row in response.json()["data"]["modules"]:
            for action_row in module_row["actions"]:
                action = str(action_row["action"])
                if (":diagnostic" in action) or ("worker" in action) or ("internal" in action):
                    flagged_rows.append(action_row)

        self.assertTrue(flagged_rows)
        for row in flagged_rows:
            self.assertTrue(bool(row["is_high_risk"]) or (not bool(row["ui_exposed"])))

    def test_roles_matrix_marks_high_risk_and_hidden_actions(self) -> None:
        response = self.client.get(
            "/api/permissions/roles/matrix",
            headers=self._headers_with_roles("permission:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)

        rows = response.json()["data"]["roles"]
        sys_mgr = next((row for row in rows if row["role"] == "System Manager"), None)
        self.assertIsNotNone(sys_mgr)
        self.assertIn("outbox:worker", sys_mgr["high_risk_actions"])
        self.assertIn("report:diagnostic", sys_mgr["ui_hidden_actions"])

    def test_no_write_route_registered(self) -> None:
        routes = [
            route
            for route in app.routes
            if str(getattr(route, "path", "")).startswith("/api/permissions/")
        ]
        self.assertTrue(routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        for route in routes:
            methods = set(getattr(route, "methods", set()))
            self.assertTrue(methods.issubset(readonly_methods), f"unexpected methods on {route.path}: {methods}")

    def test_main_route_mapping_for_permission_governance_endpoints(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/permissions/actions/catalog",
            "raw_path": b"/api/permissions/actions/catalog",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_READ)
        self.assertEqual(resource_type, "PermissionActionCatalog")
        self.assertIsNone(resource_id)

        detail_scope = dict(scope)
        detail_scope["path"] = "/api/permissions/roles/matrix"
        detail_scope["raw_path"] = b"/api/permissions/roles/matrix"
        detail_request = Request(detail_scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(detail_request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_READ)
        self.assertEqual(resource_type, "PermissionRolesMatrix")
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
            "requests.",
            "httpx.",
            "/api/resource",
            "erpnext",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined.lower())


if __name__ == "__main__":
    unittest.main()
