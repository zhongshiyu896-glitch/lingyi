"""Job Card mapping sync tests for production module (TASK-004A)."""

from __future__ import annotations

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_production_adapter import ERPNextJobCard
from app.services.erpnext_production_adapter import ERPNextProductionAdapter


class ProductionJobCardSyncTest(unittest.TestCase):
    """Ensure manual Job Card sync writes local mapping only."""

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
                    id=401,
                    bom_no="BOM-PROD-JC-001",
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

        with self.SessionLocal() as session:
            session.query(LyProductionJobCardLink).delete()
            session.query(LyProductionWorkOrderLink).delete()
            session.query(LyProductionPlan).delete()
            session.commit()
            session.add(
                LyProductionPlan(
                    id=9201,
                    plan_no="PP-JC-9201",
                    company="COMP-A",
                    sales_order="SO-JC-001",
                    sales_order_item="SOI-JC-001",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=401,
                    bom_version="v1",
                    planned_qty=Decimal("30"),
                    status="work_order_created",
                    idempotency_key="idem-jc-9201",
                    request_hash="h9201",
                    created_by="seed",
                )
            )
            session.add(
                LyProductionWorkOrderLink(
                    id=1,
                    plan_id=9201,
                    work_order="WO-JC-001",
                    erpnext_docstatus=1,
                    erpnext_status="Submitted",
                    sync_status="succeeded",
                    created_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Production Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "prod.jc.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _cards() -> list[ERPNextJobCard]:
        return [
            ERPNextJobCard(
                name="JC-P-001",
                operation="Cut",
                operation_sequence=10,
                expected_qty=Decimal("20"),
                completed_qty=Decimal("8"),
                status="Open",
            ),
            ERPNextJobCard(
                name="JC-P-002",
                operation="Sew",
                operation_sequence=20,
                expected_qty=Decimal("10"),
                completed_qty=Decimal("2"),
                status="Open",
            ),
        ]

    def test_sync_job_cards_is_frozen_for_regular_path(self) -> None:
        with patch.object(ERPNextProductionAdapter, "list_job_cards", return_value=self._cards()):
            response = self.client.post(
                "/api/production/work-orders/WO-JC-001/sync-job-cards",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        self.assertIn("冻结", response.json()["message"])

        with self.SessionLocal() as session:
            rows = (
                session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.plan_id == 9201)
                .order_by(LyProductionJobCardLink.job_card.asc())
                .all()
            )
            self.assertEqual(len(rows), 0)

            audit_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "production",
                    LyOperationAuditLog.action == "production:job_card_sync",
                    LyOperationAuditLog.result == "failed",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(audit_row)

    def test_sync_job_cards_forbidden_when_resource_scope_not_allowed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = "https://erpnext.example.test"

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextProductionAdapter, "list_job_cards", return_value=self._cards()):
            response = self.client.post(
                "/api/production/work-orders/WO-JC-001/sync-job-cards",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
