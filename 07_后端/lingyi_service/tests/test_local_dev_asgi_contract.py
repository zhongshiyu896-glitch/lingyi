"""Direct contract tests for the local-dev ASGI runtime."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sqlite3
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

    def test_local_dev_forces_static_source_and_blocks_inherited_erpnext_base_url(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "false"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = "http://127.0.0.1:9081"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_DB_URL"] = f"sqlite:///{self._temp_db_path}"
        sys.modules.pop("app.local_dev", None)

        local_dev_module = importlib.import_module("app.local_dev")
        engine_db = Path(local_dev_module.main_module.engine.url.database).resolve()

        self.assertEqual(os.environ["APP_ENV"], "development")
        self.assertEqual(os.environ["LINGYI_ALLOW_DEV_AUTH"], "true")
        self.assertEqual(os.environ["LINGYI_ERPNEXT_BASE_URL"], "")
        self.assertEqual(os.environ["LINGYI_PERMISSION_SOURCE"], "static")
        self.assertEqual(engine_db, self._temp_db_path.resolve())
        self._assert_repo_db_stats_unchanged()

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

    def test_local_dev_seeds_clean_api_report_and_purchase_requirement_rows(self) -> None:
        local_dev_module = self._load_local_dev_module()
        headers = {
            "X-LY-Dev-User": "local.dev.contract",
            "X-LY-Dev-Roles": "System Manager",
        }

        with TestClient(local_dev_module.app) as client:
            report_response = client.get(
                "/api/production/report-suite",
                params={"report_key": "productOrderProfitReport"},
                headers=headers,
            )
            requirement_response = client.get(
                "/api/material-purchase/requirements",
                params={"status": "pending"},
                headers=headers,
            )

        self.assertEqual(report_response.status_code, 200, report_response.text)
        report_payload = report_response.json()
        self.assertEqual(report_payload["code"], "0")
        report_data = report_payload["data"]
        self.assertEqual(report_data["report_key"], "productOrderProfitReport")
        self.assertGreater(len(report_data["items"]), 0)
        demo_row = next(
            item for item in report_data["items"] if item["sales_order"] == "SO-LOCAL-DEMO-001"
        )
        self.assertEqual(demo_row["styleNo"], "DEMO-TEE")
        self.assertGreater(float(demo_row["amount"]), 0)
        self.assertGreater(float(demo_row["totalCost"]), 0)

        self.assertEqual(requirement_response.status_code, 200, requirement_response.text)
        requirement_payload = requirement_response.json()
        self.assertEqual(requirement_payload["code"], "0")
        requirement_data = requirement_payload["data"]
        self.assertGreater(len(requirement_data["items"]), 0)
        self.assertTrue(
            any(item["sales_order"] == "SO-LOCAL-DEMO-001" for item in requirement_data["items"])
        )
        self._assert_repo_db_stats_unchanged()

    def test_local_dev_migrates_legacy_sales_order_item_style_master_column(self) -> None:
        with sqlite3.connect(self._temp_db_path) as connection:
            connection.execute(
                """
                CREATE TABLE ly_sales_order_item (
                    id INTEGER PRIMARY KEY,
                    sales_order_id INTEGER NOT NULL,
                    company VARCHAR(140) NOT NULL,
                    line_no INTEGER NOT NULL,
                    sales_order_item VARCHAR(140) NOT NULL,
                    item_code VARCHAR(140) NOT NULL,
                    item_name VARCHAR(255),
                    color VARCHAR(64),
                    size VARCHAR(64),
                    qty NUMERIC NOT NULL,
                    planned_qty NUMERIC NOT NULL DEFAULT 0,
                    delivered_qty NUMERIC NOT NULL DEFAULT 0,
                    ys_material_calc_state VARCHAR(32) NOT NULL DEFAULT '待算料',
                    rate NUMERIC,
                    amount NUMERIC,
                    uom VARCHAR(32) NOT NULL DEFAULT 'Nos',
                    warehouse VARCHAR(140),
                    delivery_date DATE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE ly_style_master (
                    id INTEGER PRIMARY KEY,
                    company VARCHAR(140) NOT NULL,
                    ys_style_no VARCHAR(140) NOT NULL,
                    ys_style_name_cn VARCHAR(255) NOT NULL,
                    ys_season VARCHAR(64),
                    ys_year VARCHAR(16),
                    ys_brand VARCHAR(64),
                    ys_style_status VARCHAR(32) NOT NULL,
                    colors JSON NOT NULL DEFAULT '[]',
                    sizes JSON NOT NULL DEFAULT '[]',
                    version INTEGER NOT NULL DEFAULT 1,
                    created_by VARCHAR(140) NOT NULL DEFAULT 'legacy.test',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_by VARCHAR(140) NOT NULL DEFAULT 'legacy.test',
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    disabled_by VARCHAR(140),
                    disabled_at DATETIME,
                    disable_reason VARCHAR(255)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO ly_style_master (
                    id, company, ys_style_no, ys_style_name_cn, ys_style_status
                )
                VALUES (101, '默认公司', 'LEGACY-STYLE', '旧表款式', 'enabled')
                """
            )
            connection.execute(
                """
                INSERT INTO ly_sales_order_item (
                    id, sales_order_id, company, line_no, sales_order_item, item_code, qty
                )
                VALUES (1, 1, '默认公司', 1, 'SO-LEGACY-001-001', 'LEGACY-STYLE', 10)
                """
            )
            connection.commit()

        self._load_local_dev_module()

        with sqlite3.connect(self._temp_db_path) as connection:
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(ly_sales_order_item)").fetchall()
            }
            indexes = {
                str(row[1])
                for row in connection.execute("PRAGMA index_list(ly_sales_order_item)").fetchall()
            }
            linked_id = connection.execute(
                "SELECT style_master_id FROM ly_sales_order_item WHERE id = 1"
            ).fetchone()[0]

        self.assertIn("style_master_id", columns)
        self.assertIn("idx_ly_sales_order_item_style_master", indexes)
        self.assertEqual(linked_id, 101)
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
