"""Tests for sample-to-bulk production tracking reconcile."""

from __future__ import annotations

from datetime import date
from datetime import datetime
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
from app.models.production import LyProductionTrackingReconcile
from app.models.production import LyProductionTrackingReconcileBatch
from app.models.sample import Base as SampleBase
from app.models.sample import LySampleOrder
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionTrackingReconcileTest(unittest.TestCase):
    """Validate true DB writes, reads, audit, permissions and idempotency."""

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
            session.query(LyProductionTrackingReconcileBatch).delete()
            session.query(LyProductionTrackingReconcile).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LySampleOrder).delete()
            session.commit()

    @staticmethod
    def _headers(roles: str = "System Manager", request_id: str = "PTR-REQ-001") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "production.reconcile.user",
            "X-LY-Dev-Roles": roles,
            "X-Request-ID": request_id,
        }

    def _seed_sample(
        self,
        *,
        sample_no: str,
        status: str,
        bulk_handoff_no: str | None,
        due_date: date = date(2026, 6, 30),
    ) -> LySampleOrder:
        row = LySampleOrder(
            company="COMP-PTR",
            sample_no=sample_no,
            style_no="ST-PTR-001",
            style_name="PTR 测试款",
            customer="PTR 客户",
            factory="PTR 样衣组",
            sample_type="初样",
            stage="已封样",
            progress=100,
            pattern_maker="版师 PTR",
            sample_maker="样衣 PTR",
            due_date=due_date,
            status=status,
            image_tone="blue",
            owner_note="",
            bulk_handoff_no=bulk_handoff_no,
            bulk_handoff_status="已生成 A4 销售订单草稿" if bulk_handoff_no else None,
            created_by="seed",
            updated_by="seed",
            converted_by="seed" if status == "converted" else None,
            converted_at=datetime(2026, 6, 17, 10, 0, 0) if status == "converted" else None,
        )
        with self.SessionLocal() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def _seed_sales_order(self, *, sample: LySampleOrder, sales_order_no: str, qty: str = "36", rate: str = "128") -> None:
        with self.SessionLocal() as session:
            order = LySalesOrder(
                sales_order_no=sales_order_no,
                source_order_ref=f"SAMPLE-{sample.sample_no}",
                company="COMP-PTR",
                customer="PTR 客户",
                status="draft",
                docstatus=0,
                transaction_date=date(2026, 6, 18),
                delivery_date=date(2026, 7, 15),
                currency="CNY",
                grand_total="4608",
                idempotency_key=f"IDEMP-{sales_order_no}",
                request_hash=f"HASH-{sales_order_no}",
                scenario_tag="sample_convert",
                payload={"source": "test"},
                created_by="seed",
            )
            session.add(order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company="COMP-PTR",
                    line_no=1,
                    sales_order_item=f"{sales_order_no}-001",
                    item_code="ST-PTR-001",
                    item_name="PTR 测试款",
                    qty=qty,
                    planned_qty="0",
                    delivered_qty="0",
                    rate=rate,
                    amount="4608",
                    uom="件",
                    delivery_date=date(2026, 7, 15),
                )
            )
            session.commit()

    def test_generate_list_idempotency_and_conflict(self) -> None:
        sample = self._seed_sample(sample_no="SMP-PTR-001", status="converted", bulk_handoff_no="SO-PTR-001")
        self._seed_sales_order(sample=sample, sales_order_no="SO-PTR-001")

        payload = {
            "company": "COMP-PTR",
            "keyword": "SMP-PTR-001",
            "operation": "generate",
            "idempotency_key": "IDEMP-PTR-GEN-001",
        }
        created = self.client.post(
            "/api/production/tracking-reconciliations/generate",
            headers=self._headers(request_id="PTR-GEN-001"),
            json=payload,
        )
        self.assertEqual(created.status_code, 200)
        data = created.json()["data"]
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(data["matched_count"], 1)
        self.assertEqual(data["items"][0]["sample_no"], "SMP-PTR-001")
        self.assertEqual(data["items"][0]["sales_order"], "SO-PTR-001")
        self.assertEqual(data["items"][0]["diff_status"], "matched")
        self.assertEqual(data["items"][0]["order_qty"], "36.000000")

        listed = self.client.get(
            "/api/production/tracking-reconciliations?company=COMP-PTR&keyword=SMP-PTR-001&page=1&page_size=10",
            headers=self._headers(roles="production:read", request_id="PTR-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        retry = self.client.post(
            "/api/production/tracking-reconciliations/generate",
            headers=self._headers(request_id="PTR-GEN-002"),
            json=payload,
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["data"]["batch_no"], data["batch_no"])

        conflict_payload = {**payload, "keyword": "changed"}
        conflict = self.client.post(
            "/api/production/tracking-reconciliations/generate",
            headers=self._headers(request_id="PTR-GEN-003"),
            json=conflict_payload,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionTrackingReconcile).count(), 1)
            self.assertEqual(session.query(LyProductionTrackingReconcileBatch).count(), 1)
            self.assertEqual(
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "production",
                    LyOperationAuditLog.resource_type == "production_tracking_reconcile",
                    LyOperationAuditLog.result == "success",
                )
                .count(),
                2,
            )

    def test_unmatched_reconcile_and_write_permission_denial(self) -> None:
        self._seed_sample(sample_no="SMP-PTR-UNMATCHED", status="sealed", bulk_handoff_no=None)
        payload = {
            "company": "COMP-PTR",
            "keyword": "SMP-PTR-UNMATCHED",
            "operation": "generate",
            "idempotency_key": "IDEMP-PTR-GEN-UNMATCHED",
        }

        denied = self.client.post(
            "/api/production/tracking-reconciliations/generate",
            headers=self._headers(roles="production:read", request_id="PTR-DENY-001"),
            json=payload,
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")

        created = self.client.post(
            "/api/production/tracking-reconciliations/generate",
            headers=self._headers(request_id="PTR-GEN-UNMATCHED"),
            json=payload,
        )
        self.assertEqual(created.status_code, 200)
        item = created.json()["data"]["items"][0]
        self.assertEqual(item["sample_no"], "SMP-PTR-UNMATCHED")
        self.assertIsNone(item["sales_order"])
        self.assertEqual(item["diff_status"], "unmatched")
        self.assertIn("未找到本地大货销售订单", item["remark"])


if __name__ == "__main__":
    unittest.main()
