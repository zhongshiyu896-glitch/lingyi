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
from app.models.bom import Base as BomBase  # noqa: E402
from app.models.bom import LyApparelBom  # noqa: E402
from app.models.factory_statement import Base as FactoryStatementBase  # noqa: E402
from app.models.factory_statement import LyFactoryStatement  # noqa: E402
from app.models.factory_statement import LyFactoryStatementPayableOutbox  # noqa: E402
from app.models.master_data import Base as MasterDataBase  # noqa: E402
from app.models.material_purchase import Base as MaterialPurchaseBase  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrder  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseOrderItem  # noqa: E402
from app.models.quality import Base as QualityBase  # noqa: E402
from app.models.quality import LyQualityInspection  # noqa: E402
from app.models.sales_order import Base as SalesOrderBase  # noqa: E402
from app.models.sales_order import LyDeliveryInvoice  # noqa: E402
from app.models.sales_order import LySalesOrder  # noqa: E402
from app.models.sales_order import LySalesOrderItem  # noqa: E402
from app.models.style_profit import Base as StyleProfitBase  # noqa: E402
from app.models.style_profit import LyStyleProfitSnapshot  # noqa: E402
from app.models.subcontract import Base as SubcontractBase  # noqa: E402
from app.models.subcontract import LySubcontractInspection  # noqa: E402
from app.models.subcontract import LySubcontractOrder  # noqa: E402
from app.models.production import Base as ProductionBase  # noqa: E402
from app.models.warehouse import LyWarehouseInventoryCount  # noqa: E402
from app.models.warehouse import LyWarehouseInventoryCountItem  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryDraft  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryDraftItem  # noqa: E402
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent  # noqa: E402
from app.models.workshop import Base as WorkshopBase  # noqa: E402
from app.routers.auth import get_db_session as auth_db_dep  # noqa: E402
from app.routers.bom import get_db_session as bom_db_dep  # noqa: E402
from app.routers.cross_module_view import get_db_session as cross_module_db_dep  # noqa: E402
from app.routers.dashboard import get_db_session as dashboard_db_dep  # noqa: E402
from app.routers.factory_statement import get_db_session as factory_statement_db_dep  # noqa: E402
from app.routers.master_data import get_db_session as master_data_db_dep  # noqa: E402
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
from app.services.quality_service import QualitySourceValidationSnapshot  # noqa: E402


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


def _quality_request_id(
    *,
    scenario_tag: str,
    operation: str,
    idempotency_key: str,
    source_ref: str,
    inspection_ref: str,
    item_code: str,
    result: str,
) -> str:
    operation_code = {"create": "C", "confirm": "F", "cancel": "X", "defects": "D"}[operation]
    return "-".join(
        [
            scenario_tag,
            "QI",
            operation_code,
            _carrier_code(idempotency_key),
            _carrier_code(source_ref),
            _carrier_code(inspection_ref),
            _carrier_code(item_code),
            _carrier_code(result),
        ]
    )


def _workshop_ticket_request_id(payload: dict[str, object]) -> str:
    operation_code = {"register": "R", "reversal": "V", "batch": "B"}[str(payload["operation"])]
    operator_id = payload.get("operator_id") or payload["employee"]
    return "-".join(
        [
            str(payload["scenario_tag"]),
            "RW",
            operation_code,
            _carrier_code(payload["idempotency_key"]),
            _carrier_code(payload["source_ref"]),
            _carrier_code(payload["ticket_key"]),
            _carrier_code(payload["job_card"]),
            _carrier_code(operator_id),
            _carrier_code(payload["batch_no"]),
        ]
    )


