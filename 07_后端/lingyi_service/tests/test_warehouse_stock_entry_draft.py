"""TASK-050B warehouse stock-entry draft outbox baseline tests."""

from __future__ import annotations

from datetime import date
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
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.services.erpnext_permission_adapter import UserPermissionResult


class WarehouseStockEntryDraftApiBase(unittest.TestCase):
    """In-memory app wiring for warehouse stock-entry draft APIs."""

    SCENARIO_TAG = "Z003-WAREHOUSE-20260526-005"
    BUSINESS_DATE = date(2026, 5, 26).isoformat()
    SOURCE_REF = f"{SCENARIO_TAG}-SRC-001"
    IDEMPOTENCY_KEY = f"{SCENARIO_TAG}-IDEM-001"
    WAREHOUSE = "WH-B"
    ITEM_CODE = "ITEM-A"

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
        AuditBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _carrier_code(value: object, *, length: int = 3) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-length:]

    @staticmethod
    def _decimal_text(value: object) -> str:
        normalized = format(Decimal(str(value)).normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized or "0"

    @classmethod
    def _request_id(
        cls,
        *,
        operation: str = "create_stock_entry_draft",
        idempotency_key: str | None = None,
        source_ref: str | None = None,
        warehouse: str | None = None,
        item_code: str | None = None,
        quantity: object = "5",
        business_date: str | None = None,
        status_action: str = "create",
    ) -> str:
        operation_code = {
            "create_stock_entry_draft": "C",
            "audit_stock_entry_draft": "A",
            "cancel_stock_entry_draft": "X",
            "release_material_hold": "R",
        }.get(operation, "X")
        status_action_code = {
            "create": "C",
            "audit": "A",
            "cancel": "X",
            "release": "R",
        }.get(status_action, "X")
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                operation_code,
                cls._carrier_code(idempotency_key or cls.IDEMPOTENCY_KEY),
                cls._carrier_code(source_ref or cls.SOURCE_REF),
                cls._carrier_code(warehouse or cls.WAREHOUSE),
                cls._carrier_code(item_code or cls.ITEM_CODE),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(business_date or cls.BUSINESS_DATE),
                cls._carrier_code(status_action_code),
            ]
        )

    @classmethod
    def _headers(cls, roles: str, *, request_id: str | None = None) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.writer",
            "X-LY-Dev-Roles": roles,
            "X-Request-ID": request_id or cls._request_id(),
        }

    @classmethod
    def _payload(cls, *, qty: str = "5") -> dict:
        return {
            "company": "COMP-A",
            "purpose": "Material Transfer",
            "source_type": "manual",
            "source_id": cls.SOURCE_REF,
            "source_ref": cls.SOURCE_REF,
            "warehouse": cls.WAREHOUSE,
            "item_code": cls.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": qty,
            "business_date": cls.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": cls.SCENARIO_TAG,
            "source_warehouse": cls.WAREHOUSE,
            "target_warehouse": cls.WAREHOUSE,
            "idempotency_key": cls.IDEMPOTENCY_KEY,
            "items": [
                {
                    "item_code": cls.ITEM_CODE,
                    "qty": qty,
                    "uom": "Nos",
                    "batch_no": None,
                    "serial_no": None,
                    "source_warehouse": cls.WAREHOUSE,
                    "target_warehouse": cls.WAREHOUSE,
                }
            ],
        }

    @classmethod
    def _material_issue_payload(cls, *, qty: str = "5") -> dict:
        payload = cls._payload(qty=qty)
        payload["purpose"] = "Material Issue"
        payload["target_warehouse"] = None
        payload["items"][0]["target_warehouse"] = None
        return payload

    @classmethod
    def _material_receipt_payload(cls, *, qty: str = "5") -> dict:
        payload = cls._payload(qty=qty)
        payload["purpose"] = "Material Receipt"
        payload["source_warehouse"] = None
        payload["items"][0]["source_warehouse"] = None
        return payload

    @classmethod
    def _process_inbound_payload(cls, *, qty: str = "6") -> dict:
        payload = cls._material_receipt_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-PROC-IN-001"
        payload["source_type"] = "material_process_inbound"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-PROC-IN-001"
        return payload

    @classmethod
    def _other_inbound_payload(cls, *, qty: str = "7") -> dict:
        payload = cls._material_receipt_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-OTHER-IN-001"
        payload["source_type"] = "material_other_inbound"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-OTHER-IN-001"
        return payload

    @classmethod
    def _purchase_return_payload(cls, *, qty: str = "4") -> dict:
        payload = cls._material_issue_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-PUR-RET-001"
        payload["source_type"] = "material_purchase_return"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-PUR-RET-001"
        return payload

    @classmethod
    def _sale_outbound_payload(cls, *, qty: str = "3") -> dict:
        payload = cls._material_issue_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-SALE-OUT-001"
        payload["source_type"] = "material_sale_outbound"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-SALE-OUT-001"
        return payload

    @classmethod
    def _hold_payload(cls, *, qty: str = "5") -> dict:
        payload = cls._material_issue_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-HOLD-001"
        payload["source_type"] = "material_hold"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-HOLD-001"
        return payload

    @classmethod
    def _retention_disposal_payload(cls, *, qty: str = "8") -> dict:
        payload = cls._material_issue_payload(qty=qty)
        source_ref = f"{cls.SCENARIO_TAG}-RET-DISP-001"
        payload["source_type"] = "material_retention_disposal"
        payload["source_id"] = source_ref
        payload["source_ref"] = source_ref
        payload["idempotency_key"] = f"{cls.SCENARIO_TAG}-IDEM-RET-DISP-001"
        return payload

    @classmethod
    def _request_id_from_payload(cls, payload: dict, *, operation: str | None = None, status_action: str | None = None) -> str:
        return cls._request_id(
            operation=operation or str(payload["operation"]),
            idempotency_key=str(payload["idempotency_key"]),
            source_ref=str(payload["source_ref"]),
            warehouse=str(payload["warehouse"]),
            item_code=str(payload["item_code"]),
            quantity=payload["quantity"],
            business_date=str(payload["business_date"]),
            status_action=status_action or str(payload["status_action"]),
        )

    @classmethod
    def _cancel_payload(cls, *, reason: str, source_payload: dict | None = None) -> dict:
        payload = source_payload or cls._payload()
        return {
            "reason": reason,
            "idempotency_key": str(payload["idempotency_key"]),
            "source_ref": str(payload["source_ref"]),
            "warehouse": str(payload["warehouse"]),
            "item_code": str(payload["item_code"]),
            "operation": "cancel_stock_entry_draft",
            "quantity": payload["quantity"],
            "business_date": str(payload["business_date"]),
            "status_action": "cancel",
            "scenario_tag": str(payload["scenario_tag"]),
        }

    def _stock_ledger_items(self, *, item_code: str, warehouse: str) -> list[dict]:
        response = self.client.get(
            "/api/warehouse/stock-ledger",
            params={
                "company": "COMP-A",
                "item_code": item_code,
                "warehouse": warehouse,
                "page": 1,
                "page_size": 100,
            },
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]["items"]

    def _stock_summary_items(self, *, item_code: str, warehouse: str) -> list[dict]:
        response = self.client.get(
            "/api/warehouse/stock-summary",
            params={
                "company": "COMP-A",
                "item_code": item_code,
                "warehouse": warehouse,
            },
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]["items"]

    @classmethod
    def _audit_payload(cls, *, reason: str | None = None) -> dict:
        payload = cls._payload()
        audit_payload = {
            "idempotency_key": str(payload["idempotency_key"]),
            "source_ref": str(payload["source_ref"]),
            "warehouse": str(payload["warehouse"]),
            "item_code": str(payload["item_code"]),
            "operation": "audit_stock_entry_draft",
            "quantity": payload["quantity"],
            "business_date": str(payload["business_date"]),
            "status_action": "audit",
            "scenario_tag": str(payload["scenario_tag"]),
        }
        if reason is not None:
            audit_payload["reason"] = reason
        return audit_payload

    @classmethod
    def _release_hold_payload(cls, *, reason: str, source_payload: dict | None = None) -> dict:
        payload = source_payload or cls._hold_payload()
        return {
            "reason": reason,
            "idempotency_key": str(payload["idempotency_key"]),
            "source_ref": str(payload["source_ref"]),
            "warehouse": str(payload["warehouse"]),
            "item_code": str(payload["item_code"]),
            "operation": "release_material_hold",
            "quantity": payload["quantity"],
            "business_date": str(payload["business_date"]),
            "status_action": "release",
            "scenario_tag": str(payload["scenario_tag"]),
        }


