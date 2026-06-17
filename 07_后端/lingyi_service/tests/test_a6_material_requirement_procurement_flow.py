"""A6 material calculation to procurement requirement pool flow."""

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlanMaterial
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.material_purchase import get_db_session as material_purchase_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class A6MaterialRequirementProcurementFlowTest(unittest.TestCase):
    """Validate material check creates purchase demand and receipt closes it."""

    COMPANY = "COMP-A6"
    STYLE = "A6-TEE"
    WAREHOUSE = "WH-A6"
    MATERIAL = "FAB-A6"
    BUSINESS_DATE = date(2026, 6, 17).isoformat()
    WAREHOUSE_SCENARIO = "Z003-WAREHOUSE-20260617-301"
    MATERIAL_CHECK_SCENARIO = "Z003-PROD-PLAN-DETAIL-20260617-301"

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
        StyleMasterBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        app.dependency_overrides[material_purchase_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.add(
                LyStyleMaster(
                    company=self.COMPANY,
                    ys_style_no=self.STYLE,
                    ys_style_name_cn="A6 Tee",
                    ys_season="SS",
                    ys_year="2026",
                    ys_brand="LY",
                    ys_style_status="enabled",
                    colors=[{"ys_color_code": "WHT", "ys_color_name": "白"}],
                    sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBom(
                    id=601,
                    bom_no="BOM-A6-TEE-V1",
                    item_code=self.STYLE,
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBomItem(
                    id=6011,
                    bom_id=601,
                    material_item_code=self.MATERIAL,
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0.05"),
                    uom="米",
                    remark="供应商:SUP-A6 单价:12.5",
                )
            )
            session.commit()

    @staticmethod
    def _headers(request_id: str = "req-a6-flow") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "a6.procurement.user",
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
    def _warehouse_request_id(cls, *, idempotency_key: str, source_ref: str, item_code: str, quantity: object) -> str:
        return "-".join(
            [
                cls.WAREHOUSE_SCENARIO,
                "RW",
                "C",
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(cls.WAREHOUSE),
                cls._carrier_code(item_code),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(cls.BUSINESS_DATE),
                cls._carrier_code("C"),
            ]
        )

    def _create_stock_receipt(self, *, source_type: str, source_id: str, idempotency_key: str, qty: str) -> None:
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    item_code=self.MATERIAL,
                    quantity=qty,
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": self.COMPANY,
                "purpose": "Material Receipt",
                "source_type": source_type,
                "source_id": source_id,
                "source_ref": source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": self.MATERIAL,
                "quantity": qty,
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": idempotency_key,
                "items": [
                    {
                        "item_code": self.MATERIAL,
                        "qty": qty,
                        "uom": "米",
                        "target_warehouse": self.WAREHOUSE,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_material_check_creates_requirement_and_receipt_closes_shortage(self) -> None:
        self._create_stock_receipt(
            source_type="manual",
            source_id=f"{self.WAREHOUSE_SCENARIO}:opening:{self.MATERIAL}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:opening-idem",
            qty="30",
        )

        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": "SO-A6-001",
                "source_order_ref": "SO-A6-001",
                "idempotency_key": "idem-so-a6-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "item_code": self.STYLE,
                        "item_name": "Ignored",
                        "color": "白",
                        "size": "M",
                        "qty": 100,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A6-001", headers=self._headers())
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers(),
            json={
                "sales_order": "SO-A6-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 40,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-001",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])
        request_id = f"req-{self.MATERIAL_CHECK_SCENARIO}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{self.MATERIAL_CHECK_SCENARIO}:idem-material-check",
                "scenario_tag": self.MATERIAL_CHECK_SCENARIO,
                "plan_id": plan_id,
                "sales_order": "SO-A6-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        material_row = material_check.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(material_row["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(material_row["available_qty"])), Decimal("30.000000"))
        self.assertEqual(Decimal(str(material_row["shortage_qty"])), Decimal("54.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending",
            headers=self._headers(),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        requirement = requirement_rows[0]
        self.assertEqual(requirement["sales_order"], "SO-A6-001")
        self.assertEqual(requirement["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(requirement["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(requirement["available_qty"])), Decimal("30.000000"))
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("54.000000"))
        self.assertFalse(requirement["has_completed"])

        create_po_payload = {
            "operation": "create_order_from_requirements",
            "company": self.COMPANY,
            "requirement_ids": [requirement["id"]],
            "transaction_date": "2026-06-17",
            "expected_delivery_date": "2026-06-25",
            "idempotency_key": "idem-a6-req-to-po-001",
            "group_by_material": True,
        }
        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers(),
            json=create_po_payload,
        )
        replay_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers(),
            json=create_po_payload,
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        self.assertEqual(replay_po.status_code, 201, replay_po.text)
        purchase_order = create_po.json()["data"]["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(purchase_order["supplier_name"], "SUP-A6")
        self.assertEqual(Decimal(str(purchase_order["items"][0]["qty"])), Decimal("54.000000"))
        self.assertEqual(Decimal(str(purchase_order["items"][0]["unit_price"])), Decimal("12.500000"))
        self.assertEqual(create_po.json()["data"]["requirements"][0]["status"], "purchased")

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}",
            qty="54",
        )
        list_after_receipt = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed",
            headers=self._headers(),
        )
        self.assertEqual(list_after_receipt.status_code, 200, list_after_receipt.text)
        completed = list_after_receipt.json()["data"]["items"][0]
        self.assertTrue(completed["has_completed"])
        self.assertEqual(Decimal(str(completed["received_qty"])), Decimal("54.000000"))

        with self.SessionLocal() as session:
            requirement_row = session.query(LyMaterialPurchaseRequirement).one()
            snapshot = session.query(LyProductionPlanMaterial).one()
            order_row = session.query(LyMaterialPurchaseOrder).one()
            order_line = session.query(LyMaterialPurchaseOrderItem).one()
            self.assertEqual(str(requirement_row.status), "completed")
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("84.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("0.000000"))
            self.assertEqual(str(order_row.status), "received")
            self.assertEqual(Decimal(str(order_line.received_qty)), Decimal("54.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("production:material_check", audit_actions)
            self.assertIn("material_purchase:write", audit_actions)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)
