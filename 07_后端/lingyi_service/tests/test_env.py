"""Test environment bootstrap for pytest/unittest isolation."""

from __future__ import annotations

import os
import unittest


def configure_test_env() -> None:
    """Force test-safe env before importing app modules."""
    os.environ["APP_ENV"] = "test"
    os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
    os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
    os.environ["LINGYI_PERMISSION_SOURCE"] = "static"


class ConfigureTestEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "LINGYI_ALLOW_DEV_AUTH": os.environ.get("LINGYI_ALLOW_DEV_AUTH"),
            "LINGYI_ERPNEXT_BASE_URL": os.environ.get("LINGYI_ERPNEXT_BASE_URL"),
            "LINGYI_PERMISSION_SOURCE": os.environ.get("LINGYI_PERMISSION_SOURCE"),
            "LINGYI_AUTH_CACHE_TTL_SECONDS": os.environ.get("LINGYI_AUTH_CACHE_TTL_SECONDS"),
        }

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_configure_test_env_forces_test_safe_guards(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "false"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = "https://erpnext.example.com"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"

        configure_test_env()

        self.assertEqual(os.environ["APP_ENV"], "test")
        self.assertEqual(os.environ["LINGYI_ALLOW_DEV_AUTH"], "true")
        self.assertEqual(os.environ["LINGYI_ERPNEXT_BASE_URL"], "")
        self.assertEqual(os.environ["LINGYI_PERMISSION_SOURCE"], "static")

    def test_dev_auth_default_is_closed(self) -> None:
        from app.core.auth import is_local_session_auth_enabled

        os.environ["APP_ENV"] = "development"
        os.environ.pop("LINGYI_ALLOW_DEV_AUTH", None)

        self.assertFalse(is_local_session_auth_enabled())

    def test_auth_cache_ttl_is_capped_at_sixty_seconds(self) -> None:
        from app.core.auth import _auth_session_cache_ttl_seconds

        os.environ["LINGYI_AUTH_CACHE_TTL_SECONDS"] = "300"

        self.assertEqual(_auth_session_cache_ttl_seconds(), 60.0)


if __name__ == "__main__":
    unittest.main()
