"""Supplemental permission/date guard tests for sales_inventory (TASK-040B)."""

from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.routers.sales_inventory import _parse_optional_date
from app.routers.sales_inventory import _validate_date_range


class SalesInventoryPermissionGuardTest(unittest.TestCase):
    """Validate router-level date guard behavior."""

    def test_parse_optional_date_blank_treated_as_missing(self) -> None:
        self.assertIsNone(_parse_optional_date(None, "from_date"))
        self.assertIsNone(_parse_optional_date("", "from_date"))
        self.assertIsNone(_parse_optional_date("   ", "from_date"))

    def test_parse_optional_date_invalid_raises_http_400(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            _parse_optional_date("2026/04/01", "from_date")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail.get("code"), "INVALID_QUERY_PARAMETER")

    def test_validate_date_range_invalid_raises_http_400(self) -> None:
        from_date = _parse_optional_date("2026-04-30", "from_date")
        to_date = _parse_optional_date("2026-04-01", "to_date")
        with self.assertRaises(HTTPException) as ctx:
            _validate_date_range(from_date=from_date, to_date=to_date)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail.get("code"), "INVALID_QUERY_PARAMETER")


if __name__ == "__main__":
    unittest.main()
