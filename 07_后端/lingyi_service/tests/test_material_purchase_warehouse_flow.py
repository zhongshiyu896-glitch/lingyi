"""A5 material purchase order to warehouse receipt draft flow."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
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
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.quality import Base as QualityBase
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractStockOutbox
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.material_purchase import get_db_session as material_purchase_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class MaterialPurchaseWarehouseFlowTest(unittest.TestCase):
    """Validate existing purchase and stock-entry pages can use native data."""

    SCENARIO_TAG = "Z003-WAREHOUSE-20260616-101"
    BUSINESS_DATE = date(2026, 6, 16).isoformat()
    WAREHOUSE = "WH-A"
    ITEM_CODE = "FAB-A"

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
        MasterDataBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-WHSE-FRR-001",
                    item_code="STYLE-FRR",
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
        app.dependency_overrides[material_purchase_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ.pop("LINGYI_FASTAPI_ROLE_ACTIONS_JSON", None)
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            self._seed_purchase_master_data(
                session=session,
                company="COMP-A",
                supplier_name="SUP-A",
                material_code=self.ITEM_CODE,
                warehouse=self.WAREHOUSE,
            )
            session.commit()

    @staticmethod
    def _seed_purchase_master_data(
        *,
        session,
        company: str,
        supplier_name: str,
        material_code: str,
        material_status: str = "active",
        warehouse: str | None = None,
        warehouse_status: str = "active",
    ) -> None:
        session.add(
            LyMasterDataRecord(
                entity_type="supplier",
                company=company,
                code=supplier_name,
                name=supplier_name,
                status="active",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )
        if warehouse:
            session.add(
                LyMasterDataRecord(
                    entity_type="warehouse",
                    company=company,
                    code=warehouse,
                    name=warehouse,
                    status=warehouse_status,
                    payload={},
                    created_by="seed",
                    updated_by="seed",
                )
            )
        session.add(
            LyMasterDataRecord(
                entity_type="material",
                company=company,
                code=material_code,
                name=f"{material_code}物料",
                status=material_status,
                payload={"material_kind": "fabric", "material_item_code": material_code, "uom": "米"},
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            LyMasterDataRecord(
                entity_type="material",
                company=company,
                code="MU-METER",
                name="米",
                status="active",
                payload={"material_kind": "unit", "unit_code": "MU-METER", "unit_name": "米", "base_unit": "米"},
                created_by="seed",
                updated_by="seed",
            )
        )

    @staticmethod
    def _headers(*, request_id: str = "req-a5-material-purchase") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "a5.purchase.user",
            "X-LY-Dev-Roles": "System Manager",
            "X-Request-ID": request_id,
        }

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
    def _warehouse_request_id(
        cls,
        *,
        idempotency_key: str,
        source_ref: str,
        quantity: object,
        warehouse: str | None = None,
        item_code: str | None = None,
        business_date: str | None = None,
        operation: str = "create_stock_entry_draft",
        status_action: str = "create",
    ) -> str:
        operation_code = {
            "create_stock_entry_draft": "C",
            "audit_stock_entry_draft": "A",
            "cancel_stock_entry_draft": "X",
        }.get(operation, "X")
        status_action_code = {
            "create": "C",
            "audit": "A",
            "cancel": "X",
        }.get(status_action, "X")
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                operation_code,
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(warehouse or cls.WAREHOUSE),
                cls._carrier_code(item_code or cls.ITEM_CODE),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(business_date or cls.BUSINESS_DATE),
                cls._carrier_code(status_action_code),
            ]
        )

    def _stock_entry_payload(
        self,
        *,
        source_ref: str,
        idempotency_key: str,
        item_code: str | None = None,
        warehouse: str | None = None,
        qty: str = "5",
        company: str = "COMP-A",
    ) -> dict:
        material_code = item_code or self.ITEM_CODE
        target_warehouse = warehouse or self.WAREHOUSE
        return {
            "operation": "create_stock_entry_draft",
            "company": company,
            "purpose": "Material Receipt",
            "source_type": "material_other_inbound",
            "source_id": source_ref,
            "source_ref": source_ref,
            "warehouse": target_warehouse,
            "item_code": material_code,
            "quantity": qty,
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": target_warehouse,
            "idempotency_key": idempotency_key,
            "items": [
                {
                    "item_code": material_code,
                    "qty": qty,
                    "uom": "米",
                    "target_warehouse": target_warehouse,
                }
            ],
        }

    def _purchase_order_payload(
        self,
        *,
        purchase_no: str,
        idempotency_key: str,
        material_code: str | None = None,
        qty: str = "10",
    ) -> dict:
        material_item_code = material_code or self.ITEM_CODE
        return {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": purchase_no,
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": idempotency_key,
            "items": [
                {
                    "material_item_code": material_item_code,
                    "material_name": f"{material_item_code}物料",
                    "qty": qty,
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }

    def _material_receipt_payload(
        self,
        *,
        purchase_no: str,
        idempotency_key: str,
        qty: str = "5",
    ) -> tuple[str, dict]:
        source_ref = f"{self.SCENARIO_TAG}:purchase:{purchase_no}"
        return source_ref, {
            "company": "COMP-A",
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": source_ref,
            "source_ref": source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": qty,
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": self.WAREHOUSE,
            "idempotency_key": idempotency_key,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": qty,
                    "uom": "米",
                    "target_warehouse": self.WAREHOUSE,
                }
            ],
        }

    def test_material_purchase_orders_list_orders_by_created_at_desc_then_id_desc(self) -> None:
        first = self.client.post(
            "/api/material-purchase/orders",
            headers=self._headers(request_id="req-po-sort-a"),
            json=self._purchase_order_payload(purchase_no="PO-A5-SORT-A", idempotency_key="idem-po-sort-a"),
        )
        second = self.client.post(
            "/api/material-purchase/orders",
            headers=self._headers(request_id="req-po-sort-b"),
            json=self._purchase_order_payload(purchase_no="PO-A5-SORT-B", idempotency_key="idem-po-sort-b"),
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)

        same_created_at = datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc)
        with self.SessionLocal() as session:
            rows = (
                session.query(LyMaterialPurchaseOrder)
                .filter(LyMaterialPurchaseOrder.purchase_no.in_(["PO-A5-SORT-A", "PO-A5-SORT-B"]))
                .all()
            )
            for row in rows:
                row.created_at = same_created_at
            session.commit()

        response = self.client.get("/api/material-purchase/orders?company=COMP-A&page_size=10", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        purchase_nos = [row["purchase_no"] for row in response.json()["data"]["items"]]
        self.assertEqual(purchase_nos[:2], ["PO-A5-SORT-B", "PO-A5-SORT-A"])

    def test_purchase_receipts_list_orders_by_created_at_desc_then_id_desc(self) -> None:
        for suffix in ["A", "B"]:
            purchase_no = f"PO-A5-RECEIPT-SORT-{suffix}"
            create_po = self.client.post(
                "/api/material-purchase/orders",
                headers=self._headers(request_id=f"req-po-receipt-sort-{suffix.lower()}"),
                json=self._purchase_order_payload(
                    purchase_no=purchase_no,
                    idempotency_key=f"idem-po-receipt-sort-{suffix.lower()}",
                ),
            )
            self.assertEqual(create_po.status_code, 201, create_po.text)

            receipt_idem = f"{self.SCENARIO_TAG}:idem-receipt-sort-{suffix.lower()}"
            source_ref, receipt_payload = self._material_receipt_payload(
                purchase_no=purchase_no,
                idempotency_key=receipt_idem,
            )
            receipt = self.client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=self._headers(
                    request_id=self._warehouse_request_id(
                        idempotency_key=receipt_idem,
                        source_ref=source_ref,
                        quantity="5",
                    )
                ),
                json=receipt_payload,
            )
            self.assertEqual(receipt.status_code, 201, receipt.text)
            draft_id = int(receipt.json()["data"]["id"])
            audit = self.client.post(
                f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
                headers=self._headers(
                    request_id=self._warehouse_request_id(
                        idempotency_key=receipt_idem,
                        source_ref=source_ref,
                        quantity="5",
                        operation="audit_stock_entry_draft",
                        status_action="audit",
                    )
                ),
                json={
                    "reason": "采购入库排序保护",
                    "idempotency_key": receipt_idem,
                    "source_ref": source_ref,
                    "warehouse": self.WAREHOUSE,
                    "item_code": self.ITEM_CODE,
                    "operation": "audit_stock_entry_draft",
                    "quantity": "5",
                    "business_date": self.BUSINESS_DATE,
                    "status_action": "audit",
                    "scenario_tag": self.SCENARIO_TAG,
                },
            )
            self.assertEqual(audit.status_code, 200, audit.text)

        same_created_at = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
        with self.SessionLocal() as session:
            rows = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(
                    LyWarehouseStockEntryDraft.source_id.in_(
                        [
                            f"{self.SCENARIO_TAG}:purchase:PO-A5-RECEIPT-SORT-A",
                            f"{self.SCENARIO_TAG}:purchase:PO-A5-RECEIPT-SORT-B",
                        ]
                    )
                )
                .all()
            )
            for row in rows:
                row.created_at = same_created_at
            session.commit()

        response = self.client.get("/api/warehouse/purchase-receipts?company=COMP-A&page_size=10", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        purchase_nos = [row["purchase_no"] for row in response.json()["data"]["items"]]
        self.assertEqual(purchase_nos[:2], ["PO-A5-RECEIPT-SORT-B", "PO-A5-RECEIPT-SORT-A"])

    def test_create_purchase_order_rejects_inactive_material_master(self) -> None:
        inactive_material = "FAB-A-INACTIVE"
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code=inactive_material,
                    name="停用面料",
                    status="inactive",
                    payload={"material_kind": "fabric", "material_item_code": inactive_material, "uom": "米"},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-INACTIVE-MAT",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-inactive-mat",
            "items": [
                {
                    "material_item_code": inactive_material,
                    "material_name": "停用面料",
                    "qty": "10",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }

        response = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("物料不存在或已停用", response.json()["message"])

    def test_create_purchase_order_rejects_inactive_warehouse_master(self) -> None:
        inactive_warehouse = "WH-OFFLINE"
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="warehouse",
                    company="COMP-A",
                    code=inactive_warehouse,
                    name=inactive_warehouse,
                    status="inactive",
                    payload={},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-INACTIVE-WH",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-inactive-wh",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "10",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": inactive_warehouse,
                }
            ],
        }

        response = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("仓库不存在或已停用", response.json()["message"])

    def test_create_purchase_order_rejects_missing_or_inactive_unit_master(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code="MU-YARD-OFF",
                    name="码",
                    status="inactive",
                    payload={"material_kind": "unit", "unit_code": "MU-YARD-OFF", "unit_name": "码", "base_unit": "码"},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-INACTIVE-UOM",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-inactive-uom",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "10",
                    "uom": "码",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }

        response = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("物料单位不存在或已停用", response.json()["message"])

    def test_stock_entry_draft_rejects_inactive_material_master(self) -> None:
        inactive_material = "FAB-STOCK-INACTIVE"
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code=inactive_material,
                    name="停用库存物料",
                    status="inactive",
                    payload={"material_kind": "fabric", "material_item_code": inactive_material, "uom": "米"},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        idempotency_key = f"{self.SCENARIO_TAG}:stock-inactive-material"
        source_ref = f"{self.SCENARIO_TAG}:stock-inactive-material-src"
        payload = self._stock_entry_payload(
            source_ref=source_ref,
            idempotency_key=idempotency_key,
            item_code=inactive_material,
        )
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_ref,
                    item_code=inactive_material,
                    quantity="5",
                )
            ),
            json=payload,
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_PAYLOAD")
        self.assertIn("物料主数据不存在或已停用", response.json()["message"])

    def test_stock_entry_draft_rejects_inactive_warehouse_master(self) -> None:
        inactive_warehouse = "WH-STOCK-OFFLINE"
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="warehouse",
                    company="COMP-A",
                    code=inactive_warehouse,
                    name=inactive_warehouse,
                    status="inactive",
                    payload={},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        idempotency_key = f"{self.SCENARIO_TAG}:stock-inactive-warehouse"
        source_ref = f"{self.SCENARIO_TAG}:stock-inactive-warehouse-src"
        payload = self._stock_entry_payload(
            source_ref=source_ref,
            idempotency_key=idempotency_key,
            warehouse=inactive_warehouse,
        )
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_ref,
                    warehouse=inactive_warehouse,
                    quantity="5",
                )
            ),
            json=payload,
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["code"], "WAREHOUSE_INVALID_PAYLOAD")
        self.assertIn("仓库主数据不存在或已停用", response.json()["message"])

    def test_stock_entry_draft_idempotent_replay_ignores_later_master_deactivation(self) -> None:
        idempotency_key = f"{self.SCENARIO_TAG}:stock-replay-after-master-off"
        source_ref = f"{self.SCENARIO_TAG}:stock-replay-after-master-off-src"
        payload = self._stock_entry_payload(source_ref=source_ref, idempotency_key=idempotency_key)
        headers = self._headers(
            request_id=self._warehouse_request_id(
                idempotency_key=idempotency_key,
                source_ref=source_ref,
                quantity="5",
            )
        )
        created = self.client.post("/api/warehouse/stock-entry-drafts", headers=headers, json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        draft_id = created.json()["data"]["id"]

        with self.SessionLocal() as session:
            for record in (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.company == "COMP-A",
                    LyMasterDataRecord.code.in_([self.ITEM_CODE, self.WAREHOUSE]),
                )
                .all()
            ):
                record.status = "inactive"
            session.commit()

        replayed = self.client.post("/api/warehouse/stock-entry-drafts", headers=headers, json=payload)

        self.assertEqual(replayed.status_code, 201, replayed.text)
        self.assertEqual(replayed.json()["data"]["id"], draft_id)

    def test_purchase_order_receipt_audit_updates_received_qty_and_audits(self) -> None:
        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-001",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-001",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "50",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }
        create_po = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)
        replay_po = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)
        list_po = self.client.get("/api/material-purchase/orders?keyword=PO-A5-001", headers=self._headers())

        self.assertEqual(create_po.status_code, 201, create_po.text)
        self.assertEqual(replay_po.status_code, 201, replay_po.text)
        self.assertEqual(create_po.json()["data"]["id"], replay_po.json()["data"]["id"])
        self.assertEqual(list_po.status_code, 200)
        self.assertEqual(list_po.json()["data"]["total"], 1)

        receipt_idem = f"{self.SCENARIO_TAG}:idem-whse-po-a5-001"
        receipt_source_ref = f"{self.SCENARIO_TAG}:purchase:PO-A5-001"
        receipt_payload = {
            "company": "COMP-A",
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": receipt_source_ref,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": self.WAREHOUSE,
            "idempotency_key": receipt_idem,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": "20",
                    "uom": "米",
                    "target_warehouse": self.WAREHOUSE,
                }
            ],
        }
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json=receipt_payload,
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)
        self.assertEqual(receipt.json()["data"]["status"], "draft")
        draft_id = int(receipt.json()["data"]["id"])
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).one()
            line = session.query(LyMaterialPurchaseOrderItem).one()
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).one()
            self.assertEqual(str(order.status), "draft")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(outbox.status), "in_pending")

        pre_audit_worker = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once?dry_run=true",
            headers=self._headers(request_id="req-purchase-receipt-draft-worker"),
        )
        self.assertEqual(pre_audit_worker.status_code, 200, pre_audit_worker.text)
        self.assertEqual(pre_audit_worker.json()["data"]["processed_count"], 0)

        audit_payload = {
            "reason": "采购入库审核后回写",
            "idempotency_key": receipt_idem,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "audit_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "audit",
            "scenario_tag": self.SCENARIO_TAG,
        }
        audit_request_id = self._warehouse_request_id(
            idempotency_key=receipt_idem,
            source_ref=receipt_source_ref,
            quantity="20",
            operation="audit_stock_entry_draft",
            status_action="audit",
        )
        audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers(request_id=audit_request_id),
            json=audit_payload,
        )
        replay_audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers(request_id=audit_request_id),
            json=audit_payload,
        )
        list_drafts = self.client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Receipt&keyword=PO-A5-001",
            headers=self._headers(),
        )
        stock_ledger = self.client.get(
            "/api/warehouse/stock-ledger?item_code=FAB-A",
            headers=self._headers(),
        )
        stock_summary = self.client.get(
            "/api/warehouse/stock-summary?item_code=FAB-A",
            headers=self._headers(),
        )
        count_scenario_tag = "Z002-WAREHOUSE-COUNT-20260616-101"
        count_request_id = (
            f"{count_scenario_tag}-REQ-COUNT-"
            f"W{self._carrier_code(self.WAREHOUSE, length=8)}-"
            f"D{date.fromisoformat(self.BUSINESS_DATE).strftime('%Y%m%d')}"
        )
        inventory_count = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers(request_id=count_request_id),
            json={
                "company": "COMP-A",
                "warehouse": self.WAREHOUSE,
                "count_date": self.BUSINESS_DATE,
                "idempotency_key": f"{count_scenario_tag}:inventory-count-after-po-receipt",
                "source_ref": f"{count_scenario_tag}:inventory-count-after-po-receipt",
                "remark": "采购入库后账实平串联",
                "items": [
                    {
                        "item_code": self.ITEM_CODE,
                        "batch_no": None,
                        "serial_no": None,
                        "system_qty": "0",
                        "counted_qty": "18",
                        "variance_reason": "采购入库后抽盘",
                    }
                ],
            },
        )
        inventory_reconciliation = self.client.get(
            f"/api/warehouse/inventory-balance-reconciliation?company=COMP-A&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(request_id="req-purchase-receipt-inventory-balance"),
        )
        return_report = self.client.get(
            "/api/warehouse/factory-return-material-report?item_code=FAB-A",
            headers=self._headers(),
        )
        purchase_receipts = self.client.get(
            "/api/warehouse/purchase-receipts?company=COMP-A&material_item_code=FAB-A",
            headers=self._headers(),
        )
        purchase_receipts_by_no = self.client.get(
            "/api/warehouse/purchase-receipts?company=COMP-A&purchase_no=PO-A5-001",
            headers=self._headers(),
        )
        purchase_receipts_missing = self.client.get(
            "/api/warehouse/purchase-receipts?company=COMP-A&purchase_no=PO-A5-MISSING",
            headers=self._headers(),
        )

        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        self.assertEqual(replay_audit_response.status_code, 200, replay_audit_response.text)
        self.assertEqual(audit_response.json()["data"]["status"], "pending_outbox")
        self.assertEqual(replay_audit_response.json()["data"]["id"], draft_id)
        self.assertEqual(list_drafts.status_code, 200, list_drafts.text)
        self.assertEqual(list_drafts.json()["data"]["total"], 1)
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        ledger_items = stock_ledger.json()["data"]["items"]
        self.assertEqual(stock_ledger.json()["data"]["total"], 1)
        self.assertEqual(ledger_items[0]["item_code"], self.ITEM_CODE)
        self.assertEqual(ledger_items[0]["warehouse"], self.WAREHOUSE)
        self.assertEqual(Decimal(str(ledger_items[0]["actual_qty"])), Decimal("20.0"))
        self.assertEqual(Decimal(str(ledger_items[0]["qty_after_transaction"])), Decimal("20.0"))
        self.assertEqual(ledger_items[0]["voucher_type"], "Stock Entry Draft/Material Receipt")
        self.assertEqual(ledger_items[0]["voucher_no"], f"DRAFT-{draft_id}")
        self.assertEqual(ledger_items[0]["posting_date"], self.BUSINESS_DATE)
        self.assertEqual(stock_summary.status_code, 200, stock_summary.text)
        summary_items = stock_summary.json()["data"]["items"]
        self.assertEqual(len(summary_items), 1)
        self.assertEqual(Decimal(str(summary_items[0]["actual_qty"])), Decimal("20.0"))
        self.assertEqual(
            Decimal(str(summary_items[0]["actual_qty"])),
            sum(Decimal(str(row["actual_qty"])) for row in ledger_items),
        )
        self.assertEqual(
            Decimal(str(summary_items[0]["actual_qty"])),
            Decimal(str(ledger_items[-1]["qty_after_transaction"])),
        )
        self.assertEqual(inventory_count.status_code, 201, inventory_count.text)
        self.assertEqual(inventory_count.json()["data"]["warehouse"], self.WAREHOUSE)
        self.assertEqual(inventory_reconciliation.status_code, 200, inventory_reconciliation.text)
        reconciliation_rows = inventory_reconciliation.json()["data"]["items"]
        self.assertEqual(inventory_reconciliation.json()["data"]["total"], 1)
        self.assertEqual(reconciliation_rows[0]["warehouse"], self.WAREHOUSE)
        self.assertEqual(reconciliation_rows[0]["item_code"], self.ITEM_CODE)
        self.assertEqual(Decimal(str(reconciliation_rows[0]["book_qty"])), Decimal("20.000000"))
        self.assertEqual(Decimal(str(reconciliation_rows[0]["actual_qty"])), Decimal("18.000000"))
        self.assertEqual(Decimal(str(reconciliation_rows[0]["diff_qty"])), Decimal("-2.000000"))
        self.assertEqual(reconciliation_rows[0]["status"], "pending")
        count_id = int(inventory_count.json()["data"]["id"])
        count_item_id = int(inventory_count.json()["data"]["items"][0]["id"])
        submit_count = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/submit",
            headers=self._headers(request_id=count_request_id),
        )
        self.assertEqual(submit_count.status_code, 200, submit_count.text)
        self.assertEqual(submit_count.json()["data"]["status"], "counted")
        review_count = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/variance-review",
            headers=self._headers(request_id=count_request_id),
            json={
                "items": [
                    {
                        "item_id": count_item_id,
                        "review_status": "accepted",
                        "variance_reason": "采购入库后盘点复核通过",
                    }
                ]
            },
        )
        self.assertEqual(review_count.status_code, 200, review_count.text)
        self.assertEqual(review_count.json()["data"]["variance_stats"]["pending_review_items"], 0)
        confirm_count = self.client.post(
            f"/api/warehouse/inventory-counts/{count_id}/confirm",
            headers=self._headers(request_id=count_request_id),
        )
        self.assertEqual(confirm_count.status_code, 200, confirm_count.text)
        self.assertEqual(confirm_count.json()["data"]["status"], "confirmed")
        adjusted_summary = self.client.get(
            "/api/warehouse/stock-summary?item_code=FAB-A",
            headers=self._headers(request_id="req-purchase-receipt-inventory-adjusted-summary"),
        )
        adjusted_ledger = self.client.get(
            "/api/warehouse/stock-ledger?item_code=FAB-A",
            headers=self._headers(request_id="req-purchase-receipt-inventory-adjusted-ledger"),
        )
        adjusted_reconciliation = self.client.get(
            f"/api/warehouse/inventory-balance-reconciliation?company=COMP-A&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(request_id="req-purchase-receipt-inventory-balanced"),
        )
        self.assertEqual(adjusted_summary.status_code, 200, adjusted_summary.text)
        adjusted_summary_items = adjusted_summary.json()["data"]["items"]
        self.assertEqual(Decimal(str(adjusted_summary_items[0]["actual_qty"])), Decimal("18.000000"))
        self.assertEqual(adjusted_ledger.status_code, 200, adjusted_ledger.text)
        adjusted_ledger_items = adjusted_ledger.json()["data"]["items"]
        self.assertEqual(
            sorted(Decimal(str(row["actual_qty"])) for row in adjusted_ledger_items),
            [Decimal("-2.000000"), Decimal("20.000000")],
        )
        adjustment_rows = [row for row in adjusted_ledger_items if Decimal(str(row["actual_qty"])) == Decimal("-2.000000")]
        self.assertEqual(len(adjustment_rows), 1)
        self.assertEqual(adjustment_rows[0]["voucher_type"], "Stock Entry Draft/Material Issue")
        self.assertEqual(adjusted_reconciliation.status_code, 200, adjusted_reconciliation.text)
        adjusted_reconciliation_rows = adjusted_reconciliation.json()["data"]["items"]
        self.assertEqual(adjusted_reconciliation.json()["data"]["total"], 1)
        self.assertEqual(Decimal(str(adjusted_reconciliation_rows[0]["book_qty"])), Decimal("18.000000"))
        self.assertEqual(Decimal(str(adjusted_reconciliation_rows[0]["actual_qty"])), Decimal("18.000000"))
        self.assertEqual(Decimal(str(adjusted_reconciliation_rows[0]["diff_qty"])), Decimal("0.000000"))
        self.assertEqual(adjusted_reconciliation_rows[0]["status"], "balanced")
        self.assertEqual(return_report.status_code, 200, return_report.text)
        report_items = return_report.json()["data"]["items"]
        self.assertEqual(report_items, [])
        self.assertEqual(purchase_receipts.status_code, 200, purchase_receipts.text)
        receipt_rows = purchase_receipts.json()["data"]["items"]
        self.assertEqual(purchase_receipts.json()["data"]["total"], 1)
        self.assertEqual(purchase_receipts_by_no.status_code, 200, purchase_receipts_by_no.text)
        self.assertEqual(purchase_receipts_by_no.json()["data"]["total"], 1)
        self.assertEqual(purchase_receipts_by_no.json()["data"]["items"][0]["purchase_no"], "PO-A5-001")
        self.assertEqual(purchase_receipts_missing.status_code, 200, purchase_receipts_missing.text)
        self.assertEqual(purchase_receipts_missing.json()["data"]["total"], 0)
        self.assertEqual(receipt_rows[0]["receipt_no"], "LY-WH-PR-1")
        self.assertNotEqual(receipt_rows[0]["receipt_no"], "PR-FR-001")
        self.assertEqual(receipt_rows[0]["purchase_no"], "PO-A5-001")
        self.assertEqual(receipt_rows[0]["supplier_name"], "SUP-A")
        self.assertEqual(receipt_rows[0]["material_item_code"], self.ITEM_CODE)
        self.assertEqual(receipt_rows[0]["status"], "outbox_pending")
        self.assertEqual(Decimal(str(receipt_rows[0]["received_qty"])), Decimal("20.000000"))

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).one()
            line = session.query(LyMaterialPurchaseOrderItem).one()
            ledger_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == "COMP-A",
                    LyWarehouseStockLedgerEntry.item_code == self.ITEM_CODE,
                    LyWarehouseStockLedgerEntry.warehouse == self.WAREHOUSE,
                    LyWarehouseStockLedgerEntry.voucher_type == "Stock Entry Draft/Material Receipt",
                    LyWarehouseStockLedgerEntry.voucher_no == f"DRAFT-{draft_id}",
                    LyWarehouseStockLedgerEntry.status == "active",
                )
                .all()
            )
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("20.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("20.000000"))
            self.assertEqual(len(ledger_rows), 1)
            self.assertEqual(str(ledger_rows[0].source_type), "stock_entry_draft")
            self.assertEqual(str(ledger_rows[0].source_id), str(draft_id))
            self.assertEqual(Decimal(str(ledger_rows[0].actual_qty)), Decimal("20.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("material_purchase:write", audit_actions)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)
            audit_count = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "warehouse",
                    LyOperationAuditLog.action == "warehouse:stock_entry_draft",
                    LyOperationAuditLog.resource_id == draft_id,
                    LyOperationAuditLog.request_id == audit_request_id,
                    LyOperationAuditLog.result == "success",
                )
                .count()
            )
            self.assertEqual(audit_count, 1)

    def test_purchase_receipt_then_material_issue_then_count_is_balanced(self) -> None:
        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-BALANCED-001",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-balanced-001",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "20",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }
        create_po = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)
        self.assertEqual(create_po.status_code, 201, create_po.text)

        receipt_idem = f"{self.SCENARIO_TAG}:idem-whse-po-balanced-001"
        receipt_source_ref = f"{self.SCENARIO_TAG}:purchase:PO-A5-BALANCED-001"
        receipt_payload = {
            "company": "COMP-A",
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": receipt_source_ref,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": self.WAREHOUSE,
            "idempotency_key": receipt_idem,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": "20",
                    "uom": "米",
                    "target_warehouse": self.WAREHOUSE,
                }
            ],
        }
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json=receipt_payload,
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)
        self.assertEqual(receipt.json()["data"]["status"], "draft")
        receipt_draft_id = int(receipt.json()["data"]["id"])
        audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{receipt_draft_id}/audit",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                    operation="audit_stock_entry_draft",
                    status_action="audit",
                )
            ),
            json={
                "reason": "采购入库审核后继续出库盘点",
                "idempotency_key": receipt_idem,
                "source_ref": receipt_source_ref,
                "warehouse": self.WAREHOUSE,
                "item_code": self.ITEM_CODE,
                "operation": "audit_stock_entry_draft",
                "quantity": "20",
                "business_date": self.BUSINESS_DATE,
                "status_action": "audit",
                "scenario_tag": self.SCENARIO_TAG,
            },
        )
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        self.assertEqual(audit_response.json()["data"]["status"], "pending_outbox")

        issue_idem = f"{self.SCENARIO_TAG}:idem-whse-issue-after-po-balanced"
        issue_source_ref = f"{self.SCENARIO_TAG}:issue-after-po-balanced"
        issue_payload = {
            "company": "COMP-A",
            "purpose": "Material Issue",
            "source_type": "material_sale_outbound",
            "source_id": issue_source_ref,
            "source_ref": issue_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "5",
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "source_warehouse": self.WAREHOUSE,
            "target_warehouse": None,
            "idempotency_key": issue_idem,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": "5",
                    "uom": "米",
                    "source_warehouse": self.WAREHOUSE,
                    "target_warehouse": None,
                }
            ],
        }
        issue = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=issue_idem,
                    source_ref=issue_source_ref,
                    quantity="5",
                )
            ),
            json=issue_payload,
        )
        self.assertEqual(issue.status_code, 201, issue.text)
        self.assertEqual(issue.json()["data"]["purpose"], "Material Issue")
        self.assertEqual(issue.json()["data"]["source_warehouse"], self.WAREHOUSE)

        stock_ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company=COMP-A&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(request_id="req-purchase-receipt-issue-ledger"),
        )
        stock_summary = self.client.get(
            f"/api/warehouse/stock-summary?company=COMP-A&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(request_id="req-purchase-receipt-issue-summary"),
        )
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        ledger_items = stock_ledger.json()["data"]["items"]
        self.assertEqual(stock_ledger.json()["data"]["total"], 2)
        self.assertEqual(
            [row["voucher_type"] for row in ledger_items],
            ["Stock Entry Draft/Material Receipt", "Stock Entry Draft/Material Issue"],
        )
        self.assertEqual(
            [Decimal(str(row["actual_qty"])) for row in ledger_items],
            [Decimal("20.000000"), Decimal("-5.000000")],
        )
        self.assertEqual(
            [Decimal(str(row["qty_after_transaction"])) for row in ledger_items],
            [Decimal("20.000000"), Decimal("15.000000")],
        )
        self.assertEqual(stock_summary.status_code, 200, stock_summary.text)
        summary_items = stock_summary.json()["data"]["items"]
        self.assertEqual(len(summary_items), 1)
        self.assertEqual(Decimal(str(summary_items[0]["actual_qty"])), Decimal("15.000000"))

        count_scenario_tag = "Z002-WAREHOUSE-COUNT-20260616-102"
        count_request_id = (
            f"{count_scenario_tag}-REQ-COUNT-"
            f"W{self._carrier_code(self.WAREHOUSE, length=8)}-"
            f"D{date.fromisoformat(self.BUSINESS_DATE).strftime('%Y%m%d')}"
        )
        inventory_count = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers(request_id=count_request_id),
            json={
                "company": "COMP-A",
                "warehouse": self.WAREHOUSE,
                "count_date": self.BUSINESS_DATE,
                "idempotency_key": f"{count_scenario_tag}:inventory-count-after-issue",
                "source_ref": f"{count_scenario_tag}:inventory-count-after-issue",
                "remark": "采购入库出库后账实平抽盘",
                "items": [
                    {
                        "item_code": self.ITEM_CODE,
                        "batch_no": None,
                        "serial_no": None,
                        "system_qty": "15",
                        "counted_qty": "15",
                        "variance_reason": "账实一致",
                    }
                ],
            },
        )
        self.assertEqual(inventory_count.status_code, 201, inventory_count.text)
        inventory_reconciliation = self.client.get(
            f"/api/warehouse/inventory-balance-reconciliation?company=COMP-A&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(request_id="req-purchase-receipt-issue-balanced-reconciliation"),
        )
        self.assertEqual(inventory_reconciliation.status_code, 200, inventory_reconciliation.text)
        reconciliation_rows = inventory_reconciliation.json()["data"]["items"]
        self.assertEqual(inventory_reconciliation.json()["data"]["total"], 1)
        self.assertEqual(Decimal(str(reconciliation_rows[0]["book_qty"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(reconciliation_rows[0]["actual_qty"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(reconciliation_rows[0]["diff_qty"])), Decimal("0.000000"))
        self.assertEqual(reconciliation_rows[0]["status"], "balanced")

    def test_purchase_receipt_audit_fastapi_permission_source_unavailable_does_not_mutate(self) -> None:
        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": "PO-A5-SCOPE-DOWN",
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-scope-down",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "50",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }
        create_po = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)
        self.assertEqual(create_po.status_code, 201, create_po.text)

        receipt_idem = f"{self.SCENARIO_TAG}:idem-whse-po-a5-scope-down"
        receipt_source_ref = f"{self.SCENARIO_TAG}:purchase:PO-A5-SCOPE-DOWN"
        receipt_payload = {
            "company": "COMP-A",
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": receipt_source_ref,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": self.WAREHOUSE,
            "idempotency_key": receipt_idem,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": "20",
                    "uom": "米",
                    "target_warehouse": self.WAREHOUSE,
                }
            ],
        }
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json=receipt_payload,
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)
        draft_id = int(receipt.json()["data"]["id"])

        audit_payload = {
            "reason": "FastAPI 权限源不可用时不得审核采购入库",
            "idempotency_key": receipt_idem,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "audit_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "audit",
            "scenario_tag": self.SCENARIO_TAG,
        }
        audit_request_id = self._warehouse_request_id(
            idempotency_key=receipt_idem,
            source_ref=receipt_source_ref,
            quantity="20",
            operation="audit_stock_entry_draft",
            status_action="audit",
        )
        env_keys = [
            "LINGYI_PERMISSION_SOURCE",
            "LINGYI_FASTAPI_ROLE_ACTIONS_JSON",
            "LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON",
        ]
        previous_env = {key: os.environ.get(key) for key in env_keys}
        try:
            os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
            os.environ["LINGYI_FASTAPI_ROLE_ACTIONS_JSON"] = json.dumps(
                {"roles": {"Warehouse Operator": ["warehouse:stock_entry_draft", "warehouse:read"]}},
            )
            os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = "[]"
            response = self.client.post(
                f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
                headers={
                    "X-LY-Dev-User": "warehouse.scope.user",
                    "X-LY-Dev-Roles": "Warehouse Operator",
                    "X-Request-ID": audit_request_id,
                },
                json=audit_payload,
            )

            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
            with self.SessionLocal() as session:
                draft = session.query(LyWarehouseStockEntryDraft).filter_by(id=draft_id).one()
                order = session.query(LyMaterialPurchaseOrder).one()
                line = session.query(LyMaterialPurchaseOrderItem).one()
                self.assertEqual(str(draft.status), "draft")
                self.assertEqual(str(order.status), "draft")
                self.assertEqual(Decimal(str(order.received_qty)), Decimal("0.000000"))
                self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))
                self.assertEqual(session.query(LyWarehouseStockLedgerEntry).count(), 0)
                security = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
                self.assertIsNotNone(security)
                self.assertEqual(security.event_type, "PERMISSION_SOURCE_UNAVAILABLE")
        finally:
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_purchase_order_receipt_cancel_reverses_received_qty_and_stock(self) -> None:
        purchase_no = "PO-A5-CANCEL-001"
        purchase_payload = {
            "operation": "create",
            "company": "COMP-A",
            "purchase_no": purchase_no,
            "supplier_name": "SUP-A",
            "transaction_date": "2026-06-16",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": "idem-po-a5-cancel-001",
            "items": [
                {
                    "material_item_code": self.ITEM_CODE,
                    "material_name": "棉布",
                    "qty": "50",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": self.WAREHOUSE,
                }
            ],
        }
        create_po = self.client.post("/api/material-purchase/orders", headers=self._headers(), json=purchase_payload)
        self.assertEqual(create_po.status_code, 201, create_po.text)

        receipt_idem = f"{self.SCENARIO_TAG}:idem-whse-po-a5-cancel-001"
        receipt_source_ref = f"{self.SCENARIO_TAG}:purchase:{purchase_no}"
        receipt_payload = {
            "company": "COMP-A",
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": receipt_source_ref,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": self.SCENARIO_TAG,
            "target_warehouse": self.WAREHOUSE,
            "idempotency_key": receipt_idem,
            "items": [
                {
                    "item_code": self.ITEM_CODE,
                    "qty": "20",
                    "uom": "米",
                    "target_warehouse": self.WAREHOUSE,
                }
            ],
        }
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json=receipt_payload,
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)
        draft_id = int(receipt.json()["data"]["id"])

        audit_payload = {
            "reason": "采购入库审核后准备反审核",
            "idempotency_key": receipt_idem,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "audit_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "audit",
            "scenario_tag": self.SCENARIO_TAG,
        }
        audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/audit",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                    operation="audit_stock_entry_draft",
                    status_action="audit",
                )
            ),
            json=audit_payload,
        )
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        self.assertEqual(audit_response.json()["data"]["status"], "pending_outbox")

        before_cancel_receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company=COMP-A&purchase_no={purchase_no}",
            headers=self._headers(),
        )
        self.assertEqual(before_cancel_receipts.status_code, 200, before_cancel_receipts.text)
        self.assertEqual(before_cancel_receipts.json()["data"]["total"], 1)

        cancel_payload = {
            "reason": "采购入库反审核回退",
            "idempotency_key": receipt_idem,
            "source_ref": receipt_source_ref,
            "warehouse": self.WAREHOUSE,
            "item_code": self.ITEM_CODE,
            "operation": "cancel_stock_entry_draft",
            "quantity": "20",
            "business_date": self.BUSINESS_DATE,
            "status_action": "cancel",
            "scenario_tag": self.SCENARIO_TAG,
        }
        cancel_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{draft_id}/cancel",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                    operation="cancel_stock_entry_draft",
                    status_action="cancel",
                )
            ),
            json=cancel_payload,
        )
        purchase_receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company=COMP-A&purchase_no={purchase_no}",
            headers=self._headers(),
        )
        stock_ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company=COMP-A&item_code={self.ITEM_CODE}&warehouse={self.WAREHOUSE}",
            headers=self._headers(),
        )
        stock_summary = self.client.get(
            f"/api/warehouse/stock-summary?company=COMP-A&item_code={self.ITEM_CODE}&warehouse={self.WAREHOUSE}",
            headers=self._headers(),
        )

        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)
        self.assertEqual(cancel_response.json()["data"]["status"], "cancelled")
        self.assertEqual(cancel_response.json()["data"]["outbox"]["status"], "cancelled")
        self.assertEqual(purchase_receipts.status_code, 200, purchase_receipts.text)
        self.assertEqual(purchase_receipts.json()["data"]["total"], 0)
        self.assertEqual(purchase_receipts.json()["data"]["items"], [])
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        self.assertEqual(stock_ledger.json()["data"]["items"], [])
        self.assertEqual(stock_ledger.json()["data"]["total"], 0)
        self.assertEqual(stock_summary.status_code, 200, stock_summary.text)
        self.assertEqual(stock_summary.json()["data"]["items"], [])

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).one()
            line = session.query(LyMaterialPurchaseOrderItem).one()
            draft = session.query(LyWarehouseStockEntryDraft).one()
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).one()
            self.assertEqual(str(order.status), "draft")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(draft.status), "cancelled")
            self.assertEqual(str(outbox.status), "cancelled")

    def test_factory_return_material_report_does_not_estimate_without_subcontract_issue_fact(self) -> None:
        receipt_idem = f"{self.SCENARIO_TAG}:receipt:FRR-LOCAL-IDEM"
        receipt_source_ref = f"{self.SCENARIO_TAG}:receipt:FRR-LOCAL-SRC"
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": "默认公司",
                "purpose": "Material Receipt",
                "source_type": "factory_return_report_proof",
                "source_id": receipt_source_ref,
                "source_ref": receipt_source_ref,
                "warehouse": self.WAREHOUSE,
                "item_code": self.ITEM_CODE,
                "quantity": "20",
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.SCENARIO_TAG,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": receipt_idem,
                "items": [
                    {
                        "item_code": self.ITEM_CODE,
                        "qty": "20",
                        "uom": "米",
                        "target_warehouse": self.WAREHOUSE,
                    }
                ],
            },
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)

        with patch("app.routers.warehouse.ERPNextWarehouseAdapter", side_effect=AssertionError("ERPNext adapter must not be used")):
            response = self.client.get(
                "/api/warehouse/factory-return-material-report?item_code=FAB-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["items"], [])

    def test_factory_return_material_report_prefers_subcontract_issue_facts(self) -> None:
        self._seed_factory_return_issue_fact()

        with patch("app.routers.warehouse.ERPNextWarehouseAdapter", side_effect=AssertionError("ERPNext adapter must not be used")):
            response = self.client.get(
                "/api/warehouse/factory-return-material-report?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        rows = payload["data"]["items"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["subcontract_no"], "SC-FRR-B5-001")
        self.assertEqual(row["source_doc_no"], "SC-FRR-B5-001")
        self.assertEqual(row["factory_name"], "B5加工厂")
        self.assertEqual(row["material_code"], "FAB-B5-FRR")
        self.assertEqual(row["warehouse"], self.WAREHOUSE)
        self.assertEqual(Decimal(str(row["issued_qty"])), Decimal("100.0"))
        self.assertEqual(Decimal(str(row["theoretical_usage_qty"])), Decimal("60.0"))
        self.assertEqual(Decimal(str(row["planned_return_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(row["returned_qty"])), Decimal("0.0"))
        self.assertEqual(Decimal(str(row["pending_qty"])), Decimal("40.0"))
        self.assertEqual(row["uom"], "米")
        self.assertEqual(row["status"], "pending")

    def test_factory_return_material_draft_closes_report_and_updates_stock_ledger(self) -> None:
        self._seed_factory_return_issue_fact()

        report = self.client.get(
            "/api/warehouse/factory-return-material-report?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR",
            headers=self._headers(),
        )
        self.assertEqual(report.status_code, 200, report.text)
        report_row = report.json()["data"]["items"][0]
        report_no = report_row["report_no"]
        idempotency_key = f"{self.SCENARIO_TAG}:factory-return:idem-001"
        source_ref = f"{self.SCENARIO_TAG}:factory-return:{report_no}:{self._carrier_code(idempotency_key)}"
        request_id = self._warehouse_request_id(
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            quantity=Decimal(str(report_row["pending_qty"])),
            warehouse="WH-A",
            item_code="FAB-B5-FRR",
            business_date=self.BUSINESS_DATE,
        )

        payload = {
            "operation": "create_factory_return_material_draft",
            "company": "COMP-A",
            "scenario_tag": self.SCENARIO_TAG,
            "source_ref": source_ref,
            "quantity": str(report_row["pending_qty"]),
            "uom": report_row["uom"],
            "business_date": self.BUSINESS_DATE,
            "idempotency_key": idempotency_key,
        }
        created = self.client.post(
            f"/api/warehouse/factory-return-material-report/{report_no}/return-draft",
            headers=self._headers(request_id=request_id),
            json=payload,
        )
        replay = self.client.post(
            f"/api/warehouse/factory-return-material-report/{report_no}/return-draft",
            headers=self._headers(request_id=request_id),
            json=payload,
        )
        conflict_quantity = Decimal("1")
        conflict = self.client.post(
            f"/api/warehouse/factory-return-material-report/{report_no}/return-draft",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_ref,
                    quantity=conflict_quantity,
                    warehouse="WH-A",
                    item_code="FAB-B5-FRR",
                    business_date=self.BUSINESS_DATE,
                )
            ),
            json={**payload, "quantity": str(conflict_quantity)},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "WAREHOUSE_IDEMPOTENCY_CONFLICT")
        data = created.json()["data"]
        self.assertEqual(data["draft"]["id"], replay.json()["data"]["draft"]["id"])
        self.assertEqual(data["draft"]["source_type"], "factory_return_material")
        self.assertEqual(data["draft"]["purpose"], "Material Receipt")
        self.assertEqual(data["draft"]["target_warehouse"], self.WAREHOUSE)
        self.assertEqual(data["draft"]["items"][0]["item_code"], "FAB-B5-FRR")
        self.assertEqual(Decimal(str(data["draft"]["items"][0]["qty"])), Decimal("40.000000"))
        self.assertEqual(data["draft"]["items"][0]["uom"], "米")
        self.assertEqual(data["report_item"]["status"], "confirmed")
        self.assertEqual(Decimal(str(data["report_item"]["returned_qty"])), Decimal("0.0"))
        self.assertEqual(Decimal(str(data["report_item"]["posted_returned_qty"])), Decimal("0.0"))
        self.assertEqual(Decimal(str(data["report_item"]["pending_outbox_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(data["report_item"]["pending_qty"])), Decimal("0.0"))

        pending_sync_closed_report = self.client.get(
            "/api/warehouse/factory-return-material-report?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR&status=closed",
            headers=self._headers(request_id="req-factory-return-draft-closed"),
        )
        stock_ledger = self.client.get(
            "/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR",
            headers=self._headers(request_id="req-factory-return-draft-ledger"),
        )
        self.assertEqual(pending_sync_closed_report.status_code, 200, pending_sync_closed_report.text)
        self.assertEqual(pending_sync_closed_report.json()["data"]["items"], [])
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        ledger_items = stock_ledger.json()["data"]["items"]
        self.assertTrue(any(Decimal(str(row["actual_qty"])) == Decimal("40.0") for row in ledger_items))
        self.assertEqual(Decimal(str(ledger_items[-1]["qty_after_transaction"])), Decimal("-60.0"))

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_type="factory_return_material").one()
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=int(draft.id)).one()
            outbox.status = "succeeded"
            outbox.external_ref = "LOCAL-RETURN-FRR-001"
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertEqual(str(draft.source_id), source_ref)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)
            session.commit()

        closed_report = self.client.get(
            "/api/warehouse/factory-return-material-report?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR&status=closed",
            headers=self._headers(request_id="req-factory-return-draft-closed-after-success"),
        )
        self.assertEqual(closed_report.status_code, 200, closed_report.text)
        closed_row = closed_report.json()["data"]["items"][0]
        self.assertEqual(closed_row["report_no"], report_no)
        self.assertEqual(Decimal(str(closed_row["returned_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(closed_row["posted_returned_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(closed_row["pending_outbox_qty"])), Decimal("0.0"))
        self.assertEqual(Decimal(str(closed_row["pending_qty"])), Decimal("0.0"))

        worker = self.client.post(
            "/api/warehouse/internal/stock-entry-sync/run-once?dry_run=true",
            headers=self._headers(request_id="req-factory-return-draft-worker"),
        )
        self.assertEqual(worker.status_code, 200, worker.text)
        self.assertEqual(worker.json()["data"]["processed_count"], 0)

    def _seed_factory_return_issue_fact(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=901,
                    subcontract_no="SC-FRR-B5-001",
                    supplier="B5加工厂",
                    item_code="STYLE-FRR",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    issued_qty=Decimal("100"),
                    received_qty=Decimal("60"),
                    inspected_qty=Decimal("60"),
                    accepted_qty=Decimal("60"),
                    status="inspected",
                    settlement_status="unsettled",
                )
            )
            session.add(
                LySubcontractStockOutbox(
                    id=901,
                    subcontract_id=901,
                    event_key="b5-frr-outbox-001",
                    stock_action="issue",
                    idempotency_key="b5-frr-issue-001",
                    payload_hash="b5-frr-hash",
                    company="COMP-A",
                    supplier="B5加工厂",
                    item_code="STYLE-FRR",
                    warehouse=self.WAREHOUSE,
                    action="issue",
                    status="succeeded",
                    stock_entry_name="LOCAL-ISSUE-B5-FRR-001",
                    request_id="req-b5-frr-001",
                    created_by="seed",
                )
            )
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company="COMP-A",
                    code="FAB-B5-FRR",
                    name="应退料物料",
                    status="active",
                    payload={"material_kind": "fabric", "material_item_code": "FAB-B5-FRR", "uom": "米"},
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LySubcontractStockOutbox(
                    id=902,
                    subcontract_id=901,
                    event_key="b5-frr-outbox-pending",
                    stock_action="issue",
                    idempotency_key="b5-frr-issue-pending",
                    payload_hash="b5-frr-pending-hash",
                    company="COMP-A",
                    supplier="B5加工厂",
                    item_code="STYLE-FRR",
                    warehouse=self.WAREHOUSE,
                    action="issue",
                    status="pending",
                    request_id="req-b5-frr-pending",
                    created_by="seed",
                )
            )
            session.add(
                LySubcontractMaterial(
                    id=901,
                    subcontract_id=901,
                    stock_outbox_id=901,
                    company="COMP-A",
                    issue_batch_no="SIB-B5-FRR-001",
                    material_item_code="FAB-B5-FRR",
                    required_qty=Decimal("100"),
                    issued_qty=Decimal("100"),
                    sync_status="succeeded",
                    stock_entry_name="LOCAL-ISSUE-B5-FRR-001",
                )
            )
            session.add(
                LySubcontractMaterial(
                    id=902,
                    subcontract_id=901,
                    stock_outbox_id=902,
                    company="COMP-A",
                    issue_batch_no="SIB-B5-FRR-PENDING",
                    material_item_code="FAB-B5-FRR",
                    required_qty=Decimal("999"),
                    issued_qty=Decimal("999"),
                    sync_status="pending",
                    stock_entry_name=None,
                )
            )
            session.commit()

    def test_material_retention_report_uses_fastapi_native_stock_movements(self) -> None:
        receipt_idem = f"{self.SCENARIO_TAG}:receipt:RETENTION-LOCAL-IDEM"
        receipt_source_ref = f"{self.SCENARIO_TAG}:receipt:RETENTION-LOCAL-SRC"
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                request_id=self._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": "默认公司",
                "purpose": "Material Receipt",
                "source_type": "material_retention_report_proof",
                "source_id": receipt_source_ref,
                "source_ref": receipt_source_ref,
                "warehouse": self.WAREHOUSE,
                "item_code": self.ITEM_CODE,
                "quantity": "20",
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.SCENARIO_TAG,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": receipt_idem,
                "items": [
                    {
                        "item_code": self.ITEM_CODE,
                        "qty": "20",
                        "uom": "米",
                        "target_warehouse": self.WAREHOUSE,
                    }
                ],
            },
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)

        with patch("app.routers.warehouse.ERPNextWarehouseAdapter", side_effect=AssertionError("ERPNext adapter must not be used")):
            response = self.client.get(
                "/api/warehouse/material-retention-report?keyword=FAB-A&min_retention_days=90&to_date=2026-10-01",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        rows = payload["data"]["items"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["material_code"], self.ITEM_CODE)
        self.assertEqual(rows[0]["warehouse"], self.WAREHOUSE)
        self.assertEqual(rows[0]["last_in_date"], self.BUSINESS_DATE)
        self.assertEqual(Decimal(str(rows[0]["stock_qty"])), Decimal("20.0"))
        self.assertEqual(Decimal(str(rows[0]["stock_amount"])), Decimal("172.0"))
        self.assertGreaterEqual(rows[0]["retention_days"], 90)
        self.assertEqual(rows[0]["risk_level"], "medium")


if __name__ == "__main__":
    unittest.main()
