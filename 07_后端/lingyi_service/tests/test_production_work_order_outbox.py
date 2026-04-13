"""Work Order outbox and worker behavior tests for production module (TASK-004A)."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.models.production import LyProductionWorkOrderOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextWorkOrder
from app.services.production_work_order_outbox_service import ProductionWorkOrderOutboxService


class ProductionWorkOrderOutboxTest(unittest.TestCase):
    """Validate outbox creation and worker transitions."""

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
                    id=301,
                    bom_no="BOM-PROD-WO-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
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
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.production"

        with self.SessionLocal() as session:
            session.query(LyProductionWorkOrderLink).delete()
            session.query(LyProductionWorkOrderOutbox).delete()
            session.query(LyProductionPlan).delete()
            session.commit()
            session.add(
                LyProductionPlan(
                    id=9101,
                    plan_no="PP-WO-9101",
                    company="COMP-A",
                    sales_order="SO-WO-001",
                    sales_order_item="SOI-WO-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=301,
                    bom_version="v1",
                    planned_qty=Decimal("20"),
                    status="material_checked",
                    idempotency_key="idem-wo-9101",
                    request_hash="h9101",
                    created_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _headers(user: str = "svc.production", role: str = "System Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    @staticmethod
    def _create_work_order_payload(*, idempotency_key: str, fg: str = "FG-WH-001", wip: str = "WIP-WH-001", start_date: str = "2026-04-13") -> dict[str, str]:
        return {
            "fg_warehouse": fg,
            "wip_warehouse": wip,
            "start_date": start_date,
            "idempotency_key": idempotency_key,
        }

    def _seed_due_outbox(self, *, status: str = "pending") -> int:
        now = datetime.utcnow() - timedelta(minutes=1)
        with self.SessionLocal() as session:
            row = LyProductionWorkOrderOutbox(
                plan_id=9101,
                company="COMP-A",
                item_code="ITEM-A",
                action="create_work_order",
                idempotency_key="idem-outbox-9101",
                payload_hash="h-outbox-9101",
                payload_json={
                    "doctype": "Work Order",
                    "company": "COMP-A",
                    "production_item": "ITEM-A",
                    "qty": "20",
                    "bom_no": "BOM-PROD-WO-001",
                    "custom_ly_plan_id": "9101",
                    "custom_ly_plan_no": "PP-WO-9101",
                },
                event_key="pwo:test-9101",
                status=status,
                attempts=0,
                max_attempts=5,
                next_retry_at=now,
                request_id="rid-wo-9101",
                created_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def test_create_work_order_outbox_is_idempotent_for_same_plan(self) -> None:
        first = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-plan-9101"),
        )
        second = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-plan-9101"),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["outbox_id"], second.json()["data"]["outbox_id"])
        with self.SessionLocal() as session:
            rows = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.plan_id == 9101).all()
            self.assertEqual(len(rows), 1)

    def test_create_work_order_same_idempotency_different_payload_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-plan-9101-conflict", fg="FG-A"),
        )
        second = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-plan-9101-conflict", fg="FG-B"),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "PRODUCTION_IDEMPOTENCY_CONFLICT")

    def test_create_work_order_returns_existing_pending_outbox_without_duplicate(self) -> None:
        first = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-existing-pending-1"),
        )
        second = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-existing-pending-2"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["outbox_id"], second.json()["data"]["outbox_id"])

    def test_create_work_order_returns_existing_work_order_when_link_succeeded(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyProductionWorkOrderLink(
                    plan_id=9101,
                    work_order="WO-EXIST-001",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    created_by="seed",
                )
            )
            session.commit()

        response = self.client.post(
            "/api/production/plans/9101/create-work-order",
            headers=self._headers(role="Production Manager"),
            json=self._create_work_order_payload(idempotency_key="idem-existing-link-1"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["work_order"], "WO-EXIST-001")

    def test_create_work_order_audit_write_failed_returns_audit_write_failed(self) -> None:
        with patch("app.routers.production.AuditService.record_success", side_effect=AuditWriteFailed()):
            response = self.client.post(
                "/api/production/plans/9101/create-work-order",
                headers=self._headers(role="Production Manager"),
                json=self._create_work_order_payload(idempotency_key="idem-audit-failed-1"),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")

    def test_create_work_order_commit_failure_does_not_call_erpnext(self) -> None:
        with patch("app.routers.production._commit_or_raise_write_error", side_effect=DatabaseWriteFailed()), patch.object(
            ERPNextProductionAdapter,
            "create_work_order",
        ) as create_mock, patch.object(
            ERPNextProductionAdapter,
            "submit_work_order",
        ) as submit_mock:
            response = self.client.post(
                "/api/production/plans/9101/create-work-order",
                headers=self._headers(role="Production Manager"),
                json=self._create_work_order_payload(idempotency_key="idem-plan-9101-commit-failed"),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")
        self.assertEqual(create_mock.call_count, 0)
        self.assertEqual(submit_mock.call_count, 0)

    def test_worker_success_creates_work_order_link(self) -> None:
        outbox_id = self._seed_due_outbox()
        with patch.object(ERPNextProductionAdapter, "find_work_order_by_plan", return_value=None), patch.object(
            ERPNextProductionAdapter,
            "create_work_order",
            return_value="WO-ERP-001",
        ), patch.object(ERPNextProductionAdapter, "submit_work_order", return_value=None), patch.object(
            ERPNextProductionAdapter,
            "get_work_order",
            return_value=ERPNextWorkOrder(name="WO-ERP-001", docstatus=1, status="Submitted"),
        ):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(),
                json={"batch_size": 10, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertGreaterEqual(response.json()["data"]["succeeded_count"], 1)

        with self.SessionLocal() as session:
            outbox = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.erpnext_work_order, "WO-ERP-001")
            link = session.query(LyProductionWorkOrderLink).filter(LyProductionWorkOrderLink.plan_id == 9101).first()
            self.assertIsNotNone(link)
            self.assertEqual(link.work_order, "WO-ERP-001")

    def test_worker_claim_commits_before_erpnext_call(self) -> None:
        outbox_id = self._seed_due_outbox()

        def _check_claim_committed(*, plan_id: int, plan_no: str):  # type: ignore[no-untyped-def]
            del plan_id, plan_no
            with self.SessionLocal() as verify_session:
                row = verify_session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
                self.assertIsNotNone(row)
                # If claim transaction has committed, a new session can observe processing + lock fields.
                self.assertEqual(row.status, "processing")
                self.assertIsNotNone(row.locked_by)
                self.assertIsNotNone(row.lease_until)
            return None

        with patch.object(ERPNextProductionAdapter, "find_work_order_by_plan", side_effect=_check_claim_committed), patch.object(
            ERPNextProductionAdapter,
            "create_work_order",
            return_value="WO-ERP-CLAIM-001",
        ), patch.object(ERPNextProductionAdapter, "submit_work_order", return_value=None), patch.object(
            ERPNextProductionAdapter,
            "get_work_order",
            return_value=ERPNextWorkOrder(name="WO-ERP-CLAIM-001", docstatus=1, status="Submitted"),
        ):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(),
                json={"batch_size": 1, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")

    def test_worker_existing_draft_submitted_then_succeeded(self) -> None:
        outbox_id = self._seed_due_outbox()
        with patch.object(
            ERPNextProductionAdapter,
            "find_work_order_by_plan",
            return_value=ERPNextWorkOrder(name="WO-ERP-002", docstatus=0, status="Draft"),
        ), patch.object(ERPNextProductionAdapter, "submit_work_order", return_value=None) as submit_mock, patch.object(
            ERPNextProductionAdapter,
            "get_work_order",
            return_value=ERPNextWorkOrder(name="WO-ERP-002", docstatus=1, status="Submitted"),
        ), patch.object(ERPNextProductionAdapter, "create_work_order", return_value="WO-NEVER") as create_mock:
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(),
                json={"batch_size": 5, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit_mock.call_count, 1)
        self.assertEqual(create_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            self.assertEqual(outbox.erpnext_work_order, "WO-ERP-002")

    def test_worker_cancelled_work_order_not_marked_succeeded(self) -> None:
        outbox_id = self._seed_due_outbox()
        with patch.object(
            ERPNextProductionAdapter,
            "find_work_order_by_plan",
            return_value=ERPNextWorkOrder(name="WO-ERP-003", docstatus=2, status="Cancelled"),
        ):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(),
                json={"batch_size": 5, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertGreaterEqual(data["failed_count"] + data["dead_count"], 1)

        with self.SessionLocal() as session:
            outbox = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertNotEqual(outbox.status, "succeeded")

    def test_claim_due_with_two_sessions_does_not_double_claim(self) -> None:
        self._seed_due_outbox()
        session_a = self.SessionLocal()
        session_b = self.SessionLocal()
        try:
            service_a = ProductionWorkOrderOutboxService(session=session_a)
            service_b = ProductionWorkOrderOutboxService(session=session_b)
            claims_a = service_a.claim_due(batch_size=10, worker_id="worker-a")
            session_a.commit()
            claims_b = service_b.claim_due(batch_size=10, worker_id="worker-b")
            session_b.commit()
            self.assertEqual(len(claims_a), 1)
            self.assertEqual(len(claims_b), 0)
        finally:
            session_a.close()
            session_b.close()

    def test_claim_due_can_recover_processing_row_after_lease_expired(self) -> None:
        outbox_id = self._seed_due_outbox(status="processing")
        with self.SessionLocal() as session:
            row = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
            row.lease_until = datetime.utcnow() - timedelta(minutes=1)
            row.locked_by = "worker-old"
            row.locked_at = datetime.utcnow() - timedelta(minutes=2)
            session.commit()

        with self.SessionLocal() as session:
            claims = ProductionWorkOrderOutboxService(session=session).claim_due(batch_size=5, worker_id="worker-new")
            session.commit()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].outbox_id, outbox_id)

    def test_claim_due_does_not_take_processing_row_before_lease_expired(self) -> None:
        outbox_id = self._seed_due_outbox(status="processing")
        with self.SessionLocal() as session:
            row = session.query(LyProductionWorkOrderOutbox).filter(LyProductionWorkOrderOutbox.id == outbox_id).first()
            row.lease_until = datetime.utcnow() + timedelta(minutes=3)
            row.locked_by = "worker-old"
            row.locked_at = datetime.utcnow()
            session.commit()

        with self.SessionLocal() as session:
            claims = ProductionWorkOrderOutboxService(session=session).claim_due(batch_size=5, worker_id="worker-new")
            session.commit()
        self.assertEqual(len(claims), 0)

    def test_work_order_link_plan_id_unique_constraint_effective(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyProductionWorkOrderLink(
                    plan_id=9101,
                    work_order="WO-LINK-001",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    created_by="seed",
                )
            )
            session.commit()

        with self.SessionLocal() as session:
            session.add(
                LyProductionWorkOrderLink(
                    plan_id=9101,
                    work_order="WO-LINK-002",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    created_by="seed",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main()
