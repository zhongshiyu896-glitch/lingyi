"""A5 material purchase order to warehouse receipt draft flow."""

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
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
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
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            self._seed_purchase_master_data(session=session, company="COMP-A", supplier_name="SUP-A", material_code=self.ITEM_CODE)
            session.commit()

    @staticmethod
    def _seed_purchase_master_data(*, session, company: str, supplier_name: str, material_code: str, material_status: str = "active") -> None:
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
    ) -> str:
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                "C",
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(warehouse or cls.WAREHOUSE),
                cls._carrier_code(item_code or cls.ITEM_CODE),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(business_date or cls.BUSINESS_DATE),
                cls._carrier_code("C"),
            ]
        )

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

    def test_purchase_order_receipt_draft_updates_received_qty_and_audits(self) -> None:
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

        self.assertEqual(receipt.status_code, 201, receipt.text)
        self.assertEqual(receipt.json()["data"]["status"], "pending_outbox")
        self.assertEqual(list_drafts.status_code, 200, list_drafts.text)
        self.assertEqual(list_drafts.json()["data"]["total"], 1)
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        ledger_items = stock_ledger.json()["data"]["items"]
        self.assertEqual(stock_ledger.json()["data"]["total"], 1)
        self.assertEqual(ledger_items[0]["item_code"], self.ITEM_CODE)
        self.assertEqual(ledger_items[0]["warehouse"], self.WAREHOUSE)
        self.assertEqual(Decimal(str(ledger_items[0]["actual_qty"])), Decimal("20.0"))
        self.assertEqual(Decimal(str(ledger_items[0]["qty_after_transaction"])), Decimal("20.0"))
        self.assertEqual(ledger_items[0]["posting_date"], self.BUSINESS_DATE)
        self.assertEqual(stock_summary.status_code, 200, stock_summary.text)
        summary_items = stock_summary.json()["data"]["items"]
        self.assertEqual(len(summary_items), 1)
        self.assertEqual(Decimal(str(summary_items[0]["actual_qty"])), Decimal("20.0"))
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
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("20.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("20.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("material_purchase:write", audit_actions)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)

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
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        data = created.json()["data"]
        self.assertEqual(data["draft"]["id"], replay.json()["data"]["draft"]["id"])
        self.assertEqual(data["draft"]["source_type"], "factory_return_material")
        self.assertEqual(data["draft"]["purpose"], "Material Receipt")
        self.assertEqual(data["draft"]["target_warehouse"], self.WAREHOUSE)
        self.assertEqual(data["draft"]["items"][0]["item_code"], "FAB-B5-FRR")
        self.assertEqual(Decimal(str(data["draft"]["items"][0]["qty"])), Decimal("40.000000"))
        self.assertEqual(data["draft"]["items"][0]["uom"], "米")
        self.assertEqual(data["report_item"]["status"], "closed")
        self.assertEqual(Decimal(str(data["report_item"]["returned_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(data["report_item"]["pending_qty"])), Decimal("0.0"))

        closed_report = self.client.get(
            "/api/warehouse/factory-return-material-report?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR&status=closed",
            headers=self._headers(request_id="req-factory-return-draft-closed"),
        )
        stock_ledger = self.client.get(
            "/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&item_code=FAB-B5-FRR",
            headers=self._headers(request_id="req-factory-return-draft-ledger"),
        )
        self.assertEqual(closed_report.status_code, 200, closed_report.text)
        closed_row = closed_report.json()["data"]["items"][0]
        self.assertEqual(closed_row["report_no"], report_no)
        self.assertEqual(Decimal(str(closed_row["returned_qty"])), Decimal("40.0"))
        self.assertEqual(Decimal(str(closed_row["pending_qty"])), Decimal("0.0"))
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        ledger_items = stock_ledger.json()["data"]["items"]
        self.assertTrue(any(Decimal(str(row["actual_qty"])) == Decimal("40.0") for row in ledger_items))
        self.assertEqual(Decimal(str(ledger_items[-1]["qty_after_transaction"])), Decimal("-60.0"))

        with self.SessionLocal() as session:
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_type="factory_return_material").one()
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertEqual(str(draft.source_id), source_ref)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)

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
