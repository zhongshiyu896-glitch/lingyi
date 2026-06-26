"""A6 material calculation to procurement requirement pool flow."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
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
from app.models.finance_approval import Base as FinanceApprovalBase
from app.models.finance_approval import LyFinanceApprovalOperation
from app.models.finance_approval import LyFinanceApprovalTask
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.material_purchase import LyMaterialPurchasePaymentOperation
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.quality import Base as QualityBase
from app.models.sample import Base as SampleBase
from app.models.sample import LySampleIdempotency
from app.models.sample import LySampleMaterialBom
from app.models.sample import LySampleMaterialBomItem
from app.models.sample import LySampleOrder
from app.models.sample import LySampleTrackingEvent
from app.models.sample import LySampleTrackingNode
from app.models.sample import LySampleTrackingTemplate
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LyDeliveryInvoiceOperation
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.sales_order import LySalesPaymentEntry
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.finance_approval import get_db_session as finance_approval_db_dep
from app.routers.material_purchase import get_db_session as material_purchase_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.routers.sample import get_db_session as sample_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.services.material_purchase_service import MaterialPurchaseService
from app.services.production_service import DEFAULT_MATERIAL_CHECK_WAREHOUSE_CODE
from app.services.production_service import ProductionService


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
        SampleBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        FinanceApprovalBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sample_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        app.dependency_overrides[material_purchase_db_dep] = _override_db
        app.dependency_overrides[finance_approval_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sample_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        app.dependency_overrides.pop(finance_approval_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        os.environ.pop("LINGYI_FASTAPI_ROLE_ACTIONS_JSON", None)
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyFinanceApprovalOperation).delete()
            session.query(LyFinanceApprovalTask).delete()
            session.query(LySalesPaymentEntry).delete()
            session.query(LyDeliveryInvoiceOperation).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LyMaterialPurchasePaymentOperation).delete()
            session.query(LyMaterialPurchasePayment).delete()
            session.query(LyMaterialPurchaseInvoice).delete()
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySampleIdempotency).delete()
            session.query(LySampleTrackingEvent).delete()
            session.query(LySampleTrackingNode).delete()
            session.query(LySampleTrackingTemplate).delete()
            session.query(LySampleMaterialBomItem).delete()
            session.query(LySampleMaterialBom).delete()
            session.query(LySampleOrder).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            style = LyStyleMaster(
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
            session.add(style)
            session.flush()
            self._seed_master_data(session=session)
            session.add(
                LyApparelBom(
                    id=601,
                    bom_no="BOM-A6-TEE-V1",
                    company=self.COMPANY,
                    style_master_id=int(style.id),
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
    def _scope_headers(request_id: str = "req-a6-scope") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "a6.scope.user",
            "X-LY-Dev-Roles": "Purchasing Manager",
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _enable_fastapi_material_purchase_actions(*, read: bool = False, write: bool = False) -> None:
        actions: list[str] = []
        if read:
            actions.append("material_purchase:read")
        if write:
            actions.append("material_purchase:write")
        os.environ["LINGYI_FASTAPI_ROLE_ACTIONS_JSON"] = json.dumps(
            {"roles": {"Purchasing Manager": actions}},
        )

    def _submit_sales_order(self, *, draft_id: int, sales_order_no: str, suffix: str) -> None:
        submitted = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/submit",
            headers=self._headers(f"req-a6-submit-{suffix}"),
            json={
                "operation": "submit_draft",
                "company": self.COMPANY,
                "sales_order_no_or_source_order_ref": sales_order_no,
                "idempotency_key": f"idem-a6-submit-{suffix}",
            },
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["data"]["docstatus"], 1)

    def _submit_sales_order_by_no(self, *, sales_order_no: str, suffix: str) -> None:
        with self.SessionLocal() as session:
            order_id = int(session.query(LySalesOrder.id).filter(LySalesOrder.sales_order_no == sales_order_no).scalar())
        self._submit_sales_order(draft_id=order_id, sales_order_no=sales_order_no, suffix=suffix)

    def _approve_purchase_invoice(self, invoice_id: int, *, suffix: str) -> dict[str, object]:
        created = self.client.post(
            "/api/finance/approval-tasks",
            headers=self._headers(f"req-a6-invoice-approval-create-{suffix}"),
            json={
                "operation": "create_task",
                "company": self.COMPANY,
                "source_type": "purchase_invoice",
                "source_id": invoice_id,
                "idempotency_key": f"idem-a6-invoice-approval-create-{suffix}",
                "scenario_tag": f"A6-PURCHASE-INVOICE-APPROVAL-{suffix}",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        task = created.json()["data"]
        approved = self.client.post(
            f"/api/finance/approval-tasks/{task['id']}/approve",
            headers=self._headers(f"req-a6-invoice-approval-approve-{suffix}"),
            json={
                "operation": "approve_task",
                "company": self.COMPANY,
                "idempotency_key": f"idem-a6-invoice-approval-approve-{suffix}",
                "reason": "A6 采购发票审批通过",
            },
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        data = approved.json()["data"]
        self.assertEqual(data["status"], "approved")
        return data

    def _approve_purchase_payment(self, payment_id: int, *, suffix: str) -> dict[str, object]:
        created = self.client.post(
            "/api/finance/approval-tasks",
            headers=self._headers(f"req-a6-approval-create-{suffix}"),
            json={
                "operation": "create_task",
                "company": self.COMPANY,
                "source_type": "purchase_payment",
                "source_id": payment_id,
                "idempotency_key": f"idem-a6-approval-create-{suffix}",
                "scenario_tag": f"A6-PURCHASE-PAYMENT-APPROVAL-{suffix}",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        task = created.json()["data"]
        approved = self.client.post(
            f"/api/finance/approval-tasks/{task['id']}/approve",
            headers=self._headers(f"req-a6-approval-approve-{suffix}"),
            json={
                "operation": "approve_task",
                "company": self.COMPANY,
                "idempotency_key": f"idem-a6-approval-approve-{suffix}",
                "reason": "A6 采购付款审批通过",
            },
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        data = approved.json()["data"]
        self.assertEqual(data["status"], "approved")
        return data

    def _style_id(self) -> int:
        with self.SessionLocal() as session:
            row = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            return int(row.id)

    def _seed_master_data(self, *, session) -> None:
        self._seed_master_data_record(session=session, entity_type="supplier", code="SUP-A6", name="SUP-A6")
        self._seed_master_data_record(session=session, entity_type="material", code=self.MATERIAL, name="A6 棉布")
        self._seed_material_unit(session=session, code="MU-METER", name="米")
        self._seed_material_unit(session=session, code="MU-PCS", name="件")
        self._seed_material_unit(session=session, code="MU-YARD", name="码")
        self._seed_master_data_record(session=session, entity_type="warehouse", code=self.WAREHOUSE, name=self.WAREHOUSE)

    def _seed_material_unit(self, *, session, code: str, name: str, status: str = "active") -> None:
        session.add(
            LyMasterDataRecord(
                entity_type="material",
                company=self.COMPANY,
                code=code,
                name=name,
                status=status,
                payload={"material_kind": "unit", "unit_code": code, "unit_name": name, "base_unit": name},
                created_by="seed",
                updated_by="seed",
            )
        )

    def _seed_master_data_record(
        self,
        *,
        session,
        entity_type: str,
        code: str,
        name: str | None = None,
        status: str = "active",
    ) -> None:
        session.add(
            LyMasterDataRecord(
                entity_type=entity_type,
                company=self.COMPANY,
                code=code,
                name=name or code,
                status=status,
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )

    def _sample_payload(self, *, sample_no: str, idempotency_key: str) -> dict[str, object]:
        return {
            "operation": "create",
            "company": self.COMPANY,
            "sample_no": sample_no,
            "style_master_id": self._style_id(),
            "style_no": self.STYLE,
            "style_name": "A6 Tee",
            "customer": "CUST-A6",
            "factory": "A6 样衣组",
            "sample_type": "初样",
            "stage": "建档",
            "progress": 0,
            "pattern_maker": "版师 A6",
            "sample_maker": "样衣工 A6",
            "due_date": "2026-06-30",
            "status": "draft",
            "image_tone": "blue",
            "idempotency_key": idempotency_key,
        }

    def _seed_requirement(
        self,
        *,
        requirement_no: str = "REQ-A6-SEED-001",
        status: str = "pending",
        net_required_qty: str = "10",
        sales_order: str = "SO-A6-SEED",
        sales_order_item: str = "SO-A6-SEED-ITEM",
        supplier_name: str = "SUP-A6",
        material_item_code: str | None = None,
        warehouse: str | None = None,
        unit_price: str = "12.5",
        bom_color: str | None = None,
        bom_size: str | None = None,
        bom_part: str | None = None,
        uom: str = "米",
        style_no: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> int:
        material_code = material_item_code or self.MATERIAL
        target_warehouse = warehouse or self.WAREHOUSE
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
                item_code=style_no or self.STYLE,
                bom_color=bom_color,
                bom_size=bom_size,
                bom_part=bom_part,
                material_item_code=material_code,
                material_name="A6 棉布",
                supplier_name=supplier_name,
                warehouse=target_warehouse,
                required_qty=Decimal(net_required_qty),
                available_qty=Decimal("0"),
                net_required_qty=Decimal(net_required_qty),
                purchased_qty=Decimal("0"),
                received_qty=Decimal("0"),
                uom=uom,
                unit_price=Decimal(unit_price),
                status=status,
                payload=payload or {},
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

    def _seed_receipt_backed_purchase_chain(
        self,
        *,
        plan_id: int,
        order_id: int,
        line_id: int,
        purchase_no: str,
        qty: str,
    ) -> None:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                id=plan_id,
                plan_no=f"PP-{purchase_no}",
                company=self.COMPANY,
                sales_order=f"SO-{purchase_no}",
                sales_order_item=f"SO-{purchase_no}-ITEM",
                customer="CUST-A6",
                item_code=self.STYLE,
                bom_id=601,
                bom_version="V1",
                planned_qty=Decimal("5"),
                status="material_checked",
                idempotency_key=f"idem-plan-{purchase_no}",
                request_hash=f"hash-plan-{purchase_no}",
                created_by="seed",
            )
            session.add(plan)
            session.add(
                LyProductionPlanMaterial(
                    plan_id=plan_id,
                    bom_item_id=6011,
                    material_item_code=self.MATERIAL,
                    warehouse=self.WAREHOUSE,
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0"),
                    required_qty=Decimal(qty),
                    available_qty=Decimal("0"),
                    shortage_qty=Decimal(qty),
                )
            )
            order = LyMaterialPurchaseOrder(
                id=order_id,
                company=self.COMPANY,
                purchase_no=purchase_no,
                supplier_name="SUP-A6",
                status="draft",
                total_qty=Decimal(qty),
                received_qty=Decimal("0"),
                total_amount=Decimal(qty) * Decimal("12.5"),
                currency="CNY",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.add(
                LyMaterialPurchaseOrderItem(
                    id=line_id,
                    order_id=order_id,
                    company=self.COMPANY,
                    item_code=self.MATERIAL,
                    material_item_code=self.MATERIAL,
                    material_name="A6 棉布",
                    qty=Decimal(qty),
                    received_qty=Decimal("0"),
                    uom="米",
                    unit_price=Decimal("12.5"),
                    amount=Decimal(qty) * Decimal("12.5"),
                    warehouse=self.WAREHOUSE,
                )
            )
            session.add(
                LyMaterialPurchaseRequirement(
                    company=self.COMPANY,
                    requirement_no=f"REQ-{purchase_no}",
                    source_type="production_plan",
                    source_id=str(plan_id),
                    source_no=f"PP-{purchase_no}",
                    plan_id=plan_id,
                    bom_item_id=6011,
                    sales_order=f"SO-{purchase_no}",
                    sales_order_item=f"SO-{purchase_no}-ITEM",
                    item_code=self.STYLE,
                    material_item_code=self.MATERIAL,
                    material_name="A6 棉布",
                    supplier_name="SUP-A6",
                    warehouse=self.WAREHOUSE,
                    required_qty=Decimal(qty),
                    available_qty=Decimal("0"),
                    net_required_qty=Decimal(qty),
                    purchased_qty=Decimal(qty),
                    received_qty=Decimal("0"),
                    purchase_order_id=order_id,
                    purchase_order_item_id=line_id,
                    purchase_no=purchase_no,
                    uom="米",
                    unit_price=Decimal("12.5"),
                    status="purchased",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

    def _from_requirements_payload(
        self,
        *,
        requirement_ids: list[int],
        idempotency_key: str,
        purchase_no: str | None = None,
        supplier_name: str | None = None,
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
        if supplier_name:
            payload["supplier_name"] = supplier_name
        return payload

    def _cancel_order_payload(self, *, idempotency_key: str, reason: str = "测试取消采购单") -> dict[str, object]:
        return {
            "operation": "cancel_order",
            "company": self.COMPANY,
            "reason": reason,
            "idempotency_key": idempotency_key,
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
        item_code: str,
        quantity: object,
        warehouse: str | None = None,
        operation_code: str = "C",
        status_action_code: str = "C",
    ) -> str:
        return "-".join(
            [
                cls.WAREHOUSE_SCENARIO,
                "RW",
                operation_code,
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(warehouse or cls.WAREHOUSE),
                cls._carrier_code(item_code),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(cls.BUSINESS_DATE),
                cls._carrier_code(status_action_code),
            ]
        )

    @classmethod
    def _inventory_count_request_id(cls, *, warehouse: str | None = None, count_date: str | None = None) -> str:
        normalized_date = date.fromisoformat(count_date or cls.BUSINESS_DATE).strftime("%Y%m%d")
        return (
            "Z002-WAREHOUSE-COUNT-20260618-601-REQ-COUNT-"
            f"W{cls._carrier_code(warehouse or cls.WAREHOUSE, length=8)}-D{normalized_date}"
        )

    def _create_stock_receipt(
        self,
        *,
        source_type: str,
        source_id: str,
        idempotency_key: str,
        qty: str,
        item_code: str | None = None,
        uom: str = "米",
        purchase_order_item_id: int | None = None,
        purchase_requirement_id: int | None = None,
    ) -> dict[str, object]:
        receipt_item_code = item_code or self.MATERIAL
        receipt_item: dict[str, object] = {
            "item_code": receipt_item_code,
            "qty": qty,
            "uom": uom,
            "target_warehouse": self.WAREHOUSE,
        }
        if purchase_order_item_id is not None:
            receipt_item["purchase_order_item_id"] = purchase_order_item_id
        if purchase_requirement_id is not None:
            receipt_item["purchase_requirement_id"] = purchase_requirement_id
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    item_code=receipt_item_code,
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
                "item_code": receipt_item_code,
                "quantity": qty,
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": idempotency_key,
                "items": [receipt_item],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        if source_type != "material_purchase_order":
            return response.json()["data"]

        draft = response.json()["data"]
        audit_response = self.client.post(
            f"/api/warehouse/stock-entry-drafts/{int(draft['id'])}/audit",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    item_code=receipt_item_code,
                    quantity=qty,
                    operation_code="A",
                    status_action_code="A",
                )
            ),
            json={
                "reason": "采购入库审核",
                "idempotency_key": idempotency_key,
                "source_ref": source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": receipt_item_code,
                "operation": "audit_stock_entry_draft",
                "quantity": qty,
                "business_date": self.BUSINESS_DATE,
                "status_action": "audit",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
            },
        )
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        return audit_response.json()["data"]

    def _assert_balanced_inventory_reconciliation(self, *, item_code: str, expected_qty: Decimal, suffix: str) -> None:
        scenario = "Z002-WAREHOUSE-COUNT-20260618-601"
        request_id = self._inventory_count_request_id()
        inventory_count = self.client.post(
            "/api/warehouse/inventory-counts",
            headers=self._headers(request_id),
            json={
                "company": self.COMPANY,
                "warehouse": self.WAREHOUSE,
                "count_date": self.BUSINESS_DATE,
                "idempotency_key": f"{scenario}:idem-a6-multi-sku-count-{suffix}",
                "source_ref": f"{scenario}:count:{suffix}",
                "remark": "A6 多颜色尺码采购入库后账实平",
                "items": [
                    {
                        "item_code": item_code,
                        "batch_no": None,
                        "serial_no": None,
                        "system_qty": "0",
                        "counted_qty": str(expected_qty),
                        "variance_reason": "A6 多 SKU 闭环账实一致",
                    }
                ],
            },
        )
        self.assertEqual(inventory_count.status_code, 201, inventory_count.text)
        self.assertEqual(Decimal(str(inventory_count.json()["data"]["items"][0]["system_qty"])), expected_qty)
        self.assertEqual(Decimal(str(inventory_count.json()["data"]["items"][0]["counted_qty"])), expected_qty)
        self.assertEqual(Decimal(str(inventory_count.json()["data"]["items"][0]["variance_qty"])), Decimal("0.000000"))

        reconciliation = self.client.get(
            f"/api/warehouse/inventory-balance-reconciliation?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={item_code}",
            headers=self._headers(f"req-a6-multi-sku-reconciliation-{suffix}"),
        )
        self.assertEqual(reconciliation.status_code, 200, reconciliation.text)
        reconciliation_rows = reconciliation.json()["data"]["items"]
        self.assertEqual(reconciliation.json()["data"]["total"], 1)
        self.assertEqual(reconciliation_rows[0]["warehouse"], self.WAREHOUSE)
        self.assertEqual(reconciliation_rows[0]["item_code"], item_code)
        self.assertEqual(Decimal(str(reconciliation_rows[0]["book_qty"])), expected_qty)
        self.assertEqual(Decimal(str(reconciliation_rows[0]["actual_qty"])), expected_qty)
        self.assertEqual(Decimal(str(reconciliation_rows[0]["diff_qty"])), Decimal("0.000000"))
        self.assertEqual(reconciliation_rows[0]["status"], "balanced")

    def _create_finished_goods_inbound(
        self,
        *,
        sales_order: str,
        qty: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        source_id = f"{self.WAREHOUSE_SCENARIO}:finished-goods:{sales_order}"
        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    item_code=self.STYLE,
                    quantity=qty,
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": self.COMPANY,
                "purpose": "Material Receipt",
                "source_type": "manual",
                "source_id": source_id,
                "source_ref": source_id,
                "finished_goods_source_id": source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": self.STYLE,
                "quantity": qty,
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": idempotency_key,
                "items": [
                    {
                        "item_code": self.STYLE,
                        "qty": qty,
                        "uom": "件",
                        "target_warehouse": self.WAREHOUSE,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["data"]

    def _cancel_stock_receipt(self, *, draft: dict[str, object], source_id: str, idempotency_key: str, qty: str):
        return self.client.post(
            f"/api/warehouse/stock-entry-drafts/{int(draft['id'])}/cancel",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    item_code=self.MATERIAL,
                    quantity=qty,
                    operation_code="X",
                    status_action_code="X",
                )
            ),
            json={
                "reason": "撤销采购入库",
                "idempotency_key": idempotency_key,
                "source_ref": source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": self.MATERIAL,
                "operation": "cancel_stock_entry_draft",
                "quantity": qty,
                "business_date": self.BUSINESS_DATE,
                "status_action": "cancel",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
            },
        )

    def test_purchase_receipt_cancel_reverses_requirement_plan_and_stock(self) -> None:
        purchase_no = "PO-A6-CANCEL-001"
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}"
        idempotency_key = f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}"
        self._seed_receipt_backed_purchase_chain(
            plan_id=9801,
            order_id=9802,
            line_id=98021,
            purchase_no=purchase_no,
            qty="10",
        )

        draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="10",
        )
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order.id)).one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no=purchase_no).one()
            snapshot = session.query(LyProductionPlanMaterial).filter_by(plan_id=9801).one()
            self.assertEqual(str(order.status), "received")
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("10.000000"))
            self.assertEqual(str(requirement.status), "completed")
            self.assertEqual(Decimal(str(requirement.received_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("0.000000"))

        cancelled = self._cancel_stock_receipt(
            draft=draft,
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="10",
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["outbox"]["status"], "cancelled")

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&keyword={purchase_no}",
            headers=self._headers("req-a6-cancel-requirement"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_data = requirements.json()["data"]["items"][0]
        self.assertEqual(requirement_data["status"], "purchased")
        self.assertFalse(requirement_data["has_completed"])
        self.assertEqual(Decimal(str(requirement_data["received_qty"])), Decimal("0.000000"))

        stock_ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-cancel-ledger"),
        )
        purchase_receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company={self.COMPANY}&material_item_code={self.MATERIAL}",
            headers=self._headers("req-a6-cancel-receipts"),
        )
        self.assertEqual(stock_ledger.status_code, 200, stock_ledger.text)
        self.assertEqual(stock_ledger.json()["data"]["total"], 0)
        self.assertEqual(purchase_receipts.status_code, 200, purchase_receipts.text)
        self.assertEqual(purchase_receipts.json()["data"]["total"], 0)

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order.id)).one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no=purchase_no).one()
            snapshot = session.query(LyProductionPlanMaterial).filter_by(plan_id=9801).one()
            self.assertEqual(str(order.status), "draft")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(Decimal(str(requirement.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("10.000000"))

    def test_partial_purchase_receipt_keeps_requirement_and_plan_not_ready(self) -> None:
        purchase_no = "PO-A6-PARTIAL-001"
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}"
        idempotency_key = f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}:partial"
        self._seed_receipt_backed_purchase_chain(
            plan_id=9803,
            order_id=9804,
            line_id=98041,
            purchase_no=purchase_no,
            qty="10",
        )

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="4",
        )

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&keyword={purchase_no}",
            headers=self._headers("req-a6-partial-requirement"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_data = requirements.json()["data"]["items"][0]
        self.assertEqual(requirement_data["status"], "purchased")
        self.assertFalse(requirement_data["has_completed"])
        self.assertEqual(Decimal(str(requirement_data["received_qty"])), Decimal("4.000000"))

        plan_detail = self.client.get("/api/production/plans/9803", headers=self._headers("req-a6-partial-plan"))
        self.assertEqual(plan_detail.status_code, 200, plan_detail.text)
        plan_data = plan_detail.json()["data"]
        self.assertFalse(plan_data["material_ready"])
        self.assertEqual(plan_data["purchase_status"], "purchasing")
        self.assertEqual(plan_data["pending_requirement_count"], 1)
        self.assertEqual(Decimal(str(plan_data["available_qty_total"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(plan_data["shortage_qty_total"])), Decimal("6.000000"))

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order.id)).one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no=purchase_no).one()
            snapshot = session.query(LyProductionPlanMaterial).filter_by(plan_id=9803).one()
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("4.000000"))
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(Decimal(str(requirement.received_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("6.000000"))

    def test_purchase_receipt_source_id_with_item_code_updates_requirement(self) -> None:
        purchase_no = "PO-A6-SRC-ITEM-001"
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}:{self.MATERIAL}"
        idempotency_key = f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}:source-item"
        self._seed_receipt_backed_purchase_chain(
            plan_id=9805,
            order_id=9806,
            line_id=98061,
            purchase_no=purchase_no,
            qty="7",
        )

        draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="7",
        )
        self.assertEqual(draft["source_id"], source_id)

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}",
            headers=self._headers("req-a6-source-item-requirement"),
        )
        receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company={self.COMPANY}&purchase_no={purchase_no}",
            headers=self._headers("req-a6-source-item-receipt"),
        )
        plan_detail = self.client.get("/api/production/plans/9805", headers=self._headers("req-a6-source-item-plan"))

        self.assertEqual(requirements.status_code, 200, requirements.text)
        self.assertEqual(requirements.json()["data"]["total"], 1)
        requirement_data = requirements.json()["data"]["items"][0]
        self.assertTrue(requirement_data["has_completed"])
        self.assertEqual(requirement_data["purchase_no"], purchase_no)
        self.assertEqual(Decimal(str(requirement_data["received_qty"])), Decimal("7.000000"))
        self.assertEqual(receipts.status_code, 200, receipts.text)
        self.assertEqual(receipts.json()["data"]["total"], 1)
        self.assertEqual(receipts.json()["data"]["items"][0]["purchase_no"], purchase_no)
        self.assertEqual(plan_detail.status_code, 200, plan_detail.text)
        self.assertTrue(plan_detail.json()["data"]["material_ready"])
        self.assertEqual(Decimal(str(plan_detail.json()["data"]["shortage_qty_total"])), Decimal("0.000000"))

    def test_purchase_receipt_rejects_wrong_purchase_line_warehouse(self) -> None:
        purchase_no = "PO-A6-WH-GUARD-001"
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}"
        idempotency_key = f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}"
        wrong_warehouse = "WH-A6-WRONG"
        self._seed_receipt_backed_purchase_chain(
            plan_id=9811,
            order_id=9812,
            line_id=98121,
            purchase_no=purchase_no,
            qty="10",
        )

        response = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=idempotency_key,
                    source_ref=source_id,
                    warehouse=wrong_warehouse,
                    item_code=self.MATERIAL,
                    quantity="10",
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": self.COMPANY,
                "purpose": "Material Receipt",
                "source_type": "material_purchase_order",
                "source_id": source_id,
                "source_ref": source_id,
                "warehouse": wrong_warehouse,
                "item_code": self.MATERIAL,
                "quantity": "10",
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": wrong_warehouse,
                "idempotency_key": idempotency_key,
                "items": [
                    {
                        "item_code": self.MATERIAL,
                        "qty": "10",
                        "uom": "米",
                        "target_warehouse": wrong_warehouse,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 0)
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order.id)).one()
            self.assertEqual(str(order.status), "draft")
            self.assertEqual(Decimal(str(order.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))

    def test_purchase_receipt_cancel_rejects_succeeded_outbox_without_reverse_doc(self) -> None:
        purchase_no = "PO-A6-CANCEL-SUCCEEDED"
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}"
        idempotency_key = f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}"
        self._seed_receipt_backed_purchase_chain(
            plan_id=9821,
            order_id=9822,
            line_id=98221,
            purchase_no=purchase_no,
            qty="10",
        )
        draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="10",
        )
        with self.SessionLocal() as session:
            outbox = session.query(LyWarehouseStockEntryOutboxEvent).filter_by(draft_id=int(draft["id"])).one()
            outbox.status = "succeeded"
            outbox.external_ref = "STE-A6-SUCCEEDED"
            session.commit()

        cancelled = self._cancel_stock_receipt(
            draft=draft,
            source_id=source_id,
            idempotency_key=idempotency_key,
            qty="10",
        )
        self.assertEqual(cancelled.status_code, 409, cancelled.text)
        self.assertEqual(cancelled.json()["code"], "WAREHOUSE_INVALID_STATUS")

        with self.SessionLocal() as session:
            draft_row = session.query(LyWarehouseStockEntryDraft).filter_by(id=int(draft["id"])).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no=purchase_no).one()
            self.assertEqual(str(draft_row.status), "pending_outbox")
            self.assertEqual(str(order.status), "received")
            self.assertEqual(str(requirement.status), "completed")

    def test_sample_convert_uses_same_style_bom_for_procurement_requirement(self) -> None:
        sample_no = "SMP-A6-BOM-001"
        style_id = self._style_id()
        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers("req-a6-sample-create"),
            json=self._sample_payload(sample_no=sample_no, idempotency_key="idem-a6-sample-create"),
        )
        self.assertEqual(created.status_code, 201, created.text)
        order_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["style_master_id"], style_id)

        copied_bom = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/copy-from-style",
            headers=self._headers("req-a6-sample-copy-bom"),
            json={
                "operation": "copy_from_style",
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-copy-bom",
            },
        )
        self.assertEqual(copied_bom.status_code, 200, copied_bom.text)
        self.assertEqual(copied_bom.json()["data"]["items"][0]["material_item_code"], self.MATERIAL)

        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers("req-a6-sample-submit"),
            json={
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-submit",
            },
        )
        sealed = self.client.post(
            f"/api/sample/orders/{order_id}/seal",
            headers=self._headers("req-a6-sample-seal"),
            json={
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-seal",
            },
        )
        converted = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers("req-a6-sample-convert"),
            json={
                "operation": "convert",
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-convert",
            },
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(sealed.status_code, 200, sealed.text)
        self.assertEqual(converted.status_code, 200, converted.text)
        bulk_no = converted.json()["data"]["bulk_handoff_no"]
        self._submit_sales_order_by_no(sales_order_no=bulk_no, suffix="sample-bom")

        detail = self.client.get(f"/api/sales-inventory/sales-orders/{bulk_no}", headers=self._headers("req-a6-bulk-detail"))
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_item = detail.json()["data"]["items"][0]
        self.assertEqual(sales_item["style_master_id"], style_id)
        self.assertEqual(sales_item["item_code"], self.STYLE)
        sales_order_item = sales_item["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-sample-plan"),
            json={
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 1,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-a6-sample-plan",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-401"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-sample-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        material_row = material_check.json()["data"]["items"][0]
        self.assertEqual(material_row["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(material_row["required_qty"])), Decimal("2.100000"))
        self.assertEqual(Decimal(str(material_row["available_qty"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(material_row["shortage_qty"])), Decimal("2.100000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={bulk_no}",
            headers=self._headers("req-a6-sample-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        requirement = requirement_rows[0]
        self.assertEqual(requirement["sales_order"], bulk_no)
        self.assertEqual(requirement["sales_order_item"], sales_order_item)
        self.assertEqual(requirement["item_code"], self.STYLE)
        self.assertEqual(requirement["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("2.100000"))

        with self.SessionLocal() as session:
            sample = session.query(LySampleOrder).one()
            sales_line = session.query(LySalesOrderItem).one()
            requirement_row = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(sample.bulk_handoff_no, bulk_no)
            self.assertEqual(sales_line.style_master_id, sample.style_master_id)
            self.assertEqual(requirement_row.sales_order, bulk_no)
            self.assertEqual(requirement_row.material_item_code, self.MATERIAL)

    def test_sample_edited_bom_feeds_bulk_procurement_requirement(self) -> None:
        sample_no = "SMP-A6-BOM-EDIT-001"
        sample_material = "FAB-A6-SAMPLE-EDIT"
        sample_uom = "码"
        created = self.client.post(
            "/api/sample/orders",
            headers=self._headers("req-a6-sample-edit-create"),
            json=self._sample_payload(sample_no=sample_no, idempotency_key="idem-a6-sample-edit-create"),
        )
        self.assertEqual(created.status_code, 201, created.text)
        order_id = int(created.json()["data"]["id"])

        with self.SessionLocal() as session:
            order = session.query(LySampleOrder).filter_by(id=order_id).one()
            self._seed_master_data_record(session=session, entity_type="material", code=sample_material, name="样板替代料")
            sample_bom = (
                session.query(LySampleMaterialBom)
                .filter_by(company=self.COMPANY, sample_order_id=order_id)
                .one()
            )
            sample_bom.style_master_id = int(order.style_master_id)
            sample_bom.item_code = self.STYLE
            sample_bom.source_bom_id = 601
            sample_bom.version_no = "S2"
            sample_bom.status = "draft"
            sample_bom.updated_by = "seed"
            session.query(LySampleMaterialBomItem).filter_by(bom_id=int(sample_bom.id)).delete()
            session.add(
                LySampleMaterialBomItem(
                    bom_id=int(sample_bom.id),
                    source_bom_item_id=None,
                    material_item_code=sample_material,
                    color=None,
                    part="样板改料",
                    qty_per_piece=Decimal("3"),
                    loss_rate=Decimal("0.10"),
                    uom=sample_uom,
                    is_alternative=1,
                    replace_group="FAB-A6",
                    remark="样板替代料",
                )
            )
            session.commit()

        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers("req-a6-sample-edit-submit"),
            json={
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-edit-submit",
            },
        )
        sealed = self.client.post(
            f"/api/sample/orders/{order_id}/seal",
            headers=self._headers("req-a6-sample-edit-seal"),
            json={
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-edit-seal",
            },
        )
        converted = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers("req-a6-sample-edit-convert"),
            json={
                "operation": "convert",
                "company": self.COMPANY,
                "idempotency_key": "idem-a6-sample-edit-convert",
            },
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(sealed.status_code, 200, sealed.text)
        self.assertEqual(converted.status_code, 200, converted.text)
        bulk_no = converted.json()["data"]["bulk_handoff_no"]
        self._submit_sales_order_by_no(sales_order_no=bulk_no, suffix="sample-edit-bom")

        detail = self.client.get(f"/api/sales-inventory/sales-orders/{bulk_no}", headers=self._headers("req-a6-sample-edit-bulk-detail"))
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_item = detail.json()["data"]["items"][0]
        sales_order_item = sales_item["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-sample-edit-plan"),
            json={
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 1,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-a6-sample-edit-plan",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-402"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-sample-edit-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        material_row = material_check.json()["data"]["items"][0]
        self.assertEqual(material_row["material_item_code"], sample_material)
        self.assertIsNone(material_row["bom_item_id"])
        self.assertEqual(material_row["uom"], sample_uom)
        self.assertEqual(Decimal(str(material_row["required_qty"])), Decimal("3.300000"))
        self.assertEqual(Decimal(str(material_row["shortage_qty"])), Decimal("3.300000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={bulk_no}",
            headers=self._headers("req-a6-sample-edit-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        requirement = requirement_rows[0]
        self.assertEqual(requirement["material_item_code"], sample_material)
        self.assertEqual(requirement["uom"], sample_uom)
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("3.300000"))

        create_po_payload = self._from_requirements_payload(
            requirement_ids=[int(requirement["id"])],
            idempotency_key="idem-a6-sample-edit-req-to-po",
            purchase_no="PO-A6-SAMPLE-EDIT",
            supplier_name="SUP-A6",
        )
        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-sample-edit-req-to-po"),
            json=create_po_payload,
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_order = create_po.json()["data"]["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(purchase_no, "PO-A6-SAMPLE-EDIT")
        self.assertEqual(purchase_order["items"][0]["material_item_code"], sample_material)
        self.assertEqual(purchase_order["items"][0]["uom"], sample_uom)
        self.assertEqual(Decimal(str(purchase_order["items"][0]["qty"])), Decimal("3.300000"))
        self.assertEqual(create_po.json()["data"]["requirements"][0]["status"], "purchased")

        receipt_draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}",
            qty="3.3",
            item_code=sample_material,
            uom=sample_uom,
        )
        self.assertEqual(receipt_draft["items"][0]["uom"], sample_uom)
        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}",
            headers=self._headers("req-a6-sample-edit-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_row = completed.json()["data"]["items"][0]
        self.assertTrue(completed_row["has_completed"])
        self.assertEqual(completed_row["material_item_code"], sample_material)
        self.assertEqual(completed_row["uom"], sample_uom)
        self.assertEqual(Decimal(str(completed_row["received_qty"])), Decimal("3.300000"))

        ready_detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers("req-a6-sample-edit-ready"))
        self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
        ready_plan = ready_detail.json()["data"]
        self.assertTrue(ready_plan["material_ready"])
        self.assertEqual(ready_plan["purchase_status"], "ready")
        self.assertEqual(ready_plan["pending_requirement_count"], 0)
        self.assertEqual(Decimal(str(ready_plan["required_qty_total"])), Decimal("3.300000"))
        self.assertEqual(Decimal(str(ready_plan["available_qty_total"])), Decimal("3.300000"))
        self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

        with self.SessionLocal() as session:
            requirement_row = session.query(LyMaterialPurchaseRequirement).one()
            snapshot = session.query(LyProductionPlanMaterial).one()
            order_row = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no=purchase_no).one()
            order_line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order_row.id)).one()
            self.assertIsNone(requirement_row.bom_item_id)
            self.assertEqual(requirement_row.material_item_code, sample_material)
            self.assertEqual(requirement_row.uom, sample_uom)
            self.assertEqual(str(requirement_row.status), "completed")
            self.assertEqual(Decimal(str(requirement_row.received_qty)), Decimal("3.300000"))
            self.assertEqual(snapshot.uom, sample_uom)
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("3.300000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("0.000000"))
            self.assertEqual(str(order_row.status), "received")
            self.assertEqual(order_line.uom, sample_uom)
            self.assertEqual(Decimal(str(order_line.received_qty)), Decimal("3.300000"))

        material_issue_scenario = "Z003-PROD-PLAN-DETAIL-20260618-403"
        material_issue_request_id = f"req-{material_issue_scenario}"
        material_issue = self.client.post(
            f"/api/production/plans/{plan_id}/material-issue",
            headers={**self._headers(material_issue_request_id), "X-Request-ID": material_issue_request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "business_date": "2026-06-18",
                "operation": "material_issue",
                "idempotency_key": f"{material_issue_scenario}:idem-a6-sample-edit-material-issue",
                "scenario_tag": material_issue_scenario,
                "plan_id": plan_id,
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": material_issue_request_id,
            },
        )
        self.assertEqual(material_issue.status_code, 200, material_issue.text)
        material_issue_item = material_issue.json()["data"]["items"][0]
        self.assertEqual(material_issue_item["material_item_code"], sample_material)
        self.assertEqual(material_issue_item["uom"], sample_uom)
        self.assertEqual(Decimal(str(material_issue_item["qty"])), Decimal("3.300000"))

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
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no="SO-A6-001", suffix="mat-check-main")
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

        checked_detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers())
        self.assertEqual(checked_detail.status_code, 200, checked_detail.text)
        checked_plan = checked_detail.json()["data"]
        self.assertFalse(checked_plan["material_ready"])
        self.assertEqual(checked_plan["purchase_status"], "pending_purchase")
        self.assertEqual(checked_plan["pending_requirement_count"], 1)
        self.assertEqual(Decimal(str(checked_plan["required_qty_total"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(checked_plan["available_qty_total"])), Decimal("30.000000"))
        self.assertEqual(Decimal(str(checked_plan["shortage_qty_total"])), Decimal("54.000000"))

        checked_list = self.client.get(
            "/api/production/plans?sales_order=SO-A6-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(checked_list.status_code, 200, checked_list.text)
        checked_list_row = checked_list.json()["data"]["items"][0]
        self.assertEqual(checked_list_row["purchase_status"], "pending_purchase")
        self.assertEqual(Decimal(str(checked_list_row["shortage_qty_total"])), Decimal("54.000000"))

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

        reset_update = self.client.patch(
            f"/api/sales-inventory/sales-orders/drafts/{order.json()['data']['id']}",
            headers=self._headers("req-a6-reset-after-material-check"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "update_draft",
                "idempotency_key": "idem-so-a6-001-update-after-material-check",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-07-01",
                "currency": "CNY",
                "items": [
                    {
                        "sales_order_item": sales_order_item,
                        "item_code": self.STYLE,
                        "item_name": "Ignored",
                        "color": "白",
                        "size": "M",
                        "qty": 120,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(reset_update.status_code, 200, reset_update.text)
        self.assertEqual(reset_update.json()["data"]["docstatus"], 0)
        self.assertEqual(reset_update.json()["data"]["items"][0]["ys_material_calc_state"], "待算料")
        requirements_after_reset_update = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending",
            headers=self._headers("req-a6-requirements-after-reset-update"),
        )
        self.assertEqual(requirements_after_reset_update.status_code, 200, requirements_after_reset_update.text)
        self.assertEqual(requirements_after_reset_update.json()["data"]["total"], 0)

        material_check_after_update = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(), "X-Request-ID": f"{request_id}-after-edit"},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{self.MATERIAL_CHECK_SCENARIO}:idem-material-check-after-edit",
                "scenario_tag": self.MATERIAL_CHECK_SCENARIO,
                "plan_id": plan_id,
                "sales_order": "SO-A6-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": f"{request_id}-after-edit",
            },
        )
        self.assertEqual(material_check_after_update.status_code, 409, material_check_after_update.text)
        self.assertEqual(material_check_after_update.json()["code"], "PRODUCTION_SO_NOT_APPROVED")
        self._submit_sales_order(
            draft_id=int(order.json()["data"]["id"]),
            sales_order_no="SO-A6-001",
            suffix="mat-check-after-edit",
        )
        material_check_after_update = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(), "X-Request-ID": f"{request_id}-after-edit-approved"},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{self.MATERIAL_CHECK_SCENARIO}:idem-material-check-after-edit-approved",
                "scenario_tag": self.MATERIAL_CHECK_SCENARIO,
                "plan_id": plan_id,
                "sales_order": "SO-A6-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": f"{request_id}-after-edit-approved",
            },
        )
        self.assertEqual(material_check_after_update.status_code, 200, material_check_after_update.text)
        self.assertEqual(Decimal(str(material_check_after_update.json()["data"]["items"][0]["shortage_qty"])), Decimal("54.000000"))

        requirements_after_recheck = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending",
            headers=self._headers("req-a6-requirements-after-recheck"),
        )
        self.assertEqual(requirements_after_recheck.status_code, 200, requirements_after_recheck.text)
        self.assertEqual(requirements_after_recheck.json()["data"]["total"], 1)
        requirement = requirements_after_recheck.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("54.000000"))

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

        ready_detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers())
        self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
        ready_plan = ready_detail.json()["data"]
        self.assertTrue(ready_plan["material_ready"])
        self.assertEqual(ready_plan["purchase_status"], "ready")
        self.assertEqual(ready_plan["pending_requirement_count"], 0)
        self.assertEqual(Decimal(str(ready_plan["required_qty_total"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(ready_plan["available_qty_total"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

        ready_list = self.client.get(
            "/api/production/plans?sales_order=SO-A6-001&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(ready_list.status_code, 200, ready_list.text)
        ready_list_row = ready_list.json()["data"]["items"][0]
        self.assertTrue(ready_list_row["material_ready"])
        self.assertEqual(ready_list_row["purchase_status"], "ready")
        self.assertEqual(Decimal(str(ready_list_row["shortage_qty_total"])), Decimal("0.000000"))

        purchase_invoice_no = f"PINV-A6-{purchase_no}"
        purchase_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers("req-a6-same-chain-pinv"),
            json={
                "operation": "create_purchase_invoice",
                "company": self.COMPANY,
                "purchase_no": purchase_no,
                "supplier_name": "SUP-A6",
                "material_item_code": self.MATERIAL,
                "qty": "54",
                "rate": "12.5",
                "posting_date": "2026-06-17",
                "due_date": "2026-07-17",
                "purchase_invoice": purchase_invoice_no,
                "source_ref": f"SRC-A6-PINV-{purchase_no}",
                "idempotency_key": f"idem-a6-pinv-{purchase_no}",
                "scenario_tag": "A6-PURCHASE-INVOICE-001",
            },
        )
        self.assertEqual(purchase_invoice.status_code, 201, purchase_invoice.text)
        invoice_data = purchase_invoice.json()["data"]
        self.assertEqual(invoice_data["purchase_no"], purchase_no)
        self.assertEqual(invoice_data["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(invoice_data["grand_total"])), Decimal("675.000000"))
        self.assertEqual(Decimal(str(invoice_data["outstanding_amount"])), Decimal("675.000000"))
        self._approve_purchase_invoice(
            int(invoice_data["id"]),
            suffix=str(purchase_no).replace("/", "-"),
        )

        purchase_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers("req-a6-same-chain-pay"),
            json={
                "operation": "create_purchase_payment",
                "company": self.COMPANY,
                "purchase_invoice": purchase_invoice_no,
                "supplier_name": "SUP-A6",
                "posting_date": "2026-06-18",
                "paid_amount": "675",
                "mode_of_payment": "Bank Transfer",
                "reference_no": f"BANK-A6-{purchase_no}",
                "reference_date": "2026-06-18",
                "payment_entry": f"PP-A6-{purchase_no}",
                "source_ref": f"SRC-A6-PP-{purchase_no}",
                "idempotency_key": f"idem-a6-pp-{purchase_no}",
                "scenario_tag": "A6-PURCHASE-PAYMENT-001",
            },
        )
        self.assertEqual(purchase_payment.status_code, 201, purchase_payment.text)
        payment_data = purchase_payment.json()["data"]
        self.assertEqual(payment_data["purchase_no"], purchase_no)
        self.assertEqual(payment_data["status"], "pending_approval")
        self.assertEqual(Decimal(str(payment_data["outstanding_before"])), Decimal("675.000000"))
        self.assertEqual(Decimal(str(payment_data["outstanding_after"])), Decimal("0.000000"))

        pending_invoices = self.client.get(
            f"/api/material-purchase/purchase-invoices?keyword={purchase_invoice_no}",
            headers=self._headers("req-a6-same-chain-pinv-pending"),
        )
        self.assertEqual(pending_invoices.status_code, 200, pending_invoices.text)
        pending_invoice = pending_invoices.json()["data"]["items"][0]
        self.assertEqual(pending_invoice["status"], "submitted")
        self.assertEqual(Decimal(str(pending_invoice["outstanding_amount"])), Decimal("675.000000"))

        approval_data = self._approve_purchase_payment(
            int(payment_data["id"]),
            suffix=str(purchase_no).replace("/", "-"),
        )
        self.assertEqual(approval_data["source_status"], "submitted")

        paid_invoices = self.client.get(
            f"/api/material-purchase/purchase-invoices?keyword={purchase_invoice_no}",
            headers=self._headers("req-a6-same-chain-pinv-list"),
        )
        self.assertEqual(paid_invoices.status_code, 200, paid_invoices.text)
        paid_invoice = paid_invoices.json()["data"]["items"][0]
        self.assertEqual(paid_invoice["purchase_no"], purchase_no)
        self.assertEqual(paid_invoice["status"], "paid")
        self.assertEqual(Decimal(str(paid_invoice["outstanding_amount"])), Decimal("0.000000"))

        with self.SessionLocal() as session:
            requirement_row = session.query(LyMaterialPurchaseRequirement).one()
            snapshot = session.query(LyProductionPlanMaterial).one()
            order_row = session.query(LyMaterialPurchaseOrder).one()
            order_line = session.query(LyMaterialPurchaseOrderItem).one()
            invoice_row = session.query(LyMaterialPurchaseInvoice).one()
            payment_row = session.query(LyMaterialPurchasePayment).one()
            self.assertEqual(str(requirement_row.status), "completed")
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("84.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal("0.000000"))
            self.assertEqual(str(order_row.status), "received")
            self.assertEqual(Decimal(str(order_line.received_qty)), Decimal("54.000000"))
            self.assertEqual(str(invoice_row.status), "paid")
            self.assertEqual(int(invoice_row.purchase_order_id), int(order_row.id))
            self.assertEqual(str(invoice_row.purchase_no), purchase_no)
            self.assertEqual(Decimal(str(invoice_row.outstanding_amount)), Decimal("0.000000"))
            self.assertEqual(str(payment_row.purchase_no), purchase_no)
            self.assertEqual(Decimal(str(payment_row.outstanding_after)), Decimal("0.000000"))
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

        finished_goods = self._create_finished_goods_inbound(
            sales_order="SO-A6-001",
            qty="10",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:fg-inbound:SO-A6-001",
        )
        self.assertEqual(finished_goods["source_type"], "finished_goods_inbound")
        self.assertEqual(finished_goods["items"][0]["item_code"], self.STYLE)
        self.assertEqual(Decimal(str(finished_goods["items"][0]["qty"])), Decimal("10.000000"))

        delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers("req-a6-delivery-invoice"),
            json={
                "operation": "create_delivery_invoice",
                "company": self.COMPANY,
                "sales_order": "SO-A6-001",
                "customer": "CUST-A6",
                "item_code": self.STYLE,
                "item_name": "A6 Tee",
                "warehouse": self.WAREHOUSE,
                "delivered_qty": 10,
                "uom": "件",
                "rate": 80,
                "posting_date": "2026-06-18",
                "due_date": "2026-07-18",
                "delivery_note": "DN-A6-001",
                "sales_invoice": "SI-A6-001",
                "source_ref": "SRC-A6-DELIVERY-001",
                "idempotency_key": "idem-a6-delivery-001",
            },
        )
        self.assertEqual(delivery.status_code, 201, delivery.text)
        delivery_data = delivery.json()["data"]
        self.assertEqual(delivery_data["sales_order"], "SO-A6-001")
        self.assertEqual(delivery_data["item_code"], self.STYLE)
        self.assertEqual(Decimal(str(delivery_data["grand_total"])), Decimal("800.000000"))
        self.assertEqual(Decimal(str(delivery_data["outstanding_amount"])), Decimal("800.000000"))

        sales_payment = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers("req-a6-sales-payment"),
            json={
                "operation": "create_payment_entry",
                "company": self.COMPANY,
                "sales_invoice": "SI-A6-001",
                "customer": "CUST-A6",
                "posting_date": "2026-06-19",
                "paid_amount": "800",
                "mode_of_payment": "Bank Transfer",
                "reference_no": "BANK-A6-SALES-001",
                "reference_date": "2026-06-19",
                "payment_entry": "PE-A6-001",
                "source_ref": "SRC-A6-PE-001",
                "idempotency_key": "idem-a6-sales-payment-001",
            },
        )
        self.assertEqual(sales_payment.status_code, 201, sales_payment.text)
        self.assertEqual(Decimal(str(sales_payment.json()["data"]["outstanding_before"])), Decimal("800.000000"))
        self.assertEqual(Decimal(str(sales_payment.json()["data"]["outstanding_after"])), Decimal("0.000000"))

        receivable = self.client.get(
            "/api/sales-inventory/sales-invoices?sales_order=SO-A6-001",
            headers=self._headers("req-a6-sales-invoice-list"),
        )
        self.assertEqual(receivable.status_code, 200, receivable.text)
        receivable_row = receivable.json()["data"]["items"][0]
        self.assertEqual(receivable_row["sales_invoice"], "SI-A6-001")
        self.assertEqual(receivable_row["status"], "paid")
        self.assertEqual(Decimal(str(receivable_row["outstanding_amount"])), Decimal("0.000000"))

        finished_goods_ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.STYLE}",
            headers=self._headers("req-a6-fg-ledger"),
        )
        self.assertEqual(finished_goods_ledger.status_code, 200, finished_goods_ledger.text)
        finished_goods_ledger_rows = finished_goods_ledger.json()["data"]["items"]
        self.assertEqual(
            [Decimal(str(row["actual_qty"])) for row in finished_goods_ledger_rows],
            [Decimal("10.000000"), Decimal("-10.000000")],
        )
        self.assertEqual(Decimal(str(finished_goods_ledger_rows[-1]["qty_after_transaction"])), Decimal("0.000000"))

        with self.SessionLocal() as session:
            sales_order = session.query(LySalesOrder).filter_by(sales_order_no="SO-A6-001").one()
            sales_line = session.query(LySalesOrderItem).filter_by(sales_order_id=int(sales_order.id)).one()
            material_snapshot = session.query(LyProductionPlanMaterial).one()
            requirement_row = session.query(LyMaterialPurchaseRequirement).one()
            purchase_invoice_row = session.query(LyMaterialPurchaseInvoice).one()
            purchase_payment_row = session.query(LyMaterialPurchasePayment).one()
            delivery_row = session.query(LyDeliveryInvoice).one()
            sales_payment_row = session.query(LySalesPaymentEntry).one()
            finished_goods_draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_type="finished_goods_inbound").one()
            finished_goods_item = session.query(LyWarehouseStockEntryDraftItem).filter_by(draft_id=int(finished_goods_draft.id)).one()
            delivery_issue_draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_type="sales_delivery_invoice").one()
            delivery_issue_item = session.query(LyWarehouseStockEntryDraftItem).filter_by(draft_id=int(delivery_issue_draft.id)).one()
            material_issue_draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter_by(
                    source_type="production_plan",
                    purpose="Material Issue",
                    source_id=f"production_plan:{plan_id}:material_issue",
                )
                .one()
            )
            material_issue_item = session.query(LyWarehouseStockEntryDraftItem).filter_by(draft_id=int(material_issue_draft.id)).one()
            self.assertEqual(sales_line.item_code, self.STYLE)
            self.assertEqual(str(material_snapshot.material_item_code), self.MATERIAL)
            self.assertEqual(str(requirement_row.sales_order), str(sales_order.sales_order_no))
            self.assertEqual(str(requirement_row.item_code), str(sales_line.item_code))
            self.assertEqual(str(requirement_row.material_item_code), str(material_snapshot.material_item_code))
            self.assertEqual(str(purchase_invoice_row.purchase_no), str(requirement_row.purchase_no))
            self.assertEqual(str(purchase_payment_row.purchase_no), str(requirement_row.purchase_no))
            self.assertEqual(str(finished_goods_draft.source_type), "finished_goods_inbound")
            self.assertEqual(str(finished_goods_item.item_code), self.STYLE)
            self.assertEqual(Decimal(str(finished_goods_item.qty)), Decimal("10.000000"))
            self.assertEqual(str(delivery_issue_draft.source_id), str(delivery_row.delivery_note))
            self.assertEqual(str(delivery_issue_item.item_code), self.STYLE)
            self.assertEqual(Decimal(str(delivery_issue_item.qty)), Decimal("10.000000"))
            self.assertEqual(str(delivery_row.sales_order), str(sales_order.sales_order_no))
            self.assertEqual(str(delivery_row.item_code), str(sales_line.item_code))
            self.assertEqual(str(delivery_row.status), "paid")
            self.assertEqual(str(sales_payment_row.sales_order), str(sales_order.sales_order_no))
            self.assertEqual(Decimal(str(sales_payment_row.outstanding_after)), Decimal("0.000000"))
            self.assertEqual(str(material_issue_item.item_code), self.MATERIAL)
            self.assertEqual(Decimal(str(material_issue_item.qty)), Decimal("84.000000"))
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("production:material_check", audit_actions)
            self.assertIn("material_purchase:write", audit_actions)
            self.assertIn("warehouse:stock_entry_draft", audit_actions)
            self.assertIn("sales_inventory:write", audit_actions)

    def test_material_check_allows_blank_warehouse_and_uses_default_material_warehouse(self) -> None:
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-optional-warehouse-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": "SO-A6-OPTIONAL-WH",
                "source_order_ref": "SO-A6-OPTIONAL-WH",
                "idempotency_key": "idem-so-a6-optional-wh",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 40,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(
            draft_id=int(order.json()["data"]["id"]),
            sales_order_no="SO-A6-OPTIONAL-WH",
            suffix="optional-warehouse",
        )
        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A6-OPTIONAL-WH", headers=self._headers())
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-optional-warehouse-plan"),
            json={
                "sales_order": "SO-A6-OPTIONAL-WH",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 40,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-optional-wh",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])
        scenario_tag = "Z003-PROD-PLAN-DETAIL-20260617-399"
        request_id = f"req-{scenario_tag}"

        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": "",
                "operation": "material_check",
                "idempotency_key": f"{scenario_tag}:idem-a6-optional-warehouse-material-check",
                "scenario_tag": scenario_tag,
                "plan_id": plan_id,
                "sales_order": "SO-A6-OPTIONAL-WH",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        self.assertNotEqual(material_check.json().get("code"), "PRODUCTION_WAREHOUSE_REQUIRED")
        material_row = material_check.json()["data"]["items"][0]
        self.assertEqual(material_row["warehouse"], DEFAULT_MATERIAL_CHECK_WAREHOUSE_CODE)
        self.assertEqual(Decimal(str(material_row["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(material_row["available_qty"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(material_row["shortage_qty"])), Decimal(str(material_row["required_qty"])))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=SO-A6-OPTIONAL-WH",
            headers=self._headers("req-a6-optional-warehouse-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        requirement = requirement_rows[0]
        self.assertEqual(requirement["sales_order"], "SO-A6-OPTIONAL-WH")
        self.assertEqual(requirement["warehouse"], DEFAULT_MATERIAL_CHECK_WAREHOUSE_CODE)
        self.assertEqual(Decimal(str(requirement["required_qty"])), Decimal("84.000000"))
        self.assertEqual(Decimal(str(requirement["available_qty"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("84.000000"))

        with self.SessionLocal() as session:
            snapshot = session.query(LyProductionPlanMaterial).filter_by(plan_id=plan_id).one()
            self.assertEqual(str(snapshot.warehouse), DEFAULT_MATERIAL_CHECK_WAREHOUSE_CODE)
            self.assertEqual(Decimal(str(snapshot.available_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(snapshot.shortage_qty)), Decimal(str(snapshot.required_qty)))
            self.assertEqual(
                session.query(LyMaterialPurchaseRequirement)
                .filter_by(sales_order="SO-A6-OPTIONAL-WH", status="pending")
                .count(),
                1,
            )

    def test_submit_sales_order_can_trigger_material_check_and_requirement_pool(self) -> None:
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-submit-auto-create"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": "SO-A6-AUTO-001",
                "source_order_ref": "SO-A6-AUTO-001",
                "idempotency_key": "idem-so-a6-auto-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
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
        draft_id = int(order.json()["data"]["id"])
        submit_payload = {
            "operation": "submit_draft",
            "company": self.COMPANY,
            "sales_order_no_or_source_order_ref": "SO-A6-AUTO-001",
            "idempotency_key": "idem-a6-submit-auto-001",
            "material_check_warehouse": self.WAREHOUSE,
        }

        submitted = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/submit",
            headers=self._headers("req-a6-submit-auto"),
            json=submit_payload,
        )
        replay = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/submit",
            headers=self._headers("req-a6-submit-auto-replay"),
            json=submit_payload,
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        submit_data = submitted.json()["data"]
        self.assertEqual(submit_data["docstatus"], 1)
        self.assertEqual(submit_data["items"][0]["ys_material_calc_state"], "已算料")

        plans = self.client.get(
            "/api/production/plans?sales_order=SO-A6-AUTO-001&page=1&page_size=20",
            headers=self._headers("req-a6-submit-auto-plans"),
        )
        self.assertEqual(plans.status_code, 200, plans.text)
        plan_rows = plans.json()["data"]["items"]
        self.assertEqual(len(plan_rows), 1)
        self.assertEqual(plan_rows[0]["purchase_status"], "pending_purchase")
        self.assertEqual(Decimal(str(plan_rows[0]["required_qty_total"])), Decimal("210.000000"))
        self.assertEqual(Decimal(str(plan_rows[0]["shortage_qty_total"])), Decimal("210.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=SO-A6-AUTO-001",
            headers=self._headers("req-a6-submit-auto-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        requirement = requirement_rows[0]
        self.assertEqual(requirement["sales_order"], "SO-A6-AUTO-001")
        self.assertEqual(requirement["material_item_code"], self.MATERIAL)
        self.assertEqual(requirement["warehouse"], self.WAREHOUSE)
        self.assertEqual(requirement["status"], "pending")
        self.assertEqual(Decimal(str(requirement["required_qty"])), Decimal("210.000000"))
        self.assertEqual(Decimal(str(requirement["net_required_qty"])), Decimal("210.000000"))

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 1)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 1)

    def test_submit_multi_sku_sales_order_triggers_material_check_per_order_item(self) -> None:
        with self.SessionLocal() as session:
            style = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            style.colors = [
                {"ys_color_code": "BLK", "ys_color_name": "黑"},
                {"ys_color_code": "WHT", "ys_color_name": "白"},
            ]
            style.sizes = [
                {"ys_size_code": "S", "ys_size_name": "S"},
                {"ys_size_code": "M", "ys_size_name": "M"},
            ]
            for code, name in [
                ("FAB-A6-SUBMIT-BLK-S", "提交即算黑色 S 码面料"),
                ("FAB-A6-SUBMIT-WHT-M", "提交即算白色 M 码面料"),
            ]:
                self._seed_master_data_record(session=session, entity_type="material", code=code, name=name)
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6081,
                        bom_id=601,
                        material_item_code="FAB-A6-SUBMIT-BLK-S",
                        color="黑",
                        size="S",
                        part="面料主身",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0.1"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:8",
                    ),
                    LyApparelBomItem(
                        id=6082,
                        bom_id=601,
                        material_item_code="FAB-A6-SUBMIT-WHT-M",
                        color="白",
                        size="M",
                        part="面料主身",
                        qty_per_piece=Decimal("2"),
                        loss_rate=Decimal("0.2"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:9",
                    ),
                ]
            )
            session.commit()

        sales_order_no = "SO-A6-SUBMIT-MULTI-001"
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-submit-multi-create"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": sales_order_no,
                "source_order_ref": sales_order_no,
                "idempotency_key": "idem-so-a6-submit-multi-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "黑",
                        "size": "S",
                        "qty": 4,
                        "rate": 80,
                        "uom": "件",
                    },
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 6,
                        "rate": 80,
                        "uom": "件",
                    },
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        draft_id = int(order.json()["data"]["id"])
        submit_payload = {
            "operation": "submit_draft",
            "company": self.COMPANY,
            "sales_order_no_or_source_order_ref": sales_order_no,
            "idempotency_key": "idem-a6-submit-multi-001",
            "material_check_warehouse": self.WAREHOUSE,
        }

        submitted = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/submit",
            headers=self._headers("req-a6-submit-multi"),
            json=submit_payload,
        )
        replay = self.client.post(
            f"/api/sales-inventory/sales-orders/drafts/{draft_id}/submit",
            headers=self._headers("req-a6-submit-multi-replay"),
            json=submit_payload,
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        submit_items = submitted.json()["data"]["items"]
        self.assertEqual({item["ys_material_calc_state"] for item in submit_items}, {"已算料"})
        detail = self.client.get(
            f"/api/sales-inventory/sales-orders/{sales_order_no}",
            headers=self._headers("req-a6-submit-multi-detail"),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_item_by_color_size = {(row["color"], row["size"]): row["name"] for row in detail.json()["data"]["items"]}
        self.assertEqual(set(sales_item_by_color_size), {("黑", "S"), ("白", "M")})

        plans = self.client.get(
            f"/api/production/plans?sales_order={sales_order_no}&page=1&page_size=20",
            headers=self._headers("req-a6-submit-multi-plans"),
        )
        self.assertEqual(plans.status_code, 200, plans.text)
        plan_rows = plans.json()["data"]["items"]
        self.assertEqual(len(plan_rows), 2)
        plan_by_color_size = {(row["color"], row["size"]): row for row in plan_rows}
        self.assertEqual(set(plan_by_color_size), {("黑", "S"), ("白", "M")})
        self.assertEqual(plan_by_color_size[("黑", "S")]["sales_order_item"], sales_item_by_color_size[("黑", "S")])
        self.assertEqual(plan_by_color_size[("白", "M")]["sales_order_item"], sales_item_by_color_size[("白", "M")])
        self.assertEqual(Decimal(str(plan_by_color_size[("黑", "S")]["planned_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(plan_by_color_size[("白", "M")]["planned_qty"])), Decimal("6.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-submit-multi-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 4)
        self.assertEqual({row["sales_order_item"] for row in requirement_rows}, set(sales_item_by_color_size.values()))
        white_m_item = sales_item_by_color_size[("白", "M")]
        requirements_by_order_item = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={white_m_item}&page=1&page_size=100",
            headers=self._headers("req-a6-submit-multi-requirements-by-item"),
        )
        self.assertEqual(requirements_by_order_item.status_code, 200, requirements_by_order_item.text)
        requirement_rows_by_order_item = requirements_by_order_item.json()["data"]["items"]
        self.assertEqual(len(requirement_rows_by_order_item), 2)
        self.assertEqual({row["sales_order_item"] for row in requirement_rows_by_order_item}, {white_m_item})
        self.assertEqual({row["bom_size"] for row in requirement_rows_by_order_item}, {None, "M"})
        dimensions_by_material: dict[str, set[tuple[object, object, object, str]]] = {}
        for row in requirement_rows:
            dimensions_by_material.setdefault(row["material_item_code"], set()).add(
                (row["bom_color"], row["bom_size"], row["bom_part"], row["sales_order_item"])
            )
        self.assertEqual(
            dimensions_by_material,
            {
                self.MATERIAL: {
                    (None, None, None, sales_item_by_color_size[("黑", "S")]),
                    (None, None, None, sales_item_by_color_size[("白", "M")]),
                },
                "FAB-A6-SUBMIT-BLK-S": {("黑", "S", "面料主身", sales_item_by_color_size[("黑", "S")])},
                "FAB-A6-SUBMIT-WHT-M": {("白", "M", "面料主身", sales_item_by_color_size[("白", "M")])},
            },
        )
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlan).count(), 2)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 4)

    def test_material_check_filters_bom_rows_by_sales_order_color_size(self) -> None:
        with self.SessionLocal() as session:
            self._seed_master_data_record(session=session, entity_type="material", code="FAB-A6-WHT", name="A6 白色配布")
            self._seed_master_data_record(session=session, entity_type="material", code="FAB-A6-BLK", name="A6 黑色配布")
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6012,
                        bom_id=601,
                        material_item_code="FAB-A6-WHT",
                        color="白",
                        size="M",
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6-WHITE 单价:9",
                    ),
                    LyApparelBomItem(
                        id=6013,
                        bom_id=601,
                        material_item_code="FAB-A6-BLK",
                        color="黑",
                        size="M",
                        qty_per_piece=Decimal("7"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6-BLACK 单价:9",
                    ),
                ]
            )
            session.commit()

        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-matrix-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": "SO-A6-MATRIX-001",
                "source_order_ref": "SO-A6-MATRIX-001",
                "idempotency_key": "idem-so-a6-matrix-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no="SO-A6-MATRIX-001", suffix="matrix")
        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A6-MATRIX-001", headers=self._headers())
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-matrix-plan"),
            json={
                "sales_order": "SO-A6-MATRIX-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 10,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-matrix-001",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])
        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-402"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-matrix-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": "SO-A6-MATRIX-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        items = material_check.json()["data"]["items"]
        material_codes = [item["material_item_code"] for item in items]
        self.assertEqual(material_codes, [self.MATERIAL, "FAB-A6-WHT"])
        self.assertNotIn("FAB-A6-BLK", material_codes)
        self.assertEqual(Decimal(str(items[0]["required_qty"])), Decimal("21.000000"))
        self.assertEqual(Decimal(str(items[1]["required_qty"])), Decimal("5.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=SO-A6-MATRIX-001",
            headers=self._headers("req-a6-matrix-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_codes = [row["material_item_code"] for row in requirements.json()["data"]["items"]]
        self.assertEqual(set(requirement_codes), {self.MATERIAL, "FAB-A6-WHT"})
        self.assertNotIn("FAB-A6-BLK", requirement_codes)

    def test_material_check_keeps_universal_rows_with_size_specific_same_material(self) -> None:
        with self.SessionLocal() as session:
            style = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            style.colors = [{"ys_color_code": "WHT", "ys_color_name": "白"}]
            style.sizes = [{"ys_size_code": "M", "ys_size_name": "M"}]
            self._seed_master_data_record(session=session, entity_type="material", code="FAB-A6-BLK-ONLY", name="A6 黑色排除布")
            session.query(LyApparelBomItem).filter_by(bom_id=601).delete()
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6021,
                        bom_id=601,
                        material_item_code=self.MATERIAL,
                        part="通用辅料",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:12.5",
                    ),
                    LyApparelBomItem(
                        id=6022,
                        bom_id=601,
                        material_item_code=self.MATERIAL,
                        color="白",
                        size="M",
                        part="M码用料",
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:12.5",
                    ),
                    LyApparelBomItem(
                        id=6023,
                        bom_id=601,
                        material_item_code="FAB-A6-BLK-ONLY",
                        color="黑",
                        size="M",
                        part="黑色排除",
                        qty_per_piece=Decimal("7"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:9",
                    ),
                ]
            )
            session.commit()

        sales_order_no = "SO-A6-UNIVERSAL-SIZE-001"
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-universal-size-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": sales_order_no,
                "source_order_ref": sales_order_no,
                "idempotency_key": "idem-so-a6-universal-size-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no=sales_order_no, suffix="universal-size")
        detail = self.client.get(f"/api/sales-inventory/sales-orders/{sales_order_no}", headers=self._headers("req-a6-universal-size-detail"))
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-universal-size-plan"),
            json={
                "sales_order": sales_order_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 10,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-universal-size-001",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-405"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-universal-size-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": sales_order_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        material_rows = material_check.json()["data"]["items"]
        material_by_part = {row["bom_part"]: row for row in material_rows}
        self.assertEqual(set(material_by_part), {"通用辅料", "M码用料"})
        self.assertEqual({row["material_item_code"] for row in material_rows}, {self.MATERIAL})
        self.assertEqual(Decimal(str(material_by_part["通用辅料"]["required_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(material_by_part["M码用料"]["required_qty"])), Decimal("5.000000"))
        self.assertIsNone(material_by_part["通用辅料"]["bom_color"])
        self.assertIsNone(material_by_part["通用辅料"]["bom_size"])
        self.assertEqual(material_by_part["M码用料"]["bom_color"], "白")
        self.assertEqual(material_by_part["M码用料"]["bom_size"], "M")

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-universal-size-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        requirement_by_part = {row["bom_part"]: row for row in requirement_rows}
        self.assertEqual(set(requirement_by_part), {"通用辅料", "M码用料"})
        self.assertEqual(Decimal(str(requirement_by_part["通用辅料"]["net_required_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(requirement_by_part["M码用料"]["net_required_qty"])), Decimal("5.000000"))

    def test_same_material_color_size_different_parts_reaches_procurement_receipt_ready(self) -> None:
        with self.SessionLocal() as session:
            style = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            style.colors = [{"ys_color_code": "BLK", "ys_color_name": "黑"}]
            style.sizes = [{"ys_size_code": "M", "ys_size_name": "M"}]
            session.query(LyApparelBomItem).filter_by(bom_id=601).delete()
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6021,
                        bom_id=601,
                        material_item_code=self.MATERIAL,
                        color="黑",
                        size="M",
                        part="门襟",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:12.5",
                    ),
                    LyApparelBomItem(
                        id=6022,
                        bom_id=601,
                        material_item_code=self.MATERIAL,
                        color="黑",
                        size="M",
                        part="袖口",
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:12.5",
                    ),
                ]
            )
            session.commit()

        sales_order_no = "SO-A6-PART-001"
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-part-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": sales_order_no,
                "source_order_ref": sales_order_no,
                "idempotency_key": "idem-so-a6-part-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "黑",
                        "size": "M",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no=sales_order_no, suffix="part")
        detail = self.client.get(f"/api/sales-inventory/sales-orders/{sales_order_no}", headers=self._headers("req-a6-part-detail"))
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-part-plan"),
            json={
                "sales_order": sales_order_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 10,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-part-001",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-472"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-part-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": sales_order_no,
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        material_rows = material_check.json()["data"]["items"]
        material_by_part = {row["bom_part"]: row for row in material_rows}
        self.assertEqual(set(material_by_part), {"门襟", "袖口"})
        self.assertEqual({row["material_item_code"] for row in material_rows}, {self.MATERIAL})
        self.assertEqual(Decimal(str(material_by_part["门襟"]["required_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(material_by_part["袖口"]["required_qty"])), Decimal("5.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-part-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 2)
        requirement_by_part = {row["bom_part"]: row for row in requirement_rows}
        self.assertEqual(set(requirement_by_part), {"门襟", "袖口"})
        self.assertEqual({row["material_item_code"] for row in requirement_rows}, {self.MATERIAL})
        self.assertEqual({row["bom_color"] for row in requirement_rows}, {"黑"})
        self.assertEqual({row["bom_size"] for row in requirement_rows}, {"M"})
        self.assertEqual(Decimal(str(requirement_by_part["门襟"]["net_required_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(requirement_by_part["袖口"]["net_required_qty"])), Decimal("5.000000"))

        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-part-req-to-po"),
            json=self._from_requirements_payload(
                requirement_ids=[int(row["id"]) for row in requirement_rows],
                idempotency_key="idem-a6-part-req-to-po",
                purchase_no="PO-A6-PART-001",
                supplier_name="SUP-A6",
            ),
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_order = create_po.json()["data"]["purchase_order"]
        self.assertEqual(purchase_order["purchase_no"], "PO-A6-PART-001")
        self.assertEqual(len(purchase_order["items"]), 2)
        purchase_items_by_part = {row["bom_part"]: row for row in purchase_order["items"]}
        self.assertEqual(set(purchase_items_by_part), {"门襟", "袖口"})
        self.assertEqual({row["material_item_code"] for row in purchase_order["items"]}, {self.MATERIAL})
        self.assertEqual(Decimal(str(purchase_items_by_part["门襟"]["qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(purchase_items_by_part["袖口"]["qty"])), Decimal("5.000000"))
        self.assertEqual({row["bom_part"] for row in create_po.json()["data"]["requirements"]}, {"门襟", "袖口"})

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-PART-001:{self.MATERIAL}:line:{purchase_items_by_part['门襟']['line_id']}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-PART-001:front",
            qty="10",
            purchase_order_item_id=int(purchase_items_by_part["门襟"]["line_id"]),
        )
        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-PART-001:{self.MATERIAL}:line:{purchase_items_by_part['袖口']['line_id']}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-PART-001:cuff",
            qty="5",
            purchase_order_item_id=int(purchase_items_by_part["袖口"]["line_id"]),
        )

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword=PO-A6-PART-001&page=1&page_size=100",
            headers=self._headers("req-a6-part-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 2)
        self.assertEqual({row["bom_part"] for row in completed_rows}, {"门襟", "袖口"})
        self.assertEqual(sum(Decimal(str(row["received_qty"])) for row in completed_rows), Decimal("15.000000"))
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        completed_by_part = {str(row["bom_part"]): row for row in completed_rows}

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-part-ledger"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_items = ledger.json()["data"]["items"]
        self.assertEqual(ledger.json()["data"]["total"], 2)
        ledger_by_part = {str(row["bom_part"]): row for row in ledger_items}
        self.assertEqual(set(ledger_by_part), {"门襟", "袖口"})
        self.assertEqual(ledger_by_part["门襟"]["purchase_requirement_id"], completed_by_part["门襟"]["id"])
        self.assertEqual(ledger_by_part["袖口"]["purchase_requirement_id"], completed_by_part["袖口"]["id"])
        self.assertEqual(ledger_by_part["门襟"]["sales_order_item"], sales_order_item)
        self.assertEqual(ledger_by_part["袖口"]["sales_order_item"], sales_order_item)
        self.assertEqual(ledger_by_part["门襟"]["bom_color"], "黑")
        self.assertEqual(ledger_by_part["袖口"]["bom_color"], "黑")
        self.assertEqual(ledger_by_part["门襟"]["bom_size"], "M")
        self.assertEqual(ledger_by_part["袖口"]["bom_size"], "M")
        self.assertEqual(Decimal(str(ledger_by_part["门襟"]["actual_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(ledger_by_part["袖口"]["actual_qty"])), Decimal("5.000000"))
        self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in ledger_items), Decimal("15.000000"))

        ready_detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers("req-a6-part-ready"))
        self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
        ready_plan = ready_detail.json()["data"]
        self.assertTrue(ready_plan["material_ready"])
        self.assertEqual(ready_plan["purchase_status"], "ready")
        self.assertEqual(ready_plan["pending_requirement_count"], 0)
        self.assertEqual(Decimal(str(ready_plan["required_qty_total"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(ready_plan["available_qty_total"])), Decimal("15.000000"))
        self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

        with self.SessionLocal() as session:
            snapshots = session.query(LyProductionPlanMaterial).filter_by(plan_id=plan_id).all()
            requirements_by_part = {
                str(row.bom_part): row
                for row in session.query(LyMaterialPurchaseRequirement).filter_by(plan_id=plan_id).all()
            }
            persisted_ledger_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter_by(company=self.COMPANY, warehouse=self.WAREHOUSE, item_code=self.MATERIAL)
                .all()
            )
        self.assertEqual({str(row.bom_part) for row in snapshots}, {"门襟", "袖口"})
        self.assertEqual(set(requirements_by_part), {"门襟", "袖口"})
        self.assertEqual(Decimal(str(requirements_by_part["门襟"].received_qty)), Decimal("10.000000"))
        self.assertEqual(Decimal(str(requirements_by_part["袖口"].received_qty)), Decimal("5.000000"))
        self.assertEqual(len(persisted_ledger_rows), 2)
        persisted_ledger_by_part = {str(row.bom_part): row for row in persisted_ledger_rows}
        self.assertEqual(set(persisted_ledger_by_part), {"门襟", "袖口"})
        self.assertEqual(persisted_ledger_by_part["门襟"].purchase_requirement_id, requirements_by_part["门襟"].id)
        self.assertEqual(persisted_ledger_by_part["袖口"].purchase_requirement_id, requirements_by_part["袖口"].id)
        self.assertEqual(Decimal(str(persisted_ledger_by_part["门襟"].actual_qty)), Decimal("10.000000"))
        self.assertEqual(Decimal(str(persisted_ledger_by_part["袖口"].actual_qty)), Decimal("5.000000"))

    def test_multi_sku_color_size_requirements_po_receipt_stock_summary_and_recheck_ready(self) -> None:
        with self.SessionLocal() as session:
            style = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            style.colors = [
                {"ys_color_code": "BLK", "ys_color_name": "黑"},
                {"ys_color_code": "WHT", "ys_color_name": "白"},
            ]
            style.sizes = [
                {"ys_size_code": "S", "ys_size_name": "S"},
                {"ys_size_code": "M", "ys_size_name": "M"},
            ]
            for code, name in [
                ("FAB-A6-BLK-S", "A6 黑色 S 码配布"),
                ("FAB-A6-BLK-M", "A6 黑色 M 码配布"),
                ("FAB-A6-WHT-M", "A6 白色 M 码配布"),
            ]:
                self._seed_master_data_record(session=session, entity_type="material", code=code, name=name)
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6012,
                        bom_id=601,
                        material_item_code="FAB-A6-BLK-S",
                        color="黑",
                        size="S",
                        part="面料主身",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0.1"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:8",
                    ),
                    LyApparelBomItem(
                        id=6013,
                        bom_id=601,
                        material_item_code="FAB-A6-BLK-M",
                        color="黑",
                        size="M",
                        part="门襟拉链",
                        qty_per_piece=Decimal("2"),
                        loss_rate=Decimal("0.2"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:9",
                    ),
                    LyApparelBomItem(
                        id=6014,
                        bom_id=601,
                        material_item_code="FAB-A6-WHT-M",
                        color="白",
                        size="M",
                        qty_per_piece=Decimal("99"),
                        loss_rate=Decimal("0"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:99",
                    ),
                ]
            )
            session.commit()

        sales_order_no = "SO-A6-MULTI-SKU-001"
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-multi-sku-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": sales_order_no,
                "source_order_ref": sales_order_no,
                "idempotency_key": "idem-so-a6-multi-sku-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "黑",
                        "size": "S",
                        "qty": 5,
                        "rate": 80,
                        "uom": "件",
                    },
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "黑",
                        "size": "M",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    },
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 3,
                        "rate": 80,
                        "uom": "件",
                    },
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no=sales_order_no, suffix="multi-sku")

        detail = self.client.get(f"/api/sales-inventory/sales-orders/{sales_order_no}", headers=self._headers("req-a6-multi-sku-detail"))
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_items = detail.json()["data"]["items"]
        sales_item_by_color_size = {(row["color"], row["size"]): row["name"] for row in sales_items}
        self.assertEqual(set(sales_item_by_color_size), {("黑", "S"), ("黑", "M"), ("白", "M")})

        def create_checked_plan(*, color: str, size: str, planned_qty: str, sequence: str) -> int:
            sales_order_item = sales_item_by_color_size[(color, size)]
            plan = self.client.post(
                "/api/production/plans",
                headers=self._headers(f"req-a6-multi-sku-plan-{sequence}"),
                json={
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "planned_qty": planned_qty,
                    "planned_start_date": "2026-06-18",
                    "operation": "create_plan",
                    "idempotency_key": f"idem-plan-a6-multi-sku-{sequence}",
                    "company": self.COMPANY,
                },
            )
            self.assertEqual(plan.status_code, 200, plan.text)
            plan_id = int(plan.json()["data"]["plan_id"])
            scenario = f"Z003-PROD-PLAN-DETAIL-20260618-46{sequence}"
            request_id = f"req-{scenario}"
            material_check = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers={**self._headers(request_id), "X-Request-ID": request_id},
                json={
                    "warehouse": self.WAREHOUSE,
                    "operation": "material_check",
                    "idempotency_key": f"{scenario}:idem-a6-multi-sku-material-check",
                    "scenario_tag": scenario,
                    "plan_id": plan_id,
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "request_id": request_id,
                },
            )
            self.assertEqual(material_check.status_code, 200, material_check.text)
            return plan_id

        plan_black_s = create_checked_plan(color="黑", size="S", planned_qty="5", sequence="1")
        plan_black_m = create_checked_plan(color="黑", size="M", planned_qty="10", sequence="2")
        plan_white_m = create_checked_plan(color="白", size="M", planned_qty="3", sequence="5")

        tracking = self.client.get(
            f"/api/production/plans?sales_order={sales_order_no}&page=1&page_size=20",
            headers=self._headers("req-a6-multi-sku-tracking"),
        )
        self.assertEqual(tracking.status_code, 200, tracking.text)
        tracking_rows = tracking.json()["data"]["items"]
        self.assertEqual(len(tracking_rows), 3)
        tracking_by_color_size = {(row["color"], row["size"]): row for row in tracking_rows}
        self.assertEqual(set(tracking_by_color_size), {("黑", "S"), ("黑", "M"), ("白", "M")})
        self.assertEqual(tracking_by_color_size[("黑", "S")]["sales_order_item"], sales_item_by_color_size[("黑", "S")])
        self.assertEqual(tracking_by_color_size[("黑", "M")]["sales_order_item"], sales_item_by_color_size[("黑", "M")])
        self.assertEqual(tracking_by_color_size[("白", "M")]["sales_order_item"], sales_item_by_color_size[("白", "M")])
        self.assertEqual(Decimal(str(tracking_by_color_size[("黑", "S")]["planned_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("黑", "M")]["planned_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("白", "M")]["planned_qty"])), Decimal("3.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("黑", "S")]["sales_order_item_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("黑", "M")]["sales_order_item_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("白", "M")]["sales_order_item_qty"])), Decimal("3.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-multi-sku-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 6)
        self.assertEqual({row["sales_order_item"] for row in requirement_rows}, set(sales_item_by_color_size.values()))
        dimensions_by_material: dict[str, set[tuple[object, object, object, str]]] = {}
        for row in requirement_rows:
            dimensions_by_material.setdefault(row["material_item_code"], set()).add(
                (row["bom_color"], row["bom_size"], row["bom_part"], row["sales_order_item"])
            )
        self.assertEqual(
            dimensions_by_material,
            {
                self.MATERIAL: {
                    (None, None, None, sales_item_by_color_size[("黑", "S")]),
                    (None, None, None, sales_item_by_color_size[("黑", "M")]),
                    (None, None, None, sales_item_by_color_size[("白", "M")]),
                },
                "FAB-A6-BLK-S": {("黑", "S", "面料主身", sales_item_by_color_size[("黑", "S")])},
                "FAB-A6-BLK-M": {("黑", "M", "门襟拉链", sales_item_by_color_size[("黑", "M")])},
                "FAB-A6-WHT-M": {("白", "M", None, sales_item_by_color_size[("白", "M")])},
            },
        )

        expected_qty_by_material = {
            self.MATERIAL: Decimal("37.800000"),
            "FAB-A6-BLK-S": Decimal("5.500000"),
            "FAB-A6-BLK-M": Decimal("24.000000"),
            "FAB-A6-WHT-M": Decimal("297.000000"),
        }
        net_required_by_material: dict[str, Decimal] = {}
        expected_receipt_contexts_by_material: dict[str, list[dict[str, object]]] = {}
        for row in requirement_rows:
            material_code = row["material_item_code"]
            net_required_by_material[material_code] = net_required_by_material.get(material_code, Decimal("0")) + Decimal(str(row["net_required_qty"]))
            expected_receipt_contexts_by_material.setdefault(material_code, []).append(
                {
                    "purchase_requirement_id": int(row["id"]),
                    "sales_order_item": row["sales_order_item"],
                    "bom_color": row["bom_color"],
                    "bom_size": row["bom_size"],
                    "bom_part": row["bom_part"],
                    "qty": Decimal(str(row["net_required_qty"])),
                }
            )
            self.assertEqual(row["status"], "pending")
            self.assertGreater(Decimal(str(row["net_required_qty"])), Decimal("0"))
        self.assertEqual(net_required_by_material, expected_qty_by_material)

        grouped_requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&group_by_material=true&page=1&page_size=100",
            headers=self._headers("req-a6-multi-sku-grouped-requirements"),
        )
        self.assertEqual(grouped_requirements.status_code, 200, grouped_requirements.text)
        grouped_rows = grouped_requirements.json()["data"]["items"]
        self.assertEqual(grouped_requirements.json()["data"]["total"], 4)
        grouped_by_material = {row["material_item_code"]: row for row in grouped_rows}
        self.assertEqual(set(grouped_by_material), set(expected_qty_by_material))
        self.assertTrue(grouped_by_material[self.MATERIAL]["is_grouped"])
        self.assertEqual(grouped_by_material[self.MATERIAL]["requirement_count"], 3)
        self.assertEqual(
            set(grouped_by_material[self.MATERIAL]["requirement_ids"]),
            {int(row["id"]) for row in requirement_rows if row["material_item_code"] == self.MATERIAL},
        )
        self.assertEqual(Decimal(str(grouped_by_material[self.MATERIAL]["net_required_qty"])), Decimal("37.800000"))
        self.assertIn("SO-A6-MULTI-SKU-001", grouped_by_material[self.MATERIAL]["sales_order"])

        grouped_requirement_ids = [
            requirement_id
            for row in grouped_rows
            for requirement_id in (row["requirement_ids"] or [row["id"]])
        ]

        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-multi-sku-req-to-po"),
            json=self._from_requirements_payload(
                requirement_ids=[int(row_id) for row_id in grouped_requirement_ids],
                idempotency_key="idem-a6-multi-sku-req-to-po",
                purchase_no="PO-A6-MULTI-SKU-001",
                supplier_name="SUP-A6",
            ),
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_data = create_po.json()["data"]
        purchase_order = purchase_data["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(purchase_no, "PO-A6-MULTI-SKU-001")
        self.assertEqual({row["status"] for row in purchase_data["requirements"]}, {"purchased"})
        purchase_qty_by_material = {
            row["material_item_code"]: Decimal(str(row["qty"]))
            for row in purchase_order["items"]
        }
        self.assertEqual(purchase_qty_by_material, expected_qty_by_material)

        for receipt_index, (material_code, expected_qty) in enumerate(expected_qty_by_material.items(), start=1):
            receipt = self._create_stock_receipt(
                source_type="material_purchase_order",
                source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}:{material_code}",
                idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}:{material_code}",
                qty=str(expected_qty),
                item_code=material_code,
            )
            self.assertEqual(receipt["source_type"], "material_purchase_order")

            ledger = self.client.get(
                f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={material_code}",
                headers=self._headers(f"req-a6-multi-sku-ledger-{material_code}"),
            )
            summary = self.client.get(
                f"/api/warehouse/stock-summary?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={material_code}",
                headers=self._headers(f"req-a6-multi-sku-summary-{material_code}"),
            )
            self.assertEqual(ledger.status_code, 200, ledger.text)
            self.assertEqual(summary.status_code, 200, summary.text)
            ledger_items = ledger.json()["data"]["items"]
            summary_items = summary.json()["data"]["items"]
            expected_contexts = expected_receipt_contexts_by_material[material_code]
            self.assertEqual(ledger.json()["data"]["total"], len(expected_contexts))
            self.assertEqual(len(summary_items), len(expected_contexts))
            self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in ledger_items), expected_qty)
            self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in summary_items), expected_qty)

            ledger_by_requirement = {int(row["purchase_requirement_id"]): row for row in ledger_items}
            summary_by_requirement = {int(row["purchase_requirement_id"]): row for row in summary_items}
            self.assertEqual(set(ledger_by_requirement), {int(row["purchase_requirement_id"]) for row in expected_contexts})
            self.assertEqual(set(summary_by_requirement), {int(row["purchase_requirement_id"]) for row in expected_contexts})
            for expected_context in expected_contexts:
                requirement_id = int(expected_context["purchase_requirement_id"])
                ledger_row = ledger_by_requirement[requirement_id]
                summary_row = summary_by_requirement[requirement_id]
                self.assertEqual(ledger_row["sales_order_item"], expected_context["sales_order_item"])
                self.assertEqual(summary_row["sales_order_item"], expected_context["sales_order_item"])
                self.assertEqual(ledger_row["bom_color"], expected_context["bom_color"])
                self.assertEqual(ledger_row["bom_size"], expected_context["bom_size"])
                self.assertEqual(ledger_row["bom_part"], expected_context["bom_part"])
                self.assertEqual(summary_row["bom_color"], expected_context["bom_color"])
                self.assertEqual(summary_row["bom_size"], expected_context["bom_size"])
                self.assertEqual(summary_row["bom_part"], expected_context["bom_part"])
                self.assertEqual(Decimal(str(ledger_row["actual_qty"])), expected_context["qty"])
                self.assertEqual(Decimal(str(ledger_row["qty_after_transaction"])), expected_context["qty"])
                self.assertEqual(Decimal(str(summary_row["actual_qty"])), expected_context["qty"])

            with self.SessionLocal() as session:
                persisted_ledger_rows = (
                    session.query(LyWarehouseStockLedgerEntry)
                    .filter_by(company=self.COMPANY, warehouse=self.WAREHOUSE, item_code=material_code)
                    .all()
                )
            self.assertEqual(len(persisted_ledger_rows), len(expected_contexts))
            persisted_by_requirement = {int(row.purchase_requirement_id): row for row in persisted_ledger_rows}
            self.assertEqual(set(persisted_by_requirement), {int(row["purchase_requirement_id"]) for row in expected_contexts})
            self.assertEqual(sum(Decimal(str(row.actual_qty)) for row in persisted_ledger_rows), expected_qty)
            for expected_context in expected_contexts:
                requirement_id = int(expected_context["purchase_requirement_id"])
                persisted_row = persisted_by_requirement[requirement_id]
                self.assertEqual(str(persisted_row.sales_order_item), expected_context["sales_order_item"])
                self.assertEqual(persisted_row.bom_color, expected_context["bom_color"])
                self.assertEqual(persisted_row.bom_size, expected_context["bom_size"])
                self.assertEqual(persisted_row.bom_part, expected_context["bom_part"])
                self.assertEqual(Decimal(str(persisted_row.actual_qty)), expected_context["qty"])
                self.assertEqual(str(persisted_row.voucher_type), "Stock Entry Draft/Material Receipt")
                self.assertEqual(persisted_row.posting_date.isoformat(), self.BUSINESS_DATE)
            self._assert_balanced_inventory_reconciliation(
                item_code=material_code,
                expected_qty=expected_qty,
                suffix=str(receipt_index),
            )

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}&page=1&page_size=100",
            headers=self._headers("req-a6-multi-sku-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 6)
        completed_dimensions_by_material: dict[str, set[tuple[object, object, object, str]]] = {}
        for row in completed_rows:
            self.assertTrue(row["has_completed"])
            self.assertEqual(row["status"], "completed")
            self.assertEqual(Decimal(str(row["received_qty"])), Decimal(str(row["net_required_qty"])))
            completed_dimensions_by_material.setdefault(row["material_item_code"], set()).add(
                (row["bom_color"], row["bom_size"], row["bom_part"], row["sales_order_item"])
            )
        self.assertEqual(completed_dimensions_by_material, dimensions_by_material)

        for plan_id in [plan_black_s, plan_black_m, plan_white_m]:
            ready_detail = self.client.get(f"/api/production/plans/{plan_id}", headers=self._headers(f"req-a6-multi-sku-ready-{plan_id}"))
            self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
            ready_plan = ready_detail.json()["data"]
            self.assertTrue(ready_plan["material_ready"])
            self.assertEqual(ready_plan["purchase_status"], "ready")
            self.assertEqual(ready_plan["pending_requirement_count"], 0)
            self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

        for plan_id, sales_order_item, sequence in [
            (plan_black_s, sales_item_by_color_size[("黑", "S")], "3"),
            (plan_black_m, sales_item_by_color_size[("黑", "M")], "4"),
            (plan_white_m, sales_item_by_color_size[("白", "M")], "6"),
        ]:
            scenario = f"Z003-PROD-PLAN-DETAIL-20260618-46{sequence}"
            request_id = f"req-{scenario}"
            recheck = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers={**self._headers(request_id), "X-Request-ID": request_id},
                json={
                    "warehouse": self.WAREHOUSE,
                    "operation": "material_check",
                    "idempotency_key": f"{scenario}:idem-a6-multi-sku-recheck",
                    "scenario_tag": scenario,
                    "plan_id": plan_id,
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "request_id": request_id,
                },
            )
            self.assertEqual(recheck.status_code, 200, recheck.text)
            self.assertTrue(all(Decimal(str(item["shortage_qty"])) == Decimal("0.000000") for item in recheck.json()["data"]["items"]))

        pending_after_recheck = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-multi-sku-pending-after-recheck"),
        )
        self.assertEqual(pending_after_recheck.status_code, 200, pending_after_recheck.text)
        self.assertEqual(pending_after_recheck.json()["data"]["total"], 0)

    def test_sales_order_material_check_multi_item_procurement_receipt_recheck_ready(self) -> None:
        with self.SessionLocal() as session:
            style = session.query(LyStyleMaster).filter_by(company=self.COMPANY, ys_style_no=self.STYLE).one()
            style.colors = [
                {"ys_color_code": "BLK", "ys_color_name": "黑"},
                {"ys_color_code": "WHT", "ys_color_name": "白"},
            ]
            style.sizes = [
                {"ys_size_code": "S", "ys_size_name": "S"},
                {"ys_size_code": "M", "ys_size_name": "M"},
            ]
            for code, name in [
                ("FAB-A6-ORDER-BLK-S", "订单级黑色 S 码面料"),
                ("FAB-A6-ORDER-WHT-M", "订单级白色 M 码面料"),
            ]:
                self._seed_master_data_record(session=session, entity_type="material", code=code, name=name)
            session.add_all(
                [
                    LyApparelBomItem(
                        id=6091,
                        bom_id=601,
                        material_item_code="FAB-A6-ORDER-BLK-S",
                        color="黑",
                        size="S",
                        part="面料主身",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0.1"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:8",
                    ),
                    LyApparelBomItem(
                        id=6092,
                        bom_id=601,
                        material_item_code="FAB-A6-ORDER-WHT-M",
                        color="白",
                        size="M",
                        part="面料主身",
                        qty_per_piece=Decimal("2"),
                        loss_rate=Decimal("0.2"),
                        uom="米",
                        remark="供应商:SUP-A6 单价:9",
                    ),
                ]
            )
            session.commit()

        sales_order_no = "SO-A6-ORDER-MAT-001"
        created_order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-order-level-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": sales_order_no,
                "source_order_ref": sales_order_no,
                "idempotency_key": "idem-so-a6-order-mat-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "黑",
                        "size": "S",
                        "qty": 4,
                        "rate": 80,
                        "uom": "件",
                    },
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 6,
                        "rate": 80,
                        "uom": "件",
                    },
                ],
            },
        )
        self.assertEqual(created_order.status_code, 201, created_order.text)
        self._submit_sales_order(
            draft_id=int(created_order.json()["data"]["id"]),
            sales_order_no=sales_order_no,
            suffix="order-level-mat",
        )

        checked = self.client.post(
            f"/api/production/sales-orders/{sales_order_no}/material-check",
            headers={**self._headers("req-a6-order-level-check"), "X-Request-ID": "req-a6-order-level-check"},
            json={
                "warehouse": self.WAREHOUSE,
                "company": self.COMPANY,
                "planned_start_date": "2026-06-18",
                "operation": "sales_order_material_check",
                "idempotency_key": "idem-a6-order-level-material-check",
            },
        )
        self.assertEqual(checked.status_code, 200, checked.text)
        checked_data = checked.json()["data"]
        self.assertEqual(checked_data["plan_count"], 2)
        self.assertEqual(checked_data["created_plan_count"], 2)
        self.assertEqual(checked_data["snapshot_count"], 4)
        self.assertEqual(Decimal(str(checked_data["required_qty_total"])), Decimal("39.800000"))
        self.assertEqual(Decimal(str(checked_data["available_qty_total"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(checked_data["shortage_qty_total"])), Decimal("39.800000"))

        detail = self.client.get(
            f"/api/sales-inventory/sales-orders/{sales_order_no}",
            headers=self._headers("req-a6-order-level-detail"),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_items = detail.json()["data"]["items"]
        sales_item_by_color_size = {(row["color"], row["size"]): row["name"] for row in sales_items}
        self.assertEqual(set(sales_item_by_color_size), {("黑", "S"), ("白", "M")})

        tracking = self.client.get(
            f"/api/production/plans?sales_order={sales_order_no}&page=1&page_size=20",
            headers=self._headers("req-a6-order-level-tracking"),
        )
        self.assertEqual(tracking.status_code, 200, tracking.text)
        tracking_rows = tracking.json()["data"]["items"]
        self.assertEqual(len(tracking_rows), 2)
        tracking_by_color_size = {(row["color"], row["size"]): row for row in tracking_rows}
        self.assertEqual(set(tracking_by_color_size), {("黑", "S"), ("白", "M")})
        self.assertEqual(tracking_by_color_size[("黑", "S")]["sales_order_item"], sales_item_by_color_size[("黑", "S")])
        self.assertEqual(tracking_by_color_size[("白", "M")]["sales_order_item"], sales_item_by_color_size[("白", "M")])
        self.assertEqual(Decimal(str(tracking_by_color_size[("黑", "S")]["planned_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(tracking_by_color_size[("白", "M")]["planned_qty"])), Decimal("6.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-order-level-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 4)
        self.assertEqual({row["sales_order_item"] for row in requirement_rows}, set(sales_item_by_color_size.values()))
        net_required_by_material: dict[str, Decimal] = {}
        dimensions_by_material: dict[str, set[tuple[object, object, object, str]]] = {}
        expected_receipt_contexts_by_material: dict[str, list[dict[str, object]]] = {}
        for row in requirement_rows:
            material_code = row["material_item_code"]
            net_required_by_material[material_code] = net_required_by_material.get(material_code, Decimal("0")) + Decimal(str(row["net_required_qty"]))
            dimensions_by_material.setdefault(material_code, set()).add(
                (row["bom_color"], row["bom_size"], row["bom_part"], row["sales_order_item"])
            )
            expected_receipt_contexts_by_material.setdefault(material_code, []).append(
                {
                    "purchase_requirement_id": int(row["id"]),
                    "sales_order_item": row["sales_order_item"],
                    "bom_color": row["bom_color"],
                    "bom_size": row["bom_size"],
                    "bom_part": row["bom_part"],
                    "qty": Decimal(str(row["net_required_qty"])),
                }
            )
        expected_qty_by_material = {
            self.MATERIAL: Decimal("21.000000"),
            "FAB-A6-ORDER-BLK-S": Decimal("4.400000"),
            "FAB-A6-ORDER-WHT-M": Decimal("14.400000"),
        }
        self.assertEqual(net_required_by_material, expected_qty_by_material)
        self.assertEqual(
            dimensions_by_material,
            {
                self.MATERIAL: {
                    (None, None, None, sales_item_by_color_size[("黑", "S")]),
                    (None, None, None, sales_item_by_color_size[("白", "M")]),
                },
                "FAB-A6-ORDER-BLK-S": {("黑", "S", "面料主身", sales_item_by_color_size[("黑", "S")])},
                "FAB-A6-ORDER-WHT-M": {("白", "M", "面料主身", sales_item_by_color_size[("白", "M")])},
            },
        )

        grouped_requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&group_by_material=true&page=1&page_size=100",
            headers=self._headers("req-a6-order-level-grouped-requirements"),
        )
        self.assertEqual(grouped_requirements.status_code, 200, grouped_requirements.text)
        grouped_rows = grouped_requirements.json()["data"]["items"]
        self.assertEqual(grouped_requirements.json()["data"]["total"], 3)
        grouped_requirement_ids = [
            requirement_id
            for row in grouped_rows
            for requirement_id in (row["requirement_ids"] or [row["id"]])
        ]
        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-order-level-req-to-po"),
            json=self._from_requirements_payload(
                requirement_ids=[int(row_id) for row_id in grouped_requirement_ids],
                idempotency_key="idem-a6-order-level-req-to-po",
                purchase_no="PO-A6-ORDER-MAT-001",
                supplier_name="SUP-A6",
            ),
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_order = create_po.json()["data"]["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(
            {row["material_item_code"]: Decimal(str(row["qty"])) for row in purchase_order["items"]},
            expected_qty_by_material,
        )

        for receipt_index, (material_code, expected_qty) in enumerate(expected_qty_by_material.items(), start=1):
            receipt = self._create_stock_receipt(
                source_type="material_purchase_order",
                source_id=f"{self.WAREHOUSE_SCENARIO}:order-level:{purchase_no}:{material_code}",
                idempotency_key=f"{self.WAREHOUSE_SCENARIO}:order-level-receipt:{purchase_no}:{material_code}",
                qty=str(expected_qty),
                item_code=material_code,
            )
            self.assertEqual(receipt["source_type"], "material_purchase_order")

            ledger = self.client.get(
                f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={material_code}",
                headers=self._headers(f"req-a6-order-level-ledger-{material_code}"),
            )
            summary = self.client.get(
                f"/api/warehouse/stock-summary?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={material_code}",
                headers=self._headers(f"req-a6-order-level-summary-{material_code}"),
            )
            self.assertEqual(ledger.status_code, 200, ledger.text)
            self.assertEqual(summary.status_code, 200, summary.text)
            ledger_items = ledger.json()["data"]["items"]
            summary_items = summary.json()["data"]["items"]
            expected_contexts = expected_receipt_contexts_by_material[material_code]
            self.assertEqual(ledger.json()["data"]["total"], len(expected_contexts))
            self.assertEqual(len(summary_items), len(expected_contexts))
            self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in ledger_items), expected_qty)
            self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in summary_items), expected_qty)
            ledger_by_requirement = {int(row["purchase_requirement_id"]): row for row in ledger_items}
            summary_by_requirement = {int(row["purchase_requirement_id"]): row for row in summary_items}
            self.assertEqual(set(ledger_by_requirement), {int(row["purchase_requirement_id"]) for row in expected_contexts})
            self.assertEqual(set(summary_by_requirement), {int(row["purchase_requirement_id"]) for row in expected_contexts})
            for expected_context in expected_contexts:
                requirement_id = int(expected_context["purchase_requirement_id"])
                ledger_row = ledger_by_requirement[requirement_id]
                summary_row = summary_by_requirement[requirement_id]
                self.assertEqual(ledger_row["sales_order_item"], expected_context["sales_order_item"])
                self.assertEqual(summary_row["sales_order_item"], expected_context["sales_order_item"])
                self.assertEqual(ledger_row["bom_color"], expected_context["bom_color"])
                self.assertEqual(ledger_row["bom_size"], expected_context["bom_size"])
                self.assertEqual(ledger_row["bom_part"], expected_context["bom_part"])
                self.assertEqual(summary_row["bom_color"], expected_context["bom_color"])
                self.assertEqual(summary_row["bom_size"], expected_context["bom_size"])
                self.assertEqual(summary_row["bom_part"], expected_context["bom_part"])
                self.assertEqual(Decimal(str(ledger_row["actual_qty"])), expected_context["qty"])
                self.assertEqual(Decimal(str(ledger_row["qty_after_transaction"])), expected_context["qty"])
                self.assertEqual(Decimal(str(summary_row["actual_qty"])), expected_context["qty"])
            self._assert_balanced_inventory_reconciliation(
                item_code=material_code,
                expected_qty=expected_qty,
                suffix=f"order-level-{receipt_index}",
            )

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}&page=1&page_size=100",
            headers=self._headers("req-a6-order-level-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 4)
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        self.assertEqual(
            {row["material_item_code"]: row["status"] for row in completed_rows},
            {
                self.MATERIAL: "completed",
                "FAB-A6-ORDER-BLK-S": "completed",
                "FAB-A6-ORDER-WHT-M": "completed",
            },
        )

        for row in tracking_rows:
            ready_detail = self.client.get(
                f"/api/production/plans/{row['id']}",
                headers=self._headers(f"req-a6-order-level-ready-{row['id']}"),
            )
            self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
            ready_plan = ready_detail.json()["data"]
            self.assertTrue(ready_plan["material_ready"])
            self.assertEqual(ready_plan["purchase_status"], "ready")
            self.assertEqual(ready_plan["pending_requirement_count"], 0)
            self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

        recheck = self.client.post(
            f"/api/production/sales-orders/{sales_order_no}/material-check",
            headers={**self._headers("req-a6-order-level-recheck"), "X-Request-ID": "req-a6-order-level-recheck"},
            json={
                "warehouse": self.WAREHOUSE,
                "company": self.COMPANY,
                "planned_start_date": "2026-06-18",
                "operation": "sales_order_material_check",
                "idempotency_key": "idem-a6-order-level-material-recheck",
            },
        )
        self.assertEqual(recheck.status_code, 200, recheck.text)
        recheck_data = recheck.json()["data"]
        self.assertEqual(recheck_data["plan_count"], 2)
        self.assertEqual(recheck_data["created_plan_count"], 0)
        self.assertEqual(Decimal(str(recheck_data["shortage_qty_total"])), Decimal("0.000000"))
        pending_after_recheck = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={sales_order_no}&page=1&page_size=100",
            headers=self._headers("req-a6-order-level-pending-after-recheck"),
        )
        self.assertEqual(pending_after_recheck.status_code, 200, pending_after_recheck.text)
        self.assertEqual(pending_after_recheck.json()["data"]["total"], 0)

    def test_material_check_reserves_stock_budget_across_open_plans(self) -> None:
        self._create_stock_receipt(
            source_type="manual",
            source_id=f"{self.WAREHOUSE_SCENARIO}:opening:cross-plan:{self.MATERIAL}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:opening-cross-plan-idem",
            qty="30",
        )
        with self.SessionLocal() as session:
            bom_item = session.query(LyApparelBomItem).filter(LyApparelBomItem.id == 6011).one()
            bom_item.loss_rate = Decimal("0")
            session.commit()

        def create_plan(*, sequence: str) -> tuple[str, str, int]:
            sales_order_no = f"SO-A6-CROSS-PLAN-{sequence}"
            order = self.client.post(
                "/api/sales-inventory/sales-orders/drafts",
                headers=self._headers(f"req-a6-cross-plan-{sequence}-order"),
                json={
                    "company": self.COMPANY,
                    "customer": "CUST-A6",
                    "operation": "create_draft",
                    "sales_order_no": sales_order_no,
                    "source_order_ref": sales_order_no,
                    "idempotency_key": f"idem-so-a6-cross-plan-{sequence}",
                    "transaction_date": "2026-06-17",
                    "delivery_date": "2026-06-30",
                    "currency": "CNY",
                    "items": [
                        {
                            "style_master_id": self._style_id(),
                            "item_code": self.STYLE,
                            "item_name": "A6 Tee",
                            "color": "白",
                            "size": "M",
                            "qty": 10,
                            "rate": 80,
                            "uom": "件",
                        }
                    ],
                },
            )
            self.assertEqual(order.status_code, 201, order.text)
            self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no=sales_order_no, suffix=f"cross-plan-{sequence}")
            detail = self.client.get(f"/api/sales-inventory/sales-orders/{sales_order_no}", headers=self._headers())
            sales_order_item = detail.json()["data"]["items"][0]["name"]
            plan = self.client.post(
                "/api/production/plans",
                headers=self._headers(f"req-a6-cross-plan-{sequence}-plan"),
                json={
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "planned_qty": 10,
                    "planned_start_date": "2026-06-18",
                    "operation": "create_plan",
                    "idempotency_key": f"idem-plan-a6-cross-plan-{sequence}",
                    "company": self.COMPANY,
                },
            )
            self.assertEqual(plan.status_code, 200, plan.text)
            return sales_order_no, sales_order_item, int(plan.json()["data"]["plan_id"])

        order_a, item_a, plan_a = create_plan(sequence="A")
        scenario_a = "Z003-PROD-PLAN-DETAIL-20260618-404"
        request_id_a = f"req-{scenario_a}"
        material_check_a = self.client.post(
            f"/api/production/plans/{plan_a}/material-check",
            headers={**self._headers(request_id_a), "X-Request-ID": request_id_a},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{scenario_a}:idem-a6-cross-plan-a-material-check",
                "scenario_tag": scenario_a,
                "plan_id": plan_a,
                "sales_order": order_a,
                "sales_order_item": item_a,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id_a,
            },
        )
        self.assertEqual(material_check_a.status_code, 200, material_check_a.text)
        row_a = material_check_a.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(row_a["required_qty"])), Decimal("20.000000"))
        self.assertEqual(Decimal(str(row_a["available_qty"])), Decimal("20.000000"))
        self.assertEqual(Decimal(str(row_a["shortage_qty"])), Decimal("0.000000"))

        order_b, item_b, plan_b = create_plan(sequence="B")
        scenario_b = "Z003-PROD-PLAN-DETAIL-20260618-405"
        request_id_b = f"req-{scenario_b}"
        material_check_b = self.client.post(
            f"/api/production/plans/{plan_b}/material-check",
            headers={**self._headers(request_id_b), "X-Request-ID": request_id_b},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{scenario_b}:idem-a6-cross-plan-b-material-check",
                "scenario_tag": scenario_b,
                "plan_id": plan_b,
                "sales_order": order_b,
                "sales_order_item": item_b,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id_b,
            },
        )
        self.assertEqual(material_check_b.status_code, 200, material_check_b.text)
        row_b = material_check_b.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(row_b["required_qty"])), Decimal("20.000000"))
        self.assertEqual(Decimal(str(row_b["available_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(row_b["shortage_qty"])), Decimal("10.000000"))

        plan_detail = self.client.get(f"/api/production/plans/{plan_b}", headers=self._headers("req-a6-cross-plan-detail"))
        self.assertEqual(plan_detail.status_code, 200, plan_detail.text)
        plan_data = plan_detail.json()["data"]
        self.assertEqual(plan_data["purchase_status"], "pending_purchase")
        self.assertEqual(Decimal(str(plan_data["available_qty_total"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(plan_data["shortage_qty_total"])), Decimal("10.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword={order_b}",
            headers=self._headers("req-a6-cross-plan-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        self.assertEqual(requirement_rows[0]["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(requirement_rows[0]["available_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(requirement_rows[0]["net_required_qty"])), Decimal("10.000000"))

    def test_material_check_shares_stock_budget_once_across_same_material_bom_rows(self) -> None:
        self._create_stock_receipt(
            source_type="manual",
            source_id=f"{self.WAREHOUSE_SCENARIO}:opening:stock-budget:{self.MATERIAL}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:opening-stock-budget-idem",
            qty="23",
        )
        with self.SessionLocal() as session:
            session.add(
                LyApparelBomItem(
                    id=6014,
                    bom_id=601,
                    material_item_code=self.MATERIAL,
                    qty_per_piece=Decimal("0.5"),
                    loss_rate=Decimal("0"),
                    uom="米",
                    remark="供应商:SUP-A6 单价:12.5",
                )
            )
            session.commit()

        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers("req-a6-stock-budget-order"),
            json={
                "company": self.COMPANY,
                "customer": "CUST-A6",
                "operation": "create_draft",
                "sales_order_no": "SO-A6-STOCK-BUDGET-001",
                "source_order_ref": "SO-A6-STOCK-BUDGET-001",
                "idempotency_key": "idem-so-a6-stock-budget-001",
                "transaction_date": "2026-06-17",
                "delivery_date": "2026-06-30",
                "currency": "CNY",
                "items": [
                    {
                        "style_master_id": self._style_id(),
                        "item_code": self.STYLE,
                        "item_name": "A6 Tee",
                        "color": "白",
                        "size": "M",
                        "qty": 10,
                        "rate": 80,
                        "uom": "件",
                    }
                ],
            },
        )
        self.assertEqual(order.status_code, 201, order.text)
        self._submit_sales_order(draft_id=int(order.json()["data"]["id"]), sales_order_no="SO-A6-STOCK-BUDGET-001", suffix="stock-budget")
        detail = self.client.get("/api/sales-inventory/sales-orders/SO-A6-STOCK-BUDGET-001", headers=self._headers())
        sales_order_item = detail.json()["data"]["items"][0]["name"]

        plan = self.client.post(
            "/api/production/plans",
            headers=self._headers("req-a6-stock-budget-plan"),
            json={
                "sales_order": "SO-A6-STOCK-BUDGET-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "planned_qty": 10,
                "planned_start_date": "2026-06-18",
                "operation": "create_plan",
                "idempotency_key": "idem-plan-a6-stock-budget-001",
                "company": self.COMPANY,
            },
        )
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = int(plan.json()["data"]["plan_id"])
        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-403"
        request_id = f"req-{material_check_scenario}"
        material_check = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers={**self._headers(request_id), "X-Request-ID": request_id},
            json={
                "warehouse": self.WAREHOUSE,
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}:idem-a6-stock-budget-material-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": "SO-A6-STOCK-BUDGET-001",
                "sales_order_item": sales_order_item,
                "item_code": self.STYLE,
                "bom_id": 601,
                "request_id": request_id,
            },
        )
        self.assertEqual(material_check.status_code, 200, material_check.text)
        items = material_check.json()["data"]["items"]
        self.assertEqual([item["material_item_code"] for item in items], [self.MATERIAL, self.MATERIAL])
        self.assertEqual(Decimal(str(items[0]["required_qty"])), Decimal("21.000000"))
        self.assertEqual(Decimal(str(items[0]["available_qty"])), Decimal("21.000000"))
        self.assertEqual(Decimal(str(items[0]["shortage_qty"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(items[1]["required_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(items[1]["available_qty"])), Decimal("2.000000"))
        self.assertEqual(Decimal(str(items[1]["shortage_qty"])), Decimal("3.000000"))

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=SO-A6-STOCK-BUDGET-001",
            headers=self._headers("req-a6-stock-budget-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 1)
        self.assertEqual(requirement_rows[0]["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(requirement_rows[0]["net_required_qty"])), Decimal("3.000000"))

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

    def test_sync_requirements_preserves_sample_bom_dimensions_without_bom_item_id(self) -> None:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                id=9602,
                plan_no="PP-A6-DIM-001",
                company=self.COMPANY,
                sales_order="SO-A6-DIM",
                sales_order_item="SO-A6-DIM-ITEM",
                customer="CUST-A6",
                item_code=self.STYLE,
                bom_id=601,
                bom_version="SAMPLE",
                planned_qty=Decimal("10"),
                status="material_checked",
                idempotency_key="idem-a6-dim-plan",
                request_hash="hash-a6-dim-plan",
                created_by="seed",
            )
            session.add(plan)
            session.add_all(
                [
                    LyProductionPlanMaterial(
                        plan_id=9602,
                        bom_item_id=None,
                        bom_color="黑",
                        bom_size="M",
                        bom_part="门襟",
                        material_item_code=self.MATERIAL,
                        warehouse=self.WAREHOUSE,
                        uom="米",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        required_qty=Decimal("10"),
                        available_qty=Decimal("0"),
                        shortage_qty=Decimal("10"),
                    ),
                    LyProductionPlanMaterial(
                        plan_id=9602,
                        bom_item_id=None,
                        bom_color="黑",
                        bom_size="M",
                        bom_part="袖口",
                        material_item_code=self.MATERIAL,
                        warehouse=self.WAREHOUSE,
                        uom="米",
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        required_qty=Decimal("5"),
                        available_qty=Decimal("0"),
                        shortage_qty=Decimal("5"),
                    ),
                ]
            )
            session.commit()

            synced = MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            self.assertEqual(len(synced), 2)
            snapshots = {
                str(row.bom_part): row
                for row in session.query(LyProductionPlanMaterial).filter_by(plan_id=9602).all()
            }
            snapshots["袖口"].required_qty = Decimal("7")
            snapshots["袖口"].shortage_qty = Decimal("7")
            snapshots["门襟"].required_qty = Decimal("13")
            snapshots["门襟"].shortage_qty = Decimal("13")
            session.commit()

            resynced = MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            requirement_rows = (
                session.query(LyMaterialPurchaseRequirement)
                .filter_by(plan_id=9602)
                .order_by(LyMaterialPurchaseRequirement.bom_part.asc())
                .all()
            )

        self.assertEqual(len(resynced), 2)
        self.assertEqual(len(requirement_rows), 2)
        self.assertEqual([str(row.bom_part) for row in requirement_rows], ["袖口", "门襟"])
        self.assertEqual({str(row.bom_color) for row in requirement_rows}, {"黑"})
        self.assertEqual({str(row.bom_size) for row in requirement_rows}, {"M"})
        self.assertEqual([Decimal(str(row.net_required_qty)) for row in requirement_rows], [Decimal("7.000000"), Decimal("13.000000")])

    def test_sync_requirements_carries_bom_specification_without_changing_qty(self) -> None:
        with self.SessionLocal() as session:
            bom_item = session.query(LyApparelBomItem).filter_by(id=6011).one()
            bom_item.spec_by_size = {"S": "4cm", "M": "4.8cm", "L": "5.6cm"}
            plan = LyProductionPlan(
                id=9604,
                plan_no="PP-A6-SPEC-001",
                company=self.COMPANY,
                sales_order="SO-A6-SPEC",
                sales_order_item="SO-A6-SPEC-ITEM",
                customer="CUST-A6",
                item_code=self.STYLE,
                bom_id=601,
                bom_version="V1",
                planned_qty=Decimal("100"),
                status="material_checked",
                idempotency_key="idem-a6-spec-plan",
                request_hash="hash-a6-spec-plan",
                created_by="seed",
            )
            session.add(plan)
            session.add(
                LyProductionPlanMaterial(
                    plan_id=9604,
                    bom_item_id=6011,
                    bom_color="黑",
                    bom_size="M",
                    bom_part="口袋",
                    material_item_code=self.MATERIAL,
                    warehouse=self.WAREHOUSE,
                    uom="条",
                    qty_per_piece=Decimal("2"),
                    loss_rate=Decimal("0"),
                    required_qty=Decimal("200"),
                    available_qty=Decimal("0"),
                    shortage_qty=Decimal("200"),
                )
            )
            session.commit()

            synced = MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(plan_id=9604).one()

        self.assertEqual(len(synced), 1)
        self.assertEqual(synced[0].specification, "4.8cm")
        self.assertEqual(synced[0].spec_by_size, {"S": "4cm", "M": "4.8cm", "L": "5.6cm"})
        self.assertEqual(Decimal(str(synced[0].net_required_qty)), Decimal("200.000000"))
        self.assertEqual(Decimal(str(requirement.net_required_qty)), Decimal("200.000000"))

        listed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&keyword=PP-A6-SPEC-001",
            headers=self._headers("req-a6-spec-list"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        item = listed.json()["data"]["items"][0]
        self.assertEqual(item["specification"], "4.8cm")
        self.assertEqual(item["spec_by_size"], {"S": "4cm", "M": "4.8cm", "L": "5.6cm"})
        self.assertEqual(item["net_required_qty"], "200.000000")

    def test_sync_requirements_deduplicates_identical_bom_dimension_snapshots_without_bom_item_id(self) -> None:
        with self.SessionLocal() as session:
            plan = LyProductionPlan(
                id=9603,
                plan_no="PP-A6-DIM-DUP-001",
                company=self.COMPANY,
                sales_order="SO-A6-DIM-DUP",
                sales_order_item="SO-A6-DIM-DUP-ITEM",
                customer="CUST-A6",
                item_code=self.STYLE,
                bom_id=601,
                bom_version="SAMPLE",
                planned_qty=Decimal("10"),
                status="material_checked",
                idempotency_key="idem-a6-dim-dup-plan",
                request_hash="hash-a6-dim-dup-plan",
                created_by="seed",
            )
            session.add(plan)
            session.add_all(
                [
                    LyProductionPlanMaterial(
                        plan_id=9603,
                        bom_item_id=None,
                        bom_color="黑",
                        bom_size="M",
                        bom_part="门襟",
                        material_item_code=self.MATERIAL,
                        warehouse=self.WAREHOUSE,
                        uom="米",
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        required_qty=Decimal("10"),
                        available_qty=Decimal("0"),
                        shortage_qty=Decimal("10"),
                    ),
                    LyProductionPlanMaterial(
                        plan_id=9603,
                        bom_item_id=None,
                        bom_color="黑",
                        bom_size="M",
                        bom_part="门襟",
                        material_item_code=self.MATERIAL,
                        warehouse=self.WAREHOUSE,
                        uom="米",
                        qty_per_piece=Decimal("1.2"),
                        loss_rate=Decimal("0"),
                        required_qty=Decimal("12"),
                        available_qty=Decimal("0"),
                        shortage_qty=Decimal("12"),
                    ),
                ]
            )
            session.commit()

            synced = MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            requirement_rows = session.query(LyMaterialPurchaseRequirement).filter_by(plan_id=9603).all()
            first_sync_count = len(requirement_rows)
            first_sync_net_required_qty = Decimal(str(requirement_rows[0].net_required_qty))
            snapshots = session.query(LyProductionPlanMaterial).filter_by(plan_id=9603).order_by(LyProductionPlanMaterial.id.asc()).all()
            snapshots[1].required_qty = Decimal("15")
            snapshots[1].shortage_qty = Decimal("15")
            session.commit()

            resynced = MaterialPurchaseService(session).sync_requirements_from_production_plan(plan=plan, actor="a6.procurement.user")
            session.commit()

            requirement_rows_after = session.query(LyMaterialPurchaseRequirement).filter_by(plan_id=9603).all()

        self.assertEqual(len(synced), 1)
        self.assertEqual(first_sync_count, 1)
        self.assertEqual(first_sync_net_required_qty, Decimal("12.000000"))
        self.assertEqual(len(resynced), 1)
        self.assertEqual(len(requirement_rows_after), 1)
        self.assertEqual(Decimal(str(requirement_rows_after[0].net_required_qty)), Decimal("15.000000"))
        self.assertEqual(str(requirement_rows_after[0].bom_color), "黑")
        self.assertEqual(str(requirement_rows_after[0].bom_size), "M")
        self.assertEqual(str(requirement_rows_after[0].bom_part), "门襟")

    def test_from_requirements_group_by_material_merges_cross_order_demands_and_receipts(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-A",
            net_required_qty="5",
            sales_order="SO-A6-GROUP-001",
            sales_order_item="SO-A6-GROUP-001-ITEM",
            bom_color="黑",
            bom_size="S",
            bom_part="门襟",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-B",
            net_required_qty="10",
            sales_order="SO-A6-GROUP-002",
            sales_order_item="SO-A6-GROUP-002-ITEM",
            bom_color="黑",
            bom_size="S",
            bom_part="门襟",
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
        self.assertEqual({row["sales_order_item"] for row in data["requirements"]}, {"SO-A6-GROUP-001-ITEM", "SO-A6-GROUP-002-ITEM"})
        self.assertEqual({row["bom_color"] for row in data["requirements"]}, {"黑"})
        self.assertEqual({row["bom_size"] for row in data["requirements"]}, {"S"})
        self.assertEqual({row["bom_part"] for row in data["requirements"]}, {"门襟"})
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
        self.assertEqual({row["sales_order_item"] for row in completed_rows}, {"SO-A6-GROUP-001-ITEM", "SO-A6-GROUP-002-ITEM"})
        self.assertEqual({row["bom_color"] for row in completed_rows}, {"黑"})
        self.assertEqual({row["bom_size"] for row in completed_rows}, {"S"})
        self.assertEqual({row["bom_part"] for row in completed_rows}, {"门襟"})
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        self.assertEqual(sum(Decimal(str(row["received_qty"])) for row in completed_rows), Decimal("15.000000"))

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-group-material-ledger"),
        )
        summary = self.client.get(
            f"/api/warehouse/stock-summary?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-group-material-summary"),
        )
        receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company={self.COMPANY}&purchase_no={purchase_no}&page=1&page_size=100",
            headers=self._headers("req-a6-group-material-receipts"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(receipts.status_code, 200, receipts.text)
        ledger_rows = ledger.json()["data"]["items"]
        summary_rows = summary.json()["data"]["items"]
        receipt_rows = receipts.json()["data"]["items"]
        self.assertEqual(ledger.json()["data"]["total"], 2)
        self.assertEqual(len(summary_rows), 2)
        self.assertEqual(len(receipt_rows), 2)
        ledger_by_requirement = {int(row["purchase_requirement_id"]): row for row in ledger_rows}
        summary_by_requirement = {int(row["purchase_requirement_id"]): row for row in summary_rows}
        receipt_by_requirement = {int(row["purchase_requirement_id"]): row for row in receipt_rows}
        self.assertEqual(set(ledger_by_requirement), {requirement_a, requirement_b})
        self.assertEqual(set(summary_by_requirement), {requirement_a, requirement_b})
        self.assertEqual(set(receipt_by_requirement), {requirement_a, requirement_b})
        self.assertEqual(ledger_by_requirement[requirement_a]["sales_order_item"], "SO-A6-GROUP-001-ITEM")
        self.assertEqual(ledger_by_requirement[requirement_b]["sales_order_item"], "SO-A6-GROUP-002-ITEM")
        self.assertEqual(receipt_by_requirement[requirement_a]["sales_order_item"], "SO-A6-GROUP-001-ITEM")
        self.assertEqual(receipt_by_requirement[requirement_b]["sales_order_item"], "SO-A6-GROUP-002-ITEM")
        self.assertEqual(Decimal(str(ledger_by_requirement[requirement_a]["actual_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(ledger_by_requirement[requirement_b]["actual_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(summary_by_requirement[requirement_a]["actual_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(summary_by_requirement[requirement_b]["actual_qty"])), Decimal("10.000000"))

    def test_from_requirements_rejects_cross_style_merge(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-STYLE-A",
            net_required_qty="5",
            style_no="STYLE-A6-A",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-STYLE-B",
            net_required_qty="6",
            style_no="STYLE-A6-B",
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-cross-style"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-cross-style",
                purchase_no="PO-A6-CROSS-STYLE",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("款号不一致", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement_rows = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.requirement_no.asc()).all()
            self.assertEqual(len(requirement_rows), 2)
            self.assertTrue(all(str(row.status) == "pending" for row in requirement_rows))
            self.assertTrue(all(row.purchase_order_id is None for row in requirement_rows))

    def test_from_requirements_splits_purchase_lines_by_size_spec_part_and_bom_version(self) -> None:
        requirement_s = self._seed_requirement(
            requirement_no="REQ-A6-LINE-S",
            net_required_qty="100",
            bom_color="黑",
            bom_size="S",
            bom_part="口袋",
            uom="条",
            payload={"specification": "4cm", "spec_by_size": {"S": "4cm"}, "bom_version": "V1"},
        )
        requirement_m = self._seed_requirement(
            requirement_no="REQ-A6-LINE-M",
            net_required_qty="100",
            bom_color="黑",
            bom_size="M",
            bom_part="口袋",
            uom="条",
            payload={"specification": "4.8cm", "spec_by_size": {"M": "4.8cm"}, "bom_version": "V1"},
        )
        requirement_l = self._seed_requirement(
            requirement_no="REQ-A6-LINE-L",
            net_required_qty="100",
            bom_color="黑",
            bom_size="L",
            bom_part="口袋",
            uom="条",
            payload={"specification": "5.6cm", "spec_by_size": {"L": "5.6cm"}, "bom_version": "V1"},
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-line-dimensions"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_s, requirement_m, requirement_l],
                idempotency_key="idem-a6-line-dimensions",
                purchase_no="PO-A6-LINE-DIMS",
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        purchase_order = response.json()["data"]["purchase_order"]
        self.assertEqual(purchase_order["purchase_no"], "PO-A6-LINE-DIMS")
        self.assertEqual(len(purchase_order["items"]), 3)
        items_by_size = {row["bom_size"]: row for row in purchase_order["items"]}
        self.assertEqual(set(items_by_size), {"S", "M", "L"})
        self.assertEqual({row["material_item_code"] for row in purchase_order["items"]}, {self.MATERIAL})
        self.assertEqual({row["style_no"] for row in purchase_order["items"]}, {self.STYLE})
        self.assertEqual({row["supplier_name"] for row in purchase_order["items"]}, {"SUP-A6"})
        self.assertEqual(items_by_size["S"]["specification"], "4cm")
        self.assertEqual(items_by_size["M"]["specification"], "4.8cm")
        self.assertEqual(items_by_size["L"]["specification"], "5.6cm")
        self.assertEqual({row["bom_part"] for row in purchase_order["items"]}, {"口袋"})
        self.assertEqual({row["uom"] for row in purchase_order["items"]}, {"条"})
        self.assertEqual({row["bom_version"] for row in purchase_order["items"]}, {"V1"})
        self.assertEqual({Decimal(str(row["qty"])) for row in purchase_order["items"]}, {Decimal("100.000000")})
        self.assertTrue(all(int(row["requirement_count"]) == 1 for row in purchase_order["items"]))

    def test_purchase_receipt_without_requirement_id_auto_allocates_by_purchase_line(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-SIMPLE-A",
            net_required_qty="5",
            sales_order="SO-A6-SIMPLE-001",
            sales_order_item="SO-A6-SIMPLE-001-ITEM",
            bom_color="黑",
            bom_size="M",
            bom_part="口袋",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-SIMPLE-B",
            net_required_qty="5",
            sales_order="SO-A6-SIMPLE-002",
            sales_order_item="SO-A6-SIMPLE-002-ITEM",
            bom_color="黑",
            bom_size="M",
            bom_part="口袋",
        )
        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-simple-po"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-simple-po",
                purchase_no="PO-A6-SIMPLE",
            ),
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_order = create_po.json()["data"]["purchase_order"]
        self.assertEqual(len(purchase_order["items"]), 1)
        line = purchase_order["items"][0]
        self.assertEqual(int(line["requirement_count"]), 2)

        first_receipt = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-SIMPLE:{self.MATERIAL}:line:{line['line_id']}:part1",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-SIMPLE:part1",
            qty="4",
            purchase_order_item_id=int(line["line_id"]),
        )
        self.assertEqual(first_receipt["source_type"], "material_purchase_order")
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-SIMPLE").one()
            line_row = session.query(LyMaterialPurchaseOrderItem).filter_by(id=int(line["line_id"])).one()
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(line_row.received_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("0.000000"))
            ledger_rows = session.query(LyWarehouseStockLedgerEntry).filter_by(company=self.COMPANY, item_code=self.MATERIAL).all()
            self.assertEqual(len(ledger_rows), 1)
            self.assertEqual(ledger_rows[0].purchase_requirement_id, requirement_a)
            self.assertEqual(Decimal(str(ledger_rows[0].actual_qty)), Decimal("4.000000"))

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-SIMPLE:{self.MATERIAL}:line:{line['line_id']}:part2",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-SIMPLE:part2",
            qty="6",
            purchase_order_item_id=int(line["line_id"]),
        )
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-SIMPLE").one()
            line_row = session.query(LyMaterialPurchaseOrderItem).filter_by(id=int(line["line_id"])).one()
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            self.assertEqual(str(order.status), "received")
            self.assertEqual(Decimal(str(line_row.received_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("5.000000"))
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("5.000000"))
            self.assertEqual(str(req_a.status), "completed")
            self.assertEqual(str(req_b.status), "completed")
            ledger_rows = session.query(LyWarehouseStockLedgerEntry).filter_by(company=self.COMPANY, item_code=self.MATERIAL).all()
            self.assertEqual(sum(Decimal(str(row.actual_qty)) for row in ledger_rows), Decimal("10.000000"))
            self.assertEqual({int(row.purchase_requirement_id) for row in ledger_rows}, {requirement_a, requirement_b})

    def test_material_check_cross_order_requirements_grouped_po_receipt_marks_both_ready(self) -> None:
        def create_checked_plan(*, sequence: str) -> tuple[str, str, int]:
            sales_order_no = f"SO-A6-GROUP-CHECK-{sequence}"
            order = self.client.post(
                "/api/sales-inventory/sales-orders/drafts",
                headers=self._headers(f"req-a6-group-check-{sequence}-order"),
                json={
                    "company": self.COMPANY,
                    "customer": "CUST-A6",
                    "operation": "create_draft",
                    "sales_order_no": sales_order_no,
                    "source_order_ref": sales_order_no,
                    "idempotency_key": f"idem-so-a6-group-check-{sequence}",
                    "transaction_date": "2026-06-17",
                    "delivery_date": "2026-06-30",
                    "currency": "CNY",
                    "items": [
                        {
                            "style_master_id": self._style_id(),
                            "item_code": self.STYLE,
                            "item_name": "A6 Tee",
                            "color": "白",
                            "size": "M",
                            "qty": 10,
                            "rate": 80,
                            "uom": "件",
                        }
                    ],
                },
            )
            self.assertEqual(order.status_code, 201, order.text)
            self._submit_sales_order(
                draft_id=int(order.json()["data"]["id"]),
                sales_order_no=sales_order_no,
                suffix=f"group-check-{sequence}",
            )
            detail = self.client.get(
                f"/api/sales-inventory/sales-orders/{sales_order_no}",
                headers=self._headers(f"req-a6-group-check-{sequence}-detail"),
            )
            self.assertEqual(detail.status_code, 200, detail.text)
            sales_order_item = detail.json()["data"]["items"][0]["name"]

            plan = self.client.post(
                "/api/production/plans",
                headers=self._headers(f"req-a6-group-check-{sequence}-plan"),
                json={
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "planned_qty": 10,
                    "planned_start_date": "2026-06-18",
                    "operation": "create_plan",
                    "idempotency_key": f"idem-plan-a6-group-check-{sequence}",
                    "company": self.COMPANY,
                },
            )
            self.assertEqual(plan.status_code, 200, plan.text)
            plan_id = int(plan.json()["data"]["plan_id"])

            scenario_suffix = {"A": "470", "B": "471"}[sequence]
            scenario = f"Z003-PROD-PLAN-DETAIL-20260618-{scenario_suffix}"
            request_id = f"req-{scenario}"
            material_check = self.client.post(
                f"/api/production/plans/{plan_id}/material-check",
                headers={**self._headers(request_id), "X-Request-ID": request_id},
                json={
                    "warehouse": self.WAREHOUSE,
                    "operation": "material_check",
                    "idempotency_key": f"{scenario}:idem-a6-group-check-material-check",
                    "scenario_tag": scenario,
                    "plan_id": plan_id,
                    "sales_order": sales_order_no,
                    "sales_order_item": sales_order_item,
                    "item_code": self.STYLE,
                    "bom_id": 601,
                    "request_id": request_id,
                },
            )
            self.assertEqual(material_check.status_code, 200, material_check.text)
            material_row = material_check.json()["data"]["items"][0]
            self.assertEqual(material_row["material_item_code"], self.MATERIAL)
            self.assertEqual(Decimal(str(material_row["required_qty"])), Decimal("21.000000"))
            self.assertEqual(Decimal(str(material_row["available_qty"])), Decimal("0.000000"))
            self.assertEqual(Decimal(str(material_row["shortage_qty"])), Decimal("21.000000"))
            return sales_order_no, sales_order_item, plan_id

        order_a, item_a, plan_a = create_checked_plan(sequence="A")
        order_b, item_b, plan_b = create_checked_plan(sequence="B")

        requirements = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=SO-A6-GROUP-CHECK&page=1&page_size=100",
            headers=self._headers("req-a6-group-check-requirements"),
        )
        self.assertEqual(requirements.status_code, 200, requirements.text)
        requirement_rows = requirements.json()["data"]["items"]
        self.assertEqual(len(requirement_rows), 2)
        self.assertEqual({row["sales_order"] for row in requirement_rows}, {order_a, order_b})
        self.assertEqual({row["sales_order_item"] for row in requirement_rows}, {item_a, item_b})
        self.assertEqual({row["material_item_code"] for row in requirement_rows}, {self.MATERIAL})
        self.assertEqual({row["status"] for row in requirement_rows}, {"pending"})
        self.assertEqual(
            sum(Decimal(str(row["net_required_qty"])) for row in requirement_rows),
            Decimal("42.000000"),
        )

        create_po = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-group-check-req-to-po"),
            json=self._from_requirements_payload(
                requirement_ids=[int(row["id"]) for row in requirement_rows],
                idempotency_key="idem-a6-group-check-req-to-po",
                purchase_no="PO-A6-GROUP-CHECK-001",
                supplier_name="SUP-A6",
            ),
        )
        self.assertEqual(create_po.status_code, 201, create_po.text)
        purchase_data = create_po.json()["data"]
        purchase_order = purchase_data["purchase_order"]
        purchase_no = purchase_order["purchase_no"]
        self.assertEqual(len(purchase_order["items"]), 1)
        self.assertEqual(purchase_order["items"][0]["material_item_code"], self.MATERIAL)
        self.assertEqual(Decimal(str(purchase_order["items"][0]["qty"])), Decimal("42.000000"))
        self.assertEqual({row["status"] for row in purchase_data["requirements"]}, {"purchased"})
        self.assertEqual({row["sales_order"] for row in purchase_data["requirements"]}, {order_a, order_b})

        receipt = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:{purchase_no}:group-check",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:{purchase_no}:group-check",
            qty="42",
        )
        self.assertEqual(receipt["source_type"], "material_purchase_order")

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword={purchase_no}&page=1&page_size=100",
            headers=self._headers("req-a6-group-check-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 2)
        self.assertEqual({row["sales_order"] for row in completed_rows}, {order_a, order_b})
        self.assertEqual({row["sales_order_item"] for row in completed_rows}, {item_a, item_b})
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        self.assertEqual({row["status"] for row in completed_rows}, {"completed"})
        self.assertEqual(
            sum(Decimal(str(row["received_qty"])) for row in completed_rows),
            Decimal("42.000000"),
        )

        for plan_id in [plan_a, plan_b]:
            ready_detail = self.client.get(
                f"/api/production/plans/{plan_id}",
                headers=self._headers(f"req-a6-group-check-ready-{plan_id}"),
            )
            self.assertEqual(ready_detail.status_code, 200, ready_detail.text)
            ready_plan = ready_detail.json()["data"]
            self.assertTrue(ready_plan["material_ready"])
            self.assertEqual(ready_plan["purchase_status"], "ready")
            self.assertEqual(ready_plan["pending_requirement_count"], 0)
            self.assertEqual(Decimal(str(ready_plan["shortage_qty_total"])), Decimal("0.000000"))

    def test_grouped_material_partial_receipt_auto_allocates_and_keeps_explicit_requirement_mode(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-ALLOC-A",
            net_required_qty="5",
            sales_order="SO-A6-ALLOC-001",
            sales_order_item="SO-A6-ALLOC-001-ITEM",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-ALLOC-B",
            net_required_qty="10",
            sales_order="SO-A6-ALLOC-002",
            sales_order_item="SO-A6-ALLOC-002-ITEM",
        )
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-alloc-material"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-alloc-material",
                purchase_no="PO-A6-ALLOC",
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        line_id = int(response.json()["data"]["purchase_order"]["items"][0]["line_id"])

        simple_source_ref = f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-ALLOC:{self.MATERIAL}:line:{line_id}:simple"
        simple_draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=simple_source_ref,
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-ALLOC:simple",
            qty="4",
            purchase_order_item_id=line_id,
        )
        with self.SessionLocal() as session:
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-ALLOC").one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).one()
            self.assertEqual(str(req_a.status), "purchased")
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("4.000000"))
            self.assertEqual(str(req_b.status), "purchased")
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("4.000000"))
            self.assertEqual(str(order.status), "partially_received")

        cancel_simple = self._cancel_stock_receipt(
            draft=simple_draft,
            source_id=simple_source_ref,
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-ALLOC:simple",
            qty="4",
        )
        self.assertEqual(cancel_simple.status_code, 200, cancel_simple.text)

        draft = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-ALLOC",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-ALLOC:req-b",
            qty="10",
            purchase_requirement_id=requirement_b,
        )

        with self.SessionLocal() as session:
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-ALLOC").one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).one()

            self.assertEqual(str(req_a.status), "purchased")
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(req_b.status), "completed")
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("10.000000"))
            self.assertEqual(str(order.status), "partially_received")

        cancel_response = self._cancel_stock_receipt(
            draft=draft,
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-ALLOC",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-ALLOC:req-b",
            qty="10",
        )
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)

        with self.SessionLocal() as session:
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-ALLOC").one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).one()

            self.assertEqual(str(req_a.status), "purchased")
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(req_b.status), "purchased")
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("0.000000"))
            self.assertEqual(str(order.status), "draft")

    def test_grouped_material_can_receive_same_po_item_by_requirement_source_scope(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-SPLIT-A",
            net_required_qty="5",
            sales_order="SO-A6-SPLIT-001",
            sales_order_item="SO-A6-SPLIT-001-ITEM",
            bom_color="黑",
            bom_size="L",
            bom_part="前片",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-SPLIT-B",
            net_required_qty="10",
            sales_order="SO-A6-SPLIT-001",
            sales_order_item="SO-A6-SPLIT-001-ITEM",
            bom_color="黑",
            bom_size="L",
            bom_part="后片",
        )
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-split-material"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-split-material",
                purchase_no="PO-A6-SPLIT",
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        purchase_order = response.json()["data"]["purchase_order"]
        self.assertEqual(len(purchase_order["items"]), 2)
        purchase_items_by_part = {row["bom_part"]: row for row in purchase_order["items"]}
        self.assertEqual(set(purchase_items_by_part), {"前片", "后片"})
        self.assertEqual({row["material_item_code"] for row in purchase_order["items"]}, {self.MATERIAL})
        self.assertEqual(Decimal(str(purchase_items_by_part["前片"]["qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(purchase_items_by_part["后片"]["qty"])), Decimal("10.000000"))

        draft_a = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-SPLIT:{self.MATERIAL}:req:{requirement_a}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-SPLIT:req-a",
            qty="5",
            purchase_requirement_id=requirement_a,
        )
        draft_b = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-SPLIT:{self.MATERIAL}:req:{requirement_b}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-SPLIT:req-b",
            qty="10",
            purchase_requirement_id=requirement_b,
        )
        self.assertNotEqual(draft_a["id"], draft_b["id"])
        self.assertIn(f":req:{requirement_a}", draft_a["source_id"])
        self.assertIn(f":req:{requirement_b}", draft_b["source_id"])

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword=PO-A6-SPLIT&page=1&page_size=100",
            headers=self._headers("req-a6-split-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_rows = completed.json()["data"]["items"]
        self.assertEqual(len(completed_rows), 2)
        completed_by_part = {str(row["bom_part"]): row for row in completed_rows}
        self.assertEqual(set(completed_by_part), {"前片", "后片"})
        self.assertTrue(all(row["has_completed"] for row in completed_rows))
        self.assertEqual(Decimal(str(completed_by_part["前片"]["received_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(completed_by_part["后片"]["received_qty"])), Decimal("10.000000"))

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-split-ledger"),
        )
        summary = self.client.get(
            f"/api/warehouse/stock-summary?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-split-summary"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        self.assertEqual(summary.status_code, 200, summary.text)
        ledger_rows = ledger.json()["data"]["items"]
        self.assertEqual(ledger.json()["data"]["total"], 2)
        self.assertEqual([Decimal(str(row["actual_qty"])) for row in ledger_rows], [Decimal("5.000000"), Decimal("10.000000")])
        ledger_by_part = {str(row["bom_part"]): row for row in ledger_rows}
        self.assertEqual(set(ledger_by_part), {"前片", "后片"})
        self.assertEqual(ledger_by_part["前片"]["purchase_requirement_id"], requirement_a)
        self.assertEqual(ledger_by_part["后片"]["purchase_requirement_id"], requirement_b)
        self.assertEqual(ledger_by_part["前片"]["sales_order_item"], "SO-A6-SPLIT-001-ITEM")
        self.assertEqual(ledger_by_part["后片"]["sales_order_item"], "SO-A6-SPLIT-001-ITEM")
        self.assertEqual(ledger_by_part["前片"]["bom_color"], "黑")
        self.assertEqual(ledger_by_part["后片"]["bom_color"], "黑")
        self.assertEqual(ledger_by_part["前片"]["bom_size"], "L")
        self.assertEqual(ledger_by_part["后片"]["bom_size"], "L")
        self.assertEqual(Decimal(str(ledger_by_part["前片"]["qty_after_transaction"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(ledger_by_part["后片"]["qty_after_transaction"])), Decimal("10.000000"))
        summary_rows = summary.json()["data"]["items"]
        self.assertEqual(len(summary_rows), 2)
        summary_by_part = {str(row["bom_part"]): row for row in summary_rows}
        self.assertEqual(set(summary_by_part), {"前片", "后片"})
        self.assertEqual(Decimal(str(summary_by_part["前片"]["actual_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(summary_by_part["后片"]["actual_qty"])), Decimal("10.000000"))
        self.assertEqual(sum(Decimal(str(row["actual_qty"])) for row in summary_rows), Decimal("15.000000"))
        self._assert_balanced_inventory_reconciliation(
            item_code=self.MATERIAL,
            expected_qty=Decimal("15.000000"),
            suffix="split-bom-parts",
        )
        with self.SessionLocal() as session:
            self.assertEqual(
                ProductionService(session=session)._local_material_stock_balance(
                    company=self.COMPANY,
                    item_code=self.MATERIAL,
                    warehouse=self.WAREHOUSE,
                ),
                Decimal("15.000000"),
            )

        receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company={self.COMPANY}&purchase_no=PO-A6-SPLIT&page=1&page_size=100",
            headers=self._headers("req-a6-split-receipts"),
        )
        self.assertEqual(receipts.status_code, 200, receipts.text)
        receipt_rows = receipts.json()["data"]["items"]
        self.assertEqual(len(receipt_rows), 2)
        receipt_by_part = {str(row["bom_part"]): row for row in receipt_rows}
        self.assertEqual(set(receipt_by_part), {"前片", "后片"})
        self.assertEqual(receipt_by_part["前片"]["purchase_requirement_id"], requirement_a)
        self.assertEqual(receipt_by_part["后片"]["purchase_requirement_id"], requirement_b)
        self.assertEqual(receipt_by_part["前片"]["sales_order_item"], "SO-A6-SPLIT-001-ITEM")
        self.assertEqual(receipt_by_part["后片"]["sales_order_item"], "SO-A6-SPLIT-001-ITEM")
        self.assertEqual(receipt_by_part["前片"]["bom_color"], "黑")
        self.assertEqual(receipt_by_part["后片"]["bom_color"], "黑")
        self.assertEqual(receipt_by_part["前片"]["bom_size"], "L")
        self.assertEqual(receipt_by_part["后片"]["bom_size"], "L")

        with self.SessionLocal() as session:
            req_a = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_a).one()
            req_b = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_b).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-SPLIT").one()
            lines = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).all()
            lines_by_id = {int(line.id): line for line in lines}
            draft_count = session.query(LyWarehouseStockEntryDraft).filter(
                LyWarehouseStockEntryDraft.source_id.like(f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-SPLIT:%")
            ).count()

            self.assertEqual(draft_count, 2)
            self.assertEqual(len(lines), 2)
            self.assertNotEqual(req_a.purchase_order_item_id, req_b.purchase_order_item_id)
            self.assertEqual(str(req_a.status), "completed")
            self.assertEqual(str(req_b.status), "completed")
            self.assertEqual(Decimal(str(req_a.received_qty)), Decimal("5.000000"))
            self.assertEqual(Decimal(str(req_b.received_qty)), Decimal("10.000000"))
            self.assertEqual(Decimal(str(lines_by_id[int(req_a.purchase_order_item_id)].received_qty)), Decimal("5.000000"))
            self.assertEqual(Decimal(str(lines_by_id[int(req_b.purchase_order_item_id)].received_qty)), Decimal("10.000000"))
            self.assertEqual(str(order.status), "received")

    def test_grouped_material_partial_receipt_splits_cross_order_size_traceability(self) -> None:
        requirement_s = self._seed_requirement(
            requirement_no="REQ-A6-XSIZE-S",
            net_required_qty="5",
            sales_order="SO-A6-XSIZE-001",
            sales_order_item="SO-A6-XSIZE-001-S",
            bom_color="黑",
            bom_size="S",
            bom_part="门襟",
        )
        requirement_m = self._seed_requirement(
            requirement_no="REQ-A6-XSIZE-M",
            net_required_qty="8",
            sales_order="SO-A6-XSIZE-002",
            sales_order_item="SO-A6-XSIZE-002-M",
            bom_color="黑",
            bom_size="M",
            bom_part="门襟",
        )
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-xsize-material"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_s, requirement_m],
                idempotency_key="idem-a6-xsize-material",
                purchase_no="PO-A6-XSIZE",
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        purchase_order = response.json()["data"]["purchase_order"]
        self.assertEqual(len(purchase_order["items"]), 2)
        purchase_items_by_size = {row["bom_size"]: row for row in purchase_order["items"]}
        self.assertEqual(set(purchase_items_by_size), {"S", "M"})
        self.assertEqual({row["material_item_code"] for row in purchase_order["items"]}, {self.MATERIAL})
        self.assertEqual(Decimal(str(purchase_items_by_size["S"]["qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(purchase_items_by_size["M"]["qty"])), Decimal("8.000000"))

        draft_s = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-XSIZE:{self.MATERIAL}:req:{requirement_s}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-XSIZE:req-s",
            qty="5",
            purchase_requirement_id=requirement_s,
        )
        draft_m = self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-XSIZE:{self.MATERIAL}:req:{requirement_m}",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-XSIZE:req-m",
            qty="8",
            purchase_requirement_id=requirement_m,
        )
        self.assertNotEqual(draft_s["id"], draft_m["id"])

        completed = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=completed&keyword=PO-A6-XSIZE&page=1&page_size=100",
            headers=self._headers("req-a6-xsize-completed"),
        )
        self.assertEqual(completed.status_code, 200, completed.text)
        completed_by_size = {str(row["bom_size"]): row for row in completed.json()["data"]["items"]}
        self.assertEqual(set(completed_by_size), {"S", "M"})
        self.assertEqual(completed_by_size["S"]["id"], requirement_s)
        self.assertEqual(completed_by_size["M"]["id"], requirement_m)
        self.assertEqual(completed_by_size["S"]["sales_order_item"], "SO-A6-XSIZE-001-S")
        self.assertEqual(completed_by_size["M"]["sales_order_item"], "SO-A6-XSIZE-002-M")
        self.assertEqual(Decimal(str(completed_by_size["S"]["received_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(completed_by_size["M"]["received_qty"])), Decimal("8.000000"))

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-xsize-ledger"),
        )
        summary = self.client.get(
            f"/api/warehouse/stock-summary?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.MATERIAL}",
            headers=self._headers("req-a6-xsize-summary"),
        )
        receipts = self.client.get(
            f"/api/warehouse/purchase-receipts?company={self.COMPANY}&purchase_no=PO-A6-XSIZE&page=1&page_size=100",
            headers=self._headers("req-a6-xsize-receipts"),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(receipts.status_code, 200, receipts.text)
        ledger_by_size = {str(row["bom_size"]): row for row in ledger.json()["data"]["items"]}
        summary_by_size = {str(row["bom_size"]): row for row in summary.json()["data"]["items"]}
        receipt_by_size = {str(row["bom_size"]): row for row in receipts.json()["data"]["items"]}
        self.assertEqual(set(ledger_by_size), {"S", "M"})
        self.assertEqual(set(summary_by_size), {"S", "M"})
        self.assertEqual(set(receipt_by_size), {"S", "M"})
        self.assertEqual(ledger_by_size["S"]["purchase_requirement_id"], requirement_s)
        self.assertEqual(ledger_by_size["M"]["purchase_requirement_id"], requirement_m)
        self.assertEqual(receipt_by_size["S"]["purchase_requirement_id"], requirement_s)
        self.assertEqual(receipt_by_size["M"]["purchase_requirement_id"], requirement_m)
        self.assertEqual(ledger_by_size["S"]["sales_order_item"], "SO-A6-XSIZE-001-S")
        self.assertEqual(ledger_by_size["M"]["sales_order_item"], "SO-A6-XSIZE-002-M")
        self.assertEqual(Decimal(str(summary_by_size["S"]["actual_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(summary_by_size["M"]["actual_qty"])), Decimal("8.000000"))

        with self.SessionLocal() as session:
            req_s = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_s).one()
            req_m = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_m).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-XSIZE").one()
            lines = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).all()
            lines_by_id = {int(line.id): line for line in lines}

            self.assertEqual(len(lines), 2)
            self.assertNotEqual(req_s.purchase_order_item_id, req_m.purchase_order_item_id)
            self.assertEqual(str(req_s.status), "completed")
            self.assertEqual(str(req_m.status), "completed")
            self.assertEqual(Decimal(str(req_s.received_qty)), Decimal("5.000000"))
            self.assertEqual(Decimal(str(req_m.received_qty)), Decimal("8.000000"))
            self.assertEqual(Decimal(str(lines_by_id[int(req_s.purchase_order_item_id)].received_qty)), Decimal("5.000000"))
            self.assertEqual(Decimal(str(lines_by_id[int(req_m.purchase_order_item_id)].received_qty)), Decimal("8.000000"))
            self.assertEqual(str(order.status), "received")

    def test_purchase_receipt_rejects_unknown_purchase_requirement_id_before_draft_create(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-MISSING-CONTEXT", net_required_qty="5")
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-missing-context-po"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-missing-context-po",
                purchase_no="PO-A6-MISSING-CONTEXT",
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        missing_requirement_id = requirement_id + 100000
        source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-MISSING-CONTEXT:req:{missing_requirement_id}"
        receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-MISSING-CONTEXT:bad-req",
                    source_ref=source_id,
                    item_code=self.MATERIAL,
                    quantity="5",
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": self.COMPANY,
                "purpose": "Material Receipt",
                "source_type": "material_purchase_order",
                "source_id": source_id,
                "source_ref": source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": self.MATERIAL,
                "quantity": "5",
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-MISSING-CONTEXT:bad-req",
                "items": [
                    {
                        "item_code": self.MATERIAL,
                        "qty": "5",
                        "uom": "米",
                        "target_warehouse": self.WAREHOUSE,
                        "purchase_requirement_id": missing_requirement_id,
                    }
                ],
            },
        )

        self.assertEqual(receipt.status_code, 409, receipt.text)
        self.assertEqual(receipt.json()["code"], "WAREHOUSE_PURCHASE_REQUIREMENT_NOT_FOUND")
        self.assertIn("采购需求行不存在", receipt.json()["message"])
        with self.SessionLocal() as session:
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_id).one()
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(Decimal(str(requirement.received_qty)), Decimal("0.000000"))
            self.assertEqual(session.query(LyWarehouseStockEntryDraft).count(), 0)

    def test_purchase_receipt_rejects_cumulative_over_receipt_for_same_requirement_before_draft_create(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-OVER-RECEIPT", net_required_qty="5")
        sibling_requirement_id = self._seed_requirement(
            requirement_no="REQ-A6-OVER-RECEIPT-SIBLING",
            net_required_qty="10",
            sales_order="SO-A6-OVER-RECEIPT-002",
            sales_order_item="SO-A6-OVER-RECEIPT-002-ITEM",
        )
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-over-receipt-po"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id, sibling_requirement_id],
                idempotency_key="idem-a6-over-receipt-po",
                purchase_no="PO-A6-OVER-RECEIPT",
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)

        self._create_stock_receipt(
            source_type="material_purchase_order",
            source_id=f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-OVER-RECEIPT:{self.MATERIAL}:req:{requirement_id}:part-1",
            idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-OVER-RECEIPT:req:{requirement_id}:part-1",
            qty="4",
            purchase_requirement_id=requirement_id,
        )

        over_receipt_source_id = f"{self.WAREHOUSE_SCENARIO}:purchase:PO-A6-OVER-RECEIPT:{self.MATERIAL}:req:{requirement_id}:part-2"
        over_receipt = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(
                self._warehouse_request_id(
                    idempotency_key=f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-OVER-RECEIPT:req:{requirement_id}:part-2",
                    source_ref=over_receipt_source_id,
                    item_code=self.MATERIAL,
                    quantity="2",
                )
            ),
            json={
                "operation": "create_stock_entry_draft",
                "company": self.COMPANY,
                "purpose": "Material Receipt",
                "source_type": "material_purchase_order",
                "source_id": over_receipt_source_id,
                "source_ref": over_receipt_source_id,
                "warehouse": self.WAREHOUSE,
                "item_code": self.MATERIAL,
                "quantity": "2",
                "business_date": self.BUSINESS_DATE,
                "status_action": "create",
                "scenario_tag": self.WAREHOUSE_SCENARIO,
                "target_warehouse": self.WAREHOUSE,
                "idempotency_key": f"{self.WAREHOUSE_SCENARIO}:receipt:PO-A6-OVER-RECEIPT:req:{requirement_id}:part-2",
                "items": [
                    {
                        "item_code": self.MATERIAL,
                        "qty": "2",
                        "uom": "米",
                        "target_warehouse": self.WAREHOUSE,
                        "purchase_requirement_id": requirement_id,
                    }
                ],
            },
        )

        self.assertEqual(over_receipt.status_code, 409, over_receipt.text)
        self.assertEqual(over_receipt.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("收货数量超过需求采购数量", over_receipt.json()["message"])
        with self.SessionLocal() as session:
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_id).one()
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-OVER-RECEIPT").one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=order.id).one()

            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(Decimal(str(requirement.received_qty)), Decimal("4.000000"))
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("4.000000"))
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(
                session.query(LyWarehouseStockEntryDraft).filter_by(source_id=over_receipt_source_id).count(),
                0,
            )

    def test_from_requirements_rejects_mixed_unit_prices_when_grouping_by_material(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-PRICE-A",
            net_required_qty="5",
            sales_order="SO-A6-GROUP-PRICE-001",
            sales_order_item="SO-A6-GROUP-PRICE-001-ITEM",
            unit_price="12.5",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-GROUP-PRICE-B",
            net_required_qty="10",
            sales_order="SO-A6-GROUP-PRICE-002",
            sales_order_item="SO-A6-GROUP-PRICE-002-ITEM",
            unit_price="13.0",
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-mixed-unit-price"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-mixed-unit-price",
            ),
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("单价不一致", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement_rows = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.requirement_no.asc()).all()
            self.assertEqual(len(requirement_rows), 2)
            self.assertTrue(all(str(row.status) == "pending" for row in requirement_rows))
            self.assertTrue(all(row.purchase_order_id is None for row in requirement_rows))

    def test_from_requirements_rejects_inactive_supplier_master(self) -> None:
        supplier_name = "SUP-A6-OFF"
        with self.SessionLocal() as session:
            self._seed_master_data_record(
                session=session,
                entity_type="supplier",
                code=supplier_name,
                name=supplier_name,
                status="inactive",
            )
            session.commit()
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-SUP-OFF", supplier_name=supplier_name)

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-inactive-supplier"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-inactive-supplier",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("供应商不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.status), "pending")
            self.assertIsNone(requirement.purchase_order_id)

    def test_from_requirements_rejects_inactive_material_master(self) -> None:
        material_code = "FAB-A6-OFF"
        with self.SessionLocal() as session:
            self._seed_master_data_record(
                session=session,
                entity_type="material",
                code=material_code,
                name="停用布料",
                status="inactive",
            )
            session.commit()
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-MAT-OFF", material_item_code=material_code)

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-inactive-material"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-inactive-material",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("物料不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.status), "pending")
            self.assertIsNone(requirement.purchase_order_id)

    def test_from_requirements_rejects_inactive_warehouse_master(self) -> None:
        warehouse = "WH-A6-OFF"
        with self.SessionLocal() as session:
            self._seed_master_data_record(
                session=session,
                entity_type="warehouse",
                code=warehouse,
                name=warehouse,
                status="inactive",
            )
            session.commit()
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-WH-OFF", warehouse=warehouse)

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-inactive-warehouse"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-inactive-warehouse",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("仓库不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.status), "pending")
            self.assertIsNone(requirement.purchase_order_id)

    def test_from_requirements_auto_creates_default_material_warehouse(self) -> None:
        warehouse = "DEFAULT-MATERIAL-WH"
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-DEFAULT-WH", warehouse=warehouse)

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-default-warehouse"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-default-warehouse",
                purchase_no="PO-A6-DEFAULT-WH",
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        purchase_order = data["purchase_order"]
        self.assertEqual(purchase_order["purchase_no"], "PO-A6-DEFAULT-WH")
        self.assertEqual(purchase_order["items"][0]["warehouse"], warehouse)
        with self.SessionLocal() as session:
            default_warehouse = (
                session.query(LyMasterDataRecord)
                .filter_by(company=self.COMPANY, entity_type="warehouse", code=warehouse)
                .one()
            )
            self.assertEqual(str(default_warehouse.name), "默认物料仓")
            self.assertEqual(str(default_warehouse.status), "active")
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(requirement_no="REQ-A6-DEFAULT-WH").one()
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(str(requirement.warehouse), warehouse)

    def test_from_requirements_rejects_missing_or_inactive_unit_master(self) -> None:
        with self.SessionLocal() as session:
            self._seed_material_unit(session=session, code="MU-INACTIVE-YARD", name="英码", status="inactive")
            session.commit()
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-UOM-OFF", uom="英码")

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-inactive-uom"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-inactive-uom",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("物料单位不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertEqual(str(requirement.status), "pending")
            self.assertIsNone(requirement.purchase_order_id)

    def test_from_requirements_accepts_camel_group_by_material_false(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-CAMEL-A",
            net_required_qty="5",
            sales_order="SO-A6-CAMEL-001",
            sales_order_item="SO-A6-CAMEL-001-ITEM",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-CAMEL-B",
            net_required_qty="10",
            sales_order="SO-A6-CAMEL-002",
            sales_order_item="SO-A6-CAMEL-002-ITEM",
        )

        payload = self._from_requirements_payload(
            requirement_ids=[requirement_a, requirement_b],
            idempotency_key="idem-a6-camel-group-material-false",
        )
        payload.pop("group_by_material")
        payload["groupByMaterial"] = False
        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-camel-group-material-false"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)

        purchase_order = response.json()["data"]["purchase_order"]
        self.assertEqual(len(purchase_order["items"]), 2)
        self.assertEqual([Decimal(str(row["qty"])) for row in purchase_order["items"]], [Decimal("5.000000"), Decimal("10.000000")])

        with self.SessionLocal() as session:
            requirement_rows = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.requirement_no.asc()).all()
            self.assertEqual(len({int(row.purchase_order_item_id) for row in requirement_rows}), 2)

    def test_cancel_purchase_order_reverts_requirement_pool_and_is_idempotent(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-CANCEL-A",
            net_required_qty="4",
            sales_order="SO-A6-CANCEL-001",
            sales_order_item="SO-A6-CANCEL-001-ITEM",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-CANCEL-B",
            net_required_qty="6",
            sales_order="SO-A6-CANCEL-002",
            sales_order_item="SO-A6-CANCEL-002-ITEM",
        )
        create_response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-cancel-create"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-cancel-create",
                purchase_no="PO-A6-CANCEL-REQ",
            ),
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        purchase_order = create_response.json()["data"]["purchase_order"]
        self.assertEqual(purchase_order["status"], "draft")
        order_id = int(purchase_order["id"])

        payload = self._cancel_order_payload(idempotency_key="idem-a6-cancel-order")
        cancel_response = self.client.post(
            f"/api/material-purchase/orders/{order_id}/cancel",
            headers=self._headers("req-a6-cancel-order"),
            json=payload,
        )
        replay_response = self.client.post(
            f"/api/material-purchase/orders/{order_id}/cancel",
            headers=self._headers("req-a6-cancel-order-replay"),
            json=payload,
        )
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)
        self.assertEqual(replay_response.status_code, 200, replay_response.text)
        self.assertEqual(cancel_response.json()["data"], replay_response.json()["data"])
        conflict_response = self.client.post(
            f"/api/material-purchase/orders/{order_id}/cancel",
            headers=self._headers("req-a6-cancel-order-conflict"),
            json=self._cancel_order_payload(idempotency_key="idem-a6-cancel-order", reason="换一个取消原因"),
        )
        self.assertEqual(conflict_response.status_code, 409, conflict_response.text)
        self.assertEqual(conflict_response.json()["code"], "MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT")

        data = cancel_response.json()["data"]
        self.assertEqual(data["purchase_order"]["status"], "cancelled")
        self.assertEqual(data["purchase_order"]["purchase_no"], "PO-A6-CANCEL-REQ")
        self.assertEqual(data["reason"], "测试取消采购单")
        self.assertEqual({row["status"] for row in data["requirements"]}, {"pending"})
        self.assertEqual({Decimal(str(row["purchased_qty"])) for row in data["requirements"]}, {Decimal("0.000000")})
        self.assertEqual({Decimal(str(row["received_qty"])) for row in data["requirements"]}, {Decimal("0.000000")})
        self.assertTrue(all(row["purchase_no"] is None for row in data["requirements"]))

        pending = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&status=pending&keyword=REQ-A6-CANCEL",
            headers=self._headers("req-a6-cancel-pending"),
        )
        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertEqual(pending.json()["data"]["total"], 2)
        with self.SessionLocal() as session:
            order_row = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-CANCEL-REQ").one()
            requirement_rows = session.query(LyMaterialPurchaseRequirement).order_by(LyMaterialPurchaseRequirement.requirement_no.asc()).all()
            self.assertEqual(str(order_row.status), "cancelled")
            self.assertEqual({str(row.status) for row in requirement_rows}, {"pending"})
            self.assertTrue(all(row.purchase_order_id is None for row in requirement_rows))
            self.assertTrue(all(row.purchase_order_item_id is None for row in requirement_rows))
            self.assertTrue(all(row.purchase_no is None for row in requirement_rows))
            audit_rows = session.query(LyOperationAuditLog).all()
            audit_actions = {row.action for row in audit_rows}
            self.assertIn("material_purchase:write", audit_actions)
            self.assertTrue(any((row.after_data or {}).get("reason") == "测试取消采购单" for row in audit_rows))

    def test_cancel_purchase_order_rejects_received_order_without_releasing_requirements(self) -> None:
        self._seed_receipt_backed_purchase_chain(
            plan_id=9001,
            order_id=9101,
            line_id=9201,
            purchase_no="PO-A6-CANCEL-RECEIVED",
            qty="8",
        )
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-CANCEL-RECEIVED").one()
            line = session.query(LyMaterialPurchaseOrderItem).filter_by(order_id=int(order.id)).one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no="PO-A6-CANCEL-RECEIVED").one()
            order.status = "partially_received"
            order.received_qty = Decimal("2")
            line.received_qty = Decimal("2")
            requirement.received_qty = Decimal("2")
            requirement.status = "purchased"
            session.commit()

        response = self.client.post(
            "/api/material-purchase/orders/9101/cancel",
            headers=self._headers("req-a6-cancel-received"),
            json=self._cancel_order_payload(idempotency_key="idem-a6-cancel-received"),
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("已有收货", response.json()["message"])
        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).filter_by(purchase_no="PO-A6-CANCEL-RECEIVED").one()
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(purchase_no="PO-A6-CANCEL-RECEIVED").one()
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(int(requirement.purchase_order_id), 9101)

    def test_cancel_purchase_order_unauthenticated_security_audit_is_write_order(self) -> None:
        response = self.client.post(
            "/api/material-purchase/orders/123/cancel",
            json=self._cancel_order_payload(idempotency_key="idem-a6-cancel-unauth"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).one()
            self.assertEqual(row.module, "material_purchase")
            self.assertEqual(row.action, "material_purchase:write")
            self.assertEqual(row.resource_type, "MaterialPurchaseOrder")
            self.assertEqual(row.resource_id, "123")
            self.assertEqual(row.request_path, "/api/material-purchase/orders/123/cancel")

    def test_from_requirements_rejects_mixed_requirement_suppliers(self) -> None:
        requirement_a = self._seed_requirement(
            requirement_no="REQ-A6-SUP-A",
            supplier_name="SUP-A6-A",
            sales_order="SO-A6-SUP-A",
            sales_order_item="SO-A6-SUP-A-ITEM",
        )
        requirement_b = self._seed_requirement(
            requirement_no="REQ-A6-SUP-B",
            supplier_name="SUP-A6-B",
            sales_order="SO-A6-SUP-B",
            sales_order_item="SO-A6-SUP-B-ITEM",
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-mixed-suppliers"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_a, requirement_b],
                idempotency_key="idem-a6-mixed-suppliers",
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("供应商不一致", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            requirement_rows = session.query(LyMaterialPurchaseRequirement).all()
            self.assertTrue(all(str(row.status) == "pending" for row in requirement_rows))

    def test_from_requirements_rejects_requested_supplier_mismatch(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-SUP-MISMATCH", supplier_name="SUP-A6")
        payload = self._from_requirements_payload(
            requirement_ids=[requirement_id],
            idempotency_key="idem-a6-supplier-mismatch",
        )
        payload["supplier_name"] = "SUP-A6-OTHER"

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._headers("req-a6-supplier-mismatch"),
            json=payload,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertIn("请求供应商", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)

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

    def test_requirements_list_filters_fastapi_resource_scope(self) -> None:
        allowed_id = self._seed_requirement(requirement_no="REQ-A6-SCOPE-ALLOW")
        self._seed_requirement(
            requirement_no="REQ-A6-SCOPE-BLOCK-MAT",
            material_item_code="FAB-A6-BLOCK",
            supplier_name="SUP-A6",
            warehouse=self.WAREHOUSE,
        )
        self._seed_requirement(
            requirement_no="REQ-A6-SCOPE-BLOCK-WH",
            material_item_code=self.MATERIAL,
            supplier_name="SUP-A6",
            warehouse="WH-A6-BLOCK",
        )
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._enable_fastapi_material_purchase_actions(read=True)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "a6.scope.user": {
                        "companies": [self.COMPANY],
                        "item_codes": [self.MATERIAL],
                        "suppliers": ["SUP-A6"],
                        "warehouses": [self.WAREHOUSE],
                    }
                }
            }
        )

        response = self.client.get(
            "/api/material-purchase/requirements?status=pending&page_size=100",
            headers=self._scope_headers("req-a6-list-scope"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual([int(row["id"]) for row in data["items"]], [allowed_id])

    def test_orders_list_filters_fastapi_resource_scope(self) -> None:
        with self.SessionLocal() as session:
            allowed_order = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no="PO-A6-SCOPE-ALLOW",
                supplier_name="SUP-A6",
                status="draft",
                total_qty=Decimal("10"),
                received_qty=Decimal("0"),
                total_amount=Decimal("125"),
                currency="CNY",
                created_by="seed",
                updated_by="seed",
            )
            blocked_order = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no="PO-A6-SCOPE-BLOCK",
                supplier_name="SUP-A6",
                status="draft",
                total_qty=Decimal("10"),
                received_qty=Decimal("0"),
                total_amount=Decimal("125"),
                currency="CNY",
                created_by="seed",
                updated_by="seed",
            )
            session.add_all([allowed_order, blocked_order])
            session.flush()
            allowed_line = LyMaterialPurchaseOrderItem(
                order_id=int(allowed_order.id),
                company=self.COMPANY,
                item_code=self.STYLE,
                material_item_code=self.MATERIAL,
                material_name="A6 棉布",
                qty=Decimal("10"),
                received_qty=Decimal("0"),
                uom="米",
                unit_price=Decimal("12.5"),
                amount=Decimal("125"),
                warehouse=self.WAREHOUSE,
            )
            blocked_line = LyMaterialPurchaseOrderItem(
                order_id=int(blocked_order.id),
                company=self.COMPANY,
                item_code=self.STYLE,
                material_item_code="FAB-A6-BLOCK",
                material_name="A6 禁止面料",
                qty=Decimal("10"),
                received_qty=Decimal("0"),
                uom="米",
                unit_price=Decimal("12.5"),
                amount=Decimal("125"),
                warehouse=self.WAREHOUSE,
            )
            session.add_all([allowed_line, blocked_line])
            session.commit()
            allowed_line_id = int(allowed_line.id)

        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._enable_fastapi_material_purchase_actions(read=True)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "a6.scope.user": {
                        "companies": [self.COMPANY],
                        "item_codes": [self.MATERIAL],
                        "suppliers": ["SUP-A6"],
                        "warehouses": [self.WAREHOUSE],
                    }
                }
            }
        )

        response = self.client.get(
            "/api/material-purchase/orders?page_size=100",
            headers=self._scope_headers("req-a6-order-list-scope"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual([int(row["line_id"]) for row in data["items"]], [allowed_line_id])

    def test_requirements_list_filters_by_supplier_name(self) -> None:
        self._seed_requirement(requirement_no="REQ-A6-SUP-FILTER-KEEP", supplier_name="SUP-A6-KEEP")
        self._seed_requirement(requirement_no="REQ-A6-SUP-FILTER-BLOCK", supplier_name="SUP-A6-BLOCK")

        response = self.client.get(
            f"/api/material-purchase/requirements?company={self.COMPANY}&supplier_name=KEEP&page_size=100",
            headers=self._headers("req-a6-list-supplier-filter"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["requirement_no"], "REQ-A6-SUP-FILTER-KEEP")
        self.assertEqual(data["items"][0]["supplier_name"], "SUP-A6-KEEP")

    def test_from_requirements_fastapi_scope_denied_does_not_mutate(self) -> None:
        requirement_id = self._seed_requirement(
            requirement_no="REQ-A6-SCOPE-DENY",
            material_item_code="FAB-A6-DENY",
            supplier_name="SUP-A6",
            warehouse=self.WAREHOUSE,
        )
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._enable_fastapi_material_purchase_actions(write=True)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "a6.scope.user": {
                        "companies": [self.COMPANY],
                        "item_codes": [self.MATERIAL],
                        "suppliers": ["SUP-A6"],
                        "warehouses": [self.WAREHOUSE],
                    }
                }
            }
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._scope_headers("req-a6-from-req-scope-deny"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-scope-deny",
            ),
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseIdempotency).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_id).one()
            self.assertEqual(str(requirement.status), "pending")
            audit = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.event_type, "RESOURCE_ACCESS_DENIED")
            self.assertEqual(audit.resource_type, "MATERIAL_PURCHASE_REQUIREMENT")
            self.assertEqual(audit.resource_no, "REQ-A6-SCOPE-DENY")

    def test_from_requirements_fastapi_permission_source_unavailable_does_not_mutate(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-SCOPE-SOURCE-DOWN")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._enable_fastapi_material_purchase_actions(write=True)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = "[]"

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._scope_headers("req-a6-from-req-source-down"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-source-down",
            ),
        )

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseIdempotency).count(), 0)
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_id).one()
            self.assertEqual(str(requirement.status), "pending")
            audit = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.event_type, "PERMISSION_SOURCE_UNAVAILABLE")
            self.assertEqual(audit.resource_type, "MATERIAL_PURCHASE_REQUIREMENT")

    def test_from_requirements_fastapi_scope_allowed_creates_order(self) -> None:
        requirement_id = self._seed_requirement(requirement_no="REQ-A6-SCOPE-ALLOW-CREATE")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        self._enable_fastapi_material_purchase_actions(write=True)
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "a6.scope.user": {
                        "companies": [self.COMPANY],
                        "item_codes": [self.MATERIAL],
                        "suppliers": ["SUP-A6"],
                        "warehouses": [self.WAREHOUSE],
                    }
                }
            }
        )

        response = self.client.post(
            "/api/material-purchase/orders/from-requirements",
            headers=self._scope_headers("req-a6-from-req-scope-allow"),
            json=self._from_requirements_payload(
                requirement_ids=[requirement_id],
                idempotency_key="idem-a6-scope-allow",
                purchase_no="PO-A6-SCOPE-ALLOW",
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["code"], "0")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMaterialPurchaseOrder).count(), 1)
            requirement = session.query(LyMaterialPurchaseRequirement).filter_by(id=requirement_id).one()
            self.assertEqual(str(requirement.status), "purchased")
            self.assertEqual(str(requirement.purchase_no), "PO-A6-SCOPE-ALLOW")

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
