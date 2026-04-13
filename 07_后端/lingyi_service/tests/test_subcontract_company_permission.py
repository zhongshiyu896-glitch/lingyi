"""Local company fact permission tests for subcontract module (TASK-002C)."""

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractOrder
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter as ERPNextItemAdapter
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.exceptions import PermissionSourceUnavailable
from app.services.subcontract_service import SubcontractService


class SubcontractCompanyPermissionTest(unittest.TestCase):
    """Verify subcontract permissions use local company fact as authority."""

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
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add_all(
                [
                    LyApparelBom(
                        id=1,
                        bom_no="BOM-SC-A",
                        item_code="ITEM-A",
                        version_no="v1",
                        is_default=True,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                    LyApparelBom(
                        id=2,
                        bom_no="BOM-SC-B",
                        item_code="ITEM-B",
                        version_no="v1",
                        is_default=False,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                    LyBomOperation(
                        id=1,
                        bom_id=1,
                        process_name="外发裁剪",
                        sequence_no=1,
                        is_subcontract=True,
                        subcontract_cost_per_piece=Decimal("0.5"),
                    ),
                    LyBomOperation(
                        id=2,
                        bom_id=2,
                        process_name="外发裁剪",
                        sequence_no=1,
                        is_subcontract=True,
                        subcontract_cost_per_piece=Decimal("0.6"),
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
        app.dependency_overrides[subcontract_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with self.SessionLocal() as session:
            session.query(LySubcontractOrder).delete()
            session.commit()
            session.add_all(
                [
                    LySubcontractOrder(
                        id=101,
                        subcontract_no="SC-COMP-A",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("100"),
                        status="processing",
                    ),
                    LySubcontractOrder(
                        id=102,
                        subcontract_no="SC-COMP-B",
                        supplier="SUP-B",
                        item_code="ITEM-B",
                        company="COMP-B",
                        bom_id=2,
                        process_name="外发裁剪",
                        planned_qty=Decimal("80"),
                        status="waiting_inspection",
                    ),
                    LySubcontractOrder(
                        id=103,
                        subcontract_no="SC-BLOCKED",
                        supplier="SUP-A",
                        item_code="ITEM-A",
                        company="COMP-A",
                        bom_id=1,
                        process_name="外发裁剪",
                        planned_qty=Decimal("60"),
                        status="processing",
                        resource_scope_status="blocked_scope",
                        scope_error_code="SUBCONTRACT_COMPANY_UNRESOLVED",
                    ),
                ]
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager", user: str = "sub.user") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    @staticmethod
    def _permissions_for_company_b() -> UserPermissionResult:
        return UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items={"ITEM-B"},
            allowed_companies={"COMP-B"},
            allowed_suppliers={"SUP-B"},
            allowed_warehouses={"WH-B"},
        )

    def test_subcontract_list_filters_by_local_company_in_database_query(self) -> None:
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=self._permissions_for_company_b()):
            response = self.client.get("/api/subcontract/", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        items = payload["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["subcontract_no"], "SC-COMP-B")
        self.assertEqual(items[0]["company"], "COMP-B")

    def test_subcontract_detail_forbidden_when_local_company_not_allowed(self) -> None:
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=self._permissions_for_company_b()):
            response = self.client.get("/api/subcontract/101", headers=self._headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_subcontract_detail_forbidden_does_not_read_child_details(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._permissions_for_company_b(),
        ), patch.object(
            SubcontractService,
            "latest_issue_outbox",
            side_effect=AssertionError("latest_issue_outbox must not be called before resource permission passes"),
        ), patch.object(
            SubcontractService,
            "latest_receipt_outbox",
            side_effect=AssertionError("latest_receipt_outbox must not be called before resource permission passes"),
        ), patch.object(
            SubcontractService,
            "list_inspections",
            side_effect=AssertionError("list_inspections must not be called before resource permission passes"),
        ):
            response = self.client.get("/api/subcontract/101", headers=self._headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_subcontract_detail_permission_source_unavailable_does_not_read_child_details(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="permission source unavailable",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ), patch.object(
            SubcontractService,
            "latest_issue_outbox",
            side_effect=AssertionError("latest_issue_outbox must not be called when permission source is unavailable"),
        ), patch.object(
            SubcontractService,
            "latest_receipt_outbox",
            side_effect=AssertionError("latest_receipt_outbox must not be called when permission source is unavailable"),
        ), patch.object(
            SubcontractService,
            "list_inspections",
            side_effect=AssertionError("list_inspections must not be called when permission source is unavailable"),
        ):
            response = self.client.get("/api/subcontract/101", headers=self._headers())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_receive_forbidden_when_local_company_not_allowed_before_payload_validation(self) -> None:
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=self._permissions_for_company_b()):
            response = self.client.post("/api/subcontract/101/receive", headers=self._headers(), json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_inspect_forbidden_when_local_company_not_allowed_before_payload_validation(self) -> None:
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=self._permissions_for_company_b()):
            response = self.client.post("/api/subcontract/101/inspect", headers=self._headers(), json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_inspect_forbidden_does_not_read_order_snapshot_before_resource_permission(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._permissions_for_company_b(),
        ), patch.object(
            SubcontractService,
            "get_order_snapshot",
            side_effect=AssertionError("inspect forbidden path must not read order snapshot before resource permission passes"),
        ):
            response = self.client.post("/api/subcontract/101/inspect", headers=self._headers(), json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_inspect_permission_source_unavailable_does_not_read_order_snapshot(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="permission source unavailable",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ), patch.object(
            SubcontractService,
            "get_order_snapshot",
            side_effect=AssertionError("inspect must not read order snapshot when permission source is unavailable"),
        ):
            response = self.client.post("/api/subcontract/101/inspect", headers=self._headers(), json={})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_blocked_scope_order_cannot_receive_or_inspect(self) -> None:
        unrestricted_permissions = UserPermissionResult(
            source_available=True,
            unrestricted=True,
            allowed_items=set(),
            allowed_companies=set(),
            allowed_suppliers=set(),
            allowed_warehouses=set(),
        )
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=unrestricted_permissions):
            receive_resp = self.client.post(
                "/api/subcontract/103/receive",
                headers=self._headers(),
                json={"receipt_warehouse": "WH-A"},
            )
            inspect_resp = self.client.post(
                "/api/subcontract/103/inspect",
                headers=self._headers(),
                json={},
            )
        self.assertEqual(receive_resp.status_code, 409)
        self.assertEqual(receive_resp.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")
        self.assertEqual(inspect_resp.status_code, 409)
        self.assertEqual(inspect_resp.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")

    def test_create_order_returns_backend_resolved_company(self) -> None:
        permissions = UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items={"ITEM-A"},
            allowed_companies={"COMP-A"},
            allowed_suppliers={"SUP-A"},
            allowed_warehouses={"WH-A"},
        )
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=permissions), patch.object(
            ERPNextItemAdapter,
            "get_item",
            return_value=ItemInfo(
                name="ITEM-A",
                item_code="ITEM-A",
                disabled=False,
                companies=("COMP-A",),
            ),
        ):
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(),
                json={
                    "supplier": "SUP-A",
                    "item_code": "ITEM-A",
                    "company": "   ",
                    "bom_id": 1,
                    "planned_qty": "20",
                    "process_name": "外发裁剪",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["company"], "COMP-A")

    def test_create_subcontract_ambiguous_company_returns_company_ambiguous_envelope(self) -> None:
        permissions = UserPermissionResult(
            source_available=True,
            unrestricted=True,
            allowed_items=set(),
            allowed_companies=set(),
            allowed_suppliers=set(),
            allowed_warehouses=set(),
        )
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=permissions), patch.object(
            ERPNextItemAdapter,
            "get_item",
            return_value=ItemInfo(
                name="ITEM-A",
                item_code="ITEM-A",
                disabled=False,
                companies=("COMP-A", "COMP-B"),
            ),
        ):
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(),
                json={
                    "supplier": "SUP-A",
                    "item_code": "ITEM-A",
                    "company": " ",
                    "bom_id": 1,
                    "planned_qty": "20",
                    "process_name": "外发裁剪",
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_COMPANY_AMBIGUOUS")

    def test_create_subcontract_unresolved_company_returns_company_unresolved_envelope(self) -> None:
        permissions = UserPermissionResult(
            source_available=True,
            unrestricted=True,
            allowed_items=set(),
            allowed_companies=set(),
            allowed_suppliers=set(),
            allowed_warehouses=set(),
        )
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=permissions), patch.object(
            ERPNextItemAdapter,
            "get_item",
            return_value=ItemInfo(
                name="ITEM-A",
                item_code="ITEM-A",
                disabled=False,
                companies=(),
            ),
        ):
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(),
                json={
                    "supplier": "SUP-A",
                    "item_code": "ITEM-A",
                    "company": " ",
                    "bom_id": 1,
                    "planned_qty": "20",
                    "process_name": "外发裁剪",
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_COMPANY_UNRESOLVED")

    def test_create_subcontract_erpnext_unavailable_returns_service_unavailable_envelope(self) -> None:
        permissions = UserPermissionResult(
            source_available=True,
            unrestricted=True,
            allowed_items=set(),
            allowed_companies=set(),
            allowed_suppliers=set(),
            allowed_warehouses=set(),
        )
        with patch.object(ERPNextPermissionAdapter, "get_user_permissions", return_value=permissions), patch.object(
            ERPNextItemAdapter,
            "get_item",
            side_effect=ERPNextServiceUnavailableError("erpnext unavailable"),
        ):
            response = self.client.post(
                "/api/subcontract/",
                headers=self._headers(),
                json={
                    "supplier": "SUP-A",
                    "item_code": "ITEM-A",
                    "company": " ",
                    "bom_id": 1,
                    "planned_qty": "20",
                    "process_name": "外发裁剪",
                },
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "ERPNEXT_SERVICE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
