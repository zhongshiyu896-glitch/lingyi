"""API tests for quality read baseline and status-machine write behavior."""

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
from app.models.quality_outbox import LyQualityOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.quality import get_db_session as quality_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.quality_service import QualitySourceValidationSnapshot


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
            session.query(LyQualityOutbox).delete()
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

    def _insert_inspection(
        self,
        *,
        inspection_no: str,
        status: str,
        result: str,
        inspected_qty: Decimal,
        accepted_qty: Decimal,
        rejected_qty: Decimal,
        defect_qty: Decimal,
    ) -> dict[str, int | str]:
        with self.SessionLocal() as session:
            inspection = LyQualityInspection(
                inspection_no=inspection_no,
                company="COMP-A",
                source_type="manual",
                source_id=None,
                item_code="ITEM-A",
                supplier="SUP-A",
                warehouse="WH-A",
                inspection_date=date(2026, 4, 16),
                inspected_qty=inspected_qty,
                accepted_qty=accepted_qty,
                rejected_qty=rejected_qty,
                defect_qty=defect_qty,
                defect_rate=Decimal("0") if inspected_qty == Decimal("0") else (defect_qty / inspected_qty).quantize(Decimal("0.000001")),
                rejected_rate=Decimal("0") if inspected_qty == Decimal("0") else (rejected_qty / inspected_qty).quantize(Decimal("0.000001")),
                result=result,
                status=status,
                created_by="quality.user",
                updated_by="quality.user",
            )
            session.add(inspection)
            session.flush()

            item = LyQualityInspectionItem(
                inspection_id=int(inspection.id),
                line_no=1,
                item_code="ITEM-A",
                sample_qty=inspected_qty,
                accepted_qty=accepted_qty,
                rejected_qty=rejected_qty,
                defect_qty=defect_qty,
                result=result,
            )
            session.add(item)
            session.flush()

            defect = LyQualityDefect(
                inspection_id=int(inspection.id),
                item_id=int(item.id),
                defect_code="DEF-001",
                defect_name="线头",
                defect_qty=defect_qty,
                severity="minor",
            )
            session.add(defect)

            log = LyQualityOperationLog(
                inspection_id=int(inspection.id),
                company="COMP-A",
                from_status=None,
                to_status=status,
                action="create",
                operator="quality.user",
                request_id="req-seed",
            )
            session.add(log)
            session.commit()
            return {"id": int(inspection.id), "inspection_no": str(inspection.inspection_no)}


