"""Source mapping tests for style profit skeleton service (TASK-005C1)."""

from __future__ import annotations

from decimal import Decimal
import unittest

from app.schemas.style_profit import StyleProfitMaterialSourceDTO
from app.services.style_profit_source_service import StyleProfitSourceService


class StyleProfitSourceMappingTest(unittest.TestCase):
    """Validate revenue/material source mapping rules and fail-closed gates."""

    def setUp(self) -> None:
        self.service = StyleProfitSourceService(session=None)

    def test_request_hash_excludes_created_at_operator_request_id(self) -> None:
        payload_1 = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": True,
            "formula_version": "STYLE_PROFIT_V1",
            "created_at": "2026-04-14T09:00:00+08:00",
            "operator": "u1",
            "request_id": "rid-1",
        }
        payload_2 = {
            **payload_1,
            "created_at": "2026-04-14T10:00:00+08:00",
            "operator": "u2",
            "request_id": "rid-2",
        }

        self.assertEqual(
            self.service.build_snapshot_request_hash(payload_1),
            self.service.build_snapshot_request_hash(payload_2),
        )

    def test_request_hash_includes_from_date_to_date_revenue_mode(self) -> None:
        base = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
        }
        digest_base = self.service.build_snapshot_request_hash(base)

        changed_from = {**base, "from_date": "2026-04-02"}
        changed_to = {**base, "to_date": "2026-05-01"}
        changed_mode = {**base, "revenue_mode": "estimated_only"}

        self.assertNotEqual(digest_base, self.service.build_snapshot_request_hash(changed_from))
        self.assertNotEqual(digest_base, self.service.build_snapshot_request_hash(changed_to))
        self.assertNotEqual(digest_base, self.service.build_snapshot_request_hash(changed_mode))

    def test_request_hash_includes_source_rows_payload(self) -> None:
        base = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "sales_invoice_rows": [
                {"name": "SINV-1", "line_id": "1", "amount": "100", "status": "Paid"},
            ],
            "sales_order_rows": [],
            "bom_material_rows": [],
            "bom_operation_rows": [],
            "stock_ledger_rows": [],
            "workshop_ticket_rows": [],
            "subcontract_rows": [],
            "allowed_material_item_codes": ["MAT-A"],
            "work_order": "WO-1",
        }
        changed = {
            **base,
            "sales_invoice_rows": [
                {"name": "SINV-1", "line_id": "1", "amount": "120", "status": "Paid"},
            ],
        }
        self.assertNotEqual(
            self.service.build_snapshot_request_hash(base),
            self.service.build_snapshot_request_hash(changed),
        )

    def test_request_hash_is_order_insensitive_for_source_rows(self) -> None:
        payload_1 = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "sales_invoice_rows": [
                {"name": "SINV-2", "line_id": "2", "amount": "200", "status": "Paid"},
                {"name": "SINV-1", "line_id": "1", "amount": "100", "status": "Paid"},
            ],
            "sales_order_rows": [],
            "bom_material_rows": [],
            "bom_operation_rows": [],
            "stock_ledger_rows": [],
            "workshop_ticket_rows": [],
            "subcontract_rows": [],
            "allowed_material_item_codes": ["MAT-B", "MAT-A"],
            "work_order": "WO-1",
        }
        payload_2 = {
            **payload_1,
            "sales_invoice_rows": list(reversed(payload_1["sales_invoice_rows"])),
            "allowed_material_item_codes": list(reversed(payload_1["allowed_material_item_codes"])),
        }
        self.assertEqual(
            self.service.build_snapshot_request_hash(payload_1),
            self.service.build_snapshot_request_hash(payload_2),
        )

    def test_request_hash_excludes_snapshot_no_and_sensitive_fields(self) -> None:
        base = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "sales_invoice_rows": [
                {
                    "name": "SINV-1",
                    "line_id": "1",
                    "amount": "100",
                    "status": "Paid",
                    "created_at": "2026-04-14T10:00:00+08:00",
                    "snapshot_no": "SP-001",
                    "Authorization": "Bearer x",
                    "token": "x",
                }
            ],
        }
        variant = {
            **base,
            "sales_invoice_rows": [
                {
                    **base["sales_invoice_rows"][0],
                    "created_at": "2026-04-14T11:00:00+08:00",
                    "snapshot_no": "SP-002",
                    "token": "y",
                }
            ],
        }
        self.assertEqual(
            self.service.build_snapshot_request_hash(base),
            self.service.build_snapshot_request_hash(variant),
        )

    def test_is_submitted_empty_row_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({}))

    def test_is_submitted_empty_status_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"status": ""}))

    def test_is_submitted_unknown_status_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"status": "Unknown"}))

    def test_is_submitted_docstatus_one_returns_true(self) -> None:
        self.assertTrue(self.service._is_submitted({"docstatus": 1}))

    def test_is_submitted_docstatus_zero_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"docstatus": 0}))

    def test_is_submitted_docstatus_one_with_cancelled_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"docstatus": 1, "is_cancelled": True}))

    def test_is_submitted_sales_invoice_status_paid_without_docstatus_returns_true(self) -> None:
        self.assertTrue(self.service._is_submitted({"status": " Paid "}, source_doctype="Sales Invoice"))

    def test_is_submitted_sales_invoice_status_completed_without_docstatus_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"status": "Completed"}, source_doctype="Sales Invoice"))

    def test_is_submitted_sales_order_status_completed_without_docstatus_returns_true(self) -> None:
        self.assertTrue(self.service._is_submitted({"status": "Completed"}, source_doctype="Sales Order"))

    def test_is_submitted_sales_order_status_closed_without_docstatus_returns_false(self) -> None:
        self.assertFalse(self.service._is_submitted({"status": "Closed"}, source_doctype="Sales Order"))

    def test_is_submitted_stock_ledger_entry_without_docstatus_returns_false(self) -> None:
        self.assertFalse(
            self.service._is_submitted(
                {"status": "Submitted"},
                source_doctype="Stock Ledger Entry",
            )
        )

    def test_is_submitted_stock_ledger_entry_docstatus_one_returns_true(self) -> None:
        self.assertTrue(
            self.service._is_submitted(
                {"docstatus": 1, "status": "Submitted"},
                source_doctype="Stock Ledger Entry",
            )
        )

    def test_is_submitted_docstatus_zero_with_paid_status_still_false(self) -> None:
        self.assertFalse(
            self.service._is_submitted(
                {"docstatus": 0, "status": "Paid"},
                source_doctype="Sales Invoice",
            )
        )

    def test_material_source_dto_include_in_profit_default_false(self) -> None:
        dto = StyleProfitMaterialSourceDTO(
            source_system="erpnext",
            source_doctype="Stock Ledger Entry",
            source_name="STE-001",
            source_line_no="ROW-1",
            company="COMP-A",
            style_item_code="STYLE-A",
            stock_value_difference=Decimal("-1"),
            amount=Decimal("1"),
        )
        self.assertFalse(dto.include_in_profit)
        self.assertEqual(dto.mapping_status, "unresolved")

    def test_sales_invoice_priority_over_sales_order(self) -> None:
        invoice_rows = [
            {
                "name": "SINV-001",
                "line_id": "SINV-001-1",
                "company": "COMP-A",
                "sales_order": "SO-001",
                "item_code": "STYLE-A",
                "qty": "10",
                "rate": "20",
                "amount": "200",
                "docstatus": 1,
                "status": "Submitted",
            }
        ]
        order_rows = [
            {
                "name": "SO-001",
                "line_id": "SO-001-1",
                "company": "COMP-A",
                "sales_order": "SO-001",
                "item_code": "STYLE-A",
                "qty": "10",
                "rate": "18",
                "amount": "180",
                "docstatus": 1,
                "status": "To Deliver",
            }
        ]

        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-001",
            item_code="STYLE-A",
            sales_invoice_rows=invoice_rows,
            sales_order_rows=order_rows,
        )

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_type, "Sales Invoice")
        self.assertEqual(resolved[0].revenue_status, "actual")
        self.assertEqual(resolved[0].amount, Decimal("200"))
        self.assertEqual(resolved[0].source_status, "submitted")

    def test_fallback_to_sales_order_when_no_sales_invoice(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-002",
            item_code="STYLE-A",
            sales_invoice_rows=[],
            sales_order_rows=[
                {
                    "name": "SO-002",
                    "line_id": "SO-002-1",
                    "company": "COMP-A",
                    "sales_order": "SO-002",
                    "item_code": "STYLE-A",
                    "qty": "8",
                    "rate": "25",
                    "amount": "200",
                    "docstatus": 1,
                    "status": "To Deliver",
                }
            ],
        )

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_type, "Sales Order")
        self.assertEqual(resolved[0].revenue_status, "estimated")
        self.assertEqual(resolved[0].source_status, "to deliver")

    def test_revenue_sources_require_expected_sales_order_scope(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="",
            item_code="STYLE-A",
            sales_invoice_rows=[
                {
                    "name": "SINV-NO-ORDER",
                    "line_id": "SINV-NO-ORDER-1",
                    "company": "COMP-A",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "100",
                    "amount": "100",
                    "docstatus": 1,
                    "status": "Paid",
                }
            ],
            sales_order_rows=[],
        )
        self.assertEqual(resolved, [])

    def test_revenue_source_status_keeps_real_invoice_status(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-PAID",
            item_code="STYLE-A",
            sales_invoice_rows=[
                {
                    "name": "SINV-PAID",
                    "line_id": "SINV-PAID-1",
                    "company": "COMP-A",
                    "sales_order": "SO-PAID",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "100",
                    "amount": "100",
                    "status": "Paid",
                }
            ],
            sales_order_rows=[],
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_status, "paid")

    def test_revenue_source_status_submitted_only_when_docstatus_one_and_status_missing(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-SUBMITTED",
            item_code="STYLE-A",
            sales_invoice_rows=[
                {
                    "name": "SINV-SUBMITTED",
                    "line_id": "SINV-SUBMITTED-1",
                    "company": "COMP-A",
                    "sales_order": "SO-SUBMITTED",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "100",
                    "amount": "100",
                    "docstatus": 1,
                }
            ],
            sales_order_rows=[],
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_status, "submitted")

    def test_revenue_source_status_keeps_real_sales_order_status(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-BILL",
            item_code="STYLE-A",
            sales_invoice_rows=[],
            sales_order_rows=[
                {
                    "name": "SO-BILL",
                    "line_id": "SO-BILL-1",
                    "company": "COMP-A",
                    "sales_order": "SO-BILL",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "100",
                    "amount": "100",
                    "status": "To Bill",
                }
            ],
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_status, "to bill")

    def test_draft_or_cancelled_sales_invoice_not_counted(self) -> None:
        resolved = self.service.resolve_revenue_sources(
            company="COMP-A",
            sales_order="SO-003",
            item_code="STYLE-A",
            sales_invoice_rows=[
                {
                    "name": "SINV-DRAFT",
                    "line_id": "SINV-DRAFT-1",
                    "company": "COMP-A",
                    "sales_order": "SO-003",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "1",
                    "amount": "1",
                    "docstatus": 0,
                    "status": "Draft",
                },
                {
                    "name": "SINV-CAN",
                    "line_id": "SINV-CAN-1",
                    "company": "COMP-A",
                    "sales_order": "SO-003",
                    "item_code": "STYLE-A",
                    "qty": "1",
                    "rate": "1",
                    "amount": "1",
                    "docstatus": 2,
                    "status": "Cancelled",
                },
            ],
            sales_order_rows=[
                {
                    "name": "SO-003",
                    "line_id": "SO-003-1",
                    "company": "COMP-A",
                    "sales_order": "SO-003",
                    "item_code": "STYLE-A",
                    "qty": "3",
                    "rate": "30",
                    "amount": "90",
                    "docstatus": 1,
                    "status": "To Deliver",
                }
            ],
        )

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_type, "Sales Order")
        self.assertEqual(resolved[0].amount, Decimal("90"))

    def test_stock_ledger_entry_uses_abs_stock_value_difference(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-010",
            style_item_code="STYLE-A",
            work_order="WO-010",
            stock_ledger_rows=[
                {
                    "name": "SLE-001",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-001",
                    "company": "COMP-A",
                    "sales_order": "SO-010",
                    "work_order": "WO-010",
                    "item_code": "MAT-A",
                    "warehouse": "WIP-A",
                    "actual_qty": "-5",
                    "stock_value_difference": "-123.4500",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A", "MAT-B"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("123.4500"))
        self.assertEqual(len(result.mapped_sources), 1)
        self.assertEqual(result.mapped_sources[0].amount, Decimal("123.4500"))

    def test_sle_source_item_can_differ_from_style_item_when_bridge_matches(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-STYLE-01",
            style_item_code="STYLE-A",
            work_order="WO-STYLE-01",
            stock_ledger_rows=[
                {
                    "name": "SLE-STYLE-01",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-STYLE-01",
                    "company": "COMP-A",
                    "sales_order": "SO-STYLE-01",
                    "work_order": "WO-STYLE-01",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-45",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("45"))
        self.assertEqual(len(result.mapped_sources), 1)
        self.assertEqual(result.mapped_sources[0].style_item_code, "STYLE-A")
        self.assertEqual(result.mapped_sources[0].source_item_code, "MAT-A")

    def test_sle_without_bridge_or_bom_scope_is_unresolved(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-012",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-UNRESOLVED-1",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-UNRESOLVED",
                    "company": "COMP-A",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-50",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].mapping_status, "unresolved")
        self.assertEqual(
            result.unresolved_sources[0].unresolved_reason,
            "SLE_SCOPE_UNTRUSTED",
        )

    def test_sle_outside_allowed_materials_is_unresolved(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-013",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-NOT-IN-BOM",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-NOT-IN-BOM",
                    "company": "COMP-A",
                    "sales_order": "SO-013",
                    "item_code": "MAT-Z",
                    "stock_value_difference": "-30",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A", "MAT-B"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].unresolved_reason, "SLE_MATERIAL_NOT_IN_BOM")

    def test_source_status_missing_saved_as_unknown_and_not_included(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-013A",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-UNKNOWN-STATUS",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-UNKNOWN-STATUS",
                    "company": "COMP-A",
                    "sales_order": "SO-013A",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-30",
                    "docstatus": 1,
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].source_status, "unknown")
        self.assertEqual(result.unresolved_sources[0].unresolved_reason, "SLE_STATUS_UNTRUSTED")

    def test_sle_sales_order_mismatch_is_scope_untrusted(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-EXPECTED",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-ORDER-MISMATCH",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-ORDER-MISMATCH",
                    "company": "COMP-A",
                    "sales_order": "SO-OTHER",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-30",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )
        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].unresolved_reason, "SLE_SCOPE_UNTRUSTED")

    def test_sle_work_order_mismatch_is_scope_untrusted(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-EXPECTED",
            style_item_code="STYLE-A",
            work_order="WO-EXPECTED",
            stock_ledger_rows=[
                {
                    "name": "SLE-WO-MISMATCH",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-WO-MISMATCH",
                    "company": "COMP-A",
                    "sales_order": "SO-EXPECTED",
                    "work_order": "WO-OTHER",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-30",
                    "docstatus": 1,
                    "status": "Submitted",
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )
        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].unresolved_reason, "SLE_SCOPE_UNTRUSTED")

    def test_sle_missing_status_and_cancel_flag_is_status_untrusted(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-EXPECTED",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-MISS-STATUS-CANCEL",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-MISS-STATUS-CANCEL",
                    "company": "COMP-A",
                    "sales_order": "SO-EXPECTED",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-30",
                    "docstatus": 1,
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )
        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 1)
        self.assertEqual(result.unresolved_sources[0].unresolved_reason, "SLE_STATUS_UNTRUSTED")

    def test_sle_docstatus_zero_or_two_or_cancelled_is_not_counted(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-EXPECTED",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-DRAFT",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-DRAFT",
                    "company": "COMP-A",
                    "sales_order": "SO-EXPECTED",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-10",
                    "docstatus": 0,
                    "status": "Draft",
                    "is_cancelled": 0,
                },
                {
                    "name": "SLE-CANCELLED-STATUS",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-CANCELLED-STATUS",
                    "company": "COMP-A",
                    "sales_order": "SO-EXPECTED",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-10",
                    "docstatus": 2,
                    "status": "Cancelled",
                    "is_cancelled": 1,
                },
            ],
            allowed_material_item_codes={"MAT-A"},
        )
        self.assertEqual(result.actual_material_cost, Decimal("0"))
        self.assertEqual(len(result.unresolved_sources), 2)
        reasons = {row.unresolved_reason for row in result.unresolved_sources}
        self.assertIn("SLE_DRAFT_OR_UNSUBMITTED", reasons)
        self.assertIn("SLE_CANCELLED", reasons)

    def test_purchase_receipt_not_directly_counted_into_actual_material_cost(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-014",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-PR-001",
                    "voucher_type": "Purchase Receipt",
                    "voucher_no": "PR-001",
                    "company": "COMP-A",
                    "sales_order": "SO-014",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-999",
                    "docstatus": 1,
                },
                {
                    "name": "SLE-STE-001",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-014",
                    "company": "COMP-A",
                    "sales_order": "SO-014",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-10",
                    "docstatus": 1,
                    "status": "Submitted",
                },
            ],
            allowed_material_item_codes={"MAT-A"},
        )

        self.assertEqual(result.actual_material_cost, Decimal("10"))
        self.assertEqual(len(result.excluded_sources), 1)
        self.assertEqual(result.excluded_sources[0].source_type, "Purchase Receipt")
        self.assertEqual(result.excluded_sources[0].unresolved_reason, "purchase_receipt_reference_only")

    def test_sensitive_fields_are_not_in_raw_ref(self) -> None:
        result = self.service.resolve_material_cost_sources(
            company="COMP-A",
            sales_order="SO-015",
            style_item_code="STYLE-A",
            stock_ledger_rows=[
                {
                    "name": "SLE-SAFE-001",
                    "voucher_type": "Stock Entry",
                    "voucher_no": "STE-SAFE",
                    "company": "COMP-A",
                    "sales_order": "SO-015",
                    "item_code": "MAT-A",
                    "stock_value_difference": "-20",
                    "docstatus": 1,
                    "status": "Submitted",
                    "Authorization": "Bearer abc",
                    "token": "abc",
                    "password": "p",
                    "cookie": "c",
                    "secret": "s",
                    "sql": "select * from x",
                }
            ],
            allowed_material_item_codes={"MAT-A"},
        )

        self.assertEqual(len(result.mapped_sources), 1)
        raw_ref = result.mapped_sources[0].raw_ref
        lowered = {key.lower() for key in raw_ref.keys()}
        self.assertNotIn("authorization", lowered)
        self.assertNotIn("token", lowered)
        self.assertNotIn("password", lowered)
        self.assertNotIn("cookie", lowered)
        self.assertNotIn("secret", lowered)
        self.assertNotIn("sql", lowered)


if __name__ == "__main__":
    unittest.main()
