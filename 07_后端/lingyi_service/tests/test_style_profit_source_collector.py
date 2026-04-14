"""Unit tests for style-profit API source collector real-adapter contract (TASK-005F)."""

from __future__ import annotations

from datetime import date
from typing import Any
import unittest

from app.core.error_codes import STYLE_PROFIT_BOM_REQUIRED
from app.core.error_codes import STYLE_PROFIT_REVENUE_SOURCE_REQUIRED
from app.core.exceptions import BusinessException
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector


class _FakeAdapter:
    def __init__(self) -> None:
        self.sales_invoice_rows: list[dict[str, Any]] = []
        self.sales_order_rows: list[dict[str, Any]] = []
        self.bom_material_rows: list[dict[str, Any]] = []
        self.bom_operation_rows: list[dict[str, Any]] = []
        self.allowed_material_codes: list[str] = []
        self.stock_ledger_rows: list[dict[str, Any]] = []
        self.purchase_receipt_rows: list[dict[str, Any]] = []
        self.workshop_rows: list[dict[str, Any]] = []
        self.subcontract_rows: list[dict[str, Any]] = []

    def load_submitted_sales_invoice_rows(self, selector):
        _ = selector
        return list(self.sales_invoice_rows)

    def load_submitted_sales_order_rows(self, selector):
        _ = selector
        return list(self.sales_order_rows)

    def load_active_default_bom_rows(self, *, company, item_code, planned_qty):
        _ = (company, item_code, planned_qty)
        return (
            list(self.bom_material_rows),
            list(self.bom_operation_rows),
            list(self.allowed_material_codes),
        )

    def load_stock_ledger_rows(self, selector, *, allowed_material_item_codes):
        _ = (selector, allowed_material_item_codes)
        return list(self.stock_ledger_rows)

    def load_purchase_receipt_rows(self, selector, *, allowed_material_item_codes):
        _ = (selector, allowed_material_item_codes)
        return list(self.purchase_receipt_rows)

    def load_workshop_ticket_rows(self, selector):
        _ = selector
        return list(self.workshop_rows)

    def load_subcontract_rows(self, selector):
        _ = selector
        return list(self.subcontract_rows)


class StyleProfitSourceCollectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = _FakeAdapter()
        self.collector = StyleProfitApiSourceCollector(session=None, adapter=self.adapter)
        self.selector = StyleProfitSnapshotSelectorRequest(
            company="COMP-A",
            item_code="STYLE-A",
            sales_order="SO-001",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            include_provisional_subcontract=False,
            formula_version="STYLE_PROFIT_V1",
            idempotency_key="idem-collector-001",
            work_order="WO-001",
        )

    def test_collect_success_with_trusted_rows_and_stable_normalization(self) -> None:
        self.adapter.sales_invoice_rows = [
            {
                "name": "SI-002",
                "line_no": "2",
                "docstatus": 1,
                "status": "Paid",
                "company": "COMP-A",
                "sales_order": "SO-001",
                "item_code": "STYLE-A",
                "qty": "5",
                "rate": "11",
                "base_net_amount": "55",
                "created_at": "2026-04-14T00:00:00Z",
                "operator": "dev",
                "token": "should-drop",
            },
            {
                "name": "SI-001",
                "line_no": "1",
                "docstatus": 1,
                "status": "Paid",
                "company": "COMP-A",
                "sales_order": "SO-001",
                "item_code": "STYLE-A",
                "qty": "5",
                "rate": "10",
                "base_net_amount": "50",
            },
        ]
        self.adapter.bom_material_rows = [
            {
                "line_no": "1",
                "material_item_code": "MAT-A",
                "qty_per_piece": "1.2",
                "loss_rate": "0.05",
                "bom_required_qty_with_loss": "12.6",
            }
        ]
        self.adapter.bom_operation_rows = [
            {"line_no": "1", "operation": "CUT", "bom_operation_rate": "2", "planned_qty": "10"}
        ]
        self.adapter.allowed_material_codes = ["MAT-B", "MAT-A"]
        self.adapter.stock_ledger_rows = [
            {
                "name": "SLE-2",
                "item_code": "MAT-Z",
                "stock_value_difference": "9",
                "docstatus": 1,
                "status": "Submitted",
            },
            {
                "name": "SLE-1",
                "item_code": "MAT-A",
                "stock_value_difference": "6",
                "docstatus": 1,
                "status": "Submitted",
                "request_id": "volatile",
                "authorization": "should-drop",
            },
        ]

        request = self.collector.collect(self.selector)

        self.assertEqual(request.allowed_material_item_codes, ["MAT-A", "MAT-B"])
        self.assertEqual(len(request.sales_invoice_rows), 2)
        self.assertEqual(request.sales_invoice_rows[0]["name"], "SI-001")
        self.assertEqual(request.sales_invoice_rows[1]["name"], "SI-002")
        self.assertNotIn("created_at", request.sales_invoice_rows[0])
        self.assertNotIn("operator", request.sales_invoice_rows[0])
        self.assertNotIn("token", request.sales_invoice_rows[0])
        self.assertEqual(len(request.stock_ledger_rows), 1)
        self.assertEqual(request.stock_ledger_rows[0]["item_code"], "MAT-A")
        self.assertNotIn("request_id", request.stock_ledger_rows[0])
        self.assertNotIn("authorization", request.stock_ledger_rows[0])

    def test_collect_rejects_when_no_revenue_source(self) -> None:
        self.adapter.sales_invoice_rows = []
        self.adapter.sales_order_rows = []

        with self.assertRaises(BusinessException) as ctx:
            self.collector.collect(self.selector)

        self.assertEqual(ctx.exception.code, STYLE_PROFIT_REVENUE_SOURCE_REQUIRED)

    def test_collect_rejects_when_bom_missing(self) -> None:
        self.adapter.sales_order_rows = [
            {
                "name": "SO-001",
                "line_no": "1",
                "docstatus": 1,
                "status": "To Bill",
                "company": "COMP-A",
                "sales_order": "SO-001",
                "item_code": "STYLE-A",
                "qty": "10",
                "rate": "10",
                "base_amount": "100",
            }
        ]
        self.adapter.bom_material_rows = []
        self.adapter.bom_operation_rows = []

        with self.assertRaises(BusinessException) as ctx:
            self.collector.collect(self.selector)

        self.assertEqual(ctx.exception.code, STYLE_PROFIT_BOM_REQUIRED)


if __name__ == "__main__":
    unittest.main()
