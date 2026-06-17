"""Contract asset tests for the long-term FastAPI backend development plan."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import unittest

from tools.backend_contract.export_contract_assets import build_page_matrix
from tools.backend_contract.export_contract_assets import build_route_catalog
from tools.backend_contract.export_contract_assets import first_route_for
from tools.backend_contract.export_contract_assets import load_app_for_env
from tools.backend_contract.export_contract_assets import parse_frontend_page_registry_text


REPO_ROOT = Path(__file__).resolve().parents[1]


class BackendContractAssetsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "LINGYI_ALLOW_DEV_AUTH": os.environ.get("LINGYI_ALLOW_DEV_AUTH"),
            "LINGYI_ERPNEXT_BASE_URL": os.environ.get("LINGYI_ERPNEXT_BASE_URL"),
            "LINGYI_PERMISSION_SOURCE": os.environ.get("LINGYI_PERMISSION_SOURCE"),
            "LINGYI_DB_URL": os.environ.get("LINGYI_DB_URL"),
            "LINGYI_FRONTEND_READINESS_ENABLED": os.environ.get("LINGYI_FRONTEND_READINESS_ENABLED"),
        }

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import app.main as main_module

        importlib.reload(main_module)

    def test_route_catalog_classifies_real_readiness_and_stub_routes(self) -> None:
        app = load_app_for_env("test")
        catalog = {(row["method"], row["path"], row["endpoint_module"]): row for row in build_route_catalog(app)}

        readiness_row = catalog[("GET", "/api/bom/colors", "app.routers.frontend_readiness")]
        self.assertEqual(readiness_row["class"], "B")
        self.assertFalse(readiness_row["is_real_write_db"])
        self.assertEqual(readiness_row["frontend_connect_status"], "temporary_dev_only")
        self.assertTrue(readiness_row["is_paginated"])

        for path, module_name in {
            "/api/bom/materials": "app.routers.bom",
            "/api/bom/material-categories": "app.routers.bom",
            "/api/bom/units": "app.routers.bom",
            "/api/bom/styles": "app.routers.bom",
            "/api/bom/style-bom-process": "app.routers.bom",
            "/api/bom/process-requirement-templates": "app.routers.bom",
            "/api/production/work-orders": "app.routers.production",
            "/api/production/followup-templates": "app.routers.production",
            "/api/sales-inventory/suppliers": "app.routers.sales_inventory",
            "/api/sales-inventory/warehouses": "app.routers.sales_inventory",
            "/api/factory-statements/customer-receivables": "app.routers.factory_statement",
            "/api/factory-statements/purchase-invoices": "app.routers.factory_statement",
            "/api/sales-inventory/delivery-notes": "app.routers.sales_inventory",
            "/api/sales-inventory/sales-invoices": "app.routers.sales_inventory",
            "/api/style-profit/style-costs": "app.routers.style_profit",
            "/api/warehouse/finished-goods-inbound": "app.routers.warehouse",
            "/api/warehouse/inventory-balance-reconciliation": "app.routers.warehouse",
            "/api/warehouse/purchase-receipts": "app.routers.warehouse",
        }.items():
            with self.subTest(path=path):
                real_productized_row = catalog[("GET", path, module_name)]
                self.assertEqual(real_productized_row["class"], "A")
                self.assertEqual(real_productized_row["frontend_connect_status"], "candidate")
                self.assertTrue(real_productized_row["is_paginated"])

        flow_row = catalog[("POST", "/api/production/readiness/work-order-flow", "app.routers.frontend_readiness")]
        self.assertEqual(flow_row["class"], "C")
        self.assertFalse(flow_row["is_real_write_db"])
        self.assertEqual(flow_row["frontend_connect_status"], "do_not_connect_as_write")

        real_row = catalog[("GET", "/api/bom/material-gallery", "app.routers.bom")]
        self.assertEqual(real_row["class"], "A")
        self.assertEqual(real_row["frontend_connect_status"], "candidate")
        self.assertTrue(real_row["is_paginated"])
        self.assertIn("material_item_code", real_row["response_fields"])

    def test_readiness_routes_are_dev_enabled_and_production_disabled(self) -> None:
        dev_app = load_app_for_env("test")
        dev_paths = {(method, route.path) for route in dev_app.routes for method in getattr(route, "methods", set())}
        self.assertIn(("GET", "/api/bom/colors"), dev_paths)
        self.assertIn(("GET", "/api/bom/styles"), dev_paths)
        self.assertIn(("GET", "/api/bom/materials"), dev_paths)
        self.assertIn(("GET", "/api/bom/units"), dev_paths)
        self.assertIn(("GET", "/api/bom/style-bom-process"), dev_paths)
        self.assertIn(("GET", "/api/production/followup-templates"), dev_paths)
        self.assertIn(("GET", "/api/style-profit/style-costs"), dev_paths)
        self.assertIn(("GET", "/api/warehouse/purchase-receipts"), dev_paths)
        self.assertIn(("GET", "/api/factory-statements/purchase-invoices"), dev_paths)
        self.assertIn(("GET", "/api/warehouse/finished-goods-inbound"), dev_paths)
        self.assertIn(("GET", "/api/sales-inventory/delivery-notes"), dev_paths)
        self.assertIn(("GET", "/api/sales-inventory/sales-invoices"), dev_paths)
        self.assertIn(("GET", "/api/warehouse/inventory-balance-reconciliation"), dev_paths)
        self.assertIn(("POST", "/api/production/readiness/work-order-flow"), dev_paths)

        prod_app = load_app_for_env("production")
        prod_paths = {(method, route.path) for route in prod_app.routes for method in getattr(route, "methods", set())}
        self.assertNotIn(("GET", "/api/bom/colors"), prod_paths)
        self.assertIn(("GET", "/api/bom/styles"), prod_paths)
        self.assertIn(("GET", "/api/bom/materials"), prod_paths)
        self.assertIn(("GET", "/api/bom/units"), prod_paths)
        self.assertIn(("GET", "/api/bom/style-bom-process"), prod_paths)
        self.assertIn(("GET", "/api/production/followup-templates"), prod_paths)
        self.assertIn(("GET", "/api/style-profit/style-costs"), prod_paths)
        self.assertIn(("GET", "/api/warehouse/purchase-receipts"), prod_paths)
        self.assertIn(("GET", "/api/factory-statements/purchase-invoices"), prod_paths)
        self.assertIn(("GET", "/api/warehouse/finished-goods-inbound"), prod_paths)
        self.assertIn(("GET", "/api/sales-inventory/delivery-notes"), prod_paths)
        self.assertIn(("GET", "/api/sales-inventory/sales-invoices"), prod_paths)
        self.assertIn(("GET", "/api/warehouse/inventory-balance-reconciliation"), prod_paths)
        self.assertNotIn(("POST", "/api/production/readiness/work-order-flow"), prod_paths)

    def test_core_real_routes_are_not_shadowed_by_frontend_readiness_router(self) -> None:
        app = load_app_for_env("test")
        core_paths = [
            "/api/bom/material-gallery",
            "/api/bom/material-categories",
            "/api/bom/materials",
            "/api/bom/process-requirement-templates",
            "/api/bom/styles",
            "/api/bom/style-bom-process",
            "/api/bom/units",
            "/api/factory-statements/customer-receivables",
            "/api/factory-statements/purchase-invoices",
            "/api/production/followup-templates",
            "/api/production/plans",
            "/api/production/work-orders",
            "/api/sales-inventory/customers",
            "/api/sales-inventory/delivery-notes",
            "/api/sales-inventory/sales-invoices",
            "/api/sales-inventory/suppliers",
            "/api/warehouse/stock-summary",
            "/api/warehouse/finished-goods-inbound",
            "/api/warehouse/inventory-balance-reconciliation",
            "/api/warehouse/purchase-receipts",
            "/api/reports/catalog",
            "/api/style-profit/style-costs",
        ]
        for path in core_paths:
            with self.subTest(path=path):
                route = first_route_for(app, method="GET", path=path)
                self.assertIsNotNone(route)
                self.assertNotEqual(route.endpoint.__module__, "app.routers.frontend_readiness")

    def test_frontend_page_registry_parser_builds_backend_matrix(self) -> None:
        registry = """
        export const pages = [
          page(1, '基础资料', '客户', '/foundation/customer', 'config_list', '001.png', 'customer', ['CustomerItem'], [], ['新建'], ['请输入'], '/api/sales-inventory/customers'),
          page(2, '基础资料', '加工厂', '/foundation/factory', 'config_list', '002.png', 'contractGap', [], [gap('Factory')], ['新建'], ['请输入']),
        ]
        """
        pages = parse_frontend_page_registry_text(registry)
        self.assertEqual(len(pages), 2)

        app = load_app_for_env("test")
        matrix = {row["page_route"]: row for row in build_page_matrix(pages, build_route_catalog(app))}

        self.assertEqual(matrix["/foundation/customer"]["backend_status"], "real_backend_route")
        self.assertEqual(matrix["/foundation/customer"]["priority"], "P1_first_readonly_connect")
        self.assertEqual(matrix["/foundation/factory"]["backend_status"], "missing_api_path")
        self.assertEqual(matrix["/foundation/factory"]["priority"], "P3_needs_product_contract")

    def test_task2_task3_contract_handoff_documents_are_present(self) -> None:
        task2_md = (REPO_ROOT / "contracts" / "task2_page_connection_matrix.md").read_text(encoding="utf-8")
        task2_json = json.loads(
            (REPO_ROOT / "contracts" / "task2_page_connection_matrix.json").read_text(encoding="utf-8")
        )
        task3_md = (REPO_ROOT / "contracts" / "task3_existing_api_norms.md").read_text(encoding="utf-8")

        self.assertEqual(task2_json["scope"], "synced_from_frontend_page_registry_and_fastapi_routes")
        self.assertEqual(task2_json["backend_catalog_counts"], {"A": 185, "B": 19, "C": 7, "D": 11})
        self.assertEqual(task2_json["page_matrix_counts"]["total_pages"], 57)
        self.assertEqual(task2_json["page_matrix_counts"]["real_backend_route"], 48)
        self.assertEqual(task2_json["page_matrix_counts"]["api_path_miss"], 0)
        self.assertEqual(task2_json["page_matrix_counts"]["missing_api_path"], 9)
        self.assertIn("FastAPI 自建，不连接 ERPNext 9081", task2_md)
        self.assertIn("A 期已接真实后端页面", task2_md)
        self.assertIn("闭环说明", task2_md)
        self.assertNotIn("PARKED", task2_md)

        self.assertIn('{"code":"0","message":"success","data":...}', task3_md)
        self.assertIn("AUTH_UNAUTHORIZED", task3_md)
        self.assertIn("AUTH_FORBIDDEN", task3_md)
        self.assertIn("X-LY-Dev-User", task3_md)
        self.assertIn("X-LY-Dev-Roles", task3_md)
        self.assertIn("from_date", task3_md)
        self.assertIn("to_date", task3_md)
        self.assertIn("page_size", task3_md)
        self.assertIn("生产权限源已定为 FastAPI 原生", task3_md)
        self.assertIn("库存内核：FastAPI 原生", task3_md)
        self.assertIn("财务边界：A 期按现有页面覆盖", task3_md)
        self.assertNotIn("PARKED", task3_md)
        self.assertNotIn("AUTH_REQUIRED", task3_md)
        self.assertNotIn("PERMISSION_DENIED", task3_md)
        self.assertNotIn("VALIDATION_ERROR", task3_md)


if __name__ == "__main__":
    unittest.main()