def _workshop_wage_request_id(payload: dict[str, object]) -> str:
    company = payload.get("company") or "GLOBAL"
    item_scope = payload.get("item_code") or "GLOBAL"
    effective_from = str(payload["effective_from"]).replace("-", "")
    return (
        f"{payload['scenario_tag']}-RW-"
        f"C{_carrier_code(company, length=4)}-"
        f"P{_carrier_code(payload['process_name'], length=4)}-"
        f"I{_carrier_code(item_scope, length=4)}-"
        f"D{effective_from}"
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _exercise_master_data_smoke(client: TestClient) -> None:
    company = "COMP-MASTER-SMOKE"
    entities = [
        ("customers", "CUST-SMOKE-001", "Smoke Customer", {"customer_name": "Smoke Customer"}),
        ("suppliers", "SUP-SMOKE-001", "Smoke Supplier", {"supplier_name": "Smoke Supplier"}),
        ("factories", "FAC-SMOKE-001", "Smoke Factory", {"factory_name": "Smoke Factory"}),
        ("warehouses", "WH-SMOKE-MD", "Smoke Warehouse", {"warehouse_name": "Smoke Warehouse"}),
        (
            "materials",
            "MAT-SMOKE-001",
            "Smoke Material",
            {"material_kind": "fabric", "material_item_code": "MAT-SMOKE-001"},
        ),
    ]
    for entity_path, code, name, payload in entities:
        create_body = {
            "operation": "create",
            "company": company,
            "code": code,
            "name": name,
            "idempotency_key": f"master-data:{entity_path}:create:smoke",
            "payload": payload,
        }
        created = client.post(f"/api/master-data/{entity_path}", headers=_headers(), json=create_body)
        _assert(created.status_code == 201, f"master data {entity_path} create failed: {created.text}")
        created_data = created.json()["data"]
        record_id = int(created_data["id"])
        _assert(created_data["source"] == "fastapi_master_data", f"master data {entity_path} source mismatch")
        _assert(created_data["code"] == code, f"master data {entity_path} code mismatch")

        replay = client.post(f"/api/master-data/{entity_path}", headers=_headers(), json=create_body)
        _assert(replay.status_code == 201, f"master data {entity_path} replay failed: {replay.text}")
        _assert(int(replay.json()["data"]["id"]) == record_id, f"master data {entity_path} idempotent replay mismatch")

        updated = client.patch(
            f"/api/master-data/{entity_path}/{record_id}",
            headers=_headers(),
            json={
                "operation": "update",
                "company": company,
                "name": f"{name} Updated",
                "idempotency_key": f"master-data:{entity_path}:update:smoke",
                "payload": {**payload, "smoke_updated": True},
            },
        )
        _assert(updated.status_code == 200, f"master data {entity_path} update failed: {updated.text}")
        _assert(updated.json()["data"]["name"] == f"{name} Updated", f"master data {entity_path} update readback mismatch")

        listed = client.get(
            f"/api/master-data/{entity_path}?company={company}&keyword={code}&page=1&page_size=10",
            headers=_headers(),
        )
        _assert(listed.status_code == 200, f"master data {entity_path} list failed: {listed.text}")
        rows = listed.json()["data"]["items"]
        _assert(rows and rows[0]["code"] == code, f"master data {entity_path} list readback missing")

        deactivated = client.post(
            f"/api/master-data/{entity_path}/{record_id}/deactivate",
            headers=_headers(),
            json={
                "operation": "deactivate",
                "company": company,
                "idempotency_key": f"master-data:{entity_path}:deactivate:smoke",
                "reason": "acceptance-smoke",
            },
        )
        _assert(deactivated.status_code == 200, f"master data {entity_path} deactivate failed: {deactivated.text}")
        deactivated_data = deactivated.json()["data"]
        _assert(deactivated_data["disabled"], f"master data {entity_path} disabled flag mismatch")
        _assert(deactivated_data["status"] == "inactive", f"master data {entity_path} inactive status mismatch")

        inactive = client.get(
            f"/api/master-data/{entity_path}?company={company}&keyword={code}&disabled=true&page=1&page_size=10",
            headers=_headers(),
        )
        _assert(inactive.status_code == 200, f"master data {entity_path} inactive list failed: {inactive.text}")
        inactive_rows = inactive.json()["data"]["items"]
        _assert(inactive_rows and inactive_rows[0]["disabled"], f"master data {entity_path} inactive readback missing")


def _exercise_quality_smoke(client: TestClient) -> None:
    scenario_tag = "Z003-QUALITY-INSPECTION-20260617-301"
    company = "COMP-QC-SMOKE"
    item_code = "ITEM-QC-SMOKE"
    source_ref = f"manual:{scenario_tag}:quality-ui-smoke"
    inspection_ref = f"QI:{scenario_tag}:quality-ui-smoke"
    idempotency_key = f"{scenario_tag}:create:smoke"
    create_request_id = _quality_request_id(
        scenario_tag=scenario_tag,
        operation="create",
        idempotency_key=idempotency_key,
        source_ref=source_ref,
        inspection_ref=inspection_ref,
        item_code=item_code,
        result="fail",
    )
    create_payload = {
        "request_id": create_request_id,
        "idempotency_key": idempotency_key,
        "scenario_tag": scenario_tag,
        "source_ref": source_ref,
        "inspection_ref": inspection_ref,
        "source_doc": source_ref,
        "operation": "create",
        "company": company,
        "source_type": "manual",
        "source_id": None,
        "item_code": item_code,
        "supplier": "SUP-QC-SMOKE",
        "warehouse": "WH-QC-SMOKE",
        "inspection_date": date(2026, 6, 17).isoformat(),
        "inspected_qty": "20",
        "accepted_qty": "18",
        "rejected_qty": "2",
        "defect_qty": "2",
        "result": "fail",
        "remark": "acceptance-smoke rework",
        "items": [
            {
                "item_code": item_code,
                "sample_qty": "20",
                "accepted_qty": "18",
                "rejected_qty": "2",
                "defect_qty": "2",
                "result": "fail",
                "remark": "acceptance-smoke rework",
            }
        ],
        "defects": [
            {
                "defect_code": "QC-SMOKE",
                "defect_name": "Smoke Defect",
                "defect_qty": "2",
                "severity": "major",
                "item_line_no": 1,
                "remark": "acceptance-smoke rework",
            }
        ],
    }
    quality_env = {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}
    source_snapshot = QualitySourceValidationSnapshot(
        master_data={
            "company": {"name": company},
            "item": {"name": item_code},
            "supplier": {"name": "SUP-QC-SMOKE", "supplier_name": "SUP-QC-SMOKE"},
            "warehouse": {"name": "WH-QC-SMOKE", "warehouse_name": "WH-QC-SMOKE", "company": company},
        },
        source=None,
    )
    with patch.dict("os.environ", quality_env), patch(
        "app.services.quality_service.QualitySourceValidator.validate_for_payload",
        return_value=source_snapshot,
    ):
        created = client.post(
            "/api/quality/inspections",
            headers=_headers(request_id=create_request_id),
            json=create_payload,
        )
    _assert(created.status_code == 201, created.text)
    created_data = created.json()["data"]
    inspection_id = int(created_data["id"])
    inspection_no = str(created_data["inspection_no"])
    _assert(created_data["status"] == "draft", "quality create status mismatch")
    _assert(created_data["result"] == "fail", "quality create result mismatch")

    listed = client.get(
        f"/api/quality/inspections?item_code={item_code}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(listed.status_code == 200, listed.text)
    list_rows = listed.json()["data"]["items"]
    _assert(
        any(int(row["id"]) == inspection_id for row in list_rows),
        f"quality list readback missing: {listed.text}",
    )

    confirm_source_ref = f"{scenario_tag}/{inspection_no}"
    confirm_idempotency = f"{scenario_tag}:confirm:{inspection_no}:smoke"
    confirm_request_id = _quality_request_id(
        scenario_tag=scenario_tag,
        operation="confirm",
        idempotency_key=confirm_idempotency,
        source_ref=confirm_source_ref,
        inspection_ref=inspection_no,
        item_code=item_code,
        result="fail",
    )
    with patch.dict("os.environ", quality_env):
        confirmed = client.post(
            f"/api/quality/inspections/{inspection_id}/confirm",
            headers=_headers(request_id=confirm_request_id),
            json={
                "request_id": confirm_request_id,
                "idempotency_key": confirm_idempotency,
                "scenario_tag": scenario_tag,
                "source_ref": confirm_source_ref,
                "inspection_ref": inspection_no,
                "source_type": "manual",
                "source_doc": confirm_source_ref,
                "item_code": item_code,
                "operation": "confirm",
                "result": "fail",
                "remark": "acceptance-smoke rework confirm",
            },
        )
    _assert(confirmed.status_code == 200, confirmed.text)
    _assert(confirmed.json()["data"]["status"] == "confirmed", "quality confirm status mismatch")
    _assert(confirmed.json()["data"]["result"] == "fail", "quality confirm result mismatch")


def _exercise_workshop_smoke(client: TestClient) -> None:
    ticket_scenario = "Z003-WORKSHOP-TICKET-20260617-401"
    wage_scenario = "Z002-WORKSHOP-WAGE-20260617-401"
    company = "LY-LOCAL-TEST"
    item_code = "ITEM-WORKSHOP-SMOKE"
    process_name = "sew"
    work_date = date(2026, 6, 17).isoformat()

    wage_payload = {
        "scenario_tag": wage_scenario,
        "idempotency_key": f"{wage_scenario}-IDEMP-CREATE",
        "source_ref": f"{wage_scenario}-SRC-CREATE",
        "item_code": item_code,
        "company": company,
        "process_name": process_name,
        "wage_rate": "2.5",
        "effective_from": "2026-01-01",
        "effective_to": None,
    }
    workshop_env = {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}
    with patch.dict("os.environ", workshop_env):
        wage_created = client.post(
            "/api/workshop/wage-rates",
            headers=_headers(request_id=_workshop_wage_request_id(wage_payload)),
            json=wage_payload,
        )
    _assert(wage_created.status_code == 200, wage_created.text)
    wage_data = wage_created.json()["data"]
    _assert(wage_data["status"] == "active", "workshop wage rate status mismatch")

    wage_listed = client.get(
        f"/api/workshop/wage-rates?item_code={item_code}&company={company}&status=active&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(wage_listed.status_code == 200, wage_listed.text)
    wage_rows = wage_listed.json()["data"]["items"]
    _assert(wage_rows and wage_rows[0]["item_code"] == item_code, "workshop wage rate readback missing")
    _assert(Decimal(str(wage_rows[0]["wage_rate"])) == Decimal("2.500000"), "workshop wage rate value mismatch")

    ticket_payload = {
        "scenario_tag": ticket_scenario,
        "idempotency_key": f"{ticket_scenario}-IDEMP-REGISTER",
        "ticket_key": f"{ticket_scenario}-TICKET-001",
        "job_card": "JC-WORKSHOP-SMOKE",
        "item_code": item_code,
        "employee": "EMP-WORKSHOP-SMOKE",
        "process_name": process_name,
        "color": "black",
        "size": "M",
        "qty": "12",
        "work_date": work_date,
        "source": "manual",
        "source_ref": f"{ticket_scenario}-SRC-REGISTER",
        "operation": "register",
        "operator_id": "frontend.readiness.smoke",
        "batch_no": f"{ticket_scenario}-BATCH-001",
    }
    with patch.dict("os.environ", workshop_env):
        ticket_created = client.post(
            "/api/workshop/tickets/register",
            headers=_headers(request_id=_workshop_ticket_request_id(ticket_payload)),
            json=ticket_payload,
        )
    _assert(ticket_created.status_code == 200, ticket_created.text)
    ticket_data = ticket_created.json()["data"]
    _assert(Decimal(str(ticket_data["unit_wage"])) == Decimal("2.500000"), "workshop ticket unit_wage mismatch")
    _assert(Decimal(str(ticket_data["wage_amount"])) == Decimal("30.000000"), "workshop ticket wage_amount mismatch")

    ticket_listed = client.get(
        f"/api/workshop/tickets?employee=EMP-WORKSHOP-SMOKE&item_code={item_code}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(ticket_listed.status_code == 200, ticket_listed.text)
    ticket_rows = ticket_listed.json()["data"]["items"]
    _assert(ticket_rows and ticket_rows[0]["ticket_key"] == ticket_payload["ticket_key"], "workshop ticket readback missing")

    daily_wages = client.get(
        (
            "/api/workshop/daily-wages?"
            f"employee=EMP-WORKSHOP-SMOKE&from_date={work_date}&to_date={work_date}"
            f"&process_name={process_name}&item_code={item_code}&page=1&page_size=10"
        ),
        headers=_headers(),
    )
    _assert(daily_wages.status_code == 200, daily_wages.text)
    daily_rows = daily_wages.json()["data"]["items"]
    _assert(daily_rows, "workshop daily wage readback missing")
    _assert(Decimal(str(daily_rows[0]["net_qty"])) == Decimal("12.000000"), "workshop daily wage net_qty mismatch")
    _assert(Decimal(str(daily_rows[0]["wage_amount"])) == Decimal("30.000000"), "workshop daily wage amount mismatch")
    _assert(Decimal(str(daily_wages.json()["data"]["total_amount"])) == Decimal("30.000000"), "workshop total_amount mismatch")


def _exercise_finished_goods_inbound_smoke(client: TestClient) -> None:
    scenario_tag = "Z003-WAREHOUSE-20260617-701"
    company = "COMP-FG-SMOKE"
    source_ref = f"{scenario_tag}:finished-goods:FGIN-SMOKE-001"
    warehouse = "WH-FG-SMOKE"
    item_code = "ITEM-FG-SMOKE"
    quantity = "7"
    business_date = date(2026, 6, 17).isoformat()
    idempotency_key = f"{scenario_tag}:fg-inbound:001"
    request_id = _warehouse_request_id(
        scenario_tag=scenario_tag,
        idempotency_key=idempotency_key,
        source_ref=source_ref,
        warehouse=warehouse,
        item_code=item_code,
        quantity=quantity,
        business_date=business_date,
    )
    warehouse_env = {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}
    with patch.dict("os.environ", warehouse_env):
        created = client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=_headers(request_id=request_id),
            json={
                "company": company,
                "purpose": "Material Receipt",
                "source_type": "manual",
                "source_id": source_ref,
                "source_ref": source_ref,
                "warehouse": warehouse,
                "item_code": item_code,
                "operation": "create_stock_entry_draft",
                "quantity": quantity,
                "business_date": business_date,
                "status_action": "create",
                "scenario_tag": scenario_tag,
                "finished_goods_source_id": source_ref,
                "source_warehouse": None,
                "target_warehouse": warehouse,
                "idempotency_key": idempotency_key,
                "items": [
                    {
                        "item_code": item_code,
                        "qty": quantity,
                        "uom": "件",
                        "source_warehouse": None,
                        "target_warehouse": warehouse,
                    }
                ],
            },
        )
    _assert(created.status_code == 201, created.text)
    created_data = created.json()["data"]
    draft_id = int(created_data["id"])
    _assert(created_data["source_type"] == "finished_goods_inbound", "finished goods source_type mismatch")
    _assert(created_data["source_id"] == source_ref, "finished goods source_id mismatch")
    _assert(created_data["target_warehouse"] == warehouse, "finished goods target warehouse mismatch")
    _assert(created_data["status"] == "pending_outbox", "finished goods draft status mismatch")
    _assert(created_data["outbox"]["status"] == "in_pending", "finished goods outbox status mismatch")

    listed = client.get(
        f"/api/warehouse/stock-entry-drafts?purpose=Material%20Receipt&keyword=FGIN-SMOKE-001&page=1&page_size=20",
        headers=_headers(),
    )
    _assert(listed.status_code == 200, listed.text)
    rows = listed.json()["data"]["items"]
    _assert(rows and int(rows[0]["id"]) == draft_id, "finished goods inbound readback missing")
    _assert(rows[0]["source_type"] == "finished_goods_inbound", "finished goods readback source_type mismatch")


def _exercise_sales_delivery_payment_smoke(client: TestClient, session_local) -> None:  # noqa: ANN001
    company = "COMP-SALES-SMOKE"
    customer = "CUST-SALES-SMOKE"
    sales_order = "SO-SALES-SMOKE-001"
    item_code = "ITEM-SALES-SMOKE"
    warehouse = "WH-SALES-SMOKE"
    business_date = date(2026, 6, 17)
    delivery_scenario = "Z003-DELIVERY-INVOICE-20260617-501"
    payment_scenario = "Z003-SALES-PAYMENT-20260617-501"

    with session_local() as session:
        order = LySalesOrder(
            sales_order_no=sales_order,
            source_order_ref="SRC-SALES-SMOKE-ORDER-001",
            company=company,
            customer=customer,
            status="planned",
            docstatus=0,
            transaction_date=business_date,
            delivery_date=date(2026, 6, 30),
            currency="CNY",
            grand_total=Decimal("500"),
            idempotency_key="idem-sales-smoke-order-001",
            request_hash="hash-sales-smoke-order-001",
            scenario_tag="SALES-SMOKE-ORDER",
            payload={},
            created_by="frontend.readiness.smoke",
        )
        session.add(order)
        session.flush()
        session.add(
            LySalesOrderItem(
                sales_order_id=int(order.id),
                company=company,
                line_no=1,
                sales_order_item=f"{sales_order}-001",
                item_code=item_code,
                item_name="Smoke Finished Goods",
                qty=Decimal("10"),
                planned_qty=Decimal("10"),
                delivered_qty=Decimal("0"),
                rate=Decimal("50"),
                amount=Decimal("500"),
                uom="件",
                warehouse=warehouse,
                delivery_date=date(2026, 6, 30),
            )
        )
        receipt = LyWarehouseStockEntryDraft(
            company=company,
            purpose="Material Receipt",
            source_type="finished_goods_inbound",
            source_id="FGIN-SALES-SMOKE-001",
            source_warehouse=None,
            target_warehouse=warehouse,
            status="pending_outbox",
            created_by="frontend.readiness.smoke",
            created_at=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
            idempotency_key="idem-sales-smoke-fg-in-001",
            event_key="sales-smoke-fg-in-001",
        )
        session.add(receipt)
        session.flush()
        session.add(
            LyWarehouseStockEntryDraftItem(
                draft_id=int(receipt.id),
                company=company,
                item_code=item_code,
                qty=Decimal("10"),
                uom="件",
                source_warehouse=None,
                target_warehouse=warehouse,
            )
        )
        session.add(
            LyWarehouseStockEntryOutboxEvent(
                draft_id=int(receipt.id),
                event_type="finished_goods_inbound_sync",
                event_key="sales-smoke-fg-in-001",
                payload={"business_date": business_date.isoformat()},
                status="in_pending",
                retry_count=0,
                created_at=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
            )
        )
        session.commit()

    delivery_payload = {
        "company": company,
        "sales_order": sales_order,
        "customer": customer,
        "item_code": item_code,
        "item_name": "Smoke Finished Goods",
        "warehouse": warehouse,
        "delivered_qty": 4,
        "uom": "件",
        "rate": 50,
        "posting_date": business_date.isoformat(),
        "due_date": date(2026, 7, 17).isoformat(),
        "delivery_note": "DN-SALES-SMOKE-001",
        "sales_invoice": "SI-SALES-SMOKE-001",
        "source_ref": "SRC-SALES-SMOKE-DELIVERY-001",
        "idempotency_key": f"IDEMP-{delivery_scenario}-CREATE",
        "scenario_tag": delivery_scenario,
        "operation": "create_delivery_invoice",
    }
    sales_env = {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}
    with patch.dict("os.environ", sales_env):
        delivery_created = client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=_headers(request_id=f"{delivery_scenario}-SMOKE"),
            json=delivery_payload,
        )
    _assert(delivery_created.status_code == 201, delivery_created.text)
    delivery_data = delivery_created.json()["data"]
    _assert(delivery_data["delivery_note"] == "DN-SALES-SMOKE-001", "delivery note mismatch")
    _assert(delivery_data["sales_invoice"] == "SI-SALES-SMOKE-001", "sales invoice mismatch")
    _assert(Decimal(str(delivery_data["outstanding_amount"])) == Decimal("200.000000"), "sales receivable mismatch")

    delivery_listed = client.get(
        "/api/sales-inventory/delivery-invoices?keyword=SI-SALES-SMOKE-001&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(delivery_listed.status_code == 200, delivery_listed.text)
    _assert(
        delivery_listed.json()["data"]["items"][0]["delivery_note"] == "DN-SALES-SMOKE-001",
        "delivery invoice readback missing",
    )

    sales_invoices = client.get(
        f"/api/sales-inventory/sales-invoices?sales_order={sales_order}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(sales_invoices.status_code == 200, sales_invoices.text)
    _assert(
        sales_invoices.json()["data"]["items"][0]["sales_invoice"] == "SI-SALES-SMOKE-001",
        "sales invoice readback missing",
    )

    payment_payload = {
        "company": company,
        "sales_invoice": "SI-SALES-SMOKE-001",
        "customer": customer,
        "posting_date": business_date.isoformat(),
        "paid_amount": 120,
        "mode_of_payment": "Bank Transfer",
        "reference_no": "BANK-SALES-SMOKE-001",
        "reference_date": business_date.isoformat(),
        "payment_entry": "PE-SALES-SMOKE-001",
        "source_ref": "SRC-SALES-SMOKE-PAYMENT-001",
        "idempotency_key": f"IDEMP-{payment_scenario}-CREATE",
        "scenario_tag": payment_scenario,
        "operation": "create_payment_entry",
    }
    with patch.dict("os.environ", sales_env):
        payment_created = client.post(
            "/api/sales-inventory/payment-entries",
            headers=_headers(request_id=f"{payment_scenario}-SMOKE"),
            json=payment_payload,
        )
    _assert(payment_created.status_code == 201, payment_created.text)
    payment_data = payment_created.json()["data"]
    _assert(Decimal(str(payment_data["outstanding_before"])) == Decimal("200.000000"), "payment outstanding_before mismatch")
    _assert(Decimal(str(payment_data["outstanding_after"])) == Decimal("80.000000"), "payment outstanding_after mismatch")

    payments = client.get(
        "/api/sales-inventory/payment-entries?keyword=PE-SALES-SMOKE-001&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(payments.status_code == 200, payments.text)
    _assert(payments.json()["data"]["items"][0]["payment_entry"] == "PE-SALES-SMOKE-001", "payment readback missing")

    refreshed_invoices = client.get(
        f"/api/sales-inventory/sales-invoices?sales_order={sales_order}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(refreshed_invoices.status_code == 200, refreshed_invoices.text)
    invoice_row = refreshed_invoices.json()["data"]["items"][0]
    _assert(invoice_row["status"] == "partly_paid", "sales invoice status after payment mismatch")
    _assert(Decimal(str(invoice_row["paid_amount"])) == Decimal("120.000000"), "sales invoice paid amount mismatch")
    _assert(Decimal(str(invoice_row["outstanding_amount"])) == Decimal("80.000000"), "sales invoice outstanding mismatch")


def _exercise_factory_statement_payment_smoke(client: TestClient, session_local) -> None:  # noqa: ANN001
    scenario = "Z003-FACTORY-STMT-20260617-601"
    company = "COMP-FS-SMOKE"
    supplier = "SUP-FS-SMOKE"
    item_code = "ITEM-FS-SMOKE"
    statement_headers = _headers(request_id=scenario)
    statement_env = {"APP_ENV": "development", "LINGYI_DB_URL": "sqlite:///./lingyi_service.local.db"}

    with session_local() as session:
        session.add(
            LyApparelBom(
                id=601,
                bom_no="BOM-FS-SMOKE-001",
                item_code=item_code,
                version_no="v1",
                is_default=True,
                status="active",
                created_by="frontend.readiness.smoke",
                updated_by="frontend.readiness.smoke",
            )
        )
        subcontract = LySubcontractOrder(
            id=601,
            subcontract_no="SC-FS-SMOKE-001",
            supplier=supplier,
            item_code=item_code,
            company=company,
            bom_id=601,
            process_name="外发车缝",
            planned_qty=Decimal("80"),
            status="processing",
        )
        session.add(subcontract)
        session.flush()
        session.add(
            LySubcontractInspection(
                id=601,
                subcontract_id=int(subcontract.id),
                company=company,
                inspection_no="SIN-FS-SMOKE-001",
                item_code=item_code,
                inspected_qty=Decimal("80"),
                rejected_qty=Decimal("4"),
                accepted_qty=Decimal("76"),
                rejected_rate=Decimal("0.05"),
                subcontract_rate=Decimal("18"),
                gross_amount=Decimal("1440"),
                deduction_amount=Decimal("72"),
                net_amount=Decimal("1368"),
                settlement_status="unsettled",
                status="inspected",
                inspected_by="frontend.readiness.smoke",
                inspected_at=datetime(2026, 6, 17, 9, 0, 0),
                settlement_line_key="subcontract_inspection:fs-smoke-601",
            )
        )
        session.commit()

    create_payload = {
        "company": company,
        "supplier": supplier,
        "from_date": "2026-06-17",
        "to_date": "2026-06-17",
        "idempotency_key": f"{scenario}-IDEMP-CREATE",
        "scenario_tag": scenario,
    }
    with patch.dict("os.environ", statement_env):
        created = client.post("/api/factory-statements/", headers=statement_headers, json=create_payload)
    _assert(created.status_code == 200, created.text)
    created_data = created.json()["data"]
    statement_id = int(created_data["statement_id"])
    statement_no = str(created_data["statement_no"])
    _assert(created_data["source_count"] == 1, "factory statement source_count mismatch")
    _assert(Decimal(str(created_data["net_amount"])) == Decimal("1368.000000"), "factory statement net_amount mismatch")

    confirm_payload = {
        "scenario_tag": scenario,
        "company": company,
        "supplier": supplier,
        "statement_no": statement_no,
        "idempotency_key": f"{scenario}-IDEMP-CONFIRM",
        "remark": "acceptance-smoke confirm",
    }
    with patch.dict("os.environ", statement_env):
        confirmed = client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=statement_headers,
            json=confirm_payload,
        )
    _assert(confirmed.status_code == 200, confirmed.text)
    _assert(confirmed.json()["data"]["status"] == "confirmed", "factory statement confirm status mismatch")

    payment_payload = {
        "scenario_tag": scenario,
        "company": company,
        "supplier": supplier,
        "statement_no": statement_no,
        "posting_date": "2026-06-17",
        "paid_amount": "500",
        "mode_of_payment": "Bank Transfer",
        "reference_no": f"{scenario}-BANK-001",
        "reference_date": "2026-06-17",
        "payment_entry": "FSP-SMOKE-001",
        "source_ref": f"{scenario}-SRC-PAYMENT-001",
        "idempotency_key": f"{scenario}-IDEMP-PAYMENT-001",
        "operation": "create_payment_entry",
    }
    with patch.dict("os.environ", statement_env):
        paid = client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=statement_headers,
            json=payment_payload,
        )
    _assert(paid.status_code == 201, paid.text)
    paid_data = paid.json()["data"]
    _assert(Decimal(str(paid_data["outstanding_before"])) == Decimal("1368.000000"), "factory payment outstanding_before mismatch")
    _assert(Decimal(str(paid_data["outstanding_after"])) == Decimal("868.000000"), "factory payment outstanding_after mismatch")

    payments = client.get(
        f"/api/factory-statements/payments?statement_no={statement_no}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(payments.status_code == 200, payments.text)
    _assert(payments.json()["data"]["items"][0]["payment_entry"] == "FSP-SMOKE-001", "factory payment readback missing")

    statements = client.get(
        f"/api/factory-statements/?company={company}&supplier={supplier}&page=1&page_size=10",
        headers=_headers(),
    )
    _assert(statements.status_code == 200, statements.text)
    statement_row = statements.json()["data"]["items"][0]
    _assert(statement_row["payment_status"] == "partly_paid", "factory statement payment status mismatch")
    _assert(Decimal(str(statement_row["paid_amount"])) == Decimal("500.000000"), "factory statement paid amount mismatch")
    _assert(Decimal(str(statement_row["outstanding_amount"])) == Decimal("868.000000"), "factory statement outstanding mismatch")


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
    BomBase.metadata.create_all(bind=engine)
    SubcontractBase.metadata.create_all(bind=engine)
    ProductionBase.metadata.create_all(bind=engine)
    QualityBase.metadata.create_all(bind=engine)
    StyleProfitBase.metadata.create_all(bind=engine)
    FactoryStatementBase.metadata.create_all(bind=engine)
    MasterDataBase.metadata.create_all(bind=engine)
    MaterialPurchaseBase.metadata.create_all(bind=engine)
    SalesOrderBase.metadata.create_all(bind=engine)
    WorkshopBase.metadata.create_all(bind=engine)

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
    app.dependency_overrides[master_data_db_dep] = _override_db
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

        _exercise_quality_smoke(client)
        _exercise_workshop_smoke(client)
        _exercise_finished_goods_inbound_smoke(client)
        _exercise_sales_delivery_payment_smoke(client, session_local)
        _exercise_factory_statement_payment_smoke(client, session_local)

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

        _exercise_master_data_smoke(client)

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
        app.dependency_overrides.pop(master_data_db_dep, None)
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
