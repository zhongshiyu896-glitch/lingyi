"""Tests for production plan CRUD/material/outbox baseline (TASK-004A)."""

from __future__ import annotations

from datetime import datetime
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
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionWorkOrderLink
from app.models.production import LyProductionWorkOrderOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextSalesOrder
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem


class ProductionPlanTest(unittest.TestCase):
    """Validate production plan creation rules and outbox baseline."""

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
        ProductionBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=101,
                    bom_no="BOM-PROD-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1001,
                    bom_id=101,
                    material_item_code="MAT-A",
                    qty_per_piece=Decimal("1.5"),
                    loss_rate=Decimal("0.1"),
                    uom="Nos",
                )
            )
            session.commit()

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
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyProductionWorkOrderOutbox).delete()
            session.query(LyProductionPlan).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Production Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "prod.plan.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _sales_order(*, qty: str = "100", docstatus: int = 1, status: str = "To Deliver") -> ERPNextSalesOrder:
        return ERPNextSalesOrder(
            name="SO-TEST-001",
            docstatus=docstatus,
            status=status,
            company="COMP-A",
            customer="CUST-A",
            items=(
                ERPNextSalesOrderItem(name="SOI-001", item_code="ITEM-A", qty=Decimal(qty)),
            ),
        )

    @staticmethod
    def _payload(
        *,
        idempotency_key: str,
        planned_qty: str = "10",
        planned_start_date: str | None = None,
    ) -> dict[str, str]:
        payload = {
            "sales_order": "SO-TEST-001",
            "item_code": "ITEM-A",
            "planned_qty": planned_qty,
            "idempotency_key": idempotency_key,
        }
        if planned_start_date:
            payload["planned_start_date"] = planned_start_date
        return payload

    @staticmethod
    def _create_work_order_payload(*, idempotency_key: str) -> dict[str, str]:
        return {
            "fg_warehouse": "FG-WH-001",
            "wip_warehouse": "WIP-WH-001",
            "start_date": "2026-04-13",
            "idempotency_key": idempotency_key,
        }

    def _set_plan_status(self, *, plan_id: int, status: str) -> None:
        with self.SessionLocal() as session:
            row = session.query(LyProductionPlan).filter(LyProductionPlan.id == int(plan_id)).first()
            self.assertIsNotNone(row)
            row.status = status
            session.commit()

    def test_create_plan_success_and_idempotent_retry(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            response_1 = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-001", planned_qty="10"),
            )
            response_2 = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-001", planned_qty="10"),
            )

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        data_1 = response_1.json()["data"]
        data_2 = response_2.json()["data"]
        self.assertEqual(data_1["plan_id"], data_2["plan_id"])
        self.assertEqual(data_1["status"], "planned")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 1)

    def test_create_plan_idempotency_conflict_when_payload_changed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            first = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-002", planned_qty="10"),
            )
            second = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-002", planned_qty="11"),
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_plan_idempotency_conflict_when_planned_start_date_changed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            first = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-start-date-conflict",
                    planned_qty="10",
                    planned_start_date="2026-04-13",
                ),
            )
            second = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-start-date-conflict",
                    planned_qty="10",
                    planned_start_date="2026-04-14",
                ),
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_plan_with_planned_start_date_returns_in_list_and_detail(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(
                    idempotency_key="idem-pp-with-start-date",
                    planned_qty="10",
                    planned_start_date="2026-04-13",
                ),
            )

        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        list_response = self.client.get(
            "/api/production/plans?page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(list_response.status_code, 200)
        rows = list_response.json()["data"]["items"]
        self.assertTrue(rows)
        matched = next((row for row in rows if int(row["id"]) == plan_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["planned_start_date"], "2026-04-13")

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["planned_start_date"], "2026-04-13")

    def test_create_plan_rejects_unapproved_sales_order(self) -> None:
        with patch.object(
            ERPNextProductionAdapter,
            "get_sales_order",
            return_value=self._sales_order(docstatus=0, status="Draft"),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-003", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_NOT_APPROVED")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 0)

    def test_create_plan_rejects_closed_or_cancelled_sales_order(self) -> None:
        with patch.object(
            ERPNextProductionAdapter,
            "get_sales_order",
            return_value=self._sales_order(docstatus=1, status="Closed"),
        ):
            closed_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-closed", planned_qty="10"),
            )
        self.assertEqual(closed_response.status_code, 409)
        self.assertEqual(closed_response.json()["code"], "PRODUCTION_SO_CLOSED_OR_CANCELLED")

        with patch.object(
            ERPNextProductionAdapter,
            "get_sales_order",
            return_value=self._sales_order(docstatus=1, status="Cancelled"),
        ):
            cancelled_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-cancelled", planned_qty="10"),
            )
        self.assertEqual(cancelled_response.status_code, 409)
        self.assertEqual(cancelled_response.json()["code"], "PRODUCTION_SO_CLOSED_OR_CANCELLED")

    def test_create_plan_rejects_ambiguous_sales_order_item(self) -> None:
        so = ERPNextSalesOrder(
            name="SO-TEST-001",
            docstatus=1,
            status="To Deliver",
            company="COMP-A",
            customer="CUST-A",
            items=(
                ERPNextSalesOrderItem(name="SOI-001", item_code="ITEM-A", qty=Decimal("10")),
                ERPNextSalesOrderItem(name="SOI-002", item_code="ITEM-A", qty=Decimal("20")),
            ),
        )
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=so):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-004", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_SO_ITEM_AMBIGUOUS")

    def test_create_plan_rejects_when_planned_qty_exceeded(self) -> None:
        with patch.object(
            ERPNextProductionAdapter,
            "get_sales_order",
            return_value=self._sales_order(qty="8"),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-005", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_PLANNED_QTY_EXCEEDED")

    def test_create_plan_rejects_bom_item_mismatch(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=102,
                    bom_no="BOM-PROD-002",
                    item_code="ITEM-B",
                    version_no="v1",
                    is_default=False,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json={
                    **self._payload(idempotency_key="idem-pp-bom-mismatch", planned_qty="10"),
                    "bom_id": 102,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_BOM_ITEM_MISMATCH")

    def test_create_plan_database_write_failed_returns_database_write_failed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()), patch(
            "app.routers.production._commit_or_raise_write_error",
            side_effect=DatabaseWriteFailed(),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-db-failed", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

    def test_create_plan_audit_write_failed_returns_audit_write_failed(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()), patch(
            "app.routers.production.AuditService.record_success",
            side_effect=AuditWriteFailed(),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-audit-failed", planned_qty="10"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")

    def test_material_check_and_create_work_order_creates_local_outbox_candidate(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-006", planned_qty="12"),
            )

        self.assertEqual(create_response.status_code, 200)
        plan_id = create_response.json()["data"]["plan_id"]

        check_response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(),
            json={"warehouse": "WIP Warehouse - LY"},
        )
        self.assertEqual(check_response.status_code, 200)
        self.assertEqual(check_response.json()["data"]["snapshot_count"], 1)
        self.assertEqual(check_response.json()["data"]["items"][0]["warehouse"], "WIP Warehouse - LY")
        self.assertIsNotNone(check_response.json()["data"]["items"][0]["checked_at"])

        outbox_response = self.client.post(
            f"/api/production/plans/{plan_id}/create-work-order",
            headers=self._headers(),
            json=self._create_work_order_payload(idempotency_key="idem-create-wo-001"),
        )
        self.assertEqual(outbox_response.status_code, 200)
        self.assertEqual(outbox_response.json()["code"], "0")
        self.assertGreater(int(outbox_response.json()["data"]["outbox_id"]), 0)
        self.assertEqual(outbox_response.json()["data"]["sync_status"], "pending")
        self.assertTrue(str(outbox_response.json()["data"]["event_key"]).startswith("pwo:"))

        with self.SessionLocal() as session:
            outbox_rows = (
                session.query(LyProductionWorkOrderOutbox)
                .filter(LyProductionWorkOrderOutbox.plan_id == plan_id)
                .all()
            )
            self.assertEqual(len(outbox_rows), 1)
            self.assertEqual(outbox_rows[0].status, "pending")

    def test_plan_detail_returns_work_order_link_fields(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-wo-link-detail", planned_qty="12"),
            )
        plan_id = int(create_response.json()["data"]["plan_id"])

        with self.SessionLocal() as session:
            session.add(
                LyProductionWorkOrderLink(
                    plan_id=plan_id,
                    work_order="WO-DETAIL-001",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    last_synced_at=datetime(2026, 4, 13, 9, 30, 0),
                    created_by="seed",
                )
            )
            session.commit()

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        data = detail_response.json()["data"]
        self.assertEqual(data["work_order"], "WO-DETAIL-001")
        self.assertEqual(data["erpnext_docstatus"], 1)
        self.assertEqual(data["erpnext_status"], "Submitted")
        self.assertEqual(data["sync_status"], "succeeded")
        self.assertIsNotNone(data["last_synced_at"])
        self.assertTrue(data["write_entry_frozen"])
        self.assertIn("TASK-015E", data["write_entry_frozen_reason"])
        self.assertIn("sync-job-cards", data["write_entry_frozen_reason"])
        self.assertIn("create-work-order", data["write_entry_frozen_reason"])
        self.assertNotIn("普通前端仍冻结 create-work-order / sync-job-cards", data["write_entry_frozen_reason"])

    def test_material_check_requires_warehouse(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-warehouse-required", planned_qty="12"),
            )
        plan_id = create_response.json()["data"]["plan_id"]

        response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(),
            json={},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "PRODUCTION_WAREHOUSE_REQUIRED")

    def test_material_check_allows_frozen_status_whitelist(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-status-whitelist", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        allowed_statuses = [
            "planned",
            "material_checked",
            "work_order_pending",
            "work_order_created",
        ]
        for status in allowed_statuses:
            self._set_plan_status(plan_id=plan_id, status=status)
            response = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers=self._headers(),
                json={"warehouse": "WIP Warehouse - LY"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["code"], "0")
            self.assertEqual(response.json()["data"]["plan_id"], plan_id)

    def test_material_check_rejects_status_outside_whitelist(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-material-status-invalid", planned_qty="12"),
            )
        self.assertEqual(create_response.status_code, 200)
        plan_id = int(create_response.json()["data"]["plan_id"])

        self._set_plan_status(plan_id=plan_id, status="cancelled")
        response = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(),
            json={"warehouse": "WIP Warehouse - LY"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PRODUCTION_MATERIAL_CHECK_STATUS_INVALID")
        self.assertEqual(response.json()["message"], "当前生产计划状态不允许执行物料检查")

    def test_create_work_order_candidate_returns_unified_envelope(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()):
            create_response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json=self._payload(idempotency_key="idem-pp-create-wo-required", planned_qty="12"),
            )
        plan_id = create_response.json()["data"]["plan_id"]

        frozen_response = self.client.post(
            f"/api/production/plans/{plan_id}/create-work-order",
            headers=self._headers(),
            json={
                "fg_warehouse": "FG-WH",
                "wip_warehouse": "WIP-WH",
                "start_date": "2026-04-13",
                "idempotency_key": "idem-create-wo-frozen",
            },
        )
        self.assertEqual(frozen_response.status_code, 200)
        payload = frozen_response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["message"], "success")
        self.assertIn("data", payload)
        self.assertGreater(int(payload["data"]["outbox_id"]), 0)

        detail_response = self.client.get(
            f"/api/production/plans/{plan_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertTrue(detail["write_entry_frozen"])
        self.assertIn("TASK-015E", detail["write_entry_frozen_reason"])
        self.assertIn("sync-job-cards", detail["write_entry_frozen_reason"])
        self.assertIn("create-work-order", detail["write_entry_frozen_reason"])
        self.assertNotIn("普通前端仍冻结 create-work-order / sync-job-cards", detail["write_entry_frozen_reason"])


if __name__ == "__main__":
    unittest.main()
