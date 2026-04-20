"""Permission governance audit CSV export security baseline tests (TASK-070C)."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import PERMISSION_GOVERNANCE_EXPORT
from app.core.permissions import get_static_actions_for_roles
from app.core.exceptions import AuditWriteFailed
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.permission_governance import get_db_session as permission_governance_db_dep


def _csv_rows(content: bytes) -> list[list[str]]:
    return list(csv.reader(StringIO(content.decode("utf-8"))))


class PermissionGovernanceAuditExportApiTest(unittest.TestCase):
    """Validate permission export boundary, CSV safety and audit logging."""

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
                        module="permission",
                        action="+SUM(1,2)",
                        resource_type="PERMISSION",
                        resource_id="R-1",
                        resource_no="NO-1",
                        user_id="user.one",
                        user_roles=["System Manager"],
                        permission_source="static",
                        deny_reason="=cmd|'/C calc'!A0",
                        dedupe_key="SEC-1",
                        request_method="GET",
                        request_path="\t=1+1",
                        request_id="SEC-REQ-1",
                        created_at=datetime(2026, 4, 21, 9, 0, 0),
                    ),
                    LySecurityAuditLog(
                        event_type="PERMISSION_SOURCE_UNAVAILABLE",
                        module="warehouse",
                        action="warehouse:read",
                        resource_type="WAREHOUSE",
                        resource_id="R-2",
                        resource_no="NO-2",
                        user_id="user.two",
                        user_roles=["Warehouse Manager"],
                        permission_source="erpnext",
                        deny_reason="source unavailable",
                        dedupe_key="SEC-2",
                        request_method="GET",
                        request_path="/api/warehouse/stock-summary",
                        request_id="SEC-REQ-2",
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
                        before_data={"=cmd": "x", "token": "abc", "name": "role-a"},
                        after_data={"@HYPERLINK(\"http://evil\")": "y", "password": "123", "name": "role-b"},
                        result="success",
                        error_code=None,
                        request_id="OP-REQ-1",
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
                        result="failed",
                        error_code="AUTH_FORBIDDEN",
                        request_id="OP-REQ-2",
                        created_at=datetime(2026, 4, 21, 12, 0, 0),
                    ),
                ]
            )
            session.commit()

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "permission.export.user",
            "X-LY-Dev-Roles": roles,
        }

    def _latest_export_log(self, resource_type: str, result: str) -> LyOperationAuditLog | None:
        with self.SessionLocal() as session:
            return (
                session.query(LyOperationAuditLog)
                .filter(LyOperationAuditLog.module == "permission")
                .filter(LyOperationAuditLog.action == PERMISSION_GOVERNANCE_EXPORT)
                .filter(LyOperationAuditLog.resource_type == resource_type)
                .filter(LyOperationAuditLog.result == result)
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )

    def test_permission_export_registered_and_role_boundary(self) -> None:
        self.assertIn(PERMISSION_GOVERNANCE_EXPORT, MODULE_ACTION_REGISTRY.get("permission", set()))
        self.assertIn(PERMISSION_GOVERNANCE_EXPORT, get_static_actions_for_roles(["System Manager"]))
        self.assertNotIn(PERMISSION_GOVERNANCE_EXPORT, get_static_actions_for_roles(["Viewer"]))

    def test_security_export_requires_permission_export(self) -> None:
        for role in ("permission:read", "permission:audit_read", "dashboard:read", "report:read", "warehouse:read"):
            response = self.client.get(
                "/api/permissions/audit/security/export",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_operation_export_requires_permission_export(self) -> None:
        for role in ("permission:read", "permission:audit_read", "quality:read", "inventory:read"):
            response = self.client.get(
                "/api/permissions/audit/operations/export",
                headers=self._headers_with_roles(role),
            )
            self.assertEqual(response.status_code, 403, f"role={role} response={response.text}")

    def test_security_export_headers_and_fields(self) -> None:
        response = self.client.get(
            "/api/permissions/audit/security/export?module=permission&request_id=SEC-REQ-1",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers.get("content-type", "").startswith("text/csv"))
        disposition = response.headers.get("content-disposition", "")
        self.assertIn("permission_security_audit_export_", disposition)
        self.assertNotIn("SEC-REQ-1", disposition)

        rows = _csv_rows(response.content)
        self.assertEqual(
            rows[0],
            [
                "id",
                "event_type",
                "module",
                "action",
                "resource_type",
                "resource_id",
                "resource_no",
                "user_id",
                "permission_source",
                "deny_reason",
                "request_method",
                "request_path",
                "request_id",
                "created_at",
            ],
        )
        self.assertEqual(len(rows), 2)

    def test_operation_export_headers_and_no_raw_before_after(self) -> None:
        response = self.client.get(
            "/api/permissions/audit/operations/export?module=permission&limit=1000",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(
            rows[0],
            [
                "id",
                "module",
                "action",
                "operator",
                "resource_type",
                "resource_id",
                "resource_no",
                "result",
                "error_code",
                "request_id",
                "has_before_data",
                "has_after_data",
                "before_keys",
                "after_keys",
                "created_at",
            ],
        )
        self.assertNotIn("before_data", rows[0])
        self.assertNotIn("after_data", rows[0])

    def test_formula_injection_cells_are_escaped(self) -> None:
        sec_resp = self.client.get(
            "/api/permissions/audit/security/export?module=permission",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(sec_resp.status_code, 200, sec_resp.text)
        sec_rows = _csv_rows(sec_resp.content)
        self.assertEqual(sec_rows[1][3], "'+SUM(1,2)")
        self.assertEqual(sec_rows[1][9], "'=cmd|'/C calc'!A0")
        self.assertEqual(sec_rows[1][11], "'\t=1+1")

        op_resp = self.client.get(
            "/api/permissions/audit/operations/export?module=permission",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(op_resp.status_code, 200, op_resp.text)
        op_rows = _csv_rows(op_resp.content)
        self.assertTrue(op_rows[1][12].startswith("'"))
        self.assertTrue(op_rows[1][13].startswith("'"))
        self.assertNotIn("token", op_rows[1][12].lower())
        self.assertNotIn("password", op_rows[1][13].lower())

    def test_invalid_params_fail_closed(self) -> None:
        invalid_date = self.client.get(
            "/api/permissions/audit/security/export?from_date=2026-99-01",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(invalid_date.status_code, 400)
        self.assertEqual(invalid_date.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_range = self.client.get(
            "/api/permissions/audit/security/export?from_date=2026-04-22&to_date=2026-04-21",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(invalid_range.status_code, 400)
        self.assertEqual(invalid_range.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_limit = self.client.get(
            "/api/permissions/audit/security/export?limit=5001",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(invalid_limit.status_code, 400)
        self.assertEqual(invalid_limit.json()["code"], "INVALID_QUERY_PARAMETER")

        invalid_result = self.client.get(
            "/api/permissions/audit/operations/export?result=partial_success",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(invalid_result.status_code, 400)
        self.assertEqual(invalid_result.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_export_success_and_failure_both_record_operation_audit(self) -> None:
        success_response = self.client.get(
            "/api/permissions/audit/security/export?module=permission",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(success_response.status_code, 200, success_response.text)
        success_log = self._latest_export_log("permission_security_audit_export", "success")
        self.assertIsNotNone(success_log)

        failed_response = self.client.get(
            "/api/permissions/audit/security/export?from_date=2026-99-01",
            headers=self._headers_with_roles("permission:export"),
        )
        self.assertEqual(failed_response.status_code, 400)
        failed_log = self._latest_export_log("permission_security_audit_export", "failed")
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.error_code, "INVALID_QUERY_PARAMETER")

    def test_export_fails_closed_when_audit_write_fails(self) -> None:
        with patch("app.routers.permission_governance.AuditService.record_success", side_effect=AuditWriteFailed()):
            response = self.client.get(
                "/api/permissions/audit/security/export",
                headers=self._headers_with_roles("permission:export"),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")

    def test_main_route_mapping_for_export_endpoints(self) -> None:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/permissions/audit/security/export",
            "raw_path": b"/api/permissions/audit/security/export",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = Request(scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_GOVERNANCE_EXPORT)
        self.assertEqual(resource_type, "PermissionSecurityAuditExport")
        self.assertIsNone(resource_id)

        operation_scope = dict(scope)
        operation_scope["path"] = "/api/permissions/audit/operations/export"
        operation_scope["raw_path"] = b"/api/permissions/audit/operations/export"
        operation_request = Request(operation_scope)
        module, action, resource_type, resource_id = main_module._infer_security_target(operation_request)
        self.assertEqual(module, "permission")
        self.assertEqual(action, PERMISSION_GOVERNANCE_EXPORT)
        self.assertEqual(resource_type, "PermissionOperationAuditExport")
        self.assertIsNone(resource_id)

    def test_permission_governance_export_files_have_no_forbidden_signatures(self) -> None:
        files = [
            Path("app/routers/permission_governance.py"),
            Path("app/services/permission_governance_service.py"),
            Path("app/services/permission_governance_export_service.py"),
            Path("app/schemas/permission_governance.py"),
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
        blocked = [
            "session.add(",
            "session.delete(",
            "session.commit(",
            "session.rollback(",
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
            "erpnext",
            "stock reconciliation",
            "payment entry",
            "purchase invoice",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, combined)

    def test_audit_service_owns_export_commit_and_rollback(self) -> None:
        content = Path("app/services/audit_service.py").read_text(encoding="utf-8")
        self.assertIn("def record_success_and_commit(", content)
        self.assertIn("def record_failure_and_commit(", content)
        self.assertIn("self.session.commit()", content)
        self.assertIn("self.session.rollback()", content)


if __name__ == "__main__":
    unittest.main()
