"""Job Card mapping sync tests for production module (TASK-004A)."""

from __future__ import annotations

from decimal import Decimal
import json
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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep


class ProductionJobCardSyncTest(unittest.TestCase):
    """Ensure manual Job Card sync writes FastAPI-native local mapping only."""

    SCENARIO_TAG = "Z003-PROD-PLAN-DETAIL-20260619-901"

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
                    company="COMP-A",
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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {"users": {"prod.jc.user": {"company": ["COMP-A"], "item_code": ["ITEM-A"]}}}
        )

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

    @classmethod
    def _sync_payload(cls, *, idempotency_key: str = "sync-jc-001") -> dict[str, object]:
        request_id = f"req-{cls.SCENARIO_TAG}"
        return {
            "scenario_tag": cls.SCENARIO_TAG,
            "operation": "sync_job_cards",
            "plan_id": 9201,
            "plan_no_or_work_order": "WO-JC-001",
            "company": "COMP-A",
            "item_code": "ITEM-A",
            "source_ref": "|".join([cls.SCENARIO_TAG, "COMP-A", "9201", "WO-JC-001", "ITEM-A", "sync_job_cards"]),
            "idempotency_key": f"{cls.SCENARIO_TAG}-{idempotency_key}",
            "request_id": request_id,
        }

    def test_sync_job_cards_updates_local_projection_for_regular_path(self) -> None:
        request_id = f"req-{self.SCENARIO_TAG}"
        response = self.client.post(
            "/api/production/work-orders/WO-JC-001/sync-job-cards",
            headers={**self._headers(), "X-Request-ID": request_id},
            json=self._sync_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["work_order"], "WO-JC-001")
        self.assertEqual(response.json()["data"]["synced_count"], 3)

        with self.SessionLocal() as session:
            rows = (
                session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.plan_id == 9201)
                .order_by(LyProductionJobCardLink.job_card.asc())
                .all()
            )
            self.assertEqual(len(rows), 3)
            self.assertEqual({row.work_order for row in rows}, {"WO-JC-001"})
            self.assertEqual({row.operation for row in rows}, {"裁剪", "车缝", "后整"})
            self.assertEqual({row.erpnext_status for row in rows}, {"LocalSynced"})

            audit_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "production",
                    LyOperationAuditLog.action == "production:job_card_sync",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(audit_row)

    def test_sync_job_cards_forbidden_when_resource_scope_not_allowed(self) -> None:
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {"users": {"prod.jc.user": {"company": ["COMP-A"], "item_code": ["ITEM-B"]}}}
        )
        request_id = f"req-{self.SCENARIO_TAG}"
        response = self.client.post(
            "/api/production/work-orders/WO-JC-001/sync-job-cards",
            headers={**self._headers(), "X-Request-ID": request_id},
            json=self._sync_payload(idempotency_key="sync-jc-forbidden"),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")


if __name__ == "__main__":
    unittest.main()
