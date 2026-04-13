"""Integration tests for BOM read permission fail-closed behavior (TASK-001D)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

# Ensure env-dependent app settings are stable before importing app modules.
os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import PermissionSourceUnavailable
from app.core.permissions import PERMISSION_SOURCE_UNAVAILABLE_CODE
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class BomPermissionFailClosedTest(unittest.TestCase):
    """Cover fail-closed and resource-scope behavior for BOM read APIs."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

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

        with cls.SessionLocal() as session:
            session.add_all(
                [
                    LyApparelBom(
                        id=1,
                        bom_no="BOM-ITEM-A-V1",
                        item_code="ITEM-A",
                        version_no="V1",
                        is_default=True,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                    LyApparelBom(
                        id=2,
                        bom_no="BOM-ITEM-B-V1",
                        item_code="ITEM-B",
                        version_no="V1",
                        is_default=False,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                ]
            )
            session.add_all(
                [
                    LyApparelBomItem(
                        id=1,
                        bom_id=1,
                        material_item_code="MAT-A",
                        color=None,
                        size=None,
                        qty_per_piece=1,
                        loss_rate=0,
                        uom="PCS",
                        remark=None,
                    ),
                    LyApparelBomItem(
                        id=2,
                        bom_id=2,
                        material_item_code="MAT-B",
                        color=None,
                        size=None,
                        qty_per_piece=2,
                        loss_rate=0.05,
                        uom="PCS",
                        remark=None,
                    ),
                ]
            )
            session.add_all(
                [
                    LyBomOperation(
                        id=1,
                        bom_id=1,
                        process_name="cut",
                        sequence_no=1,
                        is_subcontract=False,
                        wage_rate=1,
                        subcontract_cost_per_piece=None,
                        remark=None,
                    ),
                    LyBomOperation(
                        id=2,
                        bom_id=2,
                        process_name="sew",
                        sequence_no=1,
                        is_subcontract=True,
                        wage_rate=None,
                        subcontract_cost_per_piece=2,
                        remark=None,
                    ),
                ]
            )
            session.commit()

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[bom_db_dep] = _override_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        cls.engine.dispose()

    @staticmethod
    def _headers(role: str = "BOM Editor") -> dict[str, str]:
        return {"X-LY-Dev-User": "reader.user", "X-LY-Dev-Roles": role}

    def test_permission_source_unavailable_returns_503(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="ERPNext timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            list_resp = self.client.get("/api/bom/", headers=self._headers())
            detail_resp = self.client.get("/api/bom/1", headers=self._headers())
            explode_resp = self.client.post(
                "/api/bom/1/explode",
                headers=self._headers(),
                json={"order_qty": 100, "size_ratio": {}},
            )
            actions_resp = self.client.get("/api/auth/actions?module=bom", headers=self._headers())

        for resp in [list_resp, detail_resp, explode_resp, actions_resp]:
            payload = resp.json()
            self.assertEqual(resp.status_code, 503)
            self.assertEqual(payload.get("code"), PERMISSION_SOURCE_UNAVAILABLE_CODE)

    def test_unrestricted_access_when_user_permission_query_succeeds_with_zero_rows(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=True,
                allowed_items=set(),
                allowed_companies=set(),
            ),
        ):
            list_resp = self.client.get("/api/bom/", headers=self._headers())

        payload = list_resp.json()
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(payload.get("code"), "0")
        self.assertEqual(payload.get("data", {}).get("total"), 2)

    def test_item_scope_filters_list_and_blocks_unauthorized_detail_and_explode(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies=set(),
            ),
        ):
            list_resp = self.client.get("/api/bom/", headers=self._headers())
            detail_denied = self.client.get("/api/bom/2", headers=self._headers())
            explode_denied = self.client.post(
                "/api/bom/2/explode",
                headers=self._headers(),
                json={"order_qty": 100, "size_ratio": {}},
            )

        list_payload = list_resp.json()
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_payload.get("code"), "0")
        items = list_payload.get("data", {}).get("items", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["item_code"], "ITEM-A")

        self.assertEqual(detail_denied.status_code, 403)
        self.assertEqual(detail_denied.json().get("code"), "AUTH_FORBIDDEN")
        self.assertEqual(explode_denied.status_code, 403)
        self.assertEqual(explode_denied.json().get("code"), "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
