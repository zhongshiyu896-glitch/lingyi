"""API tests for quality management baseline (TASK-012B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityInspectionItem
from app.models.quality import LyQualityOperationLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.quality import get_db_session as quality_db_dep
from app.services.quality_service import QualitySourceValidationSnapshot
from app.services.quality_service import QualitySourceValidator
from app.core.exceptions import BusinessException
from app.core.error_codes import QUALITY_SOURCE_UNAVAILABLE
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.permission_service import PermissionService


class QualityApiBase(unittest.TestCase):
    """Shared in-memory app wiring for quality API tests."""

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
        QualityBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[quality_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(quality_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyQualityOperationLog).delete()
            session.query(LyQualityDefect).delete()
            session.query(LyQualityInspectionItem).delete()
            session.query(LyQualityInspection).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Quality Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "quality.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _payload(**overrides) -> dict:
        payload = {
            "company": "COMP-A",
            "source_type": "manual",
            "source_id": None,
            "item_code": "ITEM-A",
            "supplier": "SUP-A",
            "warehouse": "WH-A",
            "inspection_date": "2026-04-16",
            "inspected_qty": "10",
            "accepted_qty": "8",
            "rejected_qty": "2",
            "defect_qty": "1",
            "result": "partial",
            "items": [
                {
                    "item_code": "ITEM-A",
                    "sample_qty": "10",
                    "accepted_qty": "8",
                    "rejected_qty": "2",
                    "defect_qty": "1",
                    "result": "partial",
                }
            ],
            "defects": [
                {
                    "defect_code": "DEF-001",
                    "defect_name": "线头",
                    "defect_qty": "1",
                    "severity": "minor",
                    "item_line_no": 1,
                }
            ],
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}}, source=None)

    def _create(self) -> dict:
        with patch.object(QualitySourceValidator, "validate_for_payload", return_value=self._snapshot()):
            response = self.client.post("/api/quality/inspections", headers=self._headers(), json=self._payload())
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]


class QualityApiTest(QualityApiBase):
    """Quality API baseline behavior."""

    def test_create_inspection_calculates_rates_and_audits(self) -> None:
        data = self._create()
        self.assertEqual(data["status"], "draft")
        self.assertEqual(Decimal(data["defect_rate"]), Decimal("0.100000"))
        self.assertEqual(Decimal(data["rejected_rate"]), Decimal("0.200000"))
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(len(data["defects"]), 1)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 1)
            self.assertEqual(session.query(LyQualityOperationLog).count(), 1)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 1)

    def test_create_rejects_qty_mismatch_without_partial_write(self) -> None:
        with patch.object(QualitySourceValidator, "validate_for_payload", return_value=self._snapshot()):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(),
                json=self._payload(accepted_qty="7", rejected_qty="2"),
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "QUALITY_QTY_MISMATCH")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 1)

    def test_update_draft_and_confirm_then_cancel(self) -> None:
        data = self._create()
        inspection_id = data["id"]
        with patch.object(QualitySourceValidator, "validate_for_payload", return_value=self._snapshot()):
            update = self.client.patch(
                f"/api/quality/inspections/{inspection_id}",
                headers=self._headers(),
                json={"remark": "复检备注", "defect_qty": "0", "result": "pass"},
            )
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(update.json()["data"]["result"], "pass")

        with patch.object(QualitySourceValidator, "validate_for_payload", return_value=self._snapshot()):
            confirm = self.client.post(
                f"/api/quality/inspections/{inspection_id}/confirm",
                headers=self._headers(),
                json={"remark": "确认"},
            )
        self.assertEqual(confirm.status_code, 200, confirm.text)
        self.assertEqual(confirm.json()["data"]["status"], "confirmed")

        update_after_confirm = self.client.patch(
            f"/api/quality/inspections/{inspection_id}",
            headers=self._headers(),
            json={"remark": "不应允许"},
        )
        self.assertEqual(update_after_confirm.status_code, 409)
        self.assertEqual(update_after_confirm.json()["code"], "QUALITY_INVALID_STATUS")

        cancel = self.client.post(
            f"/api/quality/inspections/{inspection_id}/cancel",
            headers=self._headers(),
            json={"reason": "取消"},
        )
        self.assertEqual(cancel.status_code, 200, cancel.text)
        self.assertEqual(cancel.json()["data"]["status"], "cancelled")

    def test_confirm_source_unavailable_fails_closed(self) -> None:
        data = self._create()
        with patch.object(
            QualitySourceValidator,
            "validate_for_payload",
            side_effect=BusinessException(code=QUALITY_SOURCE_UNAVAILABLE),
        ):
            response = self.client.post(
                f"/api/quality/inspections/{data['id']}/confirm",
                headers=self._headers(),
                json={},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "QUALITY_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).one()
            self.assertEqual(row.status, "draft")

    def test_list_detail_statistics_and_export(self) -> None:
        data = self._create()
        response = self.client.get("/api/quality/inspections", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total"], 1)

        detail = self.client.get(f"/api/quality/inspections/{data['id']}", headers=self._headers())
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["inspection_no"], data["inspection_no"])

        stats = self.client.get("/api/quality/statistics", headers=self._headers())
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.json()["data"]["total_count"], 1)

        export = self.client.get("/api/quality/export", headers=self._headers(role="Quality Viewer"))
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.json()["data"]["total"], 1)
        with self.SessionLocal() as session:
            self.assertGreaterEqual(session.query(LyOperationAuditLog).count(), 2)

    def test_diagnostic_requires_permission_and_records_operation_audit(self) -> None:
        self._create()
        response = self.client.get("/api/quality/diagnostic", headers=self._headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["total_count"], 1)
        self.assertEqual(response.json()["data"]["by_source_type"]["manual"], 1)
        with self.SessionLocal() as session:
            self.assertGreaterEqual(session.query(LyOperationAuditLog).count(), 2)

        denied = self.client.get("/api/quality/diagnostic", headers=self._headers(role="Quality Inspector"))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertGreaterEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_create_scope_includes_source_type_and_source_id(self) -> None:
        seen_scopes: list[dict] = []
        original = PermissionService.ensure_resource_scope_permission

        def _spy(self, **kwargs):
            seen_scopes.append(dict(kwargs.get("resource_scope") or {}))
            return original(self, **kwargs)

        with patch.object(PermissionService, "ensure_resource_scope_permission", _spy), patch.object(
            QualitySourceValidator,
            "validate_for_payload",
            return_value=self._snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(),
                json=self._payload(source_id="MANUAL-SRC-1"),
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any(scope.get("source_type") == "manual" and scope.get("source_id") == "MANUAL-SRC-1" for scope in seen_scopes))

    def test_action_permission_denied_before_write(self) -> None:
        with patch.object(QualitySourceValidator, "validate_for_payload") as validator:
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(role="Quality Viewer"),
                json=self._payload(),
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        validator.assert_not_called()
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)
            self.assertEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_detail_resource_denied_hides_existence(self) -> None:
        data = self._create()
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_roles",
            return_value=["Quality Manager"],
        ), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-B"},
            ),
        ):
            response = self.client.get(f"/api/quality/inspections/{data['id']}", headers=self._headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESOURCE_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_only_allowed_routes_do_not_expose_outbox_or_erpnext_write(self) -> None:
        methods_by_path = {route.path: route.methods for route in app.routes if getattr(route, "path", "").startswith("/api/quality")}
        self.assertTrue(methods_by_path)
        forbidden_paths = [path for path in methods_by_path if "outbox" in path or "erpnext" in path or "worker" in path]
        self.assertEqual(forbidden_paths, [])
        allowed_methods = {"GET", "POST", "PATCH", "HEAD", "OPTIONS"}
        for methods in methods_by_path.values():
            self.assertLessEqual(set(methods), allowed_methods)


if __name__ == "__main__":
    unittest.main()
