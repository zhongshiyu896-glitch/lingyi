"""Contract asset tests for the long-term FastAPI backend development plan."""

from __future__ import annotations

import importlib
import os
import unittest

from tools.backend_contract.export_contract_assets import build_page_matrix
from tools.backend_contract.export_contract_assets import build_route_catalog
from tools.backend_contract.export_contract_assets import first_route_for
from tools.backend_contract.export_contract_assets import load_app_for_env
from tools.backend_contract.export_contract_assets import parse_frontend_page_registry_text


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

        readiness_row = catalog[("GET", "/api/bom/styles", "app.routers.frontend_readiness")]
        self.assertEqual(readiness_row["class"], "B")
        self.assertFalse(readiness_row["is_real_write_db"])
        self.assertEqual(readiness_row["frontend_connect_status"], "temporary_dev_only")
        self.assertTrue(readiness_row["is_paginated"])

        for path, module_name in {
            "/api/bom/materials": "app.routers.bom",
            "/api/production/work-orders": "app.routers.production",
            "/api/sales-inventory/suppliers": "app.routers.sales_inventory",
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
        self.assertIn(("GET", "/api/bom/styles"), dev_paths)
        self.assertIn(("GET", "/api/bom/materials"), dev_paths)
        self.assertIn(("POST", "/api/production/readiness/work-order-flow"), dev_paths)

        prod_app = load_app_for_env("production")
        prod_paths = {(method, route.path) for route in prod_app.routes for method in getattr(route, "methods", set())}
        self.assertNotIn(("GET", "/api/bom/styles"), prod_paths)
        self.assertIn(("GET", "/api/bom/materials"), prod_paths)
        self.assertNotIn(("POST", "/api/production/readiness/work-order-flow"), prod_paths)

    def test_core_real_routes_are_not_shadowed_by_frontend_readiness_router(self) -> None:
        app = load_app_for_env("test")
        core_paths = [
            "/api/bom/material-gallery",
            "/api/bom/materials",
            "/api/production/plans",
            "/api/production/work-orders",
            "/api/sales-inventory/customers",
            "/api/sales-inventory/suppliers",
            "/api/warehouse/stock-summary",
            "/api/reports/catalog",
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


if __name__ == "__main__":
    unittest.main()
