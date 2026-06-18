"""Security target mapping tests for warehouse write actions."""

from __future__ import annotations

import unittest

from fastapi import Request

import app.main as main_module
from app.core.permissions import WAREHOUSE_STOCK_HOLD_RELEASE


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


class WarehouseSecurityTargetTest(unittest.TestCase):
    def test_release_hold_infers_stock_hold_release_action(self) -> None:
        module, action, resource_type, resource_id = main_module._infer_security_target(
            _request("POST", "/api/warehouse/stock-entry-drafts/123/release-hold")
        )
        self.assertEqual(module, "warehouse")
        self.assertEqual(action, WAREHOUSE_STOCK_HOLD_RELEASE)
        self.assertEqual(resource_type, "WarehouseStockEntryDraft")
        self.assertEqual(resource_id, "123")


if __name__ == "__main__":
    unittest.main()
