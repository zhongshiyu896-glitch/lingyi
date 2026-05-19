#!/usr/bin/env python3
import argparse
import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


TRAILING_WHITESPACE_RE = re.compile(r"[ \t]+$")


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def load_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "status": "FAIL",
            "line_count": 0,
            "trailing_whitespace_count": 0,
            "eof_single_newline": False,
            "error": f"missing:{path}",
        }

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()

    trailing_count = 0
    for line in lines:
        if TRAILING_WHITESPACE_RE.search(line):
            trailing_count += 1

    eof_single_newline = False
    if raw.endswith(b"\n"):
        trailing_newline_count = 0
        idx = len(raw) - 1
        while idx >= 0 and raw[idx] == 0x0A:
            trailing_newline_count += 1
            idx -= 1
        eof_single_newline = trailing_newline_count == 1

    status = "PASS" if trailing_count == 0 and eof_single_newline else "FAIL"
    return {
        "status": status,
        "line_count": len(lines),
        "trailing_whitespace_count": trailing_count,
        "eof_single_newline": eof_single_newline,
        "error": "",
    }


def write_tsv(path: Path, rows: List[Dict[str, Any]]) -> None:
    headers = [
        "entry_id",
        "path",
        "status",
        "line_count",
        "trailing_whitespace_count",
        "eof_single_newline",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "entry_id": row["entry_id"],
                    "path": row["path"],
                    "status": row["status"],
                    "line_count": row["line_count"],
                    "trailing_whitespace_count": row["trailing_whitespace_count"],
                    "eof_single_newline": "true" if row["eof_single_newline"] else "false",
                    "error": row["error"] if row["error"] else "null",
                }
            )


def run(manifest_path: Path, output_json: Path, output_tsv: Path) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    entries = manifest.get("entries", [])

    results: List[Dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    for entry in entries:
        entry_id = entry["entry_id"]
        path = Path(entry["path"])
        check = check_file(path)
        row = {
            "entry_id": entry_id,
            "path": str(path),
            "status": check["status"],
            "line_count": check["line_count"],
            "trailing_whitespace_count": check["trailing_whitespace_count"],
            "eof_single_newline": check["eof_single_newline"],
            "error": check["error"],
        }
        results.append(row)
        if row["status"] == "PASS":
            pass_count += 1
        else:
            fail_count += 1

    task_status = "PASS" if fail_count == 0 else "BLOCK"
    payload = {
        "task_id": manifest.get("task_id", "TASK-Z008B-07-IMPL"),
        "source_head": manifest.get("source_head"),
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "generated_at": now_cn(),
        "file_count": len(results),
        "pass_file_count": pass_count,
        "violation_file_count": fail_count,
        "task_status": task_status,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "results": results,
    }

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_tsv(output_tsv, results)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify text hygiene for evidence files.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Output result JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Output result TSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(Path(args.manifest), Path(args.output_json), Path(args.output_tsv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
