"""Adapter fail-closed tests for sales/inventory read-only integration (TASK-011B)."""

from __future__ import annotations

import unittest

from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


class SalesInventoryAdapterTest(unittest.TestCase):
    """Validate ERPNext read-only facts are normalized fail-closed."""

    def test_sales_order_missing_docstatus_fails_closed(self) -> None:
        with self.assertRaises(ERPNextAdapterException) as ctx:
            ERPNextSalesInventoryAdapter._require_sales_order({"name": "SO-001", "company": "COMP-A"})
        self.assertEqual(ctx.exception.error_code, "ERPNEXT_DOCSTATUS_REQUIRED")

    def test_sales_order_draft_fails_closed(self) -> None:
        with self.assertRaises(ERPNextAdapterException) as ctx:
            ERPNextSalesInventoryAdapter._require_sales_order(
                {"name": "SO-001", "company": "COMP-A", "docstatus": 0}
            )
        self.assertEqual(ctx.exception.error_code, "ERPNEXT_DOCSTATUS_INVALID")

    def test_sales_order_submitted_passes(self) -> None:
        row = ERPNextSalesInventoryAdapter._require_sales_order(
            {"name": "SO-001", "company": "COMP-A", "docstatus": "1"}
        )
        self.assertEqual(row["name"], "SO-001")
        self.assertEqual(row["docstatus"], "1")

    def test_sle_missing_required_field_is_dropped(self) -> None:
        self.assertIsNone(
            ERPNextSalesInventoryAdapter._normalize_sle_row(
                {
                    "name": "SLE-BAD",
                    "company": "COMP-A",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "posting_date": "2026-04-01",
                    "actual_qty": "1",
                }
            )
        )

    def test_sle_invalid_qty_is_dropped(self) -> None:
        self.assertIsNone(
            ERPNextSalesInventoryAdapter._normalize_sle_row(
                {
                    "name": "SLE-BAD",
                    "company": "COMP-A",
                    "item_code": "ITEM-A",
                    "warehouse": "WH-A",
                    "posting_date": "2026-04-01",
                    "actual_qty": "not-a-number",
                    "qty_after_transaction": "1",
                }
            )
        )

    def test_sle_valid_row_normalizes_decimal_and_date(self) -> None:
        row = ERPNextSalesInventoryAdapter._normalize_sle_row(
            {
                "name": "SLE-OK",
                "company": "COMP-A",
                "item_code": "ITEM-A",
                "warehouse": "WH-A",
                "posting_date": "2026-04-01",
                "posting_time": "09:00:00",
                "actual_qty": "1.5",
                "qty_after_transaction": "8.5",
            }
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(str(row["actual_qty"]), "1.5")
        self.assertEqual(str(row["posting_date"]), "2026-04-01")
