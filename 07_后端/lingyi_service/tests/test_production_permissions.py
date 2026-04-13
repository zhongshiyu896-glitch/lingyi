"""Permission and security audit tests for production module (TASK-004A)."""

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
from app.core.exceptions import PermissionSourceUnavailable
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextSalesOrder
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem
from app.services.production_service import ProductionService


class ProductionPermissionTest(unittest.TestCase):
    """Ensure production endpoints enforce action + resource permissions."""

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
                    id=201,
                    bom_no="BOM-PROD-PERM-001",
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
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = "https://erpnext.example.test"

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyProductionPlan).delete()
            session.commit()
            session.add(
                LyProductionPlan(
                    id=9001,
                    plan_no="PP-PERM-9001",
                    company="COMP-A",
                    sales_order="SO-PERM-1",
                    sales_order_item="SOI-PERM-1",
                    customer="CUST-A",
                    item_code="ITEM-A",
                    bom_id=201,
                    bom_version="v1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="idem-9001",
                    request_hash="h9001",
                    created_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Production Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "prod.permission.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _sales_order() -> ERPNextSalesOrder:
        return ERPNextSalesOrder(
            name="SO-PERM-CREATE",
            docstatus=1,
            status="To Deliver",
            company="COMP-A",
            customer="CUST-A",
            items=(
                ERPNextSalesOrderItem(name="SOI-PERM-CREATE", item_code="ITEM-A", qty=Decimal("100")),
            ),
        )

    def test_detail_forbidden_when_item_not_in_scope(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ):
            response = self.client.get(
                "/api/production/plans/9001",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.module, "production")
            self.assertEqual(row.event_type, "AUTH_FORBIDDEN")

    def test_detail_forbidden_does_not_read_subtable_details(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-B"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(
            ProductionService,
            "get_plan_detail",
            side_effect=RuntimeError("should-not-read-detail"),
        ):
            response = self.client.get(
                "/api/production/plans/9001",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_create_fails_closed_when_permission_source_unavailable(self) -> None:
        with patch.object(ERPNextProductionAdapter, "get_sales_order", return_value=self._sales_order()), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="permission source down",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            response = self.client.post(
                "/api/production/plans",
                headers=self._headers(),
                json={
                    "sales_order": "SO-PERM-CREATE",
                    "item_code": "ITEM-A",
                    "planned_qty": "10",
                    "idempotency_key": "idem-perm-create-1",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            rows = (
                session.query(LyProductionPlan)
                .filter(LyProductionPlan.idempotency_key == "idem-perm-create-1")
                .all()
            )
            self.assertEqual(len(rows), 0)

    def test_internal_worker_denied_for_non_worker_action_role(self) -> None:
        # Production Manager has no production:work_order_worker action.
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items={"ITEM-A"},
            allowed_companies={"COMP-A"},
        )):
            response = self.client.post(
                "/api/production/internal/work-order-sync/run-once",
                headers=self._headers(role="Production Manager"),
                json={"batch_size": 5, "dry_run": True},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
