#!/usr/bin/env python3
import argparse
import csv
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ALLOWED_CLASSIFICATIONS = {"PASS", "BLOCKING", "RESIDUAL", "SKIPPED_BY_BOUNDARY"}


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def run_cmd(argv: List[str], cwd: Path) -> Tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def normalize_summary_text(text: str, limit: int = 320) -> str:
    compact = " | ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def tsv_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return ";".join(tsv_value(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value).replace("\t", " ")


def write_tsv(path: Path, headers: List[str], rows: List[Dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: tsv_value(row.get(h)) for h in headers})


def extract_counts(script_id: str, result_payload: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {
        "Z008-SCRIPT-001": ("pair_count", "pass_pair_count", "mismatch_pair_count"),
        "Z008-SCRIPT-002": ("file_count", "pass_file_count", "violation_file_count"),
        "Z008-SCRIPT-003": ("gate_count", "pass_gate_count", "block_gate_count"),
        "Z008-SCRIPT-004": ("test_count", "pass_test_count", "block_test_count", "skip_test_count"),
        "Z008-SCRIPT-005": (
            "target_page_count",
            "route_smoke_pass_count",
            "route_smoke_blocked_count",
            "screenshot_count",
            "valid_target_screenshot_count",
        ),
        "Z008-SCRIPT-006": (
            "checked_file_count",
            "pass_check_count",
            "block_check_count",
            "sensitive_pattern_hit_count",
            "state_misjudge_count",
        ),
        "Z008-SCRIPT-007": (
            "check_count",
            "pass_check_count",
            "misjudge_count",
            "blocked_external_dependency_count",
            "blocked_remote_lifecycle_count",
        ),
        "Z008-SCRIPT-008": ("guard_check_count", "pass_guard_count", "violation_count"),
    }
    fields = mapping.get(script_id, tuple())
    return {field: result_payload.get(field) for field in fields}


def probe_dev_server(base_url: str, timeout_seconds: float = 3.5) -> bool:
    probe_target = base_url.rstrip("/") + "/fate/"
    req = urllib.request.Request(probe_target, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            return 200 <= int(resp.status) < 500
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def browser_precondition(entry: Dict[str, Any], runtime_manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    browser_cfg = entry.get("browser_preconditions", {})
    require_browser = bool(browser_cfg.get("require_browser", True))
    require_dev_server = bool(browser_cfg.get("require_dev_server", True))
    require_login_state = bool(browser_cfg.get("require_login_state", True))
    login_env = browser_cfg.get("login_state_env", "Z009_BROWSER_LOGIN_READY")
    login_expected = browser_cfg.get("login_state_expected", "1")

    if require_browser and shutil.which("node") is None:
        missing.append("node_runtime_unavailable")
    if require_dev_server:
        base_url = str(runtime_manifest.get("base_url", "")).strip()
        if not base_url or not probe_dev_server(base_url):
            missing.append("dev_server_unavailable")
    if require_login_state:
        if os.environ.get(login_env, "") != login_expected:
            missing.append(f"login_state_env_missing:{login_env}")

    return len(missing) == 0, missing


def classify_frontend_result(result_payload: Dict[str, Any], browser_payload: Dict[str, Any]) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    task_status = str(result_payload.get("task_status", "BLOCK")).upper()
    request_methods = browser_payload.get("request_methods", [])
    if isinstance(request_methods, str):
        request_methods = [request_methods]
    method_set = {str(m).upper() for m in request_methods}
    non_get = sorted([m for m in method_set if m != "GET"])

    write_request_count = int(browser_payload.get("write_request_count", 0) or 0)
    unexpected_write_request_count = int(browser_payload.get("unexpected_write_request_count", 0) or 0)
    forbidden_request_count = int(browser_payload.get("forbidden_request_count", 0) or 0)
    blocked_count = int(browser_payload.get("route_smoke_blocked_count", 0) or 0)
    console_err = int(browser_payload.get("blocking_console_error_count", 0) or 0)
    network_err = int(browser_payload.get("network_error_count", 0) or 0)

    if task_status != "PASS":
        reasons.append(f"task_status={task_status}")
    if non_get:
        reasons.append(f"non_get_methods={','.join(non_get)}")
    if write_request_count > 0:
        reasons.append(f"write_request_count={write_request_count}")
    if unexpected_write_request_count > 0:
        reasons.append(f"unexpected_write_request_count={unexpected_write_request_count}")
    if forbidden_request_count > 0:
        reasons.append(f"forbidden_request_count={forbidden_request_count}")
    if blocked_count > 0:
        reasons.append(f"route_smoke_blocked_count={blocked_count}")
    if console_err > 0:
        reasons.append(f"blocking_console_error_count={console_err}")
    if network_err > 0:
        reasons.append(f"network_error_count={network_err}")

    return ("PASS", []) if not reasons else ("BLOCKING", reasons)


def build_command(
    entry: Dict[str, Any],
    runtime_manifest_path: Path,
    result_json_path: Path,
    result_tsv_path: Path,
    browser_json_path: Path,
    screenshot_dir: Path,
    repo_root: Path,
    backend_root: Path,
) -> List[str]:
    script_path = Path(entry["script_path"]).resolve()
    lang = entry.get("lang", "python")
    script_id = entry["script_id"]

    if lang == "python":
        cmd = [
            "python3",
            str(script_path),
            "--manifest",
            str(runtime_manifest_path),
            "--output-json",
            str(result_json_path),
            "--output-tsv",
            str(result_tsv_path),
        ]
        if script_id == "Z008-SCRIPT-003":
            cmd.extend(["--repo-root", str(repo_root)])
        if script_id == "Z008-SCRIPT-004":
            cmd.extend(["--backend-root", str(backend_root)])
        return cmd

    if lang == "node":
        return [
            "node",
            str(script_path),
            "--manifest",
            str(runtime_manifest_path),
            "--output-json",
            str(result_json_path),
            "--output-tsv",
            str(result_tsv_path),
            "--output-browser-json",
            str(browser_json_path),
            "--screenshot-dir",
            str(screenshot_dir),
        ]

    raise ValueError(f"Unsupported lang: {lang}")


def prepare_runtime_manifest(
    entry: Dict[str, Any],
    source_head: str,
    selected_candidate_id: str,
    runtime_manifest_path: Path,
) -> Dict[str, Any]:
    base_manifest_path = Path(entry["base_manifest_path"]).resolve()
    base_manifest = load_json(base_manifest_path)
    base_manifest["source_head"] = source_head
    base_manifest["selected_candidate_id"] = selected_candidate_id
    dump_json(runtime_manifest_path, base_manifest)
    return base_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Z008 local acceptance orchestrator.")
    parser.add_argument("--manifest", required=True, help="Orchestrator manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Orchestrator result JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Orchestrator result TSV path.")
    parser.add_argument("--summary-json", required=True, help="Subcheck summary JSON path.")
    parser.add_argument("--summary-tsv", required=True, help="Subcheck summary TSV path.")
    parser.add_argument("--run-root", required=True, help="Runtime output root for subchecks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    output_json_path = Path(args.output_json).resolve()
    output_tsv_path = Path(args.output_tsv).resolve()
    summary_json_path = Path(args.summary_json).resolve()
    summary_tsv_path = Path(args.summary_tsv).resolve()
    run_root = Path(args.run_root).resolve()

    manifest = load_json(manifest_path)
    task_id = manifest.get("task_id", "TASK-Z009B-02-IMPL")
    source_head = manifest.get("source_head")
    selected_candidate_id = manifest.get("selected_candidate_id")
    repo_root = Path(manifest["repo_root"]).resolve()
    backend_root = Path(manifest["backend_root"]).resolve()
    subchecks = manifest.get("subchecks", [])

    subcheck_results: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    aggregate_runtime_request_count = 0
    aggregate_write_request_count = 0
    aggregate_unexpected_write_request_count = 0
    aggregate_forbidden_request_count = 0
    production_account_used = False
    remote_lifecycle_action_executed = False

    for entry in subchecks:
        script_id = entry["script_id"]
        candidate_origin = entry["candidate_origin"]
        runtime_dir = run_root / script_id
        runtime_manifest_path = runtime_dir / "manifest.json"
        result_json_path = runtime_dir / "result.json"
        result_tsv_path = runtime_dir / "result.tsv"
        browser_json_path = runtime_dir / "browser_result.json"
        screenshot_dir = runtime_dir / "screenshots"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        runtime_manifest = prepare_runtime_manifest(
            entry=entry,
            source_head=source_head,
            selected_candidate_id=selected_candidate_id,
            runtime_manifest_path=runtime_manifest_path,
        )

        classification = "PASS"
        status = "PASS"
        exit_code = 0
        reasons: List[str] = []
        stdout_summary = ""
        stderr_summary = ""
        duration_ms = 0
        result_payload: Dict[str, Any] = {}
        browser_payload: Dict[str, Any] = {}
        summary_counts: Dict[str, Any] = {}

        command: List[str] = []
        can_run = True
        if script_id == "Z008-SCRIPT-005":
            can_run, missing = browser_precondition(entry, runtime_manifest)
            if not can_run:
                classification = "SKIPPED_BY_BOUNDARY"
                status = "SKIPPED_BY_BOUNDARY"
                reasons.extend(missing)
                summary_counts = {
                    "target_page_count": runtime_manifest.get("target_page_count")
                    or len(runtime_manifest.get("target_pages", [])),
                    "route_smoke_pass_count": 0,
                    "route_smoke_blocked_count": 0,
                    "runtime_request_count": 0,
                    "write_request_count": 0,
                }

        if can_run:
            command = build_command(
                entry=entry,
                runtime_manifest_path=runtime_manifest_path,
                result_json_path=result_json_path,
                result_tsv_path=result_tsv_path,
                browser_json_path=browser_json_path,
                screenshot_dir=screenshot_dir,
                repo_root=repo_root,
                backend_root=backend_root,
            )
            started = time.monotonic()
            exit_code, stdout, stderr = run_cmd(command, repo_root)
            duration_ms = int((time.monotonic() - started) * 1000)
            stdout_summary = normalize_summary_text(stdout)
            stderr_summary = normalize_summary_text(stderr)

            if result_json_path.exists():
                try:
                    result_payload = load_json(result_json_path)
                except Exception as exc:  # noqa: BLE001
                    classification = "BLOCKING"
                    status = "BLOCKING"
                    reasons.append(f"result_json_parse_error:{exc}")
            else:
                classification = "BLOCKING"
                status = "BLOCKING"
                reasons.append("result_json_missing")

            if script_id == "Z008-SCRIPT-005" and browser_json_path.exists():
                try:
                    browser_payload = load_json(browser_json_path)
                except Exception as exc:  # noqa: BLE001
                    reasons.append(f"browser_json_parse_error:{exc}")

            if classification == "PASS":
                summary_counts = extract_counts(script_id, result_payload)
                task_status = str(result_payload.get("task_status", "BLOCK")).upper()
                if script_id == "Z008-SCRIPT-005":
                    if not browser_payload:
                        classification = "BLOCKING"
                        status = "BLOCKING"
                        reasons.append("browser_result_json_missing_or_invalid")
                    else:
                        frontend_classification, frontend_reasons = classify_frontend_result(
                            result_payload=result_payload,
                            browser_payload=browser_payload,
                        )
                        classification = frontend_classification
                        status = frontend_classification
                        reasons.extend(frontend_reasons)
                else:
                    if task_status == "PASS":
                        classification = "PASS"
                        status = "PASS"
                    else:
                        classification = "BLOCKING"
                        status = "BLOCKING"
                        reasons.append(f"task_status={task_status}")

            if exit_code != 0 and classification == "PASS":
                classification = "BLOCKING"
                status = "BLOCKING"
                reasons.append(f"nonzero_exit_code:{exit_code}")

            if classification not in ALLOWED_CLASSIFICATIONS:
                classification = "BLOCKING"
                status = "BLOCKING"
                reasons.append("invalid_classification")

            aggregate_runtime_request_count += int(result_payload.get("runtime_request_count", 0) or 0)
            aggregate_write_request_count += int(result_payload.get("write_request_count", 0) or 0)
            aggregate_unexpected_write_request_count += int(
                result_payload.get("unexpected_write_request_count", 0) or 0
            )
            aggregate_forbidden_request_count += int(result_payload.get("forbidden_request_count", 0) or 0)
            production_account_used = production_account_used or bool(
                result_payload.get("production_account_used", False)
            )
            remote_lifecycle_action_executed = remote_lifecycle_action_executed or bool(
                result_payload.get("remote_lifecycle_action_executed", False)
            )
        else:
            command = ["<SKIPPED_BY_BOUNDARY>"]

        subcheck_row = {
            "script_id": script_id,
            "candidate_origin": candidate_origin,
            "command": command,
            "status": status,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "classification": classification,
            "runtime_request_profile": entry.get("runtime_request_profile", "NONE"),
            "write_request_profile": entry.get("write_request_profile", "NONE"),
            "summary_counts": summary_counts,
            "runtime_manifest_path": str(runtime_manifest_path),
            "result_json_path": str(result_json_path),
            "result_tsv_path": str(result_tsv_path),
            "browser_result_json_path": str(browser_json_path) if script_id == "Z008-SCRIPT-005" else "null",
            "stdout_summary": stdout_summary or "null",
            "stderr_summary": stderr_summary or "null",
            "reasons": reasons,
        }
        subcheck_results.append(subcheck_row)

        summary_rows.append(
            {
                "script_id": script_id,
                "candidate_origin": candidate_origin,
                "classification": classification,
                "status": status,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "runtime_request_count": result_payload.get("runtime_request_count", 0) if can_run else 0,
                "write_request_count": result_payload.get("write_request_count", 0) if can_run else 0,
                "reason": ";".join(reasons) if reasons else "null",
            }
        )

    subcheck_total = len(subcheck_results)
    pass_count = sum(1 for row in subcheck_results if row["classification"] == "PASS")
    blocking_count = sum(1 for row in subcheck_results if row["classification"] == "BLOCKING")
    residual_count = sum(1 for row in subcheck_results if row["classification"] == "RESIDUAL")
    skipped_by_boundary_count = sum(
        1 for row in subcheck_results if row["classification"] == "SKIPPED_BY_BOUNDARY"
    )

    if blocking_count == 0 and aggregate_write_request_count == 0 and not production_account_used and not remote_lifecycle_action_executed:
        task_status = "PASS"
    else:
        task_status = "BLOCK"

    if aggregate_unexpected_write_request_count > 0 or aggregate_forbidden_request_count > 0:
        task_status = "BLOCK"

    result_payload = {
        "task_id": task_id,
        "source_head": source_head,
        "selected_candidate_id": selected_candidate_id,
        "generated_at": now_cn(),
        "task_status": task_status,
        "orchestrator_script_path": str(Path(__file__).resolve()),
        "manifest_path": str(manifest_path),
        "subcheck_total": subcheck_total,
        "pass_count": pass_count,
        "blocking_count": blocking_count,
        "residual_count": residual_count,
        "skipped_by_boundary_count": skipped_by_boundary_count,
        "runtime_request_count": aggregate_runtime_request_count,
        "write_request_count": aggregate_write_request_count,
        "unexpected_write_request_count": aggregate_unexpected_write_request_count,
        "forbidden_request_count": aggregate_forbidden_request_count,
        "production_account_used": production_account_used,
        "remote_lifecycle_action_executed": remote_lifecycle_action_executed,
        "subchecks": subcheck_results,
    }

    summary_payload = {
        "task_id": task_id,
        "source_head": source_head,
        "selected_candidate_id": selected_candidate_id,
        "generated_at": now_cn(),
        "subcheck_total": subcheck_total,
        "pass_count": pass_count,
        "blocking_count": blocking_count,
        "residual_count": residual_count,
        "skipped_by_boundary_count": skipped_by_boundary_count,
        "runtime_request_count": aggregate_runtime_request_count,
        "write_request_count": aggregate_write_request_count,
        "production_account_used": production_account_used,
        "remote_lifecycle_action_executed": remote_lifecycle_action_executed,
        "summary_entries": summary_rows,
    }

    dump_json(output_json_path, result_payload)
    dump_json(summary_json_path, summary_payload)

    write_tsv(
        output_tsv_path,
        headers=[
            "script_id",
            "candidate_origin",
            "classification",
            "status",
            "exit_code",
            "duration_ms",
            "runtime_request_profile",
            "write_request_profile",
            "runtime_request_count",
            "write_request_count",
            "reason",
        ],
        rows=[
            {
                "script_id": row["script_id"],
                "candidate_origin": row["candidate_origin"],
                "classification": row["classification"],
                "status": row["status"],
                "exit_code": row["exit_code"],
                "duration_ms": row["duration_ms"],
                "runtime_request_profile": row["runtime_request_profile"],
                "write_request_profile": row["write_request_profile"],
                "runtime_request_count": row["summary_counts"].get("runtime_request_count", 0)
                if isinstance(row["summary_counts"], dict)
                else 0,
                "write_request_count": row["summary_counts"].get("write_request_count", 0)
                if isinstance(row["summary_counts"], dict)
                else 0,
                "reason": ";".join(row["reasons"]) if row["reasons"] else "null",
            }
            for row in subcheck_results
        ],
    )

    write_tsv(
        summary_tsv_path,
        headers=[
            "script_id",
            "candidate_origin",
            "classification",
            "status",
            "exit_code",
            "duration_ms",
            "runtime_request_count",
            "write_request_count",
            "reason",
        ],
        rows=summary_rows,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
