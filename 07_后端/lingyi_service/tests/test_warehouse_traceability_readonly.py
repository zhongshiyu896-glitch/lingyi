"""Warehouse batch/serial/traceability read-only baseline tests (TASK-050E)."""

from __future__ import annotations

from datetime import date
import os
import unittest
from unittest.mock import patch

from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from tests.test_warehouse_readonly_baseline import WarehouseReadonlyApiBase


class WarehouseTraceabilityReadonlyApiTest(WarehouseReadonlyApiBase):
    """Validate warehouse traceability read-only endpoints and boundaries."""

    def test_batches_list_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_batches",
            return_value=(
                [
                    {
                        "company": "COMP-A",
                        "batch_no": "BATCH-001",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "manufacturing_date": date(2026, 4, 1),
                        "expiry_date": date(2026, 8, 1),
                        "disabled": False,
                        "qty": "8",
                    }
                ],
                1,
            ),
        ):
            response = self.client.get("/api/warehouse/batches?company=COMP-A", headers=self._headers(read_only=True))
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        item = payload["items"][0]
        self.assertEqual(item["batch_no"], "BATCH-001")
        self.assertIn("manufacturing_date", item)
        self.assertIn("expiry_date", item)
        self.assertIn("disabled", item)
        self.assertIn("qty", item)

    def test_batch_detail_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.get_batch_detail",
            return_value={
                "batch_no": "BATCH-001",
                "company": "COMP-A",
                "warehouse": "WH-A",
                "item_code": "ITEM-A",
                "total": 1,
                "items": [
                    {
                        "company": "COMP-A",
                        "batch_no": "BATCH-001",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "manufacturing_date": date(2026, 4, 1),
                        "expiry_date": date(2026, 8, 1),
                        "disabled": False,
                        "qty": "8",
                    }
                ],
            },
        ):
            response = self.client.get(
                "/api/warehouse/batches/BATCH-001?company=COMP-A",
                headers=self._headers(read_only=True),
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["batch_no"], "BATCH-001")
        self.assertEqual(payload["total"], 1)
        self.assertIn("manufacturing_date", payload["items"][0])
        self.assertIn("expiry_date", payload["items"][0])
        self.assertIn("disabled", payload["items"][0])
        self.assertIn("qty", payload["items"][0])

    def test_serial_numbers_list_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_serial_numbers",
            return_value=(
                [
                    {
                        "company": "COMP-A",
                        "serial_no": "SER-001",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "batch_no": "BATCH-001",
                        "status": "Active",
                        "delivery_document_no": "DN-001",
                        "purchase_document_no": "PR-001",
                    }
                ],
                1,
            ),
        ):
            response = self.client.get("/api/warehouse/serial-numbers?company=COMP-A", headers=self._headers(read_only=True))
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        item = payload["items"][0]
        self.assertEqual(item["serial_no"], "SER-001")
        self.assertIn("status", item)
        self.assertIn("delivery_document_no", item)
        self.assertIn("purchase_document_no", item)

    def test_serial_number_detail_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.get_serial_number_detail",
            return_value={
                "serial_no": "SER-001",
                "company": "COMP-A",
                "warehouse": "WH-A",
                "item_code": "ITEM-A",
                "total": 1,
                "items": [
                    {
                        "company": "COMP-A",
                        "serial_no": "SER-001",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "batch_no": "BATCH-001",
                        "status": "Active",
                        "delivery_document_no": "DN-001",
                        "purchase_document_no": "PR-001",
                    }
                ],
            },
        ):
            response = self.client.get(
                "/api/warehouse/serial-numbers/SER-001?company=COMP-A",
                headers=self._headers(read_only=True),
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["serial_no"], "SER-001")
        self.assertEqual(payload["total"], 1)
        self.assertIn("status", payload["items"][0])
        self.assertIn("delivery_document_no", payload["items"][0])
        self.assertIn("purchase_document_no", payload["items"][0])

    def test_traceability_returns_rows(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_traceability_entries",
            return_value=(
                [
                    {
                        "company": "COMP-A",
                        "warehouse": "WH-A",
                        "item_code": "ITEM-A",
                        "posting_date": date(2026, 4, 20),
                        "voucher_type": "Stock Entry",
                        "voucher_no": "STE-001",
                        "actual_qty": "2",
                        "qty_after_transaction": "8",
                        "batch_no": "BATCH-001",
                        "serial_no": "SER-001,SER-002",
                    }
                ],
                1,
            ),
        ):
            response = self.client.get(
                "/api/warehouse/traceability?company=COMP-A&serial_no=SER-001",
                headers=self._headers(read_only=True),
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["batch_no"], "BATCH-001")

    def test_traceability_filters_are_passed(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_traceability_entries",
            return_value=([], 0),
        ) as mocked:
            response = self.client.get(
                "/api/warehouse/traceability"
                "?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&batch_no=BATCH-001&serial_no=SER-001"
                "&from_date=2026-04-01&to_date=2026-04-20&page=2&page_size=30",
                headers=self._headers(read_only=True),
            )
        self.assertEqual(response.status_code, 200, response.text)
        mocked.assert_called_once()
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["company"], "COMP-A")
        self.assertEqual(kwargs["warehouse"], "WH-A")
        self.assertEqual(kwargs["item_code"], "ITEM-A")
        self.assertEqual(kwargs["batch_no"], "BATCH-001")
        self.assertEqual(kwargs["serial_no"], "SER-001")
        self.assertEqual(kwargs["from_date"], date(2026, 4, 1))
        self.assertEqual(kwargs["to_date"], date(2026, 4, 20))
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 30)

    def test_traceability_company_scope_filter_effective(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
                allowed_items={"ITEM-A"},
            ),
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_traceability_entries",
            return_value=(
                [
                    {
                        "company": "COMP-A",
                        "warehouse": "WH-A",
                        "item_code": "ITEM-A",
                        "posting_date": date(2026, 4, 20),
                        "voucher_type": "Stock Entry",
                        "voucher_no": "STE-001",
                        "actual_qty": "2",
                        "qty_after_transaction": "8",
                        "batch_no": "BATCH-001",
                        "serial_no": "SER-001",
                    },
                    {
                        "company": "COMP-A",
                        "warehouse": "WH-B",
                        "item_code": "ITEM-A",
                        "posting_date": date(2026, 4, 20),
                        "voucher_type": "Stock Entry",
                        "voucher_no": "STE-002",
                        "actual_qty": "2",
                        "qty_after_transaction": "8",
                        "batch_no": "BATCH-001",
                        "serial_no": "SER-002",
                    },
                ],
                2,
            ),
        ):
            response = self.client.get("/api/warehouse/traceability?company=COMP-A", headers=self._headers(read_only=True))
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["warehouse"], "WH-A")

    def test_traceability_erpnext_malformed_fail_closed(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_traceability_entries",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ):
            response = self.client.get("/api/warehouse/traceability", headers=self._headers(read_only=True))
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESPONSE_INVALID")

    def test_inventory_read_only_forbidden_on_traceability_endpoints(self) -> None:
        headers = self._headers_with_roles("inventory:read")
        endpoints = [
            "/api/warehouse/batches",
            "/api/warehouse/batches/BATCH-001",
            "/api/warehouse/serial-numbers",
            "/api/warehouse/serial-numbers/SER-001",
            "/api/warehouse/traceability",
        ]
        for endpoint in endpoints:
            response = self.client.get(endpoint, headers=headers)
            self.assertEqual(response.status_code, 403, f"{endpoint} => {response.status_code}")


class ERPNextWarehouseAdapterBatchSerialContractTest(unittest.TestCase):
    """Validate adapter reads Batch/Serial No resources and fail-closes on missing fields."""

    def test_list_batches_reads_batch_resource(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_list_resource",
            return_value=[
                {
                    "company": "COMP-A",
                    "batch_no": "BATCH-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "manufacturing_date": "2026-04-01",
                    "expiry_date": "2026-08-01",
                    "disabled": 0,
                    "qty": "8",
                }
            ],
        ) as mocked:
            rows, total = adapter.list_batches(
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
                batch_no=None,
                page=1,
                page_size=20,
            )
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["batch_no"], "BATCH-001")
        self.assertEqual(mocked.call_args.kwargs["doctype"], "Batch")

    def test_list_serial_numbers_reads_serial_resource(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_list_resource",
            return_value=[
                {
                    "company": "COMP-A",
                    "serial_no": "SER-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "batch_no": "BATCH-001",
                    "status": "Active",
                    "delivery_document_no": "DN-001",
                    "purchase_document_no": "PR-001",
                }
            ],
        ) as mocked:
            rows, total = adapter.list_serial_numbers(
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
                batch_no=None,
                serial_no=None,
                page=1,
                page_size=20,
            )
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["serial_no"], "SER-001")
        self.assertEqual(mocked.call_args.kwargs["doctype"], "Serial No")

    def test_get_batch_detail_reads_batch_single_resource(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "list_batches",
            side_effect=AssertionError("get_batch_detail must not fallback to list_batches"),
        ) as list_mock, patch.object(
            ERPNextWarehouseAdapter,
            "_request_json",
            return_value={
                "data": {
                    "company": "COMP-A",
                    "batch_no": "BATCH-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "manufacturing_date": "2026-04-01",
                    "expiry_date": "2026-08-01",
                    "disabled": 0,
                    "qty": "8",
                }
            },
        ) as request_mock:
            payload = adapter.get_batch_detail(
                batch_no="BATCH-001",
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
            )
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["batch_no"], "BATCH-001")
        self.assertEqual(request_mock.call_args.args[0], "/api/resource/Batch/BATCH-001")
        list_mock.assert_not_called()

    def test_get_serial_detail_reads_serial_single_resource(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "list_serial_numbers",
            side_effect=AssertionError("get_serial_number_detail must not fallback to list_serial_numbers"),
        ) as list_mock, patch.object(
            ERPNextWarehouseAdapter,
            "_request_json",
            return_value={
                "data": {
                    "company": "COMP-A",
                    "serial_no": "SER-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "batch_no": "BATCH-001",
                    "status": "Active",
                    "delivery_document_no": "DN-001",
                    "purchase_document_no": "PR-001",
                }
            },
        ) as request_mock:
            payload = adapter.get_serial_number_detail(
                serial_no="SER-001",
                company="COMP-A",
                warehouse="WH-A",
                item_code="ITEM-A",
            )
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["serial_no"], "SER-001")
        self.assertEqual(request_mock.call_args.args[0], "/api/resource/Serial%20No/SER-001")
        list_mock.assert_not_called()

    def test_batch_missing_required_field_fail_closed(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_list_resource",
            return_value=[
                {
                    "company": "COMP-A",
                    "batch_no": "BATCH-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "manufacturing_date": "2026-04-01",
                    "expiry_date": "2026-08-01",
                    "disabled": 0,
                }
            ],
        ):
            with self.assertRaises(ERPNextAdapterException):
                adapter.list_batches(
                    company="COMP-A",
                    warehouse="WH-A",
                    item_code="ITEM-A",
                    batch_no=None,
                    page=1,
                    page_size=20,
                )

    def test_serial_missing_required_field_fail_closed(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_list_resource",
            return_value=[
                {
                    "company": "COMP-A",
                    "serial_no": "SER-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "batch_no": "BATCH-001",
                    "delivery_document_no": "DN-001",
                    "purchase_document_no": "PR-001",
                }
            ],
        ):
            with self.assertRaises(ERPNextAdapterException):
                adapter.list_serial_numbers(
                    company="COMP-A",
                    warehouse="WH-A",
                    item_code="ITEM-A",
                    batch_no=None,
                    serial_no=None,
                    page=1,
                    page_size=20,
                )

    def test_batch_detail_missing_required_field_fail_closed(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_request_json",
            return_value={
                "data": {
                    "company": "COMP-A",
                    "batch_no": "BATCH-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "manufacturing_date": "2026-04-01",
                    "expiry_date": "2026-08-01",
                    "disabled": 0,
                }
            },
        ):
            with self.assertRaises(ERPNextAdapterException):
                adapter.get_batch_detail(
                    batch_no="BATCH-001",
                    company="COMP-A",
                    warehouse="WH-A",
                    item_code="ITEM-A",
                )

    def test_serial_detail_missing_required_field_fail_closed(self) -> None:
        adapter = ERPNextWarehouseAdapter()
        with patch.object(
            ERPNextWarehouseAdapter,
            "_request_json",
            return_value={
                "data": {
                    "company": "COMP-A",
                    "serial_no": "SER-001",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "batch_no": "BATCH-001",
                    "delivery_document_no": "DN-001",
                    "purchase_document_no": "PR-001",
                }
            },
        ):
            with self.assertRaises(ERPNextAdapterException):
                adapter.get_serial_number_detail(
                    serial_no="SER-001",
                    company="COMP-A",
                    warehouse="WH-A",
                    item_code="ITEM-A",
                )


if __name__ == "__main__":
    unittest.main()
