#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


COUNT_PATTERNS = {
    "pass_count": re.compile(r"(\d+)\s+passed"),
    "fail_count": re.compile(r"(\d+)\s+failed"),
    "skip_count": re.compile(r"(\d+)\s+skipped"),
    "deselected_count": re.compile(r"(\d+)\s+deselected"),
}


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def choose_runner(backend_root: Path) -> str:
    preferred = backend_root / ".venv" / "bin" / "python"
    if preferred.exists():
        return str(preferred)
    return "python3"


def parse_counts(text: str) -> Dict[str, int]:
    payload = {
        "pass_count": 0,
        "fail_count": 0,
        "skip_count": 0,
        "deselected_count": 0,
    }
    for key, pattern in COUNT_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            payload[key] = int(matches[-1])
    return payload


def summarize(text: str, limit: int = 240) -> str:
    compact = " | ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def resolve_pytest_target(backend_root: Path, module: str) -> str:
    module_text = module.strip()
    if "/" in module_text or module_text.endswith(".py"):
        return module_text
    if "." in module_text:
        candidate = backend_root / (module_text.replace(".", "/") + ".py")
        if candidate.exists():
            return str(candidate.relative_to(backend_root))
    return module_text


def run_one_test(backend_root: Path, runner: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    test_id = entry["test_id"]
    module = entry["module"]
    target = resolve_pytest_target(backend_root, module)
    args = entry.get("pytest_args", [])
    required = bool(entry.get("required", True))
    allow_skip_on_no_collection = bool(entry.get("allow_skip_on_no_collection", False))

    cmd = [runner, "-m", "pytest", target] + args
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=backend_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    duration = round(time.monotonic() - start, 3)

    combined = f"{proc.stdout}\n{proc.stderr}"
    counts = parse_counts(combined)

    status = "PASS"
    skip_reason = "null"
    if proc.returncode == 0:
        if required and counts["pass_count"] == 0:
            status = "BLOCK"
            skip_reason = "required_test_has_zero_pass_count"
        elif counts["fail_count"] > 0:
            status = "BLOCK"
            skip_reason = "pytest_reported_failures"
    elif proc.returncode == 5 and allow_skip_on_no_collection:
        status = "SKIPPED_WITH_REASON"
        skip_reason = "pytest_no_tests_collected_for_selector"
    else:
        status = "BLOCK"
        if proc.returncode == 5:
            skip_reason = "pytest_no_tests_collected_for_required_item"
        else:
            skip_reason = f"nonzero_exit_code:{proc.returncode}"

    return {
        "test_id": test_id,
        "module": module,
        "resolved_target": target,
        "status": status,
        "exit_code": proc.returncode,
        "pass_count": counts["pass_count"],
        "fail_count": counts["fail_count"],
        "skip_count": counts["skip_count"],
        "deselected_count": counts["deselected_count"],
        "duration_seconds": duration,
        "required": required,
        "skip_reason": skip_reason,
        "command": " ".join(cmd),
        "stdout_summary": summarize(proc.stdout),
        "stderr_summary": summarize(proc.stderr),
    }


def write_tsv(path: Path, rows: List[Dict[str, Any]]) -> None:
    headers = [
        "test_id",
        "module",
        "status",
        "exit_code",
        "pass_count",
        "fail_count",
        "skip_count",
        "deselected_count",
        "duration_seconds",
        "required",
        "skip_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "test_id": row["test_id"],
                    "module": row["module"],
                    "status": row["status"],
                    "exit_code": row["exit_code"],
                    "pass_count": row["pass_count"],
                    "fail_count": row["fail_count"],
                    "skip_count": row["skip_count"],
                    "deselected_count": row["deselected_count"],
                    "duration_seconds": row["duration_seconds"],
                    "required": "true" if row["required"] else "false",
                    "skip_reason": row["skip_reason"],
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend contract/fixture test matrix.")
    parser.add_argument("--backend-root", required=True, help="Backend root path.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Output JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Output TSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend_root = Path(args.backend_root)
    manifest_path = Path(args.manifest)
    output_json = Path(args.output_json)
    output_tsv = Path(args.output_tsv)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tests = manifest.get("test_entries", [])
    runner = choose_runner(backend_root)

    results: List[Dict[str, Any]] = []
    for entry in tests:
        results.append(run_one_test(backend_root, runner, entry))

    test_count = len(results)
    pass_test_count = sum(1 for row in results if row["status"] == "PASS")
    block_test_count = sum(1 for row in results if row["status"] == "BLOCK")
    skip_test_count = sum(1 for row in results if row["status"] == "SKIPPED_WITH_REASON")

    required_non_pass = [
        row for row in results if row["required"] and row["status"] != "PASS"
    ]
    failure_catalog = [
        {
            "test_id": row["test_id"],
            "module": row["module"],
            "status": row["status"],
            "exit_code": row["exit_code"],
            "skip_reason": row["skip_reason"],
            "stderr_summary": row["stderr_summary"],
        }
        for row in results
        if row["status"] == "BLOCK"
    ]

    task_status = "PASS" if not required_non_pass and block_test_count == 0 else "BLOCK"

    payload = {
        "task_id": manifest.get("task_id", "TASK-Z008B-17-IMPL"),
        "source_head": manifest.get("source_head"),
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "generated_at": now_cn(),
        "backend_root": str(backend_root),
        "runner": runner,
        "task_status": task_status,
        "test_count": test_count,
        "pass_test_count": pass_test_count,
        "block_test_count": block_test_count,
        "skip_test_count": skip_test_count,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "failure_catalog": failure_catalog,
        "results": results,
    }

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_tsv(output_tsv, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
