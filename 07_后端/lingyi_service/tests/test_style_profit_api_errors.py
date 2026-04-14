"""Error envelope and idempotency-path tests for style-profit APIs (TASK-005E1)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.exceptions import DatabaseWriteFailed
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
from tests.test_style_profit_api import StyleProfitApiBase
import app.routers.style_profit as style_profit_router


class StyleProfitApiErrorTest(StyleProfitApiBase):
    """Validate unified error responses and conflict behavior."""

    def _base_create_payload(self, *, idem: str) -> dict[str, object]:
        return {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-ERR-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": idem,
        }

    def test_invalid_idempotency_key_returns_business_error(self) -> None:
        payload = self._base_create_payload(idem="x" * 129)
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY")

    def test_blank_sales_order_returns_business_error(self) -> None:
        payload = self._base_create_payload(idem="idem-blank-sales-order")
        payload["sales_order"] = "   "
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SALES_ORDER_REQUIRED")

    def test_same_idempotency_key_with_different_request_returns_conflict(self) -> None:
        first = self._base_create_payload(idem="idem-api-conflict")
        second = self._base_create_payload(idem="idem-api-conflict")
        second["to_date"] = "2026-05-01"

        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ):
            first_response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=first,
                headers=self._headers(),
            )
            self.assertEqual(first_response.status_code, 200)

            second_response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=second,
                headers=self._headers(),
            )
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json()["code"], "STYLE_PROFIT_IDEMPOTENCY_CONFLICT")

    def test_unknown_error_uses_unified_envelope_without_detail(self) -> None:
        payload = self._base_create_payload(idem="idem-unknown-error")
        with patch.object(StyleProfitApiSourceCollector, "collect", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["code"], "STYLE_PROFIT_INTERNAL_ERROR")
        self.assertIn("message", body)
        self.assertIn("data", body)
        self.assertNotIn("detail", body)

    def test_commit_failure_returns_database_write_failed(self) -> None:
        payload = self._base_create_payload(idem="idem-db-write-failed")
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ), patch.object(style_profit_router, "_commit_or_raise_write_error", side_effect=DatabaseWriteFailed()):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")


if __name__ == "__main__":
    unittest.main()
