"""Permission-source runtime config tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import app.main as main_module
from app.core.config import factory_statement_enable_payable_worker_sync
from app.core.config import production_enable_work_order_worker_sync
from app.core.config import quality_enable_outbox_worker_sync
from app.core.config import warehouse_enable_stock_entry_worker_sync
from app.core.config import workshop_enable_job_card_worker_sync
from app.core.permissions import get_permission_source


class PermissionSourceConfigTest(unittest.TestCase):
    def test_fastapi_permission_source_is_supported(self) -> None:
        with patch.dict(os.environ, {"LINGYI_PERMISSION_SOURCE": "fastapi"}):
            self.assertEqual(get_permission_source(), "fastapi")

    def test_production_requires_fastapi_permission_source(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                "LINGYI_ERPNEXT_BASE_URL": "",
            },
        ):
            main_module._validate_permission_source_config()

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_ERPNEXT_BASE_URL": "",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "fastapi"):
                main_module._validate_permission_source_config()

    def test_production_rejects_erpnext_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                "LINGYI_ERPNEXT_BASE_URL": "http://127.0.0.1:9081",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "LINGYI_ERPNEXT_BASE_URL"):
                main_module._validate_permission_source_config()

    def test_production_rejects_erpnext_api_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                "LINGYI_ERPNEXT_BASE_URL": "",
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "ERPNext API"):
                main_module._validate_permission_source_config()

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                "LINGYI_ERPNEXT_BASE_URL": "",
                "LINGYI_ERPNEXT_API_KEY": "",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "ERPNext API"):
                main_module._validate_permission_source_config()

    def test_fastapi_permission_source_disables_erp_worker_sync_switches(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "LINGYI_PERMISSION_SOURCE": "fastapi",
                "PRODUCTION_ENABLE_WORK_ORDER_WORKER_SYNC": "true",
                "WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC": "true",
                "WORKSHOP_ENABLE_JOB_CARD_WORKER_SYNC": "true",
                "FACTORY_STATEMENT_ENABLE_PAYABLE_WORKER_SYNC": "true",
                "QUALITY_ENABLE_OUTBOX_WORKER_SYNC": "true",
            },
        ):
            self.assertFalse(production_enable_work_order_worker_sync())
            self.assertFalse(warehouse_enable_stock_entry_worker_sync())
            self.assertFalse(workshop_enable_job_card_worker_sync())
            self.assertFalse(factory_statement_enable_payable_worker_sync())
            self.assertFalse(quality_enable_outbox_worker_sync())

    def test_non_fastapi_development_worker_sync_defaults_remain_enabled(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "development", "LINGYI_PERMISSION_SOURCE": "static"}, clear=False):
            self.assertTrue(production_enable_work_order_worker_sync())
            self.assertTrue(warehouse_enable_stock_entry_worker_sync())
            self.assertTrue(workshop_enable_job_card_worker_sync())
            self.assertTrue(factory_statement_enable_payable_worker_sync())
            self.assertTrue(quality_enable_outbox_worker_sync())


if __name__ == "__main__":
    unittest.main()
