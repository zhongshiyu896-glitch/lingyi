"""Security target mapping tests for sales inventory write actions."""

from __future__ import annotations

import unittest

from fastapi import Request

import app.main as main_module
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import SALES_INVENTORY_WRITE


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


class SalesInventorySecurityTargetTest(unittest.TestCase):
    def test_delivery_invoice_create_infers_write_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/sales-inventory/delivery-invoices")
        )
        self.assertEqual(module, "sales_inventory")
        self.assertEqual(action, SALES_INVENTORY_WRITE)
        self.assertEqual(resource_type, "DeliveryInvoice")
        self.assertIsNone(resource_id)

    def test_delivery_invoice_cancel_infers_write_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/sales-inventory/delivery-invoices/123/cancel")
        )
        self.assertEqual(module, "sales_inventory")
        self.assertEqual(action, SALES_INVENTORY_WRITE)
        self.assertEqual(resource_type, "DeliveryInvoice")
        self.assertEqual(resource_id, "123")

    def test_payment_entry_create_infers_write_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/sales-inventory/payment-entries")
        )
        self.assertEqual(module, "sales_inventory")
        self.assertEqual(action, SALES_INVENTORY_WRITE)
        self.assertEqual(resource_type, "SalesPaymentEntry")
        self.assertIsNone(resource_id)

    def test_payment_entry_cancel_infers_write_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/sales-inventory/payment-entries/123/cancel")
        )
        self.assertEqual(module, "sales_inventory")
        self.assertEqual(action, SALES_INVENTORY_WRITE)
        self.assertEqual(resource_type, "SalesPaymentEntry")
        self.assertEqual(resource_id, "123")

    def test_sales_order_draft_writes_infer_write_action(self) -> None:
        cases = [
            ("POST", "/api/sales-inventory/sales-orders/drafts", None),
            ("PATCH", "/api/sales-inventory/sales-orders/drafts/123", "123"),
            ("POST", "/api/sales-inventory/sales-orders/drafts/123/cancel", "123"),
        ]
        for method, path, expected_id in cases:
            with self.subTest(method=method, path=path):
                module, action, resource_type, resource_id = main_module._infer_security_target(_request(method, path))
                self.assertEqual(module, "sales_inventory")
                self.assertEqual(action, SALES_INVENTORY_WRITE)
                self.assertEqual(resource_type, "SalesOrderDraft")
                self.assertEqual(resource_id, expected_id)

    def test_sales_order_detail_still_infers_read_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("GET", "/api/sales-inventory/sales-orders/SO-001")
        )
        self.assertEqual(module, "sales_inventory")
        self.assertEqual(action, SALES_INVENTORY_READ)
        self.assertEqual(resource_type, "SalesOrder")
        self.assertEqual(resource_id, "SO-001")


if __name__ == "__main__":
    unittest.main()
