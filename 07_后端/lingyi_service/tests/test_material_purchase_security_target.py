"""Security target mapping tests for material purchase payment actions."""

from __future__ import annotations

import unittest

from fastapi import Request

import app.main as main_module
from app.core.permissions import MATERIAL_PURCHASE_WRITE


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


class MaterialPurchaseSecurityTargetTest(unittest.TestCase):
    def test_purchase_payment_cancel_infers_write_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/material-purchase/purchase-payments/123/cancel")
        )
        self.assertEqual(module, "material_purchase")
        self.assertEqual(action, MATERIAL_PURCHASE_WRITE)
        self.assertEqual(resource_type, "MaterialPurchasePayment")
        self.assertEqual(resource_id, "123")


if __name__ == "__main__":
    unittest.main()
