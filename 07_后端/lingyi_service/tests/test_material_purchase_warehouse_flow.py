"""A5 material purchase order to warehouse receipt draft flow."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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
from app.models.audit import LySecurityAuditLog
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.quality import Base as QualityBase
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
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)

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
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

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
    ) -> str:
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                "C",
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(cls.WAREHOUSE),
                cls._carrier_code(cls.ITEM_CODE),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(cls.BUSINESS_DATE),
                cls._carrier_code("C"),
            ]
        )

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
        return_report = self.client.get(
            "/api/warehouse/factory-return-material-report?item_code=FAB-A",
            headers=self._headers(),
        )

        self.assertEqual(receipt.status_code, 201, receipt.text)
        self.assertEqual(receipt.json()["data"]["status"], "pending_outbox")
        self.assertEqual(list_drafts.status_code, 200, list_drafts.text)
        self.assertEqual(list_drafts.json()["data"]["total"], 1)
        self.assertEqual(return_report.status_code, 200, return_report.text)
        report_items = return_report.json()["data"]["items"]
        self.assertEqual(len(report_items), 1)
        self.assertEqual(report_items[0]["material_code"], self.ITEM_CODE)
        self.assertEqual(report_items[0]["warehouse"], self.WAREHOUSE)
        self.assertGreater(Decimal(str(report_items[0]["pending_qty"])), Decimal("0"))

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).one()
            line = session.query(LyMaterialPurchaseOrderItem).one()
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("20.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("20.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("material_purchase:write", audit_actions)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)


if __name__ == "__main__":
    unittest.main()
