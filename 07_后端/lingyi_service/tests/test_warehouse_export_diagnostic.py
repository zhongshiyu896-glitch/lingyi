"""Warehouse readonly export and diagnostic baseline tests (TASK-050F)."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO
import os
import unittest
from unittest.mock import patch

import app.main as main_module
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.schemas.warehouse import WarehouseBatchItem
from app.schemas.warehouse import WarehouseBatchListData
from app.schemas.warehouse import WarehouseStockSummaryData
from app.schemas.warehouse import WarehouseStockSummaryItem
from tests.test_warehouse_readonly_baseline import WarehouseReadonlyApiBase


def _csv_rows(content: bytes) -> list[list[str]]:
    return list(csv.reader(StringIO(content.decode("utf-8"))))


def _build_request(path: str, method: str = "GET"):
    from fastapi import Request

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class WarehouseExportDiagnosticApiTest(WarehouseReadonlyApiBase):
    """Validate warehouse export/diagnostic behavior and boundaries."""

    def test_export_requires_warehouse_export_permission(self) -> None:
        response = self.client.get(
            "/api/warehouse/export?dataset=stock_summary",
            headers=self._headers_with_roles("warehouse:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_export_stock_summary_csv_with_scope_filter(self) -> None:
        with patch(
            "app.services.warehouse_service.WarehouseService.get_stock_summary",
            return_value=WarehouseStockSummaryData(
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
                items=[
                    WarehouseStockSummaryItem(
                        company="COMP-A",
                        warehouse="WH-A",
                        item_code="ITEM-A",
                        actual_qty="2",
                        projected_qty="3",
                        reserved_qty="1",
                        ordered_qty="5",
                        reorder_level="6",
                        safety_stock="4",
                        threshold_missing=False,
                        is_below_reorder=True,
                        is_below_safety=True,
                    ),
                    WarehouseStockSummaryItem(
                        company="COMP-A",
                        warehouse="WH-B",
                        item_code="ITEM-B",
                        actual_qty="2",
                        projected_qty="3",
                        reserved_qty="1",
                        ordered_qty="5",
                        reorder_level="6",
                        safety_stock="4",
                        threshold_missing=False,
                        is_below_reorder=True,
                        is_below_safety=True,
                    ),
                ],
            ),
        ):
            response = self.client.get(
                "/api/warehouse/export?dataset=stock_summary&company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
                headers=self._headers_with_roles("warehouse:export"),
            )

        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(rows[0][0], "company")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "COMP-A")
        self.assertEqual(rows[1][1], "WH-A")
        self.assertEqual(rows[1][2], "ITEM-A")

    def test_export_csv_formula_injection_is_escaped(self) -> None:
        with patch(
            "app.services.warehouse_service.WarehouseService.list_batches",
            return_value=WarehouseBatchListData(
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
                batch_no=None,
                total=1,
                items=[
                    WarehouseBatchItem(
                        company="COMP-A",
                        batch_no="=BATCH-001",
                        item_code="ITEM-A",
                        warehouse="WH-A",
                        manufacturing_date=date(2026, 4, 1),
                        expiry_date=date(2026, 8, 1),
                        disabled=False,
                        qty="8",
                    )
                ],
            ),
        ):
            response = self.client.get(
                "/api/warehouse/export?dataset=batches",
                headers=self._headers_with_roles("warehouse:export"),
            )
        self.assertEqual(response.status_code, 200, response.text)
        rows = _csv_rows(response.content)
        self.assertEqual(rows[1][1], "'=BATCH-001")

    def test_export_response_headers_use_safe_filename(self) -> None:
        with patch(
            "app.services.warehouse_service.WarehouseService.get_stock_summary",
            return_value=WarehouseStockSummaryData(company=None, warehouse=None, item_code=None, items=[]),
        ):
            response = self.client.get(
                "/api/warehouse/export?dataset=stock_summary&item_code=UNSAFE_INPUT",
                headers=self._headers_with_roles("warehouse:export"),
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("content-type", "").startswith("text/csv"))
        content_disposition = response.headers.get("content-disposition", "")
        self.assertIn("attachment;", content_disposition)
        self.assertIn("warehouse_export_stock_summary_", content_disposition)
        self.assertNotIn("UNSAFE_INPUT", content_disposition)

    def test_diagnostic_requires_warehouse_diagnostic_permission(self) -> None:
        response = self.client.get(
            "/api/warehouse/diagnostic",
            headers=self._headers_with_roles("warehouse:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_diagnostic_returns_readonly_summary(self) -> None:
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = "https://erpnext.example.com"
        response = self.client.get(
            "/api/warehouse/diagnostic",
            headers=self._headers_with_roles("warehouse:diagnostic"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertTrue(payload["adapter_configured"])
        self.assertIn("stock_summary", payload["supported_datasets"])
        self.assertEqual(payload["export_supported_formats"], ["csv"])
        self.assertEqual(payload["write_boundary"], "no_erpnext_write,no_submit,no_stock_reconciliation")
        self.assertEqual(
            set(payload.keys()),
            {"adapter_configured", "supported_datasets", "export_supported_formats", "write_boundary", "last_checked_at"},
        )

    def test_main_route_mapping_for_export_and_diagnostic(self) -> None:
        export_target = main_module._infer_security_target(_build_request("/api/warehouse/export"))
        self.assertEqual(export_target[0], "warehouse")
        self.assertEqual(export_target[1], WAREHOUSE_EXPORT)
        diagnostic_target = main_module._infer_security_target(_build_request("/api/warehouse/diagnostic"))
        self.assertEqual(diagnostic_target[0], "warehouse")
        self.assertEqual(diagnostic_target[1], WAREHOUSE_DIAGNOSTIC)

    def test_export_diagnostic_no_write_call_signature(self) -> None:
        from app.routers import warehouse as warehouse_router_module
        from app.services import erpnext_warehouse_adapter as adapter_module
        from app.services import warehouse_export_service as export_service_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
                open(export_service_module.__file__, encoding="utf-8").read(),
                open(adapter_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked = [
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "@router.post(\"/export\")",
            "@router.post(\"/diagnostic\")",
        ]
        for snippet in blocked:
            self.assertNotIn(snippet, content)


if __name__ == "__main__":
    unittest.main()
