"""Direct contract tests for the local-dev ASGI runtime."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

import app.main as app_main_module


class LocalDevAsgiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend_root = Path(__file__).resolve().parents[1]
        cls.repo_db_paths = [
            cls.backend_root / "lingyi_service.local.db",
            cls.backend_root / "not_local_dev_gate.db",
        ]

    def setUp(self) -> None:
        self._old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "LINGYI_ALLOW_DEV_AUTH": os.environ.get("LINGYI_ALLOW_DEV_AUTH"),
            "LINGYI_ERPNEXT_BASE_URL": os.environ.get("LINGYI_ERPNEXT_BASE_URL"),
            "LINGYI_PERMISSION_SOURCE": os.environ.get("LINGYI_PERMISSION_SOURCE"),
            "LINGYI_DB_URL": os.environ.get("LINGYI_DB_URL"),
        }
        self._temp_dir = tempfile.TemporaryDirectory()
        self._temp_db_path = Path(self._temp_dir.name) / "local-dev-runtime.sqlite3"
        self._repo_db_stats_before = self._capture_repo_db_stats()

    def tearDown(self) -> None:
        local_dev_module = sys.modules.pop("app.local_dev", None)
        if local_dev_module is not None:
            engine = getattr(getattr(local_dev_module, "main_module", None), "engine", None)
            if engine is not None:
                engine.dispose()
        importlib.reload(app_main_module)
        self._restore_env()
        self._temp_dir.cleanup()

    def _restore_env(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _capture_repo_db_stats(self) -> dict[Path, tuple[bool, int | None, int | None]]:
        snapshot: dict[Path, tuple[bool, int | None, int | None]] = {}
        for path in self.repo_db_paths:
            if path.exists():
                stat = path.stat()
                snapshot[path] = (True, stat.st_mtime_ns, stat.st_size)
            else:
                snapshot[path] = (False, None, None)
        return snapshot

    def _assert_repo_db_stats_unchanged(self) -> None:
        for path, before in self._repo_db_stats_before.items():
            if before[0]:
                self.assertTrue(path.exists(), msg=f"repo db unexpectedly missing: {path}")
                stat = path.stat()
                self.assertEqual((stat.st_mtime_ns, stat.st_size), before[1:], msg=f"repo db mutated: {path}")
            else:
                self.assertFalse(path.exists(), msg=f"repo db unexpectedly created: {path}")

    def _set_local_dev_env(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_DB_URL"] = f"sqlite:///{self._temp_db_path}"

    def _load_local_dev_module(self):
        self._set_local_dev_env()
        importlib.reload(app_main_module)
        sys.modules.pop("app.local_dev", None)
        return importlib.import_module("app.local_dev")

    def test_main_app_does_not_expose_local_dev_routes_without_direct_import(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_DB_URL"] = f"sqlite:///{self._temp_db_path}"
        reloaded_main = importlib.reload(app_main_module)

        with TestClient(reloaded_main.app) as client:
            response = client.get("/api/local-dev/dashboard/status-summary", params={"scenario_tag": "Z12A-MAIN-404"})

        self.assertEqual(response.status_code, 404)
        self._assert_repo_db_stats_unchanged()

    def test_local_dev_app_exposes_readback_summary_on_temp_sqlite_only(self) -> None:
        local_dev_module = self._load_local_dev_module()
        engine_db = Path(local_dev_module.main_module.engine.url.database).resolve()

        self.assertEqual(engine_db, self._temp_db_path.resolve())

        with TestClient(local_dev_module.app) as client:
            response = client.get(
                "/api/local-dev/dashboard/status-summary",
                params={"scenario_tag": "Z12A-LOCAL-SUMMARY"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        data = payload["data"]
        self.assertTrue(data["readback_only"])
        self.assertEqual(data["production_safety"]["production_write_requests"], 0)
        self.assertEqual(data["production_safety"]["erpnext_production_write_requests"], 0)
        self.assertFalse(data["production_safety"]["real_production_account_used"])
        self.assertTrue(self._temp_db_path.exists())
        self._assert_repo_db_stats_unchanged()

    def test_local_dev_checkpoint_rollback_is_explicit_no_op(self) -> None:
        local_dev_module = self._load_local_dev_module()

        with TestClient(local_dev_module.app) as client:
            response = client.post(
                "/api/local-dev/dashboard/checkpoints/rollback",
                json={"scenario_tag": "Z12A-NOOP-ROLLBACK"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        data = payload["data"]
        self.assertTrue(data["readback_only_no_write"])
        self.assertEqual(data["deleted_count"], 0)
        self.assertEqual(data["residual_records_after_rollback"], 0)
        self.assertTrue(data["rollback_success"])
        self._assert_repo_db_stats_unchanged()


if __name__ == "__main__":
    unittest.main()
