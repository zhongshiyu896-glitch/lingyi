"""Permission-source runtime config tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import app.main as main_module
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


if __name__ == "__main__":
    unittest.main()