class QualityApiTest(QualityApiBase):
    """Quality API read baseline and status-machine write behavior."""

    @staticmethod
    def _source_snapshot() -> QualitySourceValidationSnapshot:
        return QualitySourceValidationSnapshot(
            master_data={"company": {"name": "COMP-A"}, "item": {"name": "ITEM-A"}},
            source=None,
        )

    def test_create_endpoint_returns_201_with_draft(self) -> None:
        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._source_snapshot(),
        ):
            response = self.client.post(
                "/api/quality/inspections",
                headers=self._headers(),
                json=self._payload(),
            )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["status"], "draft")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 1)
            self.assertEqual(session.query(LyQualityOperationLog).count(), 1)

    def test_cancelled_status_rejects_followup_writes(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-STATE-001",
            status="draft",
            result="partial",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("1"),
        )
        inspection_id = int(seeded["id"])

        with patch(
            "app.services.quality_service.QualitySourceValidator.validate_for_payload",
            return_value=self._source_snapshot(),
        ):
            confirm = self.client.post(
                f"/api/quality/inspections/{inspection_id}/confirm",
                headers=self._headers(),
                json={"remark": "确认"},
            )
        self.assertEqual(confirm.status_code, 200, confirm.text)
        self.assertEqual(confirm.json()["data"]["status"], "confirmed")

        cancel = self.client.post(
            f"/api/quality/inspections/{inspection_id}/cancel",
            headers=self._headers(),
            json={"reason": "取消"},
        )
        self.assertEqual(cancel.status_code, 200, cancel.text)
        self.assertEqual(cancel.json()["data"]["status"], "cancelled")

        update = self.client.patch(
            f"/api/quality/inspections/{inspection_id}",
            headers=self._headers(),
            json={"remark": "不应更新"},
        )
        self.assertEqual(update.status_code, 409)
        self.assertEqual(update.json()["code"], "QUALITY_INVALID_STATUS")

        defects = self.client.post(
            f"/api/quality/inspections/{inspection_id}/defects",
            headers=self._headers(),
            json={
                "defects": [
                    {
                        "defect_code": "DEF-999",
                        "defect_name": "不应录入",
                        "defect_qty": "1",
                        "severity": "minor",
                        "item_line_no": 1,
                    }
                ]
            },
        )
        self.assertEqual(defects.status_code, 409)
        self.assertEqual(defects.json()["code"], "QUALITY_INVALID_STATUS")

        confirm = self.client.post(
            f"/api/quality/inspections/{inspection_id}/confirm",
            headers=self._headers(),
            json={"remark": "不应确认"},
        )
        self.assertEqual(confirm.status_code, 409)
        self.assertEqual(confirm.json()["code"], "QUALITY_INVALID_STATUS")

        cancel = self.client.post(
            f"/api/quality/inspections/{inspection_id}/cancel",
            headers=self._headers(),
            json={"reason": "不应取消"},
        )
        self.assertEqual(cancel.status_code, 409)
        self.assertEqual(cancel.json()["code"], "QUALITY_INVALID_STATUS")

        with self.SessionLocal() as session:
            row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one()
            self.assertEqual(row.status, "cancelled")
            self.assertGreaterEqual(session.query(LyQualityOperationLog).count(), 3)

    def test_list_detail_statistics_export_keep_read_ability(self) -> None:
        first = self._insert_inspection(
            inspection_no="QI-READ-001",
            status="confirmed",
            result="pass",
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
        self._insert_inspection(
            inspection_no="QI-READ-002",
            status="cancelled",
            result="fail",
            inspected_qty=Decimal("5"),
            accepted_qty=Decimal("2"),
            rejected_qty=Decimal("3"),
            defect_qty=Decimal("1"),
        )

        list_resp = self.client.get("/api/quality/inspections", headers=self._headers())
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.json()["data"]["total"], 2)

        detail = self.client.get(f"/api/quality/inspections/{int(first['id'])}", headers=self._headers())
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["inspection_no"], first["inspection_no"])

        stats = self.client.get("/api/quality/statistics", headers=self._headers())
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.json()["data"]["total_count"], 1)
        self.assertEqual(Decimal(stats.json()["data"]["inspected_qty"]), Decimal("10"))

        export = self.client.get("/api/quality/export", headers=self._headers(role="Quality Viewer"))
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.json()["data"]["total"], 2)

    def test_diagnostic_requires_permission_and_records_security_audit(self) -> None:
        self._insert_inspection(
            inspection_no="QI-DIAG-001",
            status="draft",
            result="pending",
            inspected_qty=Decimal("3"),
            accepted_qty=Decimal("2"),
            rejected_qty=Decimal("1"),
            defect_qty=Decimal("1"),
        )

        response = self.client.get("/api/quality/diagnostic", headers=self._headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["total_count"], 1)
        self.assertEqual(response.json()["data"]["by_source_type"]["manual"], 1)

        denied = self.client.get("/api/quality/diagnostic", headers=self._headers(role="Quality Inspector"))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertGreaterEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_action_permission_denied_before_frozen_response(self) -> None:
        response = self.client.post(
            "/api/quality/inspections",
            headers=self._headers(role="Quality Viewer"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyQualityInspection).count(), 0)
            self.assertGreaterEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_detail_resource_denied_hides_existence(self) -> None:
        seeded = self._insert_inspection(
            inspection_no="QI-SCOPE-001",
            status="draft",
            result="pending",
            inspected_qty=Decimal("4"),
            accepted_qty=Decimal("4"),
            rejected_qty=Decimal("0"),
            defect_qty=Decimal("0"),
        )
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
            response = self.client.get(f"/api/quality/inspections/{int(seeded['id'])}", headers=self._headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESOURCE_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertGreaterEqual(session.query(LySecurityAuditLog).count(), 1)

    def test_only_allowed_routes_keep_outbox_internal_and_no_erpnext_route(self) -> None:
        methods_by_path = {route.path: route.methods for route in app.routes if getattr(route, "path", "").startswith("/api/quality")}
        self.assertTrue(methods_by_path)
        self.assertIn("/api/quality/internal/outbox-sync/run-once", methods_by_path)
        self.assertIn("/api/quality/inspections/{inspection_id}/outbox-status", methods_by_path)
        forbidden_paths = [path for path in methods_by_path if "erpnext" in path]
        self.assertEqual(forbidden_paths, [])


if __name__ == "__main__":
    unittest.main()
