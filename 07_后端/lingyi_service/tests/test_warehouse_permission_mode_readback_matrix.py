"""Warehouse permission mode readback matrix tests (TASK-Z006B-09-IMPL)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.warehouse_service import WarehouseService
from tests.test_warehouse_readonly_baseline import WarehouseReadonlyApiBase


class WarehousePermissionModeReadbackMatrixTest(WarehouseReadonlyApiBase):
    """Validate warehouse alerts/batches behavior across permission modes M01-M06."""

    @staticmethod
    def _set_env(*, app_env: str, permission_source: str) -> None:
        os.environ["APP_ENV"] = app_env
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = permission_source

    def _get_alerts(self) -> tuple[int, dict[str, object]]:
        response = self.client.get(
            "/api/warehouse/alerts?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&alert_type=low_stock",
            headers=self._headers(),
        )
        payload = response.json()
        return response.status_code, payload

    def _get_batches(self) -> tuple[int, dict[str, object]]:
        response = self.client.get(
            "/api/warehouse/batches?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&batch_no=BATCH-1",
            headers=self._headers(read_only=True),
        )
        payload = response.json()
        return response.status_code, payload

    def test_m01_local_dev_static_external_service_unavailable_allows_fallback(self) -> None:
        self._set_env(app_env="development", permission_source="static")
        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 200, alerts_payload)
        self.assertEqual(alerts_payload["data"]["items"], [])
        self.assertEqual(alerts_payload["data"]["alert_type"], "low_stock")
        self.assertEqual(batches_status, 200, batches_payload)
        self.assertEqual(batches_payload["data"]["total"], 0)
        self.assertEqual(batches_payload["data"]["items"], [])

    def test_m02_local_dev_static_invalid_response_fail_closed(self) -> None:
        self._set_env(app_env="development", permission_source="static")
        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 502, alerts_payload)
        self.assertEqual(alerts_payload["code"], "ERPNEXT_RESPONSE_INVALID")
        self.assertEqual(batches_status, 502, batches_payload)
        self.assertEqual(batches_payload["code"], "ERPNEXT_RESPONSE_INVALID")

    def test_m03_local_dev_static_non_external_service_unavailable_fail_closed(self) -> None:
        self._set_env(app_env="development", permission_source="static")
        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_TIMEOUT", safe_message="timeout"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_TIMEOUT", safe_message="timeout"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 503, alerts_payload)
        self.assertEqual(alerts_payload["code"], "ERPNEXT_TIMEOUT")
        self.assertEqual(batches_status, 503, batches_payload)
        self.assertEqual(batches_payload["code"], "ERPNEXT_TIMEOUT")

    def test_m04_local_dev_non_static_external_service_unavailable_fail_closed(self) -> None:
        self._set_env(app_env="development", permission_source="erpnext")
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=None,
        ), patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 503, alerts_payload)
        self.assertEqual(alerts_payload["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(batches_status, 503, batches_payload)
        self.assertEqual(batches_payload["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_m05_non_local_dev_static_external_service_unavailable_fail_closed(self) -> None:
        self._set_env(app_env="test", permission_source="static")
        with patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 503, alerts_payload)
        self.assertEqual(alerts_payload["code"], "EXTERNAL_SERVICE_UNAVAILABLE")
        self.assertEqual(batches_status, 503, batches_payload)
        self.assertEqual(batches_payload["code"], "EXTERNAL_SERVICE_UNAVAILABLE")

    def test_m06_non_local_dev_non_static_external_service_unavailable_fail_closed(self) -> None:
        self._set_env(app_env="test", permission_source="erpnext")
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=None,
        ), patch.object(
            WarehouseService,
            "get_alerts",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ), patch.object(
            WarehouseService,
            "list_batches",
            side_effect=ERPNextAdapterException(error_code="EXTERNAL_SERVICE_UNAVAILABLE", safe_message="down"),
        ):
            alerts_status, alerts_payload = self._get_alerts()
            batches_status, batches_payload = self._get_batches()

        self.assertEqual(alerts_status, 503, alerts_payload)
        self.assertEqual(alerts_payload["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(batches_status, 503, batches_payload)
        self.assertEqual(batches_payload["code"], "PERMISSION_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
