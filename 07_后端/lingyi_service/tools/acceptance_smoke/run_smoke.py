"""Acceptance smoke checks for frontend readiness without starting a server."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.main as main_module  # noqa: E402
from app.main import app  # noqa: E402
from app.data.frontend_readiness_seed import DEFAULT_COMPANY  # noqa: E402
from app.data.frontend_readiness_seed import GAP_LIST_ROWS  # noqa: E402
from app.data.frontend_readiness_seed import QUALITY_STATISTICS_SEED  # noqa: E402
from app.data.frontend_readiness_seed import QUALITY_TREND_SEED  # noqa: E402
from app.data.frontend_readiness_seed import WORK_ORDER_TRAIL_SEED  # noqa: E402
from app.models.audit import Base as AuditBase  # noqa: E402
from app.models.factory_statement import Base as FactoryStatementBase  # noqa: E402
from app.models.factory_statement import LyFactoryStatement  # noqa: E402
from app.models.factory_statement import LyFactoryStatementPayableOutbox  # noqa: E402
from app.models.material_purchase import Base as MaterialPurchaseBase  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrder  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrderItem  # noqa: E402
from app.models.quality import Base as QualityBase  # noqa: E402
from app.models.quality import LyQualityInspection  # noqa: E402
from app.models.sales_order import Base as SalesOrderBase  # noqa: E402
from app.models.sales_order import LyDeliveryInvoice  # noqa: E402
from app.models.style_profit import Base as StyleProfitBase  # noqa: E402
from app.models.style_profit import LyStyleProfitSnapshot  # noqa: E402
from app.models.production import Base as ProductionBase  # noqa: E402
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
from app.routers.material_purchase import get_db_session as material_purchase_db_dep  # noqa: E402
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

GAP_PATHS = [
    "/api/subcontract/factories",
    "/api/bom/colors",
    "/api/bom/sizes",
    "/api/bom/sample-progress",
    "/api/production/material-issues",
    "/api/bom/material-requests",
    "/api/subcontract/material-issues",
    "/api/subcontract/receipts",
    "/api/subcontract/return-materials",
    "/api/sales-inventory/delivery-addresses",
    "/api/factory-statements/settlement-methods",
    "/api/factory-statements/invoice-types",
    "/api/bom/sample-types",
    "/api/factory-statements/expense-types",
    "/api/bom/size-sortings",
    "/api/sales-inventory/sales-channels",
    "/api/factory-statements/cashier-accounts",
    "/api/bom/size-chart-templates",
    "/api/bom/sample-orders",
]

WRITE_FLOW_PATHS = [
    "/api/production/readiness/work-order-flow",
    "/api/bom/readiness/procurement-flow",
    "/api/subcontract/readiness/subcontract-flow",
    "/api/production/readiness/inventory-finance-flow",
    "/api/quality/readiness/quality-flow",
    "/api/workshop/readiness/wage-flow",
    "/api/style-profit/readiness/profit-flow",
]

FIELD_EXPECTATIONS = {
    "/api/production/material-issues": {"work_order", "material_item_code", "required_qty", "issued_qty"},
    "/api/bom/material-requests": {"request_no", "material_item_code", "supplier_name", "qty", "status"},
    "/api/warehouse/purchase-receipts": {"receipt_no", "purchase_no", "material_item_code", "received_qty"},
    "/api/factory-statements/purchase-invoices": {
        "purchase_invoice_name",
        "supplier",
        "grand_total",
        "outstanding_amount",
    },
    "/api/subcontract/material-issues": {"subcontract_no", "material_item_code", "issued_qty", "pending_qty"},
    "/api/subcontract/receipts": {"subcontract_no", "receipt_batch_no", "received_qty", "accepted_qty"},
    "/api/subcontract/return-materials": {
        "subcontract_no",
        "material_item_code",
        "planned_return_qty",
        "returned_qty",
    },
    "/api/warehouse/finished-goods-inbound": {"reservation_no", "item_code", "reserve_qty", "inbound_qty"},
    "/api/sales-inventory/delivery-notes": {"delivery_note", "sales_order", "customer", "delivered_qty"},
    "/api/sales-inventory/sales-invoices": {"sales_invoice", "sales_order", "grand_total", "outstanding_amount"},
    "/api/warehouse/inventory-balance-reconciliation": {"warehouse", "item_code", "book_qty", "actual_qty", "diff_qty"},
}

WRITE_FLOW_EXPECTATIONS = {
    "/api/production/readiness/work-order-flow": {"plan_id", "event_key", "sync_status", "work_order", "sales_order"},
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
    "/api/workshop/readiness/wage-flow": {"work_order", "job_card", "process_name", "completed_qty", "wage_amount"},
    "/api/style-profit/readiness/profit-flow": {
        "snapshot_no",
        "sales_order",
        "actual_total_cost",
        "profit_amount",
        "profit_rate",
    },
}

REAL_REUSE_EXPECTATIONS = {
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
        "process_type_code",
        "process_type_name",
        "process_name",
        "sequence_no",
        "unit_rate",
        "status",
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
    "/api/factory-statements/factory-reconciliations": {"reconciliation_no", "factory_name", "pending_amount"},
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
    "/api/warehouse/inventory-balance-reconciliation": {"warehouse", "item_code", "book_qty", "actual_qty", "diff_qty"},
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


def _patches_for_real_reuse_endpoints():
    return [
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


def _headers(*, request_id: str | None = None) -> dict[str, str]:
    headers = {
        "X-LY-Dev-User": "frontend.readiness.smoke",
        "X-LY-Dev-Roles": "System Manager",
    }
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def _carrier_code(value: object, *, length: int = 3) -> str:
    normalized = str(value).strip()
    hash_value = 2166136261
    for byte in normalized.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return f"{hash_value:08X}"[-length:]


def _decimal_text(value: object) -> str:
    normalized = format(Decimal(str(value)).normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _warehouse_request_id(
    *,
    scenario_tag: str,
    idempotency_key: str,
    source_ref: str,
    warehouse: str,
    item_code: str,
    quantity: object,
    business_date: str,
) -> str:
    return "-".join(
        [
            scenario_tag,
            "RW",
            "C",
            _carrier_code(idempotency_key),
            _carrier_code(source_ref),
            _carrier_code(warehouse),
            _carrier_code(item_code),
            _carrier_code(_decimal_text(quantity)),
            _carrier_code(business_date),
            _carrier_code("C"),
        ]
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    AuditBase.metadata.create_all(bind=engine)
    ProductionBase.metadata.create_all(bind=engine)
    QualityBase.metadata.create_all(bind=engine)
    StyleProfitBase.metadata.create_all(bind=engine)
    FactoryStatementBase.metadata.create_all(bind=engine)
    MaterialPurchaseBase.metadata.create_all(bind=engine)
    SalesOrderBase.metadata.create_all(bind=engine)

    def _override_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    old_session_local = main_module.SessionLocal
    main_module.SessionLocal = session_local
    app.dependency_overrides[auth_db_dep] = _override_db
    app.dependency_overrides[bom_db_dep] = _override_db
    app.dependency_overrides[cross_module_db_dep] = _override_db
    app.dependency_overrides[sales_inventory_db_dep] = _override_db
    app.dependency_overrides[dashboard_db_dep] = _override_db
    app.dependency_overrides[production_db_dep] = _override_db
    app.dependency_overrides[factory_statement_db_dep] = _override_db
    app.dependency_overrides[material_purchase_db_dep] = _override_db
    app.dependency_overrides[quality_db_dep] = _override_db
    app.dependency_overrides[report_db_dep] = _override_db
    app.dependency_overrides[style_profit_db_dep] = _override_db
    app.dependency_overrides[subcontract_db_dep] = _override_db
    app.dependency_overrides[system_db_dep] = _override_db
    app.dependency_overrides[warehouse_db_dep] = _override_db
    app.dependency_overrides[workshop_db_dep] = _override_db

    try:
        client = TestClient(app)

        unauthorized = client.get("/api/bom/sample-types")
        _assert(unauthorized.status_code == 401, f"unauthorized expected 401, got {unauthorized.status_code}")
        _assert(isinstance(unauthorized.json().get("data"), dict), "401 envelope data must be an object")
        unauthorized_write = client.post("/api/production/readiness/work-order-flow", json={})
        _assert(
            unauthorized_write.status_code == 401,
            f"unauthorized write expected 401, got {unauthorized_write.status_code}",
        )
        _assert(isinstance(unauthorized_write.json().get("data"), dict), "write 401 envelope data must be an object")

        for path in GAP_PATHS:
            response = client.get(path, headers=_headers())
            _assert(response.status_code == 200, f"{path} expected 200, got {response.status_code}: {response.text}")
            payload = response.json()
            _assert(payload.get("code") == "0", f"{path} envelope code mismatch: {payload}")
            data = payload.get("data") or {}
            _assert(set(data.keys()) == {"items", "total", "page", "page_size"}, f"{path} pagination shape mismatch: {data}")
            _assert(isinstance(data["items"], list), f"{path} items must be a list")
            if path in FIELD_EXPECTATIONS:
                _assert(data["items"], f"{path} should include dev seed rows")
                missing = FIELD_EXPECTATIONS[path] - set(data["items"][0].keys())
                _assert(not missing, f"{path} missing contract fields: {sorted(missing)}")

        for path in WRITE_FLOW_PATHS:
            response = client.post(
                path,
                headers=_headers(),
                json={
                    "scenario_tag": "FR-WRITE-FLOW-001",
                    "idempotency_key": "FR-WRITE-FLOW-IDEM-001",
                    "request_id": "FR-WRITE-FLOW-REQ-001",
                    "operation": "frontend_readiness",
                },
            )
            _assert(response.status_code == 200, f"{path} expected 200, got {response.status_code}: {response.text}")
            payload = response.json()
            _assert(payload.get("code") == "0", f"{path} envelope code mismatch: {payload}")
            data = payload.get("data") or {}
            missing = WRITE_FLOW_EXPECTATIONS[path] - set(data.keys())
            _assert(not missing, f"{path} missing flow fields: {sorted(missing)}")
            _assert(data.get("scenario_tag") == "FR-WRITE-FLOW-001", f"{path} scenario_tag carrier mismatch")
            _assert(data.get("idempotency_key") == "FR-WRITE-FLOW-IDEM-001", f"{path} idempotency carrier mismatch")

        with session_local() as session:
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
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
                    created_by="frontend.readiness.smoke",
                )
            )
            session.commit()

        with ExitStack() as stack:
            for patcher in _patches_for_real_reuse_endpoints():
                stack.enter_context(patcher)
            for path, expected_fields in REAL_REUSE_EXPECTATIONS.items():
                response = client.get(path, headers=_headers())
                _assert(response.status_code == 200, f"{path} expected 200, got {response.status_code}: {response.text}")
                payload = response.json()
                _assert(payload.get("code") == "0", f"{path} envelope code mismatch: {payload}")
                data = payload.get("data") or {}
                items = data.get("items")
                _assert(isinstance(items, list), f"{path} items must be a list: {data}")
                _assert(bool(items), f"{path} should include dev seed rows")
                missing = expected_fields - set(items[0].keys())
                _assert(not missing, f"{path} missing contract fields: {sorted(missing)}")

            style_costs_empty = client.get("/api/style-profit/style-costs", headers=_headers())
            _assert(style_costs_empty.status_code == 200, style_costs_empty.text)
            _assert(
                style_costs_empty.json()["data"] == {"items": [], "total": 0, "page": 1, "page_size": 20},
                "style-costs empty scope pagination mismatch",
            )

            stats = client.get("/api/quality/statistics", headers=_headers())
            _assert(stats.status_code == 200, stats.text)
            _assert(
                {"total_count", "total_inspected_qty", "overall_defect_rate"}.issubset(stats.json()["data"].keys()),
                "quality statistics fields mismatch",
            )
            trend = client.get("/api/quality/statistics/trend", headers=_headers())
            _assert(trend.status_code == 200, trend.text)
            _assert(bool(trend.json()["data"]["points"]), "quality trend points missing")
            trail = client.get(f"/api/cross-module/work-order-trail/WO-FR-001?company={DEFAULT_COMPANY}", headers=_headers())
            _assert(trail.status_code == 200, trail.text)
            _assert(trail.json()["data"]["work_order"]["work_order_id"] == "WO-FR-001", "work-order trail id mismatch")

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
            sales_orders = client.get("/api/sales-inventory/sales-orders?page=1&page_size=2", headers=_headers())
            customers = client.get("/api/sales-inventory/customers?page_size=2", headers=_headers())
        _assert(sales_orders.status_code == 200, sales_orders.text)
        _assert(len(sales_orders.json()["data"]["items"]) <= 2, "sales orders page_size=2 was not enforced")
        _assert(customers.status_code == 200, customers.text)
        _assert(len(customers.json()["data"]["items"]) <= 2, "customers page_size=2 was not enforced")

        dashboard = client.get("/api/dashboard/overview", headers=_headers())
        _assert(dashboard.status_code == 200, dashboard.text)
        _assert(dashboard.json()["data"]["company"] == "LY-FRONTEND-DEV", "dashboard default company mismatch")

        purchase_company = "COMP-SMOKE"
        purchase_no = "PO-SMOKE-001"
        purchase_supplier = "SUP-SMOKE"
        purchase_item = "FAB-SMOKE"
        purchase_warehouse = "WH-SMOKE"
        purchase_scenario = "Z003-WAREHOUSE-20260617-201"
        purchase_business_date = date(2026, 6, 17).isoformat()
        purchase_order = client.post(
            "/api/material-purchase/orders",
            headers=_headers(),
            json={
                "operation": "create",
                "company": purchase_company,
                "purchase_no": purchase_no,
                "supplier_name": purchase_supplier,
                "transaction_date": purchase_business_date,
                "expected_delivery_date": None,
                "currency": "CNY",
                "idempotency_key": "material-purchase:smoke:order:001",
                "items": [
                    {
                        "material_item_code": purchase_item,
                        "material_name": "Smoke Fabric",
                        "qty": "20",
                        "uom": "米",
                        "unit_price": "12.5",
                        "warehouse": purchase_warehouse,
                    }
                ],
            },
        )
        _assert(purchase_order.status_code == 201, purchase_order.text)

        stock_idempotency = f"{purchase_scenario}:stock:stock-entry:smoke:001"
        stock_source_ref = f"{purchase_scenario}:purchase:{purchase_no}"
        stock_request_id = _warehouse_request_id(
            scenario_tag=purchase_scenario,
            idempotency_key=stock_idempotency,
            source_ref=stock_source_ref,
            warehouse=purchase_warehouse,
            item_code=purchase_item,
            quantity="20",
            business_date=purchase_business_date,
        )
        previous_app_env = os.environ.get("APP_ENV")
        previous_db_url = os.environ.get("LINGYI_DB_URL")
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        try:
            stock_receipt = client.post(
                "/api/warehouse/stock-entry-drafts",
                headers=_headers(request_id=stock_request_id),
                json={
                    "company": purchase_company,
                    "purpose": "Material Receipt",
                    "source_type": "material_purchase_order",
                    "source_id": stock_source_ref,
                    "source_ref": stock_source_ref,
                    "warehouse": purchase_warehouse,
                    "item_code": purchase_item,
                    "operation": "create_stock_entry_draft",
                    "quantity": "20",
                    "business_date": purchase_business_date,
                    "status_action": "create",
                    "scenario_tag": purchase_scenario,
                    "target_warehouse": purchase_warehouse,
                    "idempotency_key": stock_idempotency,
                    "items": [
                        {
                            "item_code": purchase_item,
                            "qty": "20",
                            "uom": "米",
                            "target_warehouse": purchase_warehouse,
                        }
                    ],
                },
            )
        finally:
            if previous_app_env is None:
                os.environ.pop("APP_ENV", None)
            else:
                os.environ["APP_ENV"] = previous_app_env
            if previous_db_url is None:
                os.environ.pop("LINGYI_DB_URL", None)
            else:
                os.environ["LINGYI_DB_URL"] = previous_db_url
        _assert(stock_receipt.status_code == 201, stock_receipt.text)

        purchase_orders = client.get(
            f"/api/material-purchase/orders?page=1&page_size=100&keyword={purchase_no}",
            headers=_headers(),
        )
        _assert(purchase_orders.status_code == 200, purchase_orders.text)
        purchase_order_rows = purchase_orders.json()["data"]["items"]
        _assert(purchase_order_rows and purchase_order_rows[0]["purchase_no"] == purchase_no, "purchase order readback missing")
        _assert(Decimal(str(purchase_order_rows[0]["received_qty"])) == Decimal("20.000000"), "purchase received qty mismatch")
        _assert(purchase_order_rows[0]["status"] == "received", "purchase order status should be received")

        stock_drafts = client.get(
            "/api/warehouse/stock-entry-drafts?purpose=Material%20Receipt&page=1&page_size=100",
            headers=_headers(),
        )
        _assert(stock_drafts.status_code == 200, stock_drafts.text)
        _assert(
            any(row["source_id"] == stock_source_ref for row in stock_drafts.json()["data"]["items"]),
            "warehouse stock receipt draft readback missing",
        )

        purchase_invoice = client.post(
            "/api/material-purchase/purchase-invoices",
            headers=_headers(request_id="req-material-purchase-invoice-smoke-001"),
            json={
                "operation": "create_purchase_invoice",
                "company": purchase_company,
                "purchase_no": purchase_no,
                "supplier_name": purchase_supplier,
                "material_item_code": purchase_item,
                "qty": "20",
                "rate": "12.5",
                "posting_date": purchase_business_date,
                "due_date": date(2026, 7, 17).isoformat(),
                "purchase_invoice": "PINV-SMOKE-001",
                "source_ref": "PINV-SMOKE-SRC-001",
                "idempotency_key": "material-purchase-invoice:smoke:001",
                "scenario_tag": None,
            },
        )
        _assert(purchase_invoice.status_code == 201, purchase_invoice.text)
        _assert(
            Decimal(str(purchase_invoice.json()["data"]["outstanding_amount"])) == Decimal("250.000000"),
            "purchase invoice outstanding mismatch",
        )

        purchase_payment = client.post(
            "/api/material-purchase/purchase-payments",
            headers=_headers(request_id="req-material-purchase-payment-smoke-001"),
            json={
                "operation": "create_purchase_payment",
                "company": purchase_company,
                "purchase_invoice": "PINV-SMOKE-001",
                "supplier_name": purchase_supplier,
                "posting_date": purchase_business_date,
                "paid_amount": "100",
                "mode_of_payment": "Bank Transfer",
                "reference_no": "BANK-SMOKE-001",
                "reference_date": purchase_business_date,
                "payment_entry": "PP-SMOKE-001",
                "source_ref": "PP-SMOKE-SRC-001",
                "idempotency_key": "material-purchase-payment:smoke:001",
                "scenario_tag": None,
            },
        )
        _assert(purchase_payment.status_code == 201, purchase_payment.text)
        _assert(
            Decimal(str(purchase_payment.json()["data"]["outstanding_after"])) == Decimal("150.000000"),
            "purchase payment outstanding_after mismatch",
        )

        refreshed_invoice = client.get(
            "/api/material-purchase/purchase-invoices?page=1&page_size=100&keyword=PINV-SMOKE-001",
            headers=_headers(),
        )
        _assert(refreshed_invoice.status_code == 200, refreshed_invoice.text)
        invoice_rows = refreshed_invoice.json()["data"]["items"]
        _assert(invoice_rows and invoice_rows[0]["status"] == "partly_paid", "purchase invoice payment status mismatch")
        _assert(
            Decimal(str(invoice_rows[0]["outstanding_amount"])) == Decimal("150.000000"),
            "purchase invoice refreshed outstanding mismatch",
        )

        purchase_payments = client.get(
            "/api/material-purchase/purchase-payments?page=1&page_size=100&keyword=PP-SMOKE-001",
            headers=_headers(),
        )
        _assert(purchase_payments.status_code == 200, purchase_payments.text)
        payment_rows = purchase_payments.json()["data"]["items"]
        _assert(payment_rows and payment_rows[0]["payment_entry"] == "PP-SMOKE-001", "purchase payment readback missing")

        print("acceptance_smoke: OK")
        return 0
    finally:
        main_module.SessionLocal = old_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        app.dependency_overrides.pop(cross_module_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(dashboard_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        app.dependency_overrides.pop(factory_statement_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        app.dependency_overrides.pop(quality_db_dep, None)
        app.dependency_overrides.pop(report_db_dep, None)
        app.dependency_overrides.pop(style_profit_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        app.dependency_overrides.pop(system_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
