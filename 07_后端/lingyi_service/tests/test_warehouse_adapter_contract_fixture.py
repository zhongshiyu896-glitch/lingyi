"""Warehouse adapter contract fixture tests (TASK-Z006B-03-IMPL)."""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.warehouse_service import WarehouseService
from tests.test_warehouse_readonly_baseline import WarehouseReadonlyApiBase


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "warehouse_adapter_contract_fixture.json"


class WarehouseAdapterContractFixtureTest(WarehouseReadonlyApiBase):
    """Validate adapter contract mapping, empty-state, exception mapping and fail-closed behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        with FIXTURE_PATH.open("r", encoding="utf-8") as fp:
            cls.fixture = json.load(fp)

    @staticmethod
    def _to_date(value: str) -> date:
        return date.fromisoformat(value)

    @classmethod
    def _latest_movement_map(cls) -> dict[tuple[str, str], date]:
        result: dict[tuple[str, str], date] = {}
        for row in cls.fixture["latest_movement_by_item_warehouse_rows"]:
            result[(row["item_code"], row["warehouse"])] = cls._to_date(row["posting_date"])
        return result

    @classmethod
    def _batch_rows(cls) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in cls.fixture["list_batches_rows"]:
            rows.append(
                {
                    "company": row["company"],
                    "batch_no": row["batch_no"],
                    "item_code": row["item_code"],
                    "warehouse": row["warehouse"],
                    "manufacturing_date": cls._to_date(row["manufacturing_date"]),
                    "expiry_date": cls._to_date(row["expiry_date"]),
                    "disabled": bool(row["disabled"]),
                    "qty": row["qty"],
                }
            )
        return rows

    def test_fixture_file_exists_and_json_parseable(self) -> None:
        self.assertTrue(FIXTURE_PATH.exists(), str(FIXTURE_PATH))
        self.assertIn("list_stock_summary_rows", self.fixture)
        self.assertIn("latest_movement_by_item_warehouse_rows", self.fixture)
        self.assertIn("list_batches_rows", self.fixture)
        self.assertIn("exception_mapping_cases", self.fixture)
        self.assertIn("fail_closed_cases", self.fixture)

    def test_alerts_contract_field_mapping(self) -> None:
        expected = self.fixture["alerts_contract_expected"]
        query = expected["query"]
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=self.fixture["list_stock_summary_rows"],
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.latest_movement_by_item_warehouse",
            return_value=self._latest_movement_map(),
        ):
            response = self.client.get(
                "/api/warehouse/alerts"
                f"?company={query['company']}&warehouse={query['warehouse']}"
                f"&item_code={query['item_code']}&alert_type={query['alert_type']}",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        for field in expected["response_fields"]:
            self.assertIn(field, payload)
        self.assertEqual(payload["company"], query["company"])
        self.assertEqual(payload["warehouse"], query["warehouse"])
        self.assertEqual(payload["item_code"], query["item_code"])
        self.assertEqual(payload["alert_type"], query["alert_type"])
        self.assertGreaterEqual(len(payload["items"]), 1)
        first = payload["items"][0]
        for field in expected["first_item_required_fields"]:
            self.assertIn(field, first)
        self.assertEqual(first["alert_type"], "low_stock")
        self.assertEqual(first["company"], query["company"])
        self.assertEqual(first["warehouse"], query["warehouse"])
        self.assertEqual(first["item_code"], query["item_code"])

    def test_batches_contract_field_mapping(self) -> None:
        expected = self.fixture["batches_contract_expected"]
        query = expected["query"]
        batch_rows = self._batch_rows()
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_batches",
            return_value=(batch_rows, len(batch_rows)),
        ):
            response = self.client.get(
                "/api/warehouse/batches"
                f"?company={query['company']}&warehouse={query['warehouse']}"
                f"&item_code={query['item_code']}&batch_no={query['batch_no']}",
                headers=self._headers(read_only=True),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        for field in expected["response_fields"]:
            self.assertIn(field, payload)
        self.assertEqual(payload["company"], query["company"])
        self.assertEqual(payload["warehouse"], query["warehouse"])
        self.assertEqual(payload["item_code"], query["item_code"])
        self.assertEqual(payload["batch_no"], query["batch_no"])
        self.assertEqual(payload["total"], 1)
        self.assertEqual(len(payload["items"]), 1)
        first = payload["items"][0]
        for field in expected["first_item_required_fields"]:
            self.assertIn(field, first)
        self.assertEqual(first["batch_no"], query["batch_no"])
        self.assertEqual(first["item_code"], query["item_code"])

    def test_alerts_empty_state(self) -> None:
        expected = self.fixture["alerts_empty_state_expected"]
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=[],
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.latest_movement_by_item_warehouse",
            return_value={},
        ):
            response = self.client.get(
                f"/api/warehouse/alerts?company={expected['company']}"
                f"&warehouse={expected['warehouse']}&item_code={expected['item_code']}",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], expected["company"])
        self.assertEqual(payload["warehouse"], expected["warehouse"])
        self.assertEqual(payload["item_code"], expected["item_code"])
        self.assertEqual(payload["alert_type"], expected["alert_type"])
        self.assertEqual(payload["items"], expected["items"])

    def test_batches_empty_state(self) -> None:
        expected = self.fixture["batches_empty_state_expected"]
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_batches",
            return_value=([], 0),
        ):
            response = self.client.get(
                f"/api/warehouse/batches?company={expected['company']}"
                f"&warehouse={expected['warehouse']}&item_code={expected['item_code']}",
                headers=self._headers(read_only=True),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], expected["company"])
        self.assertEqual(payload["warehouse"], expected["warehouse"])
        self.assertEqual(payload["item_code"], expected["item_code"])
        self.assertEqual(payload["batch_no"], expected["batch_no"])
        self.assertEqual(payload["total"], expected["total"])
        self.assertEqual(payload["items"], expected["items"])

    def test_external_service_unavailable_local_dev_static_fallback_alerts(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            response = self.client.get(
                "/api/warehouse/alerts?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&alert_type=low_stock",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(payload["warehouse"], "WH-A")
        self.assertEqual(payload["item_code"], "ITEM-A")
        self.assertEqual(payload["alert_type"], "low_stock")
        self.assertEqual(payload["items"], [])

    def test_external_service_unavailable_local_dev_static_fallback_batches(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            response = self.client.get(
                "/api/warehouse/batches?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
                headers=self._headers(read_only=True),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["company"], "COMP-A")
        self.assertEqual(payload["warehouse"], "WH-A")
        self.assertEqual(payload["item_code"], "ITEM-A")
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["items"], [])

    def test_external_service_unavailable_non_local_dev_fail_closed(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            response = self.client.get("/api/warehouse/alerts?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["code"], "EXTERNAL_SERVICE_UNAVAILABLE")

    def test_external_service_unavailable_non_static_permission_fail_closed(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"

        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ), patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=None,
        ):
            response = self.client.get("/api/warehouse/alerts?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_erpnext_response_invalid_must_fail_closed(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ):
            response = self.client.get("/api/warehouse/alerts?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESPONSE_INVALID")


if __name__ == "__main__":
    unittest.main()
