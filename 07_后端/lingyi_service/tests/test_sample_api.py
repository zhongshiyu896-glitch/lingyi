"""API tests for FastAPI-native sample workflow."""

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
from app.models.sample import Base as SampleBase
from app.models.sample import LySampleIdempotency
from app.models.sample import LySampleOrder
from app.models.sample import LySampleTrackingNode
from app.models.sample import LySampleTrackingTemplate
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.sample import get_db_session as sample_db_dep


class SampleApiTest(unittest.TestCase):
    """Validate sample workflow true DB writes, auth, audit and idempotency."""

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
        StyleMasterBase.metadata.create_all(bind=cls.engine)
        SampleBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sample_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sample_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LySampleIdempotency).delete()
            session.query(LySampleTrackingNode).delete()
            session.query(LySampleTrackingTemplate).delete()
            session.query(LySampleOrder).delete()
            session.query(LyStyleMaster).delete()
            self._seed_style(session, style_no="ST-A3-001", style_name="A3 样衣款")
            self._seed_style(session, style_no="ST-A3-002", style_name="A3 样衣款修改")
            self._seed_style(session, style_no="ST-A3-DISABLED", style_name="停用款", status="disabled")
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager", request_id: str = "SAMPLE-REQ-001") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "sample.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _order_payload(sample_no: str = "SMP-A3-001", idempotency_key: str = "IDEMP-SMP-A3-001-C") -> dict:
        return {
            "operation": "create",
            "company": "COMP-A",
            "sample_no": sample_no,
            "style_no": "ST-A3-001",
            "style_name": "A3 样衣款",
            "customer": "A3 客户",
            "factory": "A3 样衣组",
            "sample_type": "初样",
            "stage": "建档",
            "progress": 0,
            "pattern_maker": "版师 A",
            "sample_maker": "样衣工 A",
            "due_date": "2026-06-30",
            "status": "draft",
            "image_tone": "blue",
            "idempotency_key": idempotency_key,
        }

    @staticmethod
    def _seed_style(session, *, style_no: str, style_name: str, status: str = "enabled") -> None:
        session.add(
            LyStyleMaster(
                company="COMP-A",
                ys_style_no=style_no,
                ys_style_name_cn=style_name,
                ys_season="SS",
                ys_year="2026",
                ys_brand="LY",
                ys_style_status=status,
                colors=[],
                sizes=[],
                version=1,
                created_by="test",
                updated_by="test",
            )
        )

    def test_sample_order_create_list_update_submit_reverse(self) -> None:
        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-ORDER-001"),
            json=self._order_payload(),
        )
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["sample_no"], "SMP-A3-001")
        order_id = int(body["data"]["id"])

        listed = self.client.get(
            "/api/sample/orders?company=COMP-A&keyword=SMP-A3&page=1&page_size=10",
            headers=self._headers(request_id="SAMPLE-ORDER-002"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        updated = self.client.patch(
            f"/api/sample/orders/{order_id}",
            headers=self._headers(request_id="SAMPLE-ORDER-003"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "style_no": "ST-A3-002",
                "style_name": "前端传入款名不作为准",
                "stage": "打版中",
                "progress": 30,
                "idempotency_key": "IDEMP-SMP-A3-001-U",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["style_no"], "ST-A3-002")
        self.assertEqual(updated.json()["data"]["style_name"], "A3 样衣款修改")
        self.assertEqual(updated.json()["data"]["version"], 2)

        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers(request_id="SAMPLE-ORDER-004"),
            json={
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-001-S",
            },
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["data"]["status"], "pending")

        reversed_response = self.client.post(
            f"/api/sample/orders/{order_id}/reverse",
            headers=self._headers(request_id="SAMPLE-ORDER-005"),
            json={
                "company": "COMP-A",
                "reason": "返改",
                "idempotency_key": "IDEMP-SMP-A3-001-R",
            },
        )
        self.assertEqual(reversed_response.status_code, 200)
        self.assertEqual(reversed_response.json()["data"]["status"], "reversed")
        self.assertEqual(reversed_response.json()["data"]["reverse_reason"], "返改")

        with self.SessionLocal() as session:
            row = session.query(LySampleOrder).one()
            self.assertEqual(row.status, "reversed")
            self.assertEqual(row.reverse_reason, "返改")
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "sample").count(), 4)

    def test_sample_order_idempotency_conflict_and_permission(self) -> None:
        first = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-IDEM-001"),
            json=self._order_payload(sample_no="SMP-A3-IDEM", idempotency_key="IDEMP-SMP-A3-IDEM"),
        )
        retry = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-IDEM-002"),
            json=self._order_payload(sample_no="SMP-A3-IDEM", idempotency_key="IDEMP-SMP-A3-IDEM"),
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(first.json()["data"]["id"], retry.json()["data"]["id"])

        changed = self._order_payload(sample_no="SMP-A3-IDEM", idempotency_key="IDEMP-SMP-A3-IDEM")
        changed["style_name"] = "changed"
        conflict = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-IDEM-003"),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SAMPLE_IDEMPOTENCY_CONFLICT")

        denied = self.client.post(
            "/api/sample/orders",
            headers=self._headers(role="Sales Manager", request_id="SAMPLE-DENY-001"),
            json=self._order_payload(sample_no="SMP-A3-DENY", idempotency_key="IDEMP-SMP-A3-DENY"),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")

    def test_sample_order_requires_enabled_style_master(self) -> None:
        missing = self._order_payload(sample_no="SMP-A3-MISSING", idempotency_key="IDEMP-SMP-A3-MISSING")
        missing["style_no"] = "ST-A3-MISSING"
        missing_response = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-STYLE-MISSING"),
            json=missing,
        )
        self.assertEqual(missing_response.status_code, 409)
        self.assertEqual(missing_response.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

        disabled = self._order_payload(sample_no="SMP-A3-DISABLED", idempotency_key="IDEMP-SMP-A3-DISABLED")
        disabled["style_no"] = "ST-A3-DISABLED"
        disabled_response = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-STYLE-DISABLED"),
            json=disabled,
        )
        self.assertEqual(disabled_response.status_code, 409)
        self.assertEqual(disabled_response.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

    def test_sample_order_cannot_directly_write_flow_status(self) -> None:
        direct_sealed = self._order_payload(sample_no="SMP-A3-DIRECT-SEAL", idempotency_key="IDEMP-SMP-A3-DIRECT-SEAL")
        direct_sealed["status"] = "sealed"
        direct_response = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-DIRECT-SEAL-001"),
            json=direct_sealed,
        )
        self.assertEqual(direct_response.status_code, 409)
        self.assertEqual(direct_response.json()["code"], "SAMPLE_INVALID_STATUS")

        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-DIRECT-SEAL-002"),
            json=self._order_payload(sample_no="SMP-A3-DIRECT-EDIT", idempotency_key="IDEMP-SMP-A3-DIRECT-EDIT-C"),
        )
        order_id = int(created.json()["data"]["id"])
        direct_update = self.client.patch(
            f"/api/sample/orders/{order_id}",
            headers=self._headers(request_id="SAMPLE-DIRECT-SEAL-003"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "status": "sealed",
                "idempotency_key": "IDEMP-SMP-A3-DIRECT-EDIT-U",
            },
        )
        self.assertEqual(direct_update.status_code, 409)
        self.assertEqual(direct_update.json()["code"], "SAMPLE_INVALID_STATUS")

    def test_sample_order_convert_creates_sales_order_draft(self) -> None:
        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-CONVERT-001"),
            json=self._order_payload(sample_no="SMP-A3-CONVERT", idempotency_key="IDEMP-SMP-A3-CONVERT-C"),
        )
        self.assertEqual(created.status_code, 201)
        order_id = int(created.json()["data"]["id"])

        blocked = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers(request_id="SAMPLE-CONVERT-BLOCKED"),
            json={
                "operation": "convert",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-BLOCKED",
            },
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "SAMPLE_INVALID_STATUS")

        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers(request_id="SAMPLE-CONVERT-SUBMIT"),
            json={
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-S",
            },
        )
        self.assertEqual(submitted.status_code, 200)
        sealed = self.client.post(
            f"/api/sample/orders/{order_id}/seal",
            headers=self._headers(request_id="SAMPLE-CONVERT-SEAL"),
            json={
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-SEAL",
            },
        )
        self.assertEqual(sealed.status_code, 200)
        self.assertEqual(sealed.json()["data"]["status"], "sealed")

        converted = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers(request_id="SAMPLE-CONVERT-002"),
            json={
                "operation": "convert",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-X",
            },
        )
        self.assertEqual(converted.status_code, 200)
        data = converted.json()["data"]
        self.assertEqual(data["status"], "converted")
        self.assertTrue(data["bulk_handoff_no"].startswith("SO-"))
        self.assertEqual(data["bulk_handoff_status"], "已生成 A4 销售订单草稿")

        with self.SessionLocal() as session:
            row = session.query(LySampleOrder).one()
            sales_order = session.query(LySalesOrder).one()
            sales_item = session.query(LySalesOrderItem).one()
            self.assertEqual(row.status, "converted")
            self.assertEqual(row.bulk_handoff_no, sales_order.sales_order_no)
            self.assertEqual(sales_order.status, "draft")
            self.assertEqual(sales_order.customer, "A3 客户")
            self.assertEqual(sales_order.source_order_ref, "SAMPLE-SMP-A3-CONVERT")
            self.assertEqual(sales_item.item_code, "ST-A3-001")
            self.assertEqual(str(sales_item.qty), "1.000000")
            self.assertEqual(session.query(LySalesOrderIdempotency).count(), 1)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "sample").count(), 5)

    def test_sample_order_convert_can_use_target_sales_order_no(self) -> None:
        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers(request_id="SAMPLE-CONVERT-TARGET-001"),
            json=self._order_payload(sample_no="SMP-A3-CONVERT-TARGET", idempotency_key="IDEMP-SMP-A3-CONVERT-TARGET-C"),
        )
        self.assertEqual(created.status_code, 201)
        order_id = int(created.json()["data"]["id"])
        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers(request_id="SAMPLE-CONVERT-TARGET-SUBMIT"),
            json={
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-TARGET-S",
            },
        )
        self.assertEqual(submitted.status_code, 200)
        sealed = self.client.post(
            f"/api/sample/orders/{order_id}/seal",
            headers=self._headers(request_id="SAMPLE-CONVERT-TARGET-SEAL"),
            json={
                "company": "COMP-A",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-TARGET-SEAL",
            },
        )
        self.assertEqual(sealed.status_code, 200)

        converted = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers(request_id="SAMPLE-CONVERT-TARGET-002"),
            json={
                "operation": "convert",
                "company": "COMP-A",
                "target_sales_order": "SO-SAMPLE-A3-TARGET",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-TARGET-X",
            },
        )
        self.assertEqual(converted.status_code, 200)
        self.assertEqual(converted.json()["data"]["bulk_handoff_no"], "SO-SAMPLE-A3-TARGET")

        retry = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers(request_id="SAMPLE-CONVERT-TARGET-003"),
            json={
                "operation": "convert",
                "company": "COMP-A",
                "target_sales_order": "SO-SAMPLE-A3-TARGET",
                "idempotency_key": "IDEMP-SMP-A3-CONVERT-TARGET-X",
            },
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["data"]["bulk_handoff_no"], "SO-SAMPLE-A3-TARGET")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySalesOrder).count(), 1)

    def test_tracking_template_and_node_create(self) -> None:
        created = self.client.post(
            "/api/sample/tracking-templates",
            headers=self._headers(request_id="SAMPLE-TPL-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "template_code": "STPL-A3-001",
                "name": "A3 样衣跟进模板",
                "category": "女装",
                "group": "打样",
                "status": "enabled",
                "owner": "设计",
                "version": "V1",
                "summary": "A3 模板",
                "idempotency_key": "IDEMP-STPL-A3-001-C",
            },
        )
        self.assertEqual(created.status_code, 201)
        template_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["status"], "enabled")

        node = self.client.post(
            f"/api/sample/tracking-templates/{template_id}/nodes",
            headers=self._headers(request_id="SAMPLE-TPL-002"),
            json={
                "operation": "create_node",
                "company": "COMP-A",
                "name": "纸样确认",
                "role": "版师",
                "lead_time": "1天",
                "status": "required",
                "gate": "纸样确认完成",
                "output": "纸样",
                "reminder": "到期提醒",
                "sequence_no": 10,
                "idempotency_key": "IDEMP-STPL-A3-001-N",
            },
        )
        self.assertEqual(node.status_code, 201)
        node_id = int(node.json()["data"]["id"])

        updated_template = self.client.patch(
            f"/api/sample/tracking-templates/{template_id}",
            headers=self._headers(request_id="SAMPLE-TPL-004"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "name": "A3 样衣跟进模板改",
                "summary": "A3 模板改",
                "idempotency_key": "IDEMP-STPL-A3-001-U",
            },
        )
        self.assertEqual(updated_template.status_code, 200)
        self.assertEqual(updated_template.json()["data"]["name"], "A3 样衣跟进模板改")

        updated_node = self.client.patch(
            f"/api/sample/tracking-templates/{template_id}/nodes/{node_id}",
            headers=self._headers(request_id="SAMPLE-TPL-005"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "name": "纸样确认改",
                "sequence_no": 30,
                "idempotency_key": "IDEMP-STPL-A3-001-NU",
            },
        )
        self.assertEqual(updated_node.status_code, 200)
        self.assertEqual(updated_node.json()["data"]["name"], "纸样确认改")
        self.assertEqual(updated_node.json()["data"]["sequence_no"], 30)

        deactivated = self.client.post(
            f"/api/sample/tracking-templates/{template_id}/deactivate",
            headers=self._headers(request_id="SAMPLE-TPL-006"),
            json={
                "company": "COMP-A",
                "reason": "停用旧版",
                "idempotency_key": "IDEMP-STPL-A3-001-D",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(deactivated.json()["data"]["status"], "disabled")

        listed = self.client.get(
            "/api/sample/tracking-templates?company=COMP-A&keyword=A3&page=1&page_size=10",
            headers=self._headers(request_id="SAMPLE-TPL-007"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)
        self.assertEqual(listed.json()["data"]["items"][0]["nodes"][0]["name"], "纸样确认改")
        self.assertEqual(listed.json()["data"]["items"][0]["nodes"][0]["sequence_no"], 30)

        deleted = self.client.post(
            f"/api/sample/tracking-templates/{template_id}/nodes/{node_id}/delete",
            headers=self._headers(request_id="SAMPLE-TPL-008"),
            json={
                "company": "COMP-A",
                "reason": "节点废弃",
                "idempotency_key": "IDEMP-STPL-A3-001-ND",
            },
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["data"]["deleted"], True)

        deleted_retry = self.client.post(
            f"/api/sample/tracking-templates/{template_id}/nodes/{node_id}/delete",
            headers=self._headers(request_id="SAMPLE-TPL-009"),
            json={
                "company": "COMP-A",
                "reason": "节点废弃",
                "idempotency_key": "IDEMP-STPL-A3-001-ND",
            },
        )
        self.assertEqual(deleted_retry.status_code, 200)
        self.assertEqual(deleted_retry.json()["data"]["deleted"], True)

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySampleTrackingNode).count(), 0)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "sample").count(), 7)


if __name__ == "__main__":
    unittest.main()
