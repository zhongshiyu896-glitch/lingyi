"""Test environment bootstrap for pytest/unittest isolation."""

from __future__ import annotations

import os


def configure_test_env() -> None:
    """Force test-safe env before importing app modules."""
    os.environ["APP_ENV"] = "test"
    os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
    os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
    os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