class WarehouseStockEntryDraftApiTest(WarehouseStockEntryDraftApiBase):
    """Warehouse stock-entry draft outbox contract."""

    def test_create_draft_with_permission(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["status"], "pending_outbox")
        self.assertEqual(body["company"], "COMP-A")
        self.assertEqual(body["source_ref"], self.SOURCE_REF)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["outbox"]["status"], "in_pending")

    def test_audit_draft_success_is_idempotent_by_request_id(self) -> None:
        create_response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        draft_id = int(create_response.json()["data"]["id"])

        payload = self._audit_payload(reason="confirm local posting")
        request_id = self._request_id_from_payload(
            payload,
            operation="audit_stock_entry_draft",
            status_action="audit",
        )
        first_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read", request_id=request_id),
            json=payload,
        )
        self.assertEqual(first_response.status_code, 200, first_response.text)
        self.assertEqual(first_response.json()["data"]["status"], "pending_outbox")

        second_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read", request_id=request_id),
            json=payload,
        )
        self.assertEqual(second_response.status_code, 200, second_response.text)
        self.assertEqual(second_response.json()["data"]["id"], draft_id)

        with self.SessionLocal() as session:
            audit_count = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.resource_id == draft_id,
                    LyOperationAuditLog.request_id == request_id,
                    LyOperationAuditLog.result == "success",
                )
                .count()
            )
            self.assertEqual(audit_count, 1)

    def test_audit_cancelled_draft_returns_409(self) -> None:
        create_response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        draft_id = int(create_response.json()["data"]["id"])

        cancel_payload = self._cancel_payload(reason="cancel before audit")
        cancel_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(
                    cancel_payload,
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=cancel_payload,
        )
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)

        audit_payload = self._audit_payload(reason="should fail")
        audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(
                    audit_payload,
                    operation="audit_stock_entry_draft",
                    status_action="audit",
                ),
            ),
            json=audit_payload,
        )
        self.assertEqual(audit_response.status_code, 409, audit_response.text)
        self.assertEqual(audit_response.json()["code"], "WAREHOUSE_DRAFT_ALREADY_CANCELLED")

    def test_list_drafts_keyword_matches_item_code(self) -> None:
        payload = self._sale_outbound_payload(qty="3")
        create_response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        draft_id = int(create_response.json()["data"]["id"])

        response = self.client.get(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:read"),
            params={
                "company": "COMP-A",
                "purpose": "Material Issue",
                "source_type": "material_sale_outbound",
                "keyword": self.ITEM_CODE,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), draft_id)
        self.assertEqual(data["items"][0]["items"][0]["item_code"], self.ITEM_CODE)

    def test_create_transfer_allows_distinct_source_and_target_warehouses(self) -> None:
        payload = self._payload()
        payload["target_warehouse"] = "WH-C"
        payload["items"][0]["target_warehouse"] = "WH-C"
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        self.assertEqual(body["source_warehouse"], self.WAREHOUSE)
        self.assertEqual(body["target_warehouse"], "WH-C")
        self.assertEqual(body["items"][0]["source_warehouse"], self.WAREHOUSE)
        self.assertEqual(body["items"][0]["target_warehouse"], "WH-C")

    def test_create_draft_generates_in_pending_outbox(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        draft_id = int(response.json()["data"]["id"])

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "pending_outbox")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "in_pending")

    def test_create_material_issue_persists_item_outbox_payload_and_audit(self) -> None:
        payload = self._material_issue_payload(qty="7")
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()["data"]
        draft_id = int(body["id"])
        self.assertEqual(body["purpose"], "Material Issue")
        self.assertEqual(body["source_warehouse"], self.WAREHOUSE)
        self.assertIsNone(body["target_warehouse"])
        self.assertEqual(body["items"][0]["item_code"], self.ITEM_CODE)
        self.assertEqual(Decimal(str(body["items"][0]["qty"])), Decimal("7"))
        self.assertEqual(body["items"][0]["source_warehouse"], self.WAREHOUSE)
        self.assertIsNone(body["items"][0]["target_warehouse"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 1)
            self.assertEqual(session.query(LyWarehouseStockEntryDraftItem).count(), 1)
            item = session.query(LyWarehouseStockEntryDraftItem).one()
            self.assertEqual(int(item.draft_id), draft_id)
            self.assertEqual(str(item.item_code), self.ITEM_CODE)
            self.assertEqual(Decimal(str(item.qty)), Decimal("7"))
            self.assertEqual(str(item.source_warehouse), self.WAREHOUSE)
            self.assertIsNone(item.target_warehouse)

            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=draft_id).one()
            self.assertEqual(outbox.payload["purpose"], "Material Issue")
            self.assertEqual(outbox.payload["source_warehouse"], self.WAREHOUSE)
            self.assertIsNone(outbox.payload["target_warehouse"])
            self.assertEqual(outbox.payload["items"][0]["item_code"], self.ITEM_CODE)
            self.assertEqual(Decimal(str(outbox.payload["items"][0]["qty"])), Decimal("7"))
            self.assertEqual(outbox.payload["items"][0]["source_warehouse"], self.WAREHOUSE)
            self.assertIsNone(outbox.payload["items"][0]["target_warehouse"])

            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                )
                .one()
            )
            self.assertEqual(int(audit.resource_id), draft_id)
            self.assertEqual(audit.after_data["purpose"], "Material Issue")
            self.assertEqual(audit.after_data["source_warehouse"], self.WAREHOUSE)
            self.assertIsNone(audit.after_data["target_warehouse"])

    def test_material_receipt_filters_process_and_other_inbound_source_types(self) -> None:
        process_payload = self._process_inbound_payload(qty="6")
        process = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(process_payload),
            ),
            json=process_payload,
        )
        self.assertEqual(process.status_code, 201, process.text)
        self.assertEqual(process.json()["data"]["source_type"], "material_process_inbound")

        other_payload = self._other_inbound_payload(qty="7")
        other = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(other_payload),
            ),
            json=other_payload,
        )
        self.assertEqual(other.status_code, 201, other.text)
        other_id = int(other.json()["data"]["id"])
        self.assertEqual(other.json()["data"]["source_type"], "material_other_inbound")

        all_receipts = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Receipt",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(all_receipts.status_code, 200, all_receipts.text)
        self.assertEqual(all_receipts.json()["data"]["total"], 2)

        filtered = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Receipt&source_type=material_other_inbound",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        data = filtered.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), other_id)
        self.assertEqual(data["items"][0]["source_type"], "material_other_inbound")
        self.assertEqual(data["items"][0]["purpose"], "Material Receipt")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == other_id).one()
            self.assertEqual(str(draft.source_type), "material_other_inbound")
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=other_id).one()
            self.assertEqual(outbox.payload["source_type"], "material_other_inbound")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_id == other_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_other_inbound")

    def test_create_material_issue_idempotent_replay_same_payload_no_duplicate_rows(self) -> None:
        payload = self._material_issue_payload()
        headers = self._headers(
            "warehouse:stock_entry_draft,warehouse:read",
            request_id=self._request_id_from_payload(payload),
        )
        first = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=headers,
            json=payload,
        )
        self.assertEqual(first.status_code, 201, first.text)

        second = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=headers,
            json=payload,
        )
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["data"]["id"], first.json()["data"]["id"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 1)
            self.assertEqual(session.query(LyWarehouseStockEntryDraftItem).count(), 1)
            self.assertEqual(session.query(LyWarehouseStockEntryOutboxEvent).count(), 1)

    def test_purchase_return_material_issue_filters_by_source_type(self) -> None:
        purchase_return_payload = self._purchase_return_payload(qty="4")
        created = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(purchase_return_payload),
            ),
            json=purchase_return_payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        purchase_return_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["source_type"], "material_purchase_return")

        manual_payload = self._material_issue_payload(qty="2")
        manual_payload["source_id"] = f"{self.SCENARIO_TAG}-MANUAL-ISSUE-001"
        manual_payload["source_ref"] = f"{self.SCENARIO_TAG}-MANUAL-ISSUE-001"
        manual_payload["idempotency_key"] = f"{self.SCENARIO_TAG}-IDEM-MANUAL-ISSUE-001"
        manual = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(manual_payload),
            ),
            json=manual_payload,
        )
        self.assertEqual(manual.status_code, 201, manual.text)
        self.assertEqual(manual.json()["data"]["source_type"], "manual")

        all_issues = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(all_issues.status_code, 200, all_issues.text)
        self.assertEqual(all_issues.json()["data"]["total"], 2)

        filtered = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue&source_type=material_purchase_return",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        data = filtered.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), purchase_return_id)
        self.assertEqual(data["items"][0]["source_type"], "material_purchase_return")
        self.assertEqual(data["items"][0]["purpose"], "Material Issue")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == purchase_return_id).one()
            self.assertEqual(str(draft.source_type), "material_purchase_return")
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=purchase_return_id).one()
            self.assertEqual(outbox.payload["source_type"], "material_purchase_return")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_id == purchase_return_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_purchase_return")

    def test_sale_outbound_material_issue_filters_by_source_type(self) -> None:
        sale_payload = self._sale_outbound_payload(qty="3")
        created = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(sale_payload),
            ),
            json=sale_payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        sale_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["source_type"], "material_sale_outbound")

        purchase_return_payload = self._purchase_return_payload(qty="4")
        purchase_return = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(purchase_return_payload),
            ),
            json=purchase_return_payload,
        )
        self.assertEqual(purchase_return.status_code, 201, purchase_return.text)
        self.assertEqual(purchase_return.json()["data"]["source_type"], "material_purchase_return")

        filtered = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue&source_type=material_sale_outbound",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        data = filtered.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), sale_id)
        self.assertEqual(data["items"][0]["source_type"], "material_sale_outbound")
        self.assertEqual(data["items"][0]["purpose"], "Material Issue")

        detail = self.client.get(
            f"/api/warehouse/stock-entry-drafts/{sale_id}",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        detail_data = detail.json()["data"]
        self.assertEqual(detail_data["purpose"], "Material Issue")
        self.assertEqual(detail_data["source_type"], "material_sale_outbound")
        self.assertEqual(detail_data["source_warehouse"], self.WAREHOUSE)
        self.assertIsNone(detail_data["target_warehouse"])

        outbox_status = self.client.get(
            f"/api/warehouse/stock-entry-drafts/{sale_id}/outbox-status",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(outbox_status.status_code, 200, outbox_status.text)
        self.assertEqual(outbox_status.json()["data"]["event_type"], "warehouse_stock_entry_sync")
        self.assertEqual(outbox_status.json()["data"]["status"], "in_pending")

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?item_code={self.ITEM_CODE}&warehouse={self.WAREHOUSE}",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        sale_ledger_rows = [
            row
            for row in ledger.json()["data"]["items"]
            if row["voucher_no"] == f"DRAFT-{sale_id}"
        ]
        self.assertEqual(len(sale_ledger_rows), 1)
        self.assertEqual(sale_ledger_rows[0]["voucher_type"], "Stock Entry Draft/Material Issue")
        self.assertEqual(Decimal(str(sale_ledger_rows[0]["actual_qty"])), Decimal("-3.000000"))

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == sale_id).one()
            self.assertEqual(str(draft.source_type), "material_sale_outbound")
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=sale_id).one()
            self.assertEqual(outbox.payload["source_type"], "material_sale_outbound")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_id == sale_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_sale_outbound")

    def test_material_hold_issue_filters_by_source_type(self) -> None:
        hold_payload = self._hold_payload(qty="5")
        created = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(hold_payload),
            ),
            json=hold_payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        hold_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["source_type"], "material_hold")

        sale_payload = self._sale_outbound_payload(qty="3")
        sale = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(sale_payload),
            ),
            json=sale_payload,
        )
        self.assertEqual(sale.status_code, 201, sale.text)
        self.assertEqual(sale.json()["data"]["source_type"], "material_sale_outbound")

        all_issues = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(all_issues.status_code, 200, all_issues.text)
        self.assertEqual(all_issues.json()["data"]["total"], 2)

        filtered = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue&source_type=material_hold",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        data = filtered.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), hold_id)
        self.assertEqual(data["items"][0]["source_type"], "material_hold")
        self.assertEqual(data["items"][0]["purpose"], "Material Issue")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == hold_id).one()
            self.assertEqual(str(draft.source_type), "material_hold")
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=hold_id).one()
            self.assertEqual(outbox.payload["source_type"], "material_hold")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_id == hold_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_hold")

    def test_material_retention_disposal_issue_filters_and_updates_ledger(self) -> None:
        payload = self._retention_disposal_payload(qty="8")
        created = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        draft_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["source_type"], "material_retention_disposal")
        self.assertEqual(created.json()["data"]["purpose"], "Material Issue")

        filtered = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Issue&source_type=material_retention_disposal",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        data = filtered.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["items"][0]["id"]), draft_id)
        self.assertEqual(data["items"][0]["source_type"], "material_retention_disposal")

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?item_code={self.ITEM_CODE}&warehouse={self.WAREHOUSE}",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_rows = [
            row
            for row in ledger.json()["data"]["items"]
            if row["voucher_no"] == f"DRAFT-{draft_id}"
        ]
        self.assertEqual(len(ledger_rows), 1)
        self.assertEqual(ledger_rows[0]["voucher_type"], "Stock Entry Draft/Material Issue")
        self.assertEqual(Decimal(str(ledger_rows[0]["actual_qty"])), Decimal("-8.000000"))

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.source_type), "material_retention_disposal")
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=draft_id).one()
            self.assertEqual(outbox.payload["source_type"], "material_retention_disposal")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_id == draft_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_retention_disposal")

    def test_replay_with_different_payload_returns_409(self) -> None:
        first_payload = self._payload(qty="5")
        first = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(first_payload),
            ),
            json=first_payload,
        )
        self.assertEqual(first.status_code, 201, first.text)

        conflict_payload = self._payload(qty="6")
        conflict = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(conflict_payload),
            ),
            json=conflict_payload,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "WAREHOUSE_IDEMPOTENCY_CONFLICT")

    def test_qty_lte_zero_returns_400(self) -> None:
        payload = self._payload(qty="0")
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_QTY")

    def test_without_stock_entry_draft_permission_returns_403(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_write_only_cannot_create_draft(self) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("inventory:write"),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_company_scope_denied_returns_403_or_404(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-X"},
                allowed_warehouses={"WH-A", "WH-B"},
                allowed_items={"ITEM-A"},
            ),
        ):
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers("warehouse:stock_entry_draft"),
                json=self._payload(),
            )
        self.assertIn(response.status_code, {403, 404})

    def test_warehouse_scope_denied_returns_403_or_404(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
                allowed_items={"ITEM-A"},
            ),
        ):
            response = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers("warehouse:stock_entry_draft"),
                json=self._payload(),
            )
        self.assertIn(response.status_code, {403, 404})

    def test_cancel_draft_success_and_outbox_cancelled(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read"),
            json=self._payload(),
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(
                    self._cancel_payload(reason="manual cancel"),
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=self._cancel_payload(reason="manual cancel"),
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")
        self.assertEqual(cancel_resp.json()["data"]["outbox"]["status"], "cancelled")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "cancelled")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "cancelled")

    def test_cancel_material_transfer_removes_source_and_target_local_balance(self) -> None:
        payload = self._payload(qty="4")
        payload["target_warehouse"] = "WH-C"
        payload["items"][0]["target_warehouse"] = "WH-C"
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(payload),
            ),
            json=payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        source_ledger = self._stock_ledger_items(item_code=self.ITEM_CODE, warehouse=self.WAREHOUSE)
        target_ledger = self._stock_ledger_items(item_code=self.ITEM_CODE, warehouse="WH-C")
        self.assertEqual(len(source_ledger), 1)
        self.assertEqual(len(target_ledger), 1)
        self.assertEqual(Decimal(str(source_ledger[0]["actual_qty"])), Decimal("-4.000000"))
        self.assertEqual(Decimal(str(target_ledger[0]["actual_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(source_ledger[0]["qty_after_transaction"])), Decimal("-4.000000"))
        self.assertEqual(Decimal(str(target_ledger[0]["qty_after_transaction"])), Decimal("4.000000"))

        source_summary = self._stock_summary_items(item_code=self.ITEM_CODE, warehouse=self.WAREHOUSE)
        target_summary = self._stock_summary_items(item_code=self.ITEM_CODE, warehouse="WH-C")
        self.assertEqual(Decimal(str(source_summary[0]["actual_qty"])), Decimal("-4.000000"))
        self.assertEqual(Decimal(str(target_summary[0]["actual_qty"])), Decimal("4.000000"))

        cancel_payload = self._cancel_payload(reason="reverse transfer", source_payload=payload)
        cancel_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(
                    cancel_payload,
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=cancel_payload,
        )
        self.assertEqual(cancel_resp.status_code, 200, cancel_resp.text)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")
        self.assertEqual(cancel_resp.json()["data"]["outbox"]["status"], "cancelled")

        self.assertEqual(self._stock_ledger_items(item_code=self.ITEM_CODE, warehouse=self.WAREHOUSE), [])
        self.assertEqual(self._stock_ledger_items(item_code=self.ITEM_CODE, warehouse="WH-C"), [])
        self.assertEqual(self._stock_summary_items(item_code=self.ITEM_CODE, warehouse=self.WAREHOUSE), [])
        self.assertEqual(self._stock_summary_items(item_code=self.ITEM_CODE, warehouse="WH-C"), [])

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "cancelled")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "cancelled")

    def test_repeat_cancel_returns_409(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:stock_entry_cancel,warehouse:read"),
            json=self._payload(),
        )
        draft_id = int(create_resp.json()["data"]["id"])

        first = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(
                    self._cancel_payload(reason="first"),
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=self._cancel_payload(reason="first"),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                "warehouse:stock_entry_cancel,warehouse:read",
                request_id=self._request_id_from_payload(
                    self._cancel_payload(reason="again"),
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                ),
            ),
            json=self._cancel_payload(reason="again"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "WAREHOUSE_DRAFT_ALREADY_CANCELLED")

    def test_release_material_hold_success_and_outbox_cancelled(self) -> None:
        hold_payload = self._hold_payload(qty="5")
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(hold_payload),
            ),
            json=hold_payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        release_payload = self._release_hold_payload(reason="release hold", source_payload=hold_payload)
        release_resp = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/release-hold",
            headers=self._headers(
                "warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(
                    release_payload,
                    operation="release_material_hold",
                    status_action="release",
                ),
            ),
            json=release_payload,
        )
        self.assertEqual(release_resp.status_code, 200, release_resp.text)
        self.assertEqual(release_resp.json()["data"]["status"], "cancelled")
        self.assertEqual(release_resp.json()["data"]["outbox"]["status"], "cancelled")
        self.assertEqual(release_resp.json()["data"]["cancel_reason"], "release hold")

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter(LyWarehouseStockEntryDraft.id == draft_id).one()
            self.assertEqual(str(draft.status), "cancelled")
            self.assertEqual(str(draft.cancel_reason), "release hold")
            outbox = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
                .one()
            )
            self.assertEqual(str(outbox.status), "cancelled")
            audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.action == "warehouse:stock_hold_release",
                    LyOperationAuditLog.resource_id == draft_id,
                )
                .one()
            )
            self.assertEqual(audit.after_data["source_type"], "material_hold")

    def test_release_material_hold_rejects_non_hold_source_type(self) -> None:
        sale_payload = self._sale_outbound_payload(qty="5")
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(sale_payload),
            ),
            json=sale_payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        release_payload = self._release_hold_payload(reason="release non hold", source_payload=sale_payload)
        response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/release-hold",
            headers=self._headers(
                "warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(
                    release_payload,
                    operation="release_material_hold",
                    status_action="release",
                ),
            ),
            json=release_payload,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WAREHOUSE_IDEMPOTENCY_CONFLICT")

    def test_release_material_hold_rejects_succeeded_outbox(self) -> None:
        hold_payload = self._hold_payload(qty="5")
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(hold_payload),
            ),
            json=hold_payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])
        with self.SessionLocal() as session:
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=draft_id).one()
            outbox.status = "succeeded"
            session.commit()

        release_payload = self._release_hold_payload(reason="release succeeded", source_payload=hold_payload)
        response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/release-hold",
            headers=self._headers(
                "warehouse:stock_hold_release,warehouse:read",
                request_id=self._request_id_from_payload(
                    release_payload,
                    operation="release_material_hold",
                    status_action="release",
                ),
            ),
            json=release_payload,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_STATUS")

    def test_release_material_hold_requires_permission(self) -> None:
        hold_payload = self._hold_payload(qty="5")
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                "warehouse:stock_entry_draft,warehouse:read",
                request_id=self._request_id_from_payload(hold_payload),
            ),
            json=hold_payload,
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        draft_id = int(create_resp.json()["data"]["id"])

        release_payload = self._release_hold_payload(reason="no permission", source_payload=hold_payload)
        response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/release-hold",
            headers=self._headers(
                "warehouse:read",
                request_id=self._request_id_from_payload(
                    release_payload,
                    operation="release_material_hold",
                    status_action="release",
                ),
            ),
            json=release_payload,
        )
        self.assertEqual(response.status_code, 403)

    def test_outbox_status_returns_correct_payload(self) -> None:
        create_resp = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers("warehouse:stock_entry_draft,warehouse:read"),
            json=self._payload(),
        )
        draft_id = int(create_resp.json()["data"]["id"])

        status_resp = self.client.get(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/outbox-status",
            headers=self._headers("warehouse:read"),
        )
        self.assertEqual(status_resp.status_code, 200, status_resp.text)
        data = status_resp.json()["data"]
        self.assertEqual(int(data["draft_id"]), draft_id)
        self.assertEqual(data["status"], "in_pending")
        self.assertEqual(data["event_type"], "warehouse_stock_entry_sync")

    def test_no_erpnext_write_call_signature(self) -> None:
        from app.routers import warehouse as warehouse_router_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked = [
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "/api/resource/Stock Entry",
            "/api/resource/Stock Reconciliation",
            "/api/resource/Stock Ledger Entry",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, content)

    def test_no_forbidden_business_semantics_signature(self) -> None:
        from app.models import warehouse as warehouse_model_module
        from app.routers import warehouse as warehouse_router_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_model_module.__file__, encoding="utf-8").read(),
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked = [
            "submit_stock_entry",
            "Stock Reconciliation",
            "GL Entry",
            "Payment Entry",
            "Purchase Invoice",
            "docstatus = 1",
            "docstatus==1",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, content)


if __name__ == "__main__":
    unittest.main()
