"""Error envelope and idempotency-path tests for style-profit APIs (TASK-005E1)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.exceptions import DatabaseWriteFailed
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
from tests.test_style_profit_api import StyleProfitApiBase
import app.routers.style_profit as style_profit_router


class StyleProfitApiErrorTest(StyleProfitApiBase):
    """Validate unified error responses and conflict behavior."""

    _scenario_tag = "Z003-STYLE-PROFIT-20260525-003"

    def setUp(self) -> None:
        super().setUp()
        self._old_app_env = os.environ.get("APP_ENV")
        self._old_lingyi_db_url = os.environ.get("LINGYI_DB_URL")
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = style_profit_router.STYLE_PROFIT_LOCAL_ALLOWED_DB_URL

    def tearDown(self) -> None:
        if self._old_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = self._old_app_env
        if self._old_lingyi_db_url is None:
            os.environ.pop("LINGYI_DB_URL", None)
        else:
            os.environ["LINGYI_DB_URL"] = self._old_lingyi_db_url

    def _headers(self, role: str = "Finance Manager") -> dict[str, str]:
        headers = super()._headers(role=role)
        headers["X-Request-ID"] = self._scenario_tag
        return headers

    def _source_ref(self, *, sales_order: str, status_action: str) -> str:
        return "|".join(
            [
                self._scenario_tag,
                "COMP-A",
                "STYLE-A",
                sales_order,
                "actual_first",
                "STYLE_PROFIT_V1",
                status_action,
            ]
        )

    def _base_create_payload(self, *, idem: str) -> dict[str, object]:
        sales_order = "SO-ERR-001"
        status_action = "create"
        return {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": sales_order,
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": f"{self._scenario_tag}-{idem}",
            "scenario_tag": self._scenario_tag,
            "source_ref": self._source_ref(sales_order=sales_order, status_action=status_action),
            "status_action": status_action,
        }

    def _gate_carriers_from_payload(self, payload: dict[str, object]) -> dict[str, str]:
        return {
            "scenario_tag": str(payload["scenario_tag"]),
            "idempotency_key": str(payload["idempotency_key"]),
            "source_ref": str(payload["source_ref"]),
            "company": str(payload["company"]),
            "item_code": str(payload["item_code"]),
            "sales_order": str(payload["sales_order"]).strip(),
            "revenue_mode": str(payload["revenue_mode"]),
            "formula_version": str(payload["formula_version"]),
            "status_action": str(payload["status_action"]),
        }

    def test_invalid_idempotency_key_returns_business_error(self) -> None:
        payload = self._base_create_payload(idem="x" * 129)
        with patch.object(
            style_profit_router,
            "_validate_local_style_profit_write_gate",
            return_value=self._gate_carriers_from_payload(payload),
        ):
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
        with patch.object(
            style_profit_router,
            "_validate_local_style_profit_write_gate",
            return_value=self._gate_carriers_from_payload(payload),
        ):
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
