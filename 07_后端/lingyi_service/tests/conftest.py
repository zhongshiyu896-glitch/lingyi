"""Shared test bootstrap for stable import-time settings."""

from __future__ import annotations

from tests.test_env import configure_test_env
from tests.test_env import ensure_test_fastapi_role_actions

configure_test_env()


def pytest_runtest_setup(item):  # noqa: ARG001
    ensure_test_fastapi_role_actions()


def pytest_runtest_teardown(item, nextitem):  # noqa: ARG001
    ensure_test_fastapi_role_actions()
