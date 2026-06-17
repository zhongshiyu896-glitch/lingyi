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
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
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
from app.services.material_purchase_service import MaterialPurchaseService


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
            session.query(LySecurityAuditLog).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
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

    def _seed_requirement(
        self,
        *,
        requirement_no: str = "REQ-A6-SEED-001",
        status: str = "pending",
        net_required_qty: str = "10",
        sales_order: str = "SO-A6-SEED",
        sales_order_item: str = "SO-A6-SEED-ITEM",
    ) -> int:
        with self.SessionLocal() as session:
            row = LyMaterialPurchaseRequirement(
                company=self.COMPANY,
                requirement_no=requirement_no,
                source_type="production_plan_material",
                source_id=requirement_no,
                source_no=sales_order,
                plan_id=1,
                bom_item_id=6011,
                sales_order=sales_order,
                sales_order_item=sales_order_item,
                item_code=self.STYLE,
                material_item_code=self.MATERIAL,
                material_name="A6 棉布",
                supplier_name="SUP-A6",
                warehouse=self.WAREHOUSE,
                required_qty=Decimal(net_required_qty),
                available_qty=Decimal("0"),
                net_required_qty=Decimal(net_required_qty),
                purchased_qty=Decimal("0"),
                received_qty=Decimal("0"),
                uom="米",
                unit_price=Decimal("12.5"),
                status=status,
                created_by="seed",
                updated_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def _seed_purchase_order(self, *, purchase_no: str) -> int:
        with self.SessionLocal() as session:
            row = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no=purchase_no,
                supplier_name="SUP-A6",
                status="draft",
                total_qty=Decimal("0"),
                received_qty=Decimal("0"),
                total_amount=Decimal("0"),
                currency="CNY",
                created_by="seed",
                updated_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def _from_requirements_payload(
        self,
        *,
        requirement_ids: list[int],
        idempotency_key: str,
        purchase_no: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "create_order_from_requirements",
            "company": self.COMPANY,
            "requirement_ids": requirement_ids,
            "transaction_date": "2026-06-17",
            "expected_delivery_date": "2026-06-25",
            "idempotency_key": idempotency_key,
            "group_by_material": True,
        }
        if purchase_no:
            payload["purchase_no"] = purchase_no
        return payload

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
        list_after_receipt_by_purchase_no = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}",
            headers=self._headers(),
        )
        self.assertEqual(list_after_receipt.status_code, 200, list_after_receipt.text)
        completed = list_after_receipt.json()["data"]["items"][0]
        self.assertTrue(completed["has_completed"])
        self.assertEqual(Decimal(str(completed["received_qty"])), Decimal("54.000000"))
        self.assertEqual(list_after_receipt_by_purchase_no.status_code, 200, list_after_receipt_by_purchase_no.text)
        self.assertEqual(list_after_receipt_by_purchase_no.json()["data"]["total"], 1)
        self.assertEqual(list_after_receipt_by_purchase_no.json()["data"]["items"][0]["purchase_no"], purchase_no)

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

        material_issue_scenario = "Z003-PROD-PLAN-DETAIL-20260617-302"
        material_issue_request_id = f"req-{material_issue_scenario}"
        material_issue = self.client.post(
            f"/api/production/plans/{plan_id}/material-issue",
            headers={**self._headers(), "X-Request-ID": material_issue_request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "business_date": "2026-06-18",
                "operation": "material_issue",
                "idempotency_key": f"{material_issue_scenario}:idem-material-issue",
                "scenario_tag": material_issue_scenario,
                "plan_id": plan_id,
                "sales_order": "SO-A6-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": material_issue_request_id,
            },
        )
        self.assertEqual(material_issue.status_code, 200, material_issue.text)
        material_issue_data = material_issue.json()["data"]
        self.assertEqual(material_issue_data["stock_entry_status"], "pending_outbox")
        self.assertEqual(material_issue_data["items"][0]["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(material_issue_data["items"][0]["qty"])), Decimal("84.000000"))

    def test_rerun_material_check_preserves_completed_requirement_purchase_fields(self) -> None:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                id=9601,
                plan_no="PP-A6-PRESERVE-001",
                company=self.COMPANY,
                sales_order="SO-A6-PRESERVE",
                sales_order_item="SO-A6-PRESERVE-ITEM",
                customer="CUST-A6",
                item_code=self.STYLE,
                bom_id=601,
                bom_version="V1",
                planned_qty=Decimal("40"),
                status="material_checked",
                idempotency_key="idem-a6-preserve-plan",
                request_hash="hash-a6-preserve-plan",
                created_by="seed",
            )
            session.add(plan)
            session.add(
                LyProductionPlanMaterial(
                    plan_id=9601,
                    bom_item_id=6011,
                    material_item_code=self.MATERIAL,
                    warehouse=self.WAREHOUSE,
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0.05"),
                    required_qty=Decimal("84"),
                    available_qty=Decimal("84"),
                    shortage_qty=Decimal("0"),
                )
            )
            order = LyMaterialPurchaseOrder(
                id=9701,
                company=self.COMPANY,
                purchase_no="PO-A6-PRESERVE",
                supplier_name="SUP-A6",
                status="received",
                total_qty=Decimal("54"),
                received_qty=Decimal("54"),
                total_amount=Decimal("675"),
                currency="CNY",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            order_line = LyMaterialPurchaseOrderItem(
                id=97011,
                order_id=9701,
                company=self.COMPANY,
                item_code=self.STYLE,
                material_item_code=self.MATERIAL,
                material_name="A6 棉布",
                qty=Decimal("54"),
                received_qty=Decimal("54"),
                uom="米",
                unit_price=Decimal("12.5"),
                amount=Decimal("675"),
                warehouse=self.WAREHOUSE,
            )
            session.add(order_line)
            requirement = LyMaterialPurchaseRequirement(
                company=self.COMPANY,
                requirement_no="REQ-A6-PRESERVE",
                source_type="production_plan",
                source_id="9601",
                source_no="PP-A6-PRESERVE-001",
                plan_id=9601,
                bom_item_id=6011,
                sales_order="SO-A6-PRESERVE",
                sales_order_item="SO-A6-PRESERVE-ITEM",
                item_code=self.STYLE,
                material_item_code=self.MATERIAL,
                material_name="A6 棉布",
                supplier_name="SUP-A6",
                warehouse=self.WAREHOUSE,
                required_qty=Decimal("84"),
                available_qty=Decimal("84"),
                net_required_qty=Decimal("0"),
                purchased_qty=Decimal("54"),
                received_qty=Decimal("54"),
                uom="米",
                unit_price=Decimal("12.5"),
                status="completed",
                purchase_order_id=9701,
                purchase_order_item_id=97011,
                purchase_no="PO-A6-PRESERVE",
                created_by="seed",
                updated_by="seed",
            )
            session.add(requirement)
            session.commit()

            MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            preserved = session.query(LyMaterialPurchaseRequirement).filter_by(requirement_no="REQ-A6-PRESERVE").one()
            self.assertEqual(str(preserved.status), "completed")
            self.assertEqual(str(preserved.purchase_no), "PO-A6-PRESERVE")
            self.assertEqual(int(preserved.purchase_order_id), 9701)
            self.assertEqual(int(preserved.purchase_order_item_id), 97011)
            self.assertEqual(Decimal(str(preserved.purchased_qty)), Decimal("54.000000"))
            self.assertEqual(Decimal(str(preserved.received_qty)), Decimal("54.000000"))

    def test_from_requirements_group_by_material_merges_cross_order_demands_and_receipts(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-A",
            net_required_qty="5",
            sales_order="SO-A6-GROUP-001",
            sales_order_item="SO-A6-GROUP-001-ITEM",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-B",
            net_required_qty="10",
            sales_order="SO-A6-GROUP-002",
            sales_order_item="SO-A6-GROUP-002-ITEM",
        )

        payload = self._from_requirements_payload(
            requirement_ids=[requirement_a, requirement_b],
            idempotency_key="idem-a6-group-material",
        )
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-group-material"),
            json=payload,
        )
        replay = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-group-material-replay"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(replay.status_code, 201, replay.text)

        data = response.json()["data"]
        purchase_order = data["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(len(purchase_order["items"]), 1)
        self.assertEqual(purchase_order["items"][0]["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(purchase_order["items"][0]["qty"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(purchase_order["total_qty"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(purchase_order["total_amount"])), Decimal("187.500000"))
        self.assertEqual({row["sales_order"] for row in data["requirements"]}, {"SO-A6-GROUP-001", "SO-A6-GROUP-002"})
        self.assertTrue(all(row["status"] == "purchased" for row in data["requirements"]))
        self.assertTrue(all(row["purchase_no"] == purchase_no for row in data["requirements"]))
        self.assertTrue(all(row["has_completed"] is False for row in data["requirements"]))

        with self.SessionLocal() as session:
            order_line = session.query(LyMaterialPurchaseOrderItem).one()
            requirement_rows = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.requirement_no.asc()).all()
            self.assertEqual(len(requirement_rows), 2)
            self.assertEqual({int(row.purchase_order_item_id) for row in requirement_rows}, {int(order_line.id)})
            self.assertEqual({str(row.sales_order) for row in requirement_rows}, {"SO-A6-GROUP-001", "SO-A6-GROUP-002"})

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}:group",
            qty="15",
        )
        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}",
            headers=self._headers("req-a6-group-material-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 2)
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        self.assertEqual(sum(Decimal(str(row["received_qty"])) for row in completed_rows), Decimal("15.000000"))

    def test_from_requirements_unauthenticated_security_audit_is_write_requirement(self) -> None:
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            json=self._from_requirements_payload(requirement_ids=[999], idempotency_key="idem-a6-unauth"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).one()
            self.assertEqual(row.module, "material_purchase")
            self.assertEqual(row.action, "material_purchase:write")
            self.assertEqual(row.resource_type, "MaterialPurchaseRequirement")
            self.assertEqual(row.request_path, "/api/material-purchase/orders/from-requirements")

    def test_from_requirements_requires_material_purchase_write(self) -> None:
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers={**self._headers("req-a6-forbidden"), "X-LY-Dev-Roles": "NoRole"},
            json=self._from_requirements_payload(requirement_ids=[999], idempotency_key="idem-a6-forbidden"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).one()
            self.assertEqual(row.module, "material_purchase")
            self.assertEqual(row.action, "material_purchase:write")
            self.assertEqual(row.resource_type, "MATERIAL_PURCHASE_REQUIREMENT")
            self.assertEqual(row.request_path, "/api/material-purchase/orders/from-requirements")
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)

    def test_from_requirements_rejects_idempotency_payload_mismatch(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-IDEM")
        payload = self._from_requirements_payload(
            requirement_ids=[requirement_id],
            idempotency_key="idem-a6-req-idem",
            purchase_no="PO-A6-IDEM",
        )
        first = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-idem-1"),
            json=payload,
        )
        self.assertEqual(first.status_code, 201, first.text)

        mismatch = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-idem-2"),
            json={**payload, "purchase_no": "PO-A6-IDEM-OTHER"},
        )
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.json()["code"], "MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 1)
            self.assertEqual(session.query(LyMaterialPurchaseIdempotency).count(), 1)
            failed_audit = (
                session.query(LyOperationAuditLog)
                .filter(LyOperationAuditLog.result == "failed")
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(failed_audit)
            self.assertEqual(failed_audit.error_code, "MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT")
            self.assertEqual(failed_audit.resource_type, "MATERIAL_PURCHASE_ORDER")

    def test_from_requirements_rejects_missing_requirement(self) -> None:
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-missing"),
            json=self._from_requirements_payload(requirement_ids=[99999], idempotency_key="idem-a6-missing"),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            failed_audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(failed_audit.result, "failed")
            self.assertEqual(failed_audit.error_code, "MATERIAL_PURCHASE_NOT_FOUND")
            self.assertEqual(failed_audit.resource_type, "MATERIAL_PURCHASE_ORDER")

    def test_from_requirements_rejects_non_pending_requirement(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-PURCHASED", status="purchased")
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-non-pending"),
            json=self._from_requirements_payload(requirement_ids=[requirement_id], idempotency_key="idem-a6-non-pending"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)

    def test_from_requirements_rejects_zero_net_requirement(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-ZERO", net_required_qty="0")
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-zero"),
            json=self._from_requirements_payload(requirement_ids=[requirement_id], idempotency_key="idem-a6-zero"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)

    def test_from_requirements_rejects_duplicate_purchase_no(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-DUP")
        self._seed_purchase_order(purchase_no="PO-A6-DUP")
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-duplicate-po"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-duplicate-po",
                purchase_no="PO-A6-DUP",
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 1)
