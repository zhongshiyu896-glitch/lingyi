"""API tests for FastAPI-native production follow-up templates."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionFollowupTemplate
from app.models.production import LyProductionFollowupTemplateOperation
from app.models.production import LyProductionPlan
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionFollowupTemplateApiTest(unittest.TestCase):
    """Validate template writes, auth, audit and idempotency for the existing page."""

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
        ProductionBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyProductionFollowupTemplateOperation).delete()
            session.query(LyProductionFollowupTemplate).delete()
            session.query(LyProductionPlan).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Production Manager", request_id: str = "PROD-FOLLOWUP-TPL-REQ") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "prod.followup.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _payload(template_no: str, idem: str) -> dict[str, object]:
        return {
            "company": "COMP-A",
            "template_no": template_no,
            "template_name": f"{template_no} 大货跟进模板",
            "template_type": "排期跟进",
            "trigger_node": "裁床开裁",
            "followup_role": "生产跟单",
            "followup_frequency": "每日",
            "sla_hours": 24,
            "item_code": "STYLE-FOLLOW-001",
            "status": "enabled",
            "idempotency_key": idem,
        }

    def _seed_plan(self) -> int:
        with self.SessionLocal() as session:
            row = LyProductionPlan(
                id=701,
                plan_no="PP-FOLLOW-701",
                company="COMP-A",
                sales_order="SO-FOLLOW-701",
                sales_order_item="SOI-FOLLOW-701",
                customer="CUST-A",
                item_code="STYLE-DERIVED-701",
                bom_id=1,
                bom_version="V1",
                planned_qty=Decimal("12"),
                status="planned",
                idempotency_key="idem-plan-701",
                request_hash="hash-plan-701",
                created_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def test_template_create_update_copy_deactivate_and_list(self) -> None:
        created = self.client.post(
            "/api/production/followup-templates",
            headers=self._headers(request_id="PROD-FOLLOWUP-CREATE"),
            json=self._payload("FTPL-A-001", "IDEM-PROD-FOLLOW-C"),
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["code"], "0")
        template_id = int(created.json()["data"]["template_id"])

        retry = self.client.post(
            "/api/production/followup-templates",
            headers=self._headers(request_id="PROD-FOLLOWUP-CREATE-RETRY"),
            json=self._payload("FTPL-A-001", "IDEM-PROD-FOLLOW-C"),
        )
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(int(retry.json()["data"]["template_id"]), template_id)

        listed = self.client.get(
            "/api/production/followup-templates?company=COMP-A&keyword=FTPL-A-001&page=1&page_size=10",
            headers=self._headers(request_id="PROD-FOLLOWUP-LIST"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        updated = self.client.patch(
            f"/api/production/followup-templates/{template_id}",
            headers=self._headers(request_id="PROD-FOLLOWUP-UPDATE"),
            json={
                "company": "COMP-A",
                "trigger_node": "中查完成",
                "followup_role": "车间主管",
                "sla_hours": 12,
                "idempotency_key": "IDEM-PROD-FOLLOW-U",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["data"]["trigger_node"], "中查完成")

        copied = self.client.post(
            f"/api/production/followup-templates/{template_id}/copy",
            headers=self._headers(request_id="PROD-FOLLOWUP-COPY"),
            json={
                "company": "COMP-A",
                "template_no": "FTPL-A-001-COPY",
                "template_name": "FTPL-A-001 复制模板",
                "idempotency_key": "IDEM-PROD-FOLLOW-COPY",
            },
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        copied_id = int(copied.json()["data"]["template_id"])
        self.assertNotEqual(copied_id, template_id)

        stopped = self.client.post(
            f"/api/production/followup-templates/{copied_id}/deactivate",
            headers=self._headers(request_id="PROD-FOLLOWUP-STOP"),
            json={
                "company": "COMP-A",
                "reason": "旧模板停用",
                "idempotency_key": "IDEM-PROD-FOLLOW-D",
            },
        )
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()["data"]["status"], "disabled")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionFollowupTemplate).count(), 2)
            self.assertEqual(session.query(LyProductionFollowupTemplateOperation).count(), 4)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "production").count(), 5)

    def test_copy_derived_plan_template_creates_persisted_template(self) -> None:
        source_template_id = self._seed_plan()
        listed = self.client.get(
            "/api/production/followup-templates?company=COMP-A&keyword=PP-FOLLOW-701&page=1&page_size=10",
            headers=self._headers(request_id="PROD-FOLLOWUP-DERIVED-LIST"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["items"][0]["template_no"], "FT-PP-FOLLOW-701")

        copied = self.client.post(
            f"/api/production/followup-templates/{source_template_id}/copy",
            headers=self._headers(request_id="PROD-FOLLOWUP-DERIVED-COPY"),
            json={
                "company": "COMP-A",
                "template_no": "FTPL-DERIVED-COPY",
                "idempotency_key": "IDEM-PROD-FOLLOW-DERIVED-COPY",
            },
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        self.assertEqual(copied.json()["data"]["template_no"], "FTPL-DERIVED-COPY")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionFollowupTemplate).count(), 1)

    def test_create_idempotency_conflict_is_409_and_audited(self) -> None:
        payload = self._payload("FTPL-IDEM-001", "IDEM-PROD-FOLLOW-IDEM")
        created = self.client.post(
            "/api/production/followup-templates",
            headers=self._headers(request_id="PROD-FOLLOWUP-IDEM-CREATE"),
            json=payload,
        )
        self.assertEqual(created.status_code, 200)

        changed = dict(payload)
        changed["template_name"] = "不同模板名"
        conflict = self.client.post(
            "/api/production/followup-templates",
            headers=self._headers(request_id="PROD-FOLLOWUP-IDEM-CONFLICT"),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            failed = session.query(LyOperationAuditLog).filter(LyOperationAuditLog.result == "failed").one()
            self.assertEqual(failed.error_code, "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_forbidden_without_production_manager_action(self) -> None:
        denied = self.client.post(
            "/api/production/followup-templates",
            headers=self._headers(role="Viewer", request_id="PROD-FOLLOWUP-FORBIDDEN"),
            json=self._payload("FTPL-DENIED-001", "IDEM-PROD-FOLLOW-DENIED"),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionFollowupTemplate).count(), 0)


if __name__ == "__main__":
    unittest.main()
