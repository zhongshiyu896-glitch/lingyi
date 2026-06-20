#!/usr/bin/env python3
"""Smoke-test the FastAPI local-dev app from a clean temporary SQLite DB."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

COMPANY = "默认公司"
HEADERS = {
    "X-LY-Dev-User": "clean.local.dev",
    "X-LY-Dev-Roles": "System Manager",
}


def _configure_env() -> None:
    os.environ["APP_ENV"] = "development"
    os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
    os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
    os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
    os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"


def _assert_envelope(response, label: str) -> dict[str, Any]:
    if response.status_code >= 400:
        raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text}")
    payload = response.json()
    if payload.get("code") != "0":
        raise AssertionError(f"{label}: code={payload.get('code')} message={payload.get('message')}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AssertionError(f"{label}: response data is not an object")
    return data


def _table_counts(db_path: Path) -> dict[str, int]:
    required_tables = [
        "ly_master_data_record",
        "ly_style_dictionary",
        "ly_style_master",
        "ly_apparel_bom",
        "ly_apparel_bom_item",
        "ly_finance_approval_template",
    ]
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = [table for table in required_tables if table not in tables]
        if missing:
            raise AssertionError(f"missing clean local-dev tables: {missing}")
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in required_tables
        }


def _run_smoke(db_path: Path) -> dict[str, Any]:
    _configure_env()

    from app import local_dev  # noqa: PLC0415

    client = TestClient(local_dev.app)
    counts = _table_counts(db_path)

    styles = _assert_envelope(
        client.get(
            "/api/style-master/styles",
            params={"company": COMPANY, "keyword": "DEMO-TEE", "page": 1, "page_size": 10},
            headers=HEADERS,
        ),
        "style list",
    )
    style_items = styles.get("items") or []
    if not style_items:
        raise AssertionError("style list: DEMO-TEE seed was not returned")
    style = style_items[0]
    style_id = int(style["id"])

    materials = _assert_envelope(
        client.get(
            "/api/master-data/materials",
            params={"company": COMPANY, "keyword": "FABRIC-COTTON", "page": 1, "page_size": 10},
            headers=HEADERS,
        ),
        "material list",
    )
    if not (materials.get("items") or []):
        raise AssertionError("material list: FABRIC-COTTON seed was not returned")

    bom = _assert_envelope(
        client.get(
            f"/api/style-master/styles/{style_id}/material-bom",
            params={"company": COMPANY},
            headers=HEADERS,
        ),
        "style material bom",
    )
    if not bom.get("bom") or not (bom.get("items") or []):
        raise AssertionError("style material bom: seeded BOM header/items were not returned")

    exploded = _assert_envelope(
        client.post(
            f"/api/style-master/styles/{style_id}/material-bom/explode",
            params={"company": COMPANY},
            json={"order_qty": 10},
            headers=HEADERS,
        ),
        "style material bom explode",
    )
    if float(exploded.get("total_required_qty") or 0) <= 0:
        raise AssertionError("style material bom explode: total_required_qty must be positive")

    templates = _assert_envelope(
        client.get(
            "/api/finance/approval-tasks/templates",
            params={"company": COMPANY, "page": 1, "page_size": 10},
            headers=HEADERS,
        ),
        "finance approval templates",
    )
    if not (templates.get("items") or []):
        raise AssertionError("finance approval templates: default templates were not returned")

    return {
        "ok": True,
        "db_path": str(db_path),
        "table_counts": counts,
        "style": {
            "id": style_id,
            "ys_style_no": style.get("ys_style_no"),
            "ys_style_name_cn": style.get("ys_style_name_cn"),
        },
        "bom_item_count": len(bom.get("items") or []),
        "bom_total_required_qty": exploded.get("total_required_qty"),
        "finance_template_count": len(templates.get("items") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-db", action="store_true", help="Keep the temporary SQLite file for manual inspection.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="lingyi-clean-local-dev-") as tmpdir:
        original_cwd = Path.cwd()
        db_path = Path(tmpdir) / "lingyi_service.local.db"
        os.chdir(tmpdir)
        try:
            result = _run_smoke(db_path)
            if args.keep_db:
                kept_path = original_cwd / "lingyi_clean_smoke.keep.db"
                kept_path.write_bytes(db_path.read_bytes())
                result["kept_db_path"] = str(kept_path)
        finally:
            os.chdir(original_cwd)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise
