"""API tests for foundation template CRUD."""

from __future__ import annotations

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
from app.models.bom import Base as BomBase
from app.models.bom import LyFoundationTemplate
from app.models.bom import LyFoundationTemplateIdempotency
from app.models.bom import LyFoundationTemplateNode
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep


class FoundationTemplateApiTest(unittest.TestCase):
    """Validate template writes, auth, audit and idempotency."""

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
        BomBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[bom_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyFoundationTemplateIdempotency).delete()
            session.query(LyFoundationTemplateNode).delete()
            session.query(LyFoundationTemplate).delete()
            session.commit()

    @staticmethod
    def _headers(request_id: str = "FOUNDATION-TEMPLATE-REQ-001", role: str = "System Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "foundation.template.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _template_payload(code: str, idem: str) -> dict[str, str]:
        return {
            "company": "COMP-TPL",
            "template_code": code,
            "name": f"{code}-模板",
            "scene": "款式资料",
            "idempotency_key": idem,
        }

    @staticmethod
    def _node_payload(code: str, idem: str) -> dict[str, object]:
        return {
            "company": "COMP-TPL",
            "code": code,
            "name": f"{code}-节点",
            "node_type": "尺寸点",
            "required": True,
            "sort_no": 10,
            "owner": "版房",
            "idempotency_key": idem,
        }

    def test_template_and_node_crud_for_workmanship_and_size_spec(self) -> None:
        for path, prefix in [
            ("process-requirement-templates", "WK"),
            ("size-chart-templates", "SZ"),
        ]:
            with self.subTest(path=path):
                created = self.client.post(
                    f"/api/bom/{path}",
                    headers=self._headers(request_id=f"{prefix}-TPL-CREATE"),
                    json=self._template_payload(f"{prefix}-TPL-001", f"IDEM-{prefix}-TPL-C"),
                )
                self.assertEqual(created.status_code, 201)
                self.assertEqual(created.json()["code"], "0")
                template_id = int(created.json()["data"]["id"])

                node = self.client.post(
                    f"/api/bom/{path}/{template_id}/nodes",
                    headers=self._headers(request_id=f"{prefix}-NODE-CREATE"),
                    json=self._node_payload(f"{prefix}-NODE-001", f"IDEM-{prefix}-NODE-C"),
                )
                self.assertEqual(node.status_code, 201)
                node_id = int(node.json()["data"]["id"])

                listed = self.client.get(
                    f"/api/bom/{path}?company=COMP-TPL&keyword={prefix}-TPL",
                    headers=self._headers(request_id=f"{prefix}-TPL-LIST"),
                )
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(listed.json()["data"]["total"], 1)
                self.assertEqual(listed.json()["data"]["items"][0]["nodes"][0]["id"], node_id)

                updated_node = self.client.patch(
                    f"/api/bom/{path}/{template_id}/nodes/{node_id}",
                    headers=self._headers(request_id=f"{prefix}-NODE-UPDATE"),
                    json={
                        "company": "COMP-TPL",
                        "name": f"{prefix}-NODE-001-改",
                        "required": False,
                        "idempotency_key": f"IDEM-{prefix}-NODE-U",
                    },
                )
                self.assertEqual(updated_node.status_code, 200)
                self.assertFalse(updated_node.json()["data"]["required"])

                stopped_node = self.client.post(
                    f"/api/bom/{path}/{template_id}/nodes/{node_id}/deactivate",
                    headers=self._headers(request_id=f"{prefix}-NODE-STOP"),
                    json={
                        "company": "COMP-TPL",
                        "reason": "停用节点测试",
                        "idempotency_key": f"IDEM-{prefix}-NODE-D",
                    },
                )
                self.assertEqual(stopped_node.status_code, 200)
                self.assertEqual(stopped_node.json()["data"]["status"], "inactive")

                stopped_template = self.client.post(
                    f"/api/bom/{path}/{template_id}/deactivate",
                    headers=self._headers(request_id=f"{prefix}-TPL-STOP"),
                    json={
                        "company": "COMP-TPL",
                        "reason": "停用模板测试",
                        "idempotency_key": f"IDEM-{prefix}-TPL-D",
                    },
                )
                self.assertEqual(stopped_template.status_code, 200)
                self.assertEqual(stopped_template.json()["data"]["status"], "inactive")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFoundationTemplate).count(), 2)
            self.assertEqual(session.query(LyFoundationTemplateNode).count(), 2)
            self.assertEqual(session.query(LyFoundationTemplateIdempotency).count(), 10)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "bom").count(), 10)

    def test_template_create_idempotency_conflict_is_409(self) -> None:
        payload = self._template_payload("WK-IDEM-001", "IDEM-WK-IDEM")
        created = self.client.post(
            "/api/bom/process-requirement-templates",
            headers=self._headers(request_id="WK-IDEM-CREATE"),
            json=payload,
        )
        self.assertEqual(created.status_code, 201)

        changed = dict(payload)
        changed["name"] = "不同名称"
        conflict = self.client.post(
            "/api/bom/process-requirement-templates",
            headers=self._headers(request_id="WK-IDEM-CONFLICT"),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "BOM_TEMPLATE_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            failed = session.query(LyOperationAuditLog).filter(LyOperationAuditLog.result == "failed").one()
            self.assertEqual(failed.error_code, "BOM_TEMPLATE_IDEMPOTENCY_CONFLICT")

    def test_template_and_node_without_code_auto_generate(self) -> None:
        template_payload = {
            "company": "COMP-TPL",
            "template_code": "",
            "name": "自动编码工艺模板",
            "scene": "款式资料",
            "idempotency_key": "IDEM-WK-TPL-AUTO",
        }
        created = self.client.post(
            "/api/bom/process-requirement-templates",
            headers=self._headers(request_id="WK-TPL-AUTO-CREATE"),
            json=template_payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        template_data = created.json()["data"]
        self.assertRegex(template_data["template_code"], r"^WK-TPL-\d{6}$")

        replay = self.client.post(
            "/api/bom/process-requirement-templates",
            headers=self._headers(request_id="WK-TPL-AUTO-REPLAY"),
            json=template_payload,
        )
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json()["data"]["template_code"], template_data["template_code"])

        node_payload = {
            "company": "COMP-TPL",
            "code": "",
            "name": "自动编码节点",
            "node_type": "确认项",
            "required": True,
            "sort_no": 10,
            "owner": "版房",
            "idempotency_key": "IDEM-WK-NODE-AUTO",
        }
        node = self.client.post(
            f"/api/bom/process-requirement-templates/{template_data['id']}/nodes",
            headers=self._headers(request_id="WK-NODE-AUTO-CREATE"),
            json=node_payload,
        )
        self.assertEqual(node.status_code, 201, node.text)
        node_data = node.json()["data"]
        self.assertRegex(node_data["code"], r"^WK-NODE-\d{6}$")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFoundationTemplate).count(), 1)
            self.assertEqual(session.query(LyFoundationTemplateNode).count(), 1)
