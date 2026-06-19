"""Local company fact permission tests for subcontract module (TASK-002C)."""

from __future__ import annotations

from decimal import Decimal
import json
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
from app.routers import subcontract as subcontract_router
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.subcontract_service import SubcontractService


class SubcontractCompanyPermissionTest(unittest.TestCase):
    """Verify subcontract permissions use local company fact as authority."""

    SCENARIO_TAG = "Z003-SUBCONTRACT-20260619-001"

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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._set_fastapi_permissions(
            companies={"COMP-A", "COMP-B"},
            item_codes={"ITEM-A", "ITEM-B"},
            suppliers={"SUP-A", "SUP-B"},
            warehouses={"WH-A", "WH-B", "WH-RECV-A"},
        )
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
    def _headers_with_request_id(request_id: str, role: str = "Subcontract Manager", user: str = "sub.user") -> dict[str, str]:
        headers = SubcontractCompanyPermissionTest._headers(role=role, user=user)
        headers["X-Request-ID"] = request_id
        return headers

    def _set_fastapi_permissions(
        self,
        *,
        companies: set[str] | None = None,
        item_codes: set[str] | None = None,
        suppliers: set[str] | None = None,
        warehouses: set[str] | None = None,
        unrestricted: bool = False,
    ) -> None:
        entry: dict[str, object] = {"unrestricted": True} if unrestricted else {}
        if companies is not None:
            entry["companies"] = sorted(companies)
        if item_codes is not None:
            entry["item_codes"] = sorted(item_codes)
        if suppliers is not None:
            entry["suppliers"] = sorted(suppliers)
        if warehouses is not None:
            entry["warehouses"] = sorted(warehouses)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps({"users": {"sub.user": entry}})

    @staticmethod
    def _carrier_code(value: str) -> str:
        return subcontract_router._fnv_carrier_code(value)

    def _request_id(
        self,
        *,
        operation: str,
        idempotency_key: str,
        source_ref: str,
        subcontract_ref: str,
        supplier_ref: str,
        work_order_ref: str,
        item_code: str,
        status_action: str,
    ) -> str:
        operation_code = subcontract_router.SUBCONTRACT_OPERATION_CODE_BY_NAME[operation]
        return (
            f"{self.SCENARIO_TAG}-SC-{operation_code}-"
            f"{self._carrier_code(idempotency_key)}-"
            f"{self._carrier_code(source_ref)}-"
            f"{self._carrier_code(subcontract_ref)}-"
            f"{self._carrier_code(supplier_ref)}-"
            f"{self._carrier_code(work_order_ref)}-"
            f"{self._carrier_code(item_code)}-"
            f"{self._carrier_code(status_action)}"
        )

    def _write_carrier(
        self,
        *,
        operation: str,
        idempotency_key: str,
        source_suffix: str,
        subcontract_ref: str,
        supplier_ref: str,
        work_order_ref: str,
        item_code: str,
        quantity: str,
        status_action: str,
    ) -> dict[str, str]:
        source_ref = f"{self.SCENARIO_TAG}:{operation}:{source_suffix}:{idempotency_key}"
        return {
            "request_id": self._request_id(
                operation=operation,
                idempotency_key=idempotency_key,
                source_ref=source_ref,
                subcontract_ref=subcontract_ref,
                supplier_ref=supplier_ref,
                work_order_ref=work_order_ref,
                item_code=item_code,
                status_action=status_action,
            ),
            "idempotency_key": idempotency_key,
            "scenario_tag": self.SCENARIO_TAG,
            "source_ref": source_ref,
            "subcontract_ref": subcontract_ref,
            "supplier_ref": supplier_ref,
            "work_order_ref": work_order_ref,
            "operation": operation,
            "item_code": item_code,
            "quantity": quantity,
            "status_action": status_action,
        }

    def _create_payload(
        self,
        *,
        item_code: str = "ITEM-A",
        supplier: str = "SUP-A",
        company: str | None = "COMP-A",
        planned_qty: str = "20",
        idem: str = "idem-create-fastapi",
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "supplier": supplier,
            "item_code": item_code,
            "company": company,
            "bom_id": 1 if item_code == "ITEM-A" else 2,
            "planned_qty": planned_qty,
            "process_name": "外发裁剪",
        }
        payload.update(
            self._write_carrier(
                operation="create",
                idempotency_key=idem,
                source_suffix=f"create:{item_code}:{supplier}:{company or ''}",
                subcontract_ref=f"NEW-{idem}",
                supplier_ref=supplier,
                work_order_ref="NO-WORK-ORDER",
                item_code=item_code,
                quantity=planned_qty,
                status_action="create",
            )
        )
        return payload

    def _order_scope(self, order_id: int) -> dict[str, str]:
        return {
            101: {"subcontract_ref": "SC-COMP-A", "supplier_ref": "SUP-A", "item_code": "ITEM-A"},
            102: {"subcontract_ref": "SC-COMP-B", "supplier_ref": "SUP-B", "item_code": "ITEM-B"},
            103: {"subcontract_ref": "SC-BLOCKED", "supplier_ref": "SUP-A", "item_code": "ITEM-A"},
        }[order_id]

    def _receive_payload(
        self,
        *,
        order_id: int,
        idem: str,
        received_qty: str = "10",
        receipt_warehouse: str = "WH-A",
    ) -> dict[str, object]:
        scope = self._order_scope(order_id)
        payload: dict[str, object] = {
            "receipt_warehouse": receipt_warehouse,
            "received_qty": received_qty,
            "uom": "Nos",
        }
        payload.update(
            self._write_carrier(
                operation="receive",
                idempotency_key=idem,
                source_suffix=f"receive:{order_id}",
                subcontract_ref=scope["subcontract_ref"],
                supplier_ref=scope["supplier_ref"],
                work_order_ref="NO-WORK-ORDER",
                item_code=scope["item_code"],
                quantity=received_qty,
                status_action="receive",
            )
        )
        return payload

    def _inspect_payload(
        self,
        *,
        order_id: int,
        idem: str,
        inspected_qty: str = "10",
        receipt_batch_no: str = "SRB-COMP-001",
    ) -> dict[str, object]:
        scope = self._order_scope(order_id)
        payload: dict[str, object] = {
            "receipt_batch_no": receipt_batch_no,
            "inspected_qty": inspected_qty,
            "rejected_qty": "0",
            "deduction_amount_per_piece": "0",
        }
        payload.update(
            self._write_carrier(
                operation="inspect",
                idempotency_key=idem,
                source_suffix=f"inspect:{order_id}",
                subcontract_ref=scope["subcontract_ref"],
                supplier_ref=scope["supplier_ref"],
                work_order_ref="NO-WORK-ORDER",
                item_code=scope["item_code"],
                quantity=inspected_qty,
                status_action="inspect",
            )
        )
        return payload

    def test_subcontract_list_filters_by_local_company_in_database_query(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        response = self.client.get("/api/subcontract/", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        items = payload["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["subcontract_no"], "SC-COMP-B")
        self.assertEqual(items[0]["company"], "COMP-B")

    def test_subcontract_detail_forbidden_when_local_company_not_allowed(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        response = self.client.get("/api/subcontract/101", headers=self._headers())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_subcontract_detail_forbidden_does_not_read_child_details(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        with patch.object(
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
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_subcontract_detail_permission_source_unavailable_does_not_read_child_details(self) -> None:
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = "{"
        with patch.object(
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

    def test_receive_forbidden_when_local_company_not_allowed_before_fact_write(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        payload = self._receive_payload(order_id=101, idem="idem-recv-denied")
        response = self.client.post(
            "/api/subcontract/101/receive",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_inspect_forbidden_when_local_company_not_allowed_before_fact_write(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        payload = self._inspect_payload(order_id=101, idem="idem-inspect-denied")
        response = self.client.post(
            "/api/subcontract/101/inspect",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_inspect_forbidden_does_not_read_order_snapshot_before_resource_permission(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-B"},
            item_codes={"ITEM-B"},
            suppliers={"SUP-B"},
            warehouses={"WH-B"},
        )
        payload = self._inspect_payload(order_id=101, idem="idem-inspect-no-snapshot")
        with patch.object(
            SubcontractService,
            "get_order_snapshot",
            side_effect=AssertionError("inspect forbidden path must not read order snapshot before resource permission passes"),
        ):
            response = self.client.post(
                "/api/subcontract/101/inspect",
                headers=self._headers_with_request_id(str(payload["request_id"])),
                json=payload,
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_inspect_permission_source_unavailable_does_not_read_order_snapshot(self) -> None:
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = "{"
        payload = self._inspect_payload(order_id=101, idem="idem-inspect-permission-unavailable")
        with patch.object(
            SubcontractService,
            "get_order_snapshot",
            side_effect=AssertionError("inspect must not read order snapshot when permission source is unavailable"),
        ):
            response = self.client.post(
                "/api/subcontract/101/inspect",
                headers=self._headers_with_request_id(str(payload["request_id"])),
                json=payload,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_blocked_scope_order_cannot_receive_or_inspect(self) -> None:
        self._set_fastapi_permissions(unrestricted=True)
        receive_payload = self._receive_payload(order_id=103, idem="idem-recv-blocked")
        inspect_payload = self._inspect_payload(order_id=103, idem="idem-inspect-blocked")
        receive_resp = self.client.post(
            "/api/subcontract/103/receive",
            headers=self._headers_with_request_id(str(receive_payload["request_id"])),
            json=receive_payload,
        )
        inspect_resp = self.client.post(
            "/api/subcontract/103/inspect",
            headers=self._headers_with_request_id(str(inspect_payload["request_id"])),
            json=inspect_payload,
        )
        self.assertEqual(receive_resp.status_code, 409)
        self.assertEqual(receive_resp.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")
        self.assertEqual(inspect_resp.status_code, 409)
        self.assertEqual(inspect_resp.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")

    def test_create_order_persists_explicit_fastapi_company(self) -> None:
        payload = self._create_payload(idem="idem-create-company-a")
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["company"], "COMP-A")

    def test_create_subcontract_blank_fastapi_company_returns_company_required_envelope(self) -> None:
        payload = self._create_payload(company=" ", idem="idem-create-company-required")
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_COMPANY_REQUIRED")

    def test_create_subcontract_fastapi_company_scope_denied_returns_auth_forbidden(self) -> None:
        self._set_fastapi_permissions(
            companies={"COMP-A"},
            item_codes={"ITEM-A"},
            suppliers={"SUP-A"},
            warehouses={"WH-A"},
        )
        payload = self._create_payload(company="COMP-B", idem="idem-create-company-denied")
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")

    def test_create_subcontract_fastapi_permission_config_unavailable_returns_503(self) -> None:
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = "{"
        payload = self._create_payload(idem="idem-create-permission-unavailable")
        response = self.client.post(
            "/api/subcontract/",
            headers=self._headers_with_request_id(str(payload["request_id"])),
            json=payload,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
