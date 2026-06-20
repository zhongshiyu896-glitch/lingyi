"""Frontend readiness acceptance tests for development-only read endpoints."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

import app.main as main_module  # noqa: E402
from app.main import app  # noqa: E402
from app.data.frontend_readiness_seed import DEFAULT_COMPANY  # noqa: E402
from app.data.frontend_readiness_seed import GAP_LIST_ROWS  # noqa: E402
from app.data.frontend_readiness_seed import QUALITY_STATISTICS_SEED  # noqa: E402
from app.data.frontend_readiness_seed import QUALITY_TREND_SEED  # noqa: E402
from app.data.frontend_readiness_seed import WORK_ORDER_TRAIL_SEED  # noqa: E402
from app.models.audit import Base as AuditBase  # noqa: E402
from app.models.audit import LyOperationAuditLog  # noqa: E402
from app.models.audit import LySecurityAuditLog  # noqa: E402
from app.models.bom import Base as BomBase  # noqa: E402
from app.models.bom import LyFoundationTemplate  # noqa: E402
from app.models.bom import LyFoundationTemplateNode  # noqa: E402
from app.models.factory_statement import Base as FactoryStatementBase  # noqa: E402
from app.models.factory_statement import LyFactoryStatement  # noqa: E402
from app.models.factory_statement import LyFactoryStatementPayableOutbox  # noqa: E402
from app.models.factory_statement import LyFactoryStatementPayment  # noqa: E402
from app.models.material_purchase import Base as MaterialPurchaseBase  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrder  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrderItem  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseRequirement  # noqa: E402
from app.models.production import Base as ProductionBase  # noqa: E402
from app.models.quality import Base as QualityBase  # noqa: E402
from app.models.quality import LyQualityInspection  # noqa: E402
from app.models.sales_order import Base as SalesOrderBase  # noqa: E402
from app.models.sales_order import LyDeliveryInvoice  # noqa: E402
from app.models.style_profit import Base as StyleProfitBase  # noqa: E402
from app.models.style_profit import LyStyleProfitSnapshot  # noqa: E402
from app.models.subcontract import Base as SubcontractBase  # noqa: E402
from app.models.subcontract import LySubcontractMaterial  # noqa: E402
from app.models.subcontract import LySubcontractOrder  # noqa: E402
from app.models.subcontract import LySubcontractReceipt  # noqa: E402
from app.models.subcontract import LySubcontractStockOutbox  # noqa: E402
from app.models.warehouse import LyWarehouseInventoryCount  # noqa: E402
from app.models.warehouse import LyWarehouseInventoryCountItem  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryDraft  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryDraftItem  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent  # noqa: E402
from app.routers.auth import get_db_session as auth_db_dep  # noqa: E402
from app.routers.bom import get_db_session as bom_db_dep  # noqa: E402
from app.routers.cross_module_view import get_db_session as cross_module_db_dep  # noqa: E402
from app.routers.dashboard import get_db_session as dashboard_db_dep  # noqa: E402
from app.routers.factory_statement import get_db_session as factory_statement_db_dep  # noqa: E402
from app.routers.production import get_db_session as production_db_dep  # noqa: E402
from app.routers.quality import get_db_session as quality_db_dep  # noqa: E402
from app.routers.report import get_db_session as report_db_dep  # noqa: E402
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep  # noqa: E402
from app.routers.style_profit import get_db_session as style_profit_db_dep  # noqa: E402
from app.routers.subcontract import get_db_session as subcontract_db_dep  # noqa: E402
from app.routers.system_management import get_db_session as system_db_dep  # noqa: E402
from app.routers.warehouse import get_db_session as warehouse_db_dep  # noqa: E402
from app.routers.workshop import get_db_session as workshop_db_dep  # noqa: E402
from app.schemas.cross_module_view import CrossModuleWorkOrderTrailData  # noqa: E402
from app.schemas.production import ProductionOrderIOQuantityListData  # noqa: E402
from app.schemas.production import ProductionFollowupTemplateListData  # noqa: E402
from app.schemas.production import ProductionPlanListData  # noqa: E402
from app.schemas.production import ProductionWorkOrderListData  # noqa: E402
from app.schemas.quality import QualityInspectionListData  # noqa: E402
from app.schemas.quality import QualityStatisticsData  # noqa: E402
from app.schemas.quality import QualityStatisticsTrendData  # noqa: E402
from app.schemas.report import ReportApprovalReportData  # noqa: E402
from app.schemas.report import ReportCatalogListData  # noqa: E402
from app.schemas.report import ReportEmployeeTaskStatisticsData  # noqa: E402
from app.schemas.sales_inventory import SalesInventoryListData  # noqa: E402
from app.schemas.sales_inventory import SupplierItem  # noqa: E402
from app.schemas.style_profit import StyleProfitSnapshotListData  # noqa: E402
from app.schemas.system_management import SystemApprovalFlowCatalogData  # noqa: E402
from app.schemas.warehouse import WarehouseStockSummaryData  # noqa: E402
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter  # noqa: E402


class _DumpablePage:
    def __init__(self, payload: dict[str, object]) -> None:
        self.items = [SimpleNamespace(**item) for item in payload["items"]]
        self.total = payload.get("total", len(self.items))
        self.page = payload.get("page", 1)
        self.page_size = payload.get("page_size", 20)
        self._extra = {key: value for key, value in payload.items() if key not in {"items", "total", "page", "page_size"}}

    def model_dump(self, *args, **kwargs) -> dict[str, object]:  # noqa: ANN002, ANN003, ARG002
        return {
            "items": [vars(item) for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            **self._extra,
        }


def _page_payload(seed_key: str, *, page: int = 1, page_size: int = 20) -> dict[str, object]:
    rows = GAP_LIST_ROWS[seed_key]
    return {"items": rows, "total": len(rows), "page": page, "page_size": page_size}


class FrontendReadinessTest(unittest.TestCase):
    """Validate the frontend readiness contract without starting a server."""

    gap_paths = [
        "/api/subcontract/factories",
        "/api/bom/colors",
        "/api/bom/sizes",
        "/api/bom/sample-progress",
        "/api/bom/material-requests",
        "/api/subcontract/material-issues",
        "/api/subcontract/receipts",
        "/api/sales-inventory/delivery-addresses",
        "/api/factory-statements/settlement-methods",
        "/api/factory-statements/invoice-types",
        "/api/bom/sample-types",
        "/api/factory-statements/expense-types",
        "/api/bom/size-sortings",
        "/api/sales-inventory/sales-channels",
        "/api/factory-statements/cashier-accounts",
        "/api/bom/sample-orders",
    ]
    write_flow_paths = [
        "/api/production/readiness/work-order-flow",
        "/api/bom/readiness/procurement-flow",
        "/api/subcontract/readiness/subcontract-flow",
        "/api/production/readiness/inventory-finance-flow",
        "/api/quality/readiness/quality-flow",
        "/api/workshop/readiness/wage-flow",
        "/api/style-profit/readiness/profit-flow",
    ]
    real_reuse_expectations = {
        "/api/factory-statements/supplier-evaluations": {"evaluation_no", "supplier", "score", "review_status"},
        "/api/factory-statements/factory-evaluations": {"evaluation_no", "factory_name", "score", "review_status"},
        "/api/bom/material-gallery": {"bom_no", "item_code", "material_item_code", "qty_per_piece"},
        "/api/bom/fabrics": {"fabric_name", "material_item_code", "supplier_name", "qty_per_piece"},
        "/api/bom/accessories-packaging": {"material_name", "category", "supplier_name", "qty_per_piece"},
        "/api/bom/materials": {"item_code", "material_item_code", "material_type_name", "supplier_name", "status"},
        "/api/bom/material-categories": {"material_type_code", "material_type_name", "material_group", "status"},
        "/api/bom/units": {"unit_code", "unit_name", "base_unit", "precision", "status"},
        "/api/bom/styles": {"bom_no", "item_code", "version_no", "is_default", "status"},
        "/api/bom/style-bom-process": {"bom_no", "item_code", "process_name", "sequence_no", "unit_rate"},
        "/api/bom/process-requirement-templates": {
            "id",
            "company",
            "template_type",
            "template_code",
            "name",
            "status",
            "nodes",
        },
        "/api/bom/size-chart-templates": {
            "id",
            "company",
            "template_type",
            "template_code",
            "name",
            "status",
            "nodes",
        },
        "/api/bom/purchase-orders": {"purchase_no", "supplier_name", "material_item_code", "total_amount"},
        "/api/production/plans": {"plan_no", "sales_order", "item_code", "planned_qty"},
        "/api/production/work-orders": {"plan_no", "sales_order", "item_code", "work_order", "planned_qty"},
        "/api/production/followup-templates": {
            "template_no",
            "template_name",
            "template_type",
            "followup_role",
            "status",
        },
        "/api/production/order-io-quantities": {"plan_no", "sales_order", "inbound_qty", "outbound_qty"},
        "/api/quality/inspections": {"inspection_no", "source_type", "item_code", "inspected_qty"},
        "/api/workshop/tickets": {"ticket_no", "job_card", "employee", "wage_amount"},
        "/api/workshop/daily-wages": {"employee", "work_date", "net_qty", "wage_amount"},
        "/api/factory-statements/supplier-payable-summaries": {
            "summary_no",
            "supplier",
            "current_payable",
            "ending_payable",
        },
        "/api/subcontract/settlement-candidates": {"subcontract_no", "receipt_batch_no", "net_amount"},
        "/api/factory-statements/factory-reconciliations": {
            "reconciliation_no",
            "factory_name",
            "pending_amount",
        },
        "/api/factory-statements/factory-payable-summaries": {
            "summary_no",
            "factory_name",
            "current_payable",
            "ending_payable",
        },
        f"/api/warehouse/stock-summary?company={DEFAULT_COMPANY}": {"warehouse", "item_code", "actual_qty"},
        "/api/reports/catalog": {"report_key", "name", "report_type", "status"},
        "/api/reports/employee-task-statistics": {"employee_id", "pending_tasks", "completion_rate"},
        "/api/reports/approval-reports": {"approval_no", "approval_type", "approver", "status"},
        "/api/system/approval-flows": {"flow_key", "title", "audit_type", "status"},
        "/api/sales-inventory/suppliers": {"name", "supplier_name", "disabled"},
        "/api/sales-inventory/warehouses": {"name", "company", "warehouse_name", "disabled"},
        "/api/factory-statements/customer-receivables": {
            "summary_no",
            "customer_code",
            "current_receivable",
            "ending_receivable",
        },
        "/api/warehouse/purchase-receipts": {"receipt_no", "purchase_no", "material_item_code", "received_qty"},
        "/api/factory-statements/purchase-invoices": {
            "purchase_invoice_name",
            "supplier",
            "grand_total",
            "outstanding_amount",
        },
        "/api/warehouse/finished-goods-inbound": {"reservation_no", "item_code", "reserve_qty", "inbound_qty"},
        "/api/sales-inventory/delivery-notes": {"delivery_note", "sales_order", "customer", "delivered_qty"},
        "/api/sales-inventory/sales-invoices": {"sales_invoice", "sales_order", "grand_total", "outstanding_amount"},
        "/api/warehouse/inventory-balance-reconciliation": {
            "warehouse",
            "item_code",
            "book_qty",
            "actual_qty",
            "diff_qty",
        },
        "/api/reports/style-profit/snapshots?company=LY-FRONTEND-DEV&item_code=ITEM-FR-001": {
            "snapshot_no",
            "item_code",
            "profit_amount",
        },
        "/api/style-profit/style-costs?company=LY-FRONTEND-DEV&item_code=ITEM-FR-001": {
            "snapshot_no",
            "item_code",
            "actual_total_cost",
            "profit_amount",
        },
    }

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
        AuditBase.metadata.create_all(bind=cls.engine)
        FactoryStatementBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        StyleProfitBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[bom_db_dep] = _override_db
        app.dependency_overrides[cross_module_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[dashboard_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        app.dependency_overrides[factory_statement_db_dep] = _override_db
        app.dependency_overrides[quality_db_dep] = _override_db
        app.dependency_overrides[report_db_dep] = _override_db
        app.dependency_overrides[style_profit_db_dep] = _override_db
        app.dependency_overrides[subcontract_db_dep] = _override_db
        app.dependency_overrides[system_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        app.dependency_overrides[workshop_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        app.dependency_overrides.pop(cross_module_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(dashboard_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        app.dependency_overrides.pop(factory_statement_db_dep, None)
        app.dependency_overrides.pop(quality_db_dep, None)
        app.dependency_overrides.pop(report_db_dep, None)
        app.dependency_overrides.pop(style_profit_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        app.dependency_overrides.pop(system_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LyFactoryStatementPayment).delete()
            session.query(LyFactoryStatementPayableOutbox).delete()
            session.query(LyFactoryStatement).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.query(LyQualityInspection).delete()
            session.query(LyFoundationTemplateNode).delete()
            session.query(LyFoundationTemplate).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.add(
                LyFactoryStatement(
                    id=1,
                    statement_no="FS-FR-001",
                    company=DEFAULT_COMPANY,
                    supplier="SUP-FR-001",
                    from_date=date(2026, 6, 1),
                    to_date=date(2026, 6, 30),
                    source_type="subcontract_inspection",
                    source_count=1,
                    inspected_qty=Decimal("180"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("180"),
                    gross_amount=Decimal("1530.00"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("1530.00"),
                    rejected_rate=Decimal("0"),
                    statement_status="confirmed",
                    idempotency_key="FR-FACTORY-STMT-001",
                    request_hash="fr-factory-stmt-hash",
                    created_by="frontend.readiness",
                )
            )
            session.add(
                LyMaterialPurchaseOrder(
                    id=1,
                    company=DEFAULT_COMPANY,
                    purchase_no="PO-FR-001",
                    supplier_name="Frontend Readiness Supplier",
                    transaction_date=date(2026, 6, 16),
                    expected_delivery_date=date(2026, 6, 24),
                    status="partially_received",
                    total_qty=Decimal("180"),
                    received_qty=Decimal("180"),
                    total_amount=Decimal("1530.00"),
                    currency="CNY",
                    created_by="frontend.readiness",
                )
            )
            session.add(
                LyMaterialPurchaseOrderItem(
                    id=1,
                    order_id=1,
                    company=DEFAULT_COMPANY,
                    item_code="MAT-FR-FABRIC-001",
                    material_item_code="MAT-FR-FABRIC-001",
                    material_name="Frontend Readiness Fabric",
                    qty=Decimal("180"),
                    received_qty=Decimal("180"),
                    uom="Pcs",
                    unit_price=Decimal("8.5"),
                    amount=Decimal("1530.00"),
                    warehouse="WH-FR-001",
                )
            )
            warehouse_created_at = datetime.combine(date(2026, 6, 18), datetime.min.time(), timezone.utc)
            session.add(
                LyWarehouseStockEntryDraft(
                    id=1,
                    company=DEFAULT_COMPANY,
                    purpose="Material Receipt",
                    source_type="material_purchase_order",
                    source_id="PO-FR-001",
                    source_warehouse=None,
                    target_warehouse="WH-FR-001",
                    status="pending_outbox",
                    created_by="frontend.readiness",
                    created_at=warehouse_created_at,
                    idempotency_key="FR-WH-PR-IDEM-001",
                    event_key="FR-WH-PR-EVENT-001",
                )
            )
            session.add(
                LyWarehouseStockEntryDraftItem(
                    id=1,
                    draft_id=1,
                    company=DEFAULT_COMPANY,
                    item_code="MAT-FR-FABRIC-001",
                    qty=Decimal("180"),
                    uom="Pcs",
                    source_warehouse=None,
                    target_warehouse="WH-FR-001",
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    id=1,
                    draft_id=1,
                    event_type="warehouse_stock_entry_sync",
                    event_key="FR-WH-PR-EVENT-001",
                    payload={"business_date": "2026-06-18"},
                    status="in_pending",
                    retry_count=0,
                    created_at=warehouse_created_at,
                )
            )
            fg_created_at = datetime.combine(date(2026, 6, 20), datetime.min.time(), timezone.utc)
            session.add(
                LyWarehouseStockEntryDraft(
                    id=2,
                    company=DEFAULT_COMPANY,
                    purpose="Material Receipt",
                    source_type="finished_goods_inbound",
                    source_id="FGIN-FR-001",
                    source_warehouse=None,
                    target_warehouse="WH-FR-001",
                    status="pending_outbox",
                    created_by="frontend.readiness",
                    created_at=fg_created_at,
                    idempotency_key="FR-WH-FG-IDEM-001",
                    event_key="FR-WH-FG-EVENT-001",
                )
            )
            session.add(
                LyWarehouseStockEntryDraftItem(
                    id=2,
                    draft_id=2,
                    company=DEFAULT_COMPANY,
                    item_code="ITEM-FR-001",
                    qty=Decimal("20"),
                    uom="Pcs",
                    source_warehouse=None,
                    target_warehouse="WH-FR-001",
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    id=2,
                    draft_id=2,
                    event_type="warehouse_stock_entry_sync",
                    event_key="FR-WH-FG-EVENT-001",
                    payload={"business_date": "2026-06-20"},
                    status="in_pending",
                    retry_count=0,
                    created_at=fg_created_at,
                )
            )
            session.add(
                LyWarehouseInventoryCount(
                    id=1,
                    company=DEFAULT_COMPANY,
                    warehouse="WH-FR-001",
                    status="counted",
                    count_no="INV-BAL-FR-LOCAL-001",
                    count_date=date(2026, 6, 22),
                    created_by="frontend.readiness",
                )
            )
            session.add(
                LyWarehouseInventoryCountItem(
                    id=1,
                    count_id=1,
                    company=DEFAULT_COMPANY,
                    warehouse="WH-FR-001",
                    item_code="ITEM-FR-001",
                    system_qty=Decimal("20"),
                    counted_qty=Decimal("20"),
                    variance_qty=Decimal("0"),
                    review_status="accepted",
                )
            )
            session.add(
                LyDeliveryInvoice(
                    id=1,
                    company=DEFAULT_COMPANY,
                    delivery_note="DN-FR-001",
                    sales_invoice="SINV-FR-001",
                    sales_order="SO-FR-001",
                    customer="CUST-FR-001",
                    item_code="ITEM-FR-001",
                    item_name="Frontend Readiness Shirt",
                    warehouse="WH-FR-001",
                    delivered_qty=Decimal("20"),
                    uom="Pcs",
                    rate=Decimal("8"),
                    grand_total=Decimal("160.00"),
                    paid_amount=Decimal("0"),
                    outstanding_amount=Decimal("160.00"),
                    posting_date=date(2026, 6, 21),
                    due_date=date(2026, 7, 21),
                    status="submitted",
                    docstatus=1,
                    source_ref="FR-DI-SRC-001",
                    idempotency_key="FR-DI-IDEM-001",
                    request_hash="fr-delivery-invoice-hash",
                    scenario_tag="FRONTEND-READINESS",
                    created_by="frontend.readiness",
                )
            )
            session.add(
                LyFactoryStatementPayableOutbox(
                    id=1,
                    company=DEFAULT_COMPANY,
                    statement_id=1,
                    statement_no="FS-FR-001",
                    supplier="SUP-FR-001",
                    idempotency_key="FR-FACTORY-PAYABLE-001",
                    request_hash="fr-factory-payable-request-hash",
                    event_key="FR-FACTORY-PAYABLE-EVENT-001",
                    payload_json={"posting_date": "2026-06-19", "currency": "CNY"},
                    payload_hash="fr-factory-payable-payload-hash",
                    status="pending",
                    created_by="frontend.readiness",
                )
            )
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "frontend.readiness",
            "X-LY-Dev-Roles": "System Manager",
        }

    def test_unauthenticated_business_endpoint_returns_401_envelope(self) -> None:
        response = self.client.get("/api/bom/sample-types")

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["code"], "AUTH_UNAUTHORIZED")
        self.assertIsInstance(payload.get("data"), dict)

    def test_unauthenticated_write_flow_endpoint_returns_401_envelope(self) -> None:
        response = self.client.post("/api/production/readiness/work-order-flow", json={})

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["code"], "AUTH_UNAUTHORIZED")
        self.assertIsInstance(payload.get("data"), dict)

    def test_all_gap_endpoints_return_standard_pagination_with_dev_headers(self) -> None:
        for path in self.gap_paths:
            with self.subTest(path=path):
                response = self.client.get(path, headers=self._headers())
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["code"], "0")
                self.assertEqual(set(payload["data"].keys()), {"items", "total", "page", "page_size"})
                self.assertIsInstance(payload["data"]["items"], list)
                self.assertGreaterEqual(payload["data"]["total"], 0)
                self.assertEqual(payload["data"]["page"], 1)
                self.assertGreaterEqual(payload["data"]["page_size"], 1)

    def test_all_write_flow_endpoints_return_standard_envelope_with_dev_headers(self) -> None:
        for path in self.write_flow_paths:
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    headers=self._headers(),
                    json={
                        "scenario_tag": "FR-WRITE-FLOW-001",
                        "idempotency_key": "FR-WRITE-FLOW-IDEM-001",
                        "request_id": "FR-WRITE-FLOW-REQ-001",
                        "operation": "frontend_readiness",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["code"], "0")
                self.assertIsInstance(payload["data"], dict)
                self.assertEqual(payload["data"]["scenario_tag"], "FR-WRITE-FLOW-001")
                self.assertEqual(payload["data"]["idempotency_key"], "FR-WRITE-FLOW-IDEM-001")
                self.assertEqual(payload["data"]["request_id"], "FR-WRITE-FLOW-REQ-001")

    def test_six_module_supplement_fields_are_available(self) -> None:
        field_expectations = {
            "/api/warehouse/purchase-receipts": {"receipt_no", "purchase_no", "material_item_code", "received_qty"},
            "/api/factory-statements/purchase-invoices": {
                "purchase_invoice_name",
                "supplier",
                "grand_total",
                "outstanding_amount",
            },
            "/api/warehouse/finished-goods-inbound": {
                "reservation_no",
                "item_code",
                "reserve_qty",
                "inbound_qty",
            },
            "/api/sales-inventory/delivery-notes": {"delivery_note", "sales_order", "customer", "delivered_qty"},
            "/api/sales-inventory/sales-invoices": {"sales_invoice", "sales_order", "grand_total", "outstanding_amount"},
            "/api/warehouse/inventory-balance-reconciliation": {
                "warehouse",
                "item_code",
                "book_qty",
                "actual_qty",
                "diff_qty",
            },
        }

        for path, expected_fields in field_expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path, headers=self._headers())
                self.assertEqual(response.status_code, 200, response.text)
                items = response.json()["data"]["items"]
                self.assertTrue(items, f"{path} should include dev seed rows")
                self.assertTrue(expected_fields.issubset(items[0].keys()), items[0])

    def test_legacy_material_and_subcontract_readback_paths_use_real_tables(self) -> None:
        real_paths = [
            "/api/bom/material-requests",
            "/api/subcontract/material-issues",
            "/api/subcontract/receipts",
        ]
        for path in real_paths:
            with self.subTest(path=f"{path}:empty"):
                response = self.client.get(path, headers=self._headers())
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()["data"]
                self.assertEqual(data["items"], [])
                self.assertEqual(data["total"], 0)

        with self.SessionLocal() as session:
            session.add(
                LyMaterialPurchaseRequirement(
                    id=1001,
                    company=DEFAULT_COMPANY,
                    requirement_no="REQ-REAL-001",
                    source_type="production_plan",
                    source_id="PLAN-REAL-001",
                    source_no="BOM-REAL-001",
                    plan_id=901,
                    bom_item_id=902,
                    sales_order="SO-REAL-001",
                    item_code="ITEM-REAL-001",
                    material_item_code="MAT-REAL-001",
                    material_name="真实面料",
                    supplier_name="真实供应商",
                    warehouse="WH-REAL-001",
                    required_qty=Decimal("10"),
                    available_qty=Decimal("2"),
                    net_required_qty=Decimal("8"),
                    purchased_qty=Decimal("0"),
                    received_qty=Decimal("0"),
                    uom="米",
                    unit_price=Decimal("3.5"),
                    status="pending",
                    payload={},
                    created_by="frontend.readback.test",
                    created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractOrder(
                    id=2001,
                    subcontract_no="SC-REAL-001",
                    supplier="真实加工厂",
                    item_code="ITEM-REAL-001",
                    company=DEFAULT_COMPANY,
                    bom_id=902,
                    process_name="车缝",
                    planned_qty=Decimal("10"),
                    subcontract_rate=Decimal("1.2"),
                    issued_qty=Decimal("6"),
                    received_qty=Decimal("8"),
                    inspected_qty=Decimal("8"),
                    rejected_qty=Decimal("1"),
                    accepted_qty=Decimal("7"),
                    status="received",
                    settlement_status="unsettled",
                    source_ref="SRC-SC-REAL-001",
                    idempotency_key="IDEM-SC-REAL-001",
                    request_hash="HASH-SC-REAL-001",
                    created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractStockOutbox(
                    id=2002,
                    subcontract_id=2001,
                    event_key="EVT-SC-REAL-ISSUE",
                    stock_action="issue",
                    idempotency_key="IDEM-SC-REAL-ISSUE",
                    payload_hash="HASH-SC-REAL-ISSUE",
                    payload_json={},
                    company=DEFAULT_COMPANY,
                    supplier="真实加工厂",
                    item_code="ITEM-REAL-001",
                    warehouse="WH-REAL-001",
                    action="issue",
                    status="succeeded",
                    payload={},
                    request_id="REQ-SC-REAL-ISSUE",
                    created_by="frontend.readback.test",
                )
            )
            session.add(
                LySubcontractMaterial(
                    id=2003,
                    subcontract_id=2001,
                    stock_outbox_id=2002,
                    company=DEFAULT_COMPANY,
                    issue_batch_no="IB-REAL-001",
                    material_item_code="MAT-REAL-001",
                    required_qty=Decimal("10"),
                    issued_qty=Decimal("6"),
                    sync_status="succeeded",
                    stock_entry_name="STE-ISSUE-REAL-001",
                    created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=2004,
                    subcontract_id=2001,
                    company=DEFAULT_COMPANY,
                    receipt_batch_no="RB-REAL-001",
                    receipt_warehouse="WH-REAL-001",
                    item_code="ITEM-REAL-001",
                    uom="件",
                    received_qty=Decimal("8"),
                    sync_status="succeeded",
                    idempotency_key="IDEM-SC-REAL-RECEIPT",
                    received_by="frontend.readback.test",
                    received_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                    stock_entry_name="STE-RECEIPT-REAL-001",
                    inspected_qty=Decimal("8"),
                    rejected_qty=Decimal("1"),
                    rejected_rate=Decimal("0.125"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("8.4"),
                    inspect_status="received",
                    created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
                )
            )
            session.commit()

        material_requests = self.client.get("/api/bom/material-requests?keyword=REQ-REAL", headers=self._headers())
        self.assertEqual(material_requests.status_code, 200, material_requests.text)
        material_rows = material_requests.json()["data"]["items"]
        self.assertEqual(len(material_rows), 1)
        self.assertEqual(material_rows[0]["request_no"], "REQ-REAL-001")
        self.assertEqual(material_rows[0]["material_item_code"], "MAT-REAL-001")
        self.assertEqual(Decimal(str(material_rows[0]["qty"])), Decimal("8"))
        self.assertNotEqual(material_rows[0]["request_no"], "MR-FR-001")

        material_issues = self.client.get("/api/subcontract/material-issues?keyword=SC-REAL-001", headers=self._headers())
        self.assertEqual(material_issues.status_code, 200, material_issues.text)
        issue_rows = material_issues.json()["data"]["items"]
        self.assertEqual(len(issue_rows), 1)
        self.assertEqual(issue_rows[0]["subcontract_no"], "SC-REAL-001")
        self.assertEqual(issue_rows[0]["material_item_code"], "MAT-REAL-001")
        self.assertEqual(Decimal(str(issue_rows[0]["pending_qty"])), Decimal("4"))
        self.assertNotEqual(issue_rows[0]["subcontract_no"], "SUB-FR-001")

        receipts = self.client.get("/api/subcontract/receipts?keyword=RB-REAL-001", headers=self._headers())
        self.assertEqual(receipts.status_code, 200, receipts.text)
        receipt_rows = receipts.json()["data"]["items"]
        self.assertEqual(len(receipt_rows), 1)
        self.assertEqual(receipt_rows[0]["subcontract_no"], "SC-REAL-001")
        self.assertEqual(receipt_rows[0]["receipt_batch_no"], "RB-REAL-001")
        self.assertEqual(Decimal(str(receipt_rows[0]["accepted_qty"])), Decimal("7"))
        self.assertNotEqual(receipt_rows[0]["subcontract_no"], "SUB-FR-001")

    def test_style_costs_without_scope_returns_empty_page(self) -> None:
        response = self.client.get("/api/style-profit/style-costs", headers=self._headers())
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"], {"items": [], "total": 0, "page": 1, "page_size": 20})

    def test_real_reuse_page_endpoints_are_contract_ready(self) -> None:
        patches = [
            patch("app.services.bom_service.BomService.list_bom", return_value=_DumpablePage(_page_payload("styles"))),
            patch("app.services.bom_service.BomService.list_material_types", return_value=_DumpablePage(_page_payload("materials"))),
            patch("app.services.bom_service.BomService.list_material_units", return_value=_DumpablePage(_page_payload("material_units"))),
            patch("app.services.bom_service.BomService.list_processing_types", return_value=_DumpablePage(_page_payload("style_bom_process"))),
            patch("app.services.bom_service.BomService.list_material_gallery", return_value=_DumpablePage(_page_payload("material_gallery"))),
            patch("app.services.bom_service.BomService.list_fabrics", return_value=_DumpablePage(_page_payload("fabrics"))),
            patch(
                "app.services.bom_service.BomService.list_accessories_packaging",
                return_value=_DumpablePage(_page_payload("accessories_packaging")),
            ),
            patch("app.services.bom_service.BomService.list_purchase_orders", return_value=_DumpablePage(_page_payload("purchase_orders"))),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_supplier_evaluations",
                return_value=_DumpablePage(_page_payload("supplier_evaluations")),
            ),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_factory_evaluations",
                return_value=_DumpablePage(_page_payload("factory_evaluations")),
            ),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_supplier_payable_summaries",
                return_value=_DumpablePage(_page_payload("supplier_payable_summaries")),
            ),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_factory_reconciliations",
                return_value=_DumpablePage(_page_payload("factory_reconciliations")),
            ),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_factory_payable_summaries",
                return_value=_DumpablePage(_page_payload("factory_payable_summaries")),
            ),
            patch(
                "app.services.factory_statement_service.FactoryStatementService.get_customer_receivable_summaries",
                return_value=_DumpablePage(_page_payload("customer_receivables")),
            ),
            patch(
                "app.services.production_service.ProductionService.list_plans",
                return_value=ProductionPlanListData.model_validate(_page_payload("production_plans")),
            ),
            patch(
                "app.services.production_service.ProductionService.list_work_orders",
                return_value=ProductionWorkOrderListData.model_validate(_page_payload("work_orders")),
            ),
            patch(
                "app.services.production_service.ProductionService.list_followup_templates",
                return_value=ProductionFollowupTemplateListData.model_validate(_page_payload("followup_templates")),
            ),
            patch(
                "app.services.production_service.ProductionService.list_order_io_quantities",
                return_value=ProductionOrderIOQuantityListData.model_validate(_page_payload("production_order_io_quantities")),
            ),
            patch(
                "app.services.quality_service.QualityService.list_inspections",
                return_value=QualityInspectionListData.model_validate(_page_payload("quality_inspections")),
            ),
            patch(
                "app.services.quality_service.QualityService.statistics",
                return_value=QualityStatisticsData.model_validate(QUALITY_STATISTICS_SEED),
            ),
            patch(
                "app.services.quality_service.QualityService.statistics_trend",
                return_value=QualityStatisticsTrendData.model_validate(QUALITY_TREND_SEED),
            ),
            patch("app.services.workshop_service.WorkshopService.list_tickets", return_value=_DumpablePage(_page_payload("workshop_tickets"))),
            patch(
                "app.services.workshop_service.WorkshopService.list_daily_wages",
                return_value=_DumpablePage({**_page_payload("workshop_daily_wages"), "total_amount": Decimal("170.00")}),
            ),
            patch(
                "app.services.subcontract_settlement_service.SubcontractSettlementService.list_candidates",
                return_value=_DumpablePage(
                    {
                        **_page_payload("subcontract_settlement_candidates"),
                        "summary": {
                            "line_count": 1,
                            "total_qty": Decimal("20"),
                            "gross_amount": Decimal("170.00"),
                            "deduction_amount": Decimal("0"),
                            "net_amount": Decimal("170.00"),
                        },
                    }
                ),
            ),
            patch(
                "app.services.warehouse_service.WarehouseService.get_stock_summary",
                return_value=WarehouseStockSummaryData(
                    company=DEFAULT_COMPANY,
                    warehouse=None,
                    item_code=None,
                    items=GAP_LIST_ROWS["warehouse_stock_summary"],
                ),
            ),
            patch(
                "app.services.cross_module_view_service.CrossModuleViewService.get_work_order_trail",
                return_value=CrossModuleWorkOrderTrailData.model_validate(WORK_ORDER_TRAIL_SEED),
            ),
            patch(
                "app.services.report_catalog_service.ReportCatalogService.list_catalog",
                return_value=ReportCatalogListData.model_validate(
                    {
                        "items": GAP_LIST_ROWS["report_catalog"],
                        "requested_scope": {"company": None, "source_module": None, "report_type": None},
                    }
                ),
            ),
            patch(
                "app.services.report_catalog_service.ReportCatalogService.get_employee_task_statistics",
                return_value=ReportEmployeeTaskStatisticsData.model_validate(
                    {
                        "items": GAP_LIST_ROWS["employee_task_statistics"],
                        "status_tags": ["normal"],
                        "ui_buttons": ["export"],
                        "ui_table_headers": ["employee_id", "pending_tasks", "completion_rate"],
                        "requested_scope": {},
                    }
                ),
            ),
            patch(
                "app.services.report_catalog_service.ReportCatalogService.get_approval_reports",
                return_value=ReportApprovalReportData.model_validate(
                    {
                        "items": GAP_LIST_ROWS["approval_reports"],
                        "status_tags": ["pending"],
                        "ui_buttons": ["export"],
                        "ui_table_headers": ["approval_no", "approval_type", "approver", "status"],
                        "requested_scope": {},
                    }
                ),
            ),
            patch(
                "app.services.system_config_catalog_service.SystemConfigCatalogService.list_approval_flow_catalog",
                return_value=SystemApprovalFlowCatalogData.model_validate(
                    {
                        "items": GAP_LIST_ROWS["approval_flows"],
                        "total": 1,
                        "audit_type_options": ["purchase_invoice"],
                    }
                ),
            ),
            patch(
                "app.services.sales_inventory_service.SalesInventoryService.list_local_suppliers",
                return_value=SalesInventoryListData[SupplierItem].model_validate(_page_payload("suppliers")),
            ),
            patch.object(
                ERPNextSalesInventoryAdapter,
                "list_warehouses",
                return_value=(GAP_LIST_ROWS["warehouses"], len(GAP_LIST_ROWS["warehouses"])),
            ),
        ]
        with self.SessionLocal() as session:
            quality_seed = GAP_LIST_ROWS["quality_inspections"][0]
            session.add(LyQualityInspection(**quality_seed, updated_by="quality.user"))
            style_seed = GAP_LIST_ROWS["style_profit_snapshots"][0]
            session.add(
                LyStyleProfitSnapshot(
                    id=style_seed["id"],
                    snapshot_no=style_seed["snapshot_no"],
                    company=style_seed["company"],
                    sales_order=style_seed["sales_order"],
                    item_code=style_seed["item_code"],
                    revenue_status=style_seed["revenue_status"],
                    revenue_amount=style_seed["revenue_amount"],
                    actual_revenue_amount=style_seed["revenue_amount"],
                    standard_total_cost=style_seed["standard_total_cost"],
                    actual_total_cost=style_seed["actual_total_cost"],
                    profit_amount=style_seed["profit_amount"],
                    profit_rate=style_seed["profit_rate"],
                    snapshot_status=style_seed["snapshot_status"],
                    allocation_status=style_seed["allocation_status"],
                    include_provisional_subcontract=style_seed["include_provisional_subcontract"],
                    formula_version=style_seed["formula_version"],
                    unresolved_count=style_seed["unresolved_count"],
                    from_date=style_seed["from_date"],
                    to_date=style_seed["to_date"],
                    idempotency_key="FR-STYLE-PROFIT-001",
                    request_hash="fr-style-profit-hash",
                    created_by=style_seed["created_by"],
                    created_at=style_seed["created_at"],
                )
            )
            session.add_all(
                [
                    LyFoundationTemplate(
                        id=1,
                        company=DEFAULT_COMPANY,
                        template_type="workmanship",
                        template_code="FR-WORKMANSHIP-001",
                        name="Frontend Readiness Workmanship",
                        scene="款式资料",
                        status="active",
                        version=1,
                        created_by="frontend.readiness",
                        updated_by="frontend.readiness",
                    ),
                    LyFoundationTemplate(
                        id=2,
                        company=DEFAULT_COMPANY,
                        template_type="size_spec",
                        template_code="FR-SIZE-SPEC-001",
                        name="Frontend Readiness Size Spec",
                        scene="款式资料",
                        status="active",
                        version=1,
                        created_by="frontend.readiness",
                        updated_by="frontend.readiness",
                    ),
                ]
            )
            session.add_all(
                [
                    LyFoundationTemplateNode(
                        id=1,
                        template_id=1,
                        code="FR-WORKMANSHIP-NODE-001",
                        name="缝制要求",
                        node_type="工艺节点",
                        required=True,
                        status="active",
                        sort_no=10,
                        owner="工艺",
                        created_by="frontend.readiness",
                        updated_by="frontend.readiness",
                    ),
                    LyFoundationTemplateNode(
                        id=2,
                        template_id=2,
                        code="FR-SIZE-SPEC-NODE-001",
                        name="胸围",
                        node_type="尺寸点",
                        required=True,
                        status="active",
                        sort_no=10,
                        owner="版房",
                        created_by="frontend.readiness",
                        updated_by="frontend.readiness",
                    ),
                ]
            )
            session.commit()

        with ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            self._assert_real_reuse_paths()

    def _assert_real_reuse_paths(self) -> None:
        for path, expected_fields in self.real_reuse_expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path, headers=self._headers())
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["code"], "0")
                data = payload["data"]
                items = data.get("items")
                self.assertIsInstance(items, list, data)
                self.assertTrue(items, f"{path} should include dev seed rows")
                self.assertTrue(expected_fields.issubset(items[0].keys()), items[0])

        stats = self.client.get("/api/quality/statistics", headers=self._headers())
        self.assertEqual(stats.status_code, 200, stats.text)
        self.assertTrue({"total_count", "total_inspected_qty", "overall_defect_rate"}.issubset(stats.json()["data"]))

        trend = self.client.get("/api/quality/statistics/trend", headers=self._headers())
        self.assertEqual(trend.status_code, 200, trend.text)
        self.assertTrue(trend.json()["data"]["points"])

        trail = self.client.get(
            f"/api/cross-module/work-order-trail/WO-FR-001?company={DEFAULT_COMPANY}",
            headers=self._headers(),
        )
        self.assertEqual(trail.status_code, 200, trail.text)
        self.assertEqual(trail.json()["data"]["work_order"]["work_order_id"], "WO-FR-001")

    def test_minimal_write_flow_contract_fields_are_available(self) -> None:
        flow_expectations = {
            "/api/production/readiness/work-order-flow": {
                "plan_id",
                "plan_no",
                "event_key",
                "sync_status",
                "work_order",
                "sales_order",
            },
            "/api/bom/readiness/procurement-flow": {
                "request_no",
                "purchase_no",
                "receipt_no",
                "purchase_invoice_name",
                "outstanding_amount",
            },
            "/api/subcontract/readiness/subcontract-flow": {
                "subcontract_no",
                "issued_qty",
                "received_qty",
                "statement_no",
                "ending_payable",
            },
            "/api/production/readiness/inventory-finance-flow": {
                "reservation_no",
                "delivery_note",
                "sales_invoice",
                "summary_no",
                "diff_qty",
            },
            "/api/quality/readiness/quality-flow": {
                "inspection_no",
                "work_order",
                "inspected_qty",
                "accepted_qty",
                "rejected_qty",
            },
            "/api/workshop/readiness/wage-flow": {
                "work_order",
                "job_card",
                "process_name",
                "completed_qty",
                "wage_amount",
            },
            "/api/style-profit/readiness/profit-flow": {
                "snapshot_no",
                "sales_order",
                "actual_total_cost",
                "profit_amount",
                "profit_rate",
            },
        }

        for path, expected_fields in flow_expectations.items():
            with self.subTest(path=path):
                response = self.client.post(path, headers=self._headers(), json={})
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()["data"]
                self.assertTrue(expected_fields.issubset(data.keys()), data)

    def test_suppliers_full_reference_path_is_available_in_dev(self) -> None:
        data = SalesInventoryListData[SupplierItem].model_validate(_page_payload("suppliers"))
        with patch("app.services.sales_inventory_service.SalesInventoryService.list_local_suppliers", return_value=data):
            response = self.client.get("/api/sales-inventory/suppliers", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(set(payload["data"]["items"][0].keys()), {"name", "supplier_name", "disabled"})

    def test_sales_orders_and_customers_respect_page_size_two(self) -> None:
        order_rows = [
            {
                "name": f"SO-FR-{index:03d}",
                "company": "LY-FRONTEND-DEV",
                "customer": "CUST-FR-001",
                "transaction_date": "2026-06-16",
                "delivery_date": "2026-06-30",
                "status": "To Deliver",
                "docstatus": 1,
                "grand_total": str(Decimal(index)),
                "currency": "CNY",
            }
            for index in range(1, 4)
        ]
        customer_rows = [
            {"name": f"CUST-FR-{index:03d}", "customer_name": f"Customer {index}", "disabled": 0}
            for index in range(1, 4)
        ]

        with patch.object(ERPNextSalesInventoryAdapter, "list_sales_orders", return_value=(order_rows, 3)), patch.object(
            ERPNextSalesInventoryAdapter,
            "list_customers",
            return_value=(customer_rows, 3),
        ):
            sales_orders = self.client.get(
                "/api/sales-inventory/sales-orders?page=1&page_size=2",
                headers=self._headers(),
            )
            customers = self.client.get(
                "/api/sales-inventory/customers?page_size=2",
                headers=self._headers(),
            )

        self.assertEqual(sales_orders.status_code, 200, sales_orders.text)
        self.assertLessEqual(len(sales_orders.json()["data"]["items"]), 2)
        self.assertEqual(sales_orders.json()["data"]["page_size"], 2)
        self.assertEqual(customers.status_code, 200, customers.text)
        self.assertLessEqual(len(customers.json()["data"]["items"]), 2)
        self.assertEqual(customers.json()["data"]["page_size"], 2)

    def test_dashboard_overview_without_company_uses_default_company_real_overview(self) -> None:
        response = self.client.get("/api/dashboard/overview", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["company"], "LY-FRONTEND-DEV")
        self.assertIn("home_overview", payload["data"])
        self.assertNotIn("local_dev_static_fallback", response.text)


if __name__ == "__main__":
    unittest.main()
