#!/usr/bin/env python3
import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def first_nonempty(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def check_text_hygiene(path: Path) -> Tuple[int, bool]:
    data = path.read_bytes()
    text = data.decode("utf-8")
    trailing = sum(1 for line in text.splitlines() if line.rstrip(" \t") != line)
    eof_single = data.endswith(b"\n") and not data.endswith(b"\n\n")
    return trailing, eof_single


def add_check(
    checks: List[Dict[str, Any]],
    check_id: str,
    check_name: str,
    ok: bool,
    expected: Any,
    observed: Any,
    details: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "check_name": check_name,
            "status": "PASS" if ok else "BLOCK",
            "classification": "PASS" if ok else "BLOCKING",
            "expected": "-" if expected in (None, "") else expected,
            "observed": "-" if observed in (None, "") else observed,
            "details": "-" if details in (None, "") else details,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Z009 post-orchestrator regression gate.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Result JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Result TSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    output_json_path = Path(args.output_json).resolve()
    output_tsv_path = Path(args.output_tsv).resolve()

    manifest = load_json(manifest_path)
    repo_root = Path(manifest["repo_root"]).resolve()
    checks: List[Dict[str, Any]] = []

    # Check 1: source HEAD
    head_rc, head_out, head_err = run_cmd(["git", "rev-parse", "HEAD"], repo_root)
    head_value = head_out.strip()
    add_check(
        checks,
        "RG-001",
        "source_head_match",
        head_rc == 0 and head_value == manifest["source_head"],
        manifest["source_head"],
        head_value if head_rc == 0 else f"cmd_error:{head_err.strip()}",
    )

    # Check 2-9: Z008 eight candidate evidence freeze files
    for idx, item in enumerate(manifest["z008_freeze_checks"], start=2):
        path = Path(item["path"])
        cid = item["candidate_id"]
        cid_key = item["candidate_key"]
        check_id = f"RG-{idx:03d}"
        check_name = f"z008_candidate_evidence_{cid}"
        if not path.exists():
            add_check(checks, check_id, check_name, False, f"{cid_key}={cid}", "file_missing", str(path))
            continue
        payload = load_json(path)
        marker_ok = payload.get(cid_key) == cid
        task_ok = True
        expected_parts = [f"{cid_key}={cid}"]
        observed_parts = [f"{cid_key}={payload.get(cid_key)}"]
        if "task_status" in item:
            expected_parts.append(f"task_status={item['task_status']}")
            observed_parts.append(f"task_status={payload.get('task_status')}")
            task_ok = task_ok and payload.get("task_status") == item["task_status"]
        if "freeze_status" in item:
            expected_parts.append(f"freeze_status={item['freeze_status']}")
            observed_parts.append(f"freeze_status={payload.get('freeze_status')}")
            task_ok = task_ok and payload.get("freeze_status") == item["freeze_status"]
        add_check(
            checks,
            check_id,
            check_name,
            marker_ok and task_ok,
            ",".join(expected_parts),
            ",".join(observed_parts),
            str(path),
        )

    # Check 10: Z008 final closeout
    z008_final = load_json(Path(manifest["z008_final_refresh_path"]))
    add_check(
        checks,
        "RG-010",
        "z008_final_closed",
        z008_final.get("z008_local_acceptance_automation_closed") is True
        and z008_final.get("remaining_candidate_count") == 0,
        "z008_local_acceptance_automation_closed=true,remaining_candidate_count=0",
        f"z008_local_acceptance_automation_closed={z008_final.get('z008_local_acceptance_automation_closed')},"
        f"remaining_candidate_count={z008_final.get('remaining_candidate_count')}",
        manifest["z008_final_refresh_path"],
    )

    # Check 11: Z009 orchestrator committed state
    z009_state = load_json(Path(manifest["z009_orchestrator_state_path"]))
    add_check(
        checks,
        "RG-011",
        "z009_orchestrator_committed_state",
        z009_state.get("orchestrator_committed") is True
        and z009_state.get("subcheck_total") == 8
        and z009_state.get("pass_count") == 7
        and z009_state.get("blocking_count") == 0
        and z009_state.get("skipped_by_boundary_count") == 1,
        "orchestrator_committed=true,subcheck_total=8,pass_count=7,blocking_count=0,skipped_by_boundary_count=1",
        f"orchestrator_committed={z009_state.get('orchestrator_committed')},subcheck_total={z009_state.get('subcheck_total')},"
        f"pass_count={z009_state.get('pass_count')},blocking_count={z009_state.get('blocking_count')},"
        f"skipped_by_boundary_count={z009_state.get('skipped_by_boundary_count')}",
        manifest["z009_orchestrator_state_path"],
    )

    # Check 12: Z009 browser login rerun freeze
    z009_rerun = load_json(Path(manifest["z009_browser_rerun_freeze_path"]))
    be = manifest["browser_skip_expected"]
    add_check(
        checks,
        "RG-012",
        "z009_browser_rerun_skip_boundary",
        z009_rerun.get("script_005_status") == be["script_005_status"]
        and z009_rerun.get("skipped_reason") == be["skipped_reason"]
        and z009_rerun.get("full_browser_route_smoke_closed") == be["full_browser_route_smoke_closed"]
        and z009_rerun.get("subcheck_total") == 8
        and z009_rerun.get("pass_count") == 7
        and z009_rerun.get("blocking_count") == 0,
        "script_005_status=SKIPPED_BY_BOUNDARY,skipped_reason=login_state_env_missing:Z009_BROWSER_LOGIN_READY,full_browser_route_smoke_closed=false",
        f"script_005_status={z009_rerun.get('script_005_status')},skipped_reason={z009_rerun.get('skipped_reason')},"
        f"full_browser_route_smoke_closed={z009_rerun.get('full_browser_route_smoke_closed')}",
        manifest["z009_browser_rerun_freeze_path"],
    )

    # Check 13: skip-aware anchor
    anchor = load_json(Path(manifest["z009_skip_anchor_path"]))
    add_check(
        checks,
        "RG-013",
        "z009_skip_aware_anchor",
        anchor.get("z009_orchestrator_local_closed") is True
        and anchor.get("z009_orchestrator_closed_mode") == "SKIP_AWARE_LOCAL_CLOSED_WITH_RESIDUAL"
        and anchor.get("subcheck_total") == 8
        and anchor.get("pass_count") == 7
        and anchor.get("blocking_count") == 0
        and anchor.get("skipped_by_boundary_count") == 1,
        "z009_orchestrator_local_closed=true,mode=SKIP_AWARE_LOCAL_CLOSED_WITH_RESIDUAL,subcheck_total=8,pass_count=7,blocking_count=0,skipped_by_boundary_count=1",
        f"z009_orchestrator_local_closed={anchor.get('z009_orchestrator_local_closed')},"
        f"mode={anchor.get('z009_orchestrator_closed_mode')},subcheck_total={anchor.get('subcheck_total')},"
        f"pass_count={anchor.get('pass_count')},blocking_count={anchor.get('blocking_count')},"
        f"skipped_by_boundary_count={anchor.get('skipped_by_boundary_count')}",
        manifest["z009_skip_anchor_path"],
    )

    # Check 14: summary dashboard core state
    dash_json = load_json(Path(manifest["z009_dashboard_json_path"]))
    add_check(
        checks,
        "RG-014",
        "z009_summary_dashboard_core_state",
        dash_json.get("dashboard_generated") is True
        and dash_json.get("dashboard_entry_count") == 14
        and dash_json.get("z009_orchestrator_local_closed") is True
        and dash_json.get("full_browser_route_smoke_closed") is False
        and dash_json.get("subcheck_total") == 8
        and dash_json.get("pass_count") == 7
        and dash_json.get("skipped_by_boundary_count") == 1,
        "dashboard_generated=true,dashboard_entry_count=14,z009_orchestrator_local_closed=true,full_browser_route_smoke_closed=false,subcheck_total=8,pass_count=7,skipped_by_boundary_count=1",
        f"dashboard_generated={dash_json.get('dashboard_generated')},dashboard_entry_count={dash_json.get('dashboard_entry_count')},"
        f"z009_orchestrator_local_closed={dash_json.get('z009_orchestrator_local_closed')},"
        f"full_browser_route_smoke_closed={dash_json.get('full_browser_route_smoke_closed')},"
        f"subcheck_total={dash_json.get('subcheck_total')},pass_count={dash_json.get('pass_count')},"
        f"skipped_by_boundary_count={dash_json.get('skipped_by_boundary_count')}",
        manifest["z009_dashboard_json_path"],
    )

    # Check 15: dashboard json/tsv alignment
    dash_rows: List[Dict[str, Any]] = list(
        csv.DictReader(Path(manifest["z009_dashboard_tsv_path"]).open("r", encoding="utf-8"), delimiter="\t")
    )
    dash_entries = dash_json.get("dashboard_entries", [])
    alignment_ok = len(dash_rows) == len(dash_entries)
    if alignment_ok:
        for entry, row in zip(dash_entries, dash_rows):
            for key in ["entry_id", "domain", "item_id", "status_bucket", "summary", "evidence_source", "next_action"]:
                if str(entry.get(key)) != str(row.get(key)):
                    alignment_ok = False
                    break
            if not alignment_ok:
                break
    add_check(
        checks,
        "RG-015",
        "z009_dashboard_json_tsv_alignment",
        alignment_ok,
        "count/order/core-fields match",
        f"json_entries={len(dash_entries)},tsv_rows={len(dash_rows)}",
        manifest["z009_dashboard_tsv_path"],
    )

    # Check 16: dashboard html required status texts
    html_text = Path(manifest["z009_dashboard_html_path"]).read_text(encoding="utf-8")
    missing_required = [s for s in manifest["dashboard_required_strings"] if s not in html_text]
    add_check(
        checks,
        "RG-016",
        "z009_dashboard_html_required_status_texts",
        len(missing_required) == 0,
        "all required status texts present",
        "missing=[]" if not missing_required else f"missing={';'.join(missing_required)}",
        manifest["z009_dashboard_html_path"],
    )

    # Check 17: global state guard (from anchor)
    state_expected = manifest["state_expected"]
    state_ok = all(anchor.get(k) == v for k, v in state_expected.items())
    add_check(
        checks,
        "RG-017",
        "global_state_guard",
        state_ok,
        ",".join(f"{k}={v}" for k, v in state_expected.items()),
        ",".join(f"{k}={anchor.get(k)}" for k in state_expected.keys()),
        manifest["z009_skip_anchor_path"],
    )

    # Check 18: zero write / prod account / remote lifecycle guard still pass
    zero_write_ok = (
        z009_rerun.get("write_request_count") == 0
        and z009_rerun.get("unexpected_write_request_count") == 0
        and z009_rerun.get("forbidden_request_count") == 0
        and anchor.get("write_request_count") == 0
        and anchor.get("production_account_used") is False
        and anchor.get("remote_lifecycle_action_executed") is False
    )
    add_check(
        checks,
        "RG-018",
        "zero_write_prod_remote_guard",
        zero_write_ok,
        "write_request_count=0,unexpected_write_request_count=0,forbidden_request_count=0,production_account_used=false,remote_lifecycle_action_executed=false",
        f"rerun_write={z009_rerun.get('write_request_count')},rerun_unexpected_write={z009_rerun.get('unexpected_write_request_count')},"
        f"rerun_forbidden={z009_rerun.get('forbidden_request_count')},anchor_write={anchor.get('write_request_count')},"
        f"anchor_production_account_used={anchor.get('production_account_used')},"
        f"anchor_remote_lifecycle_action_executed={anchor.get('remote_lifecycle_action_executed')}",
        "task_z009b_09 + task_z009b_13",
    )

    # Check 19: sensitive pattern scan in html/json/tsv artifacts
    sensitive_pat = re.compile(
        r"(?i)(bearer\s+[a-z0-9\-\._~\+/]+=*|api[_\s-]?key|token\s*[:=]|cookie\s*[:=]|password\s*[:=])"
    )
    sensitive_hits: List[str] = []
    for file_path in manifest["sensitive_pattern_files"]:
        content = Path(file_path).read_text(encoding="utf-8")
        for match in sensitive_pat.finditer(content):
            sensitive_hits.append(f"{file_path}:{match.group(0)[:40]}")
    add_check(
        checks,
        "RG-019",
        "sensitive_pattern_scan",
        len(sensitive_hits) == 0,
        "no sensitive credential markers",
        "hits=0" if not sensitive_hits else f"hits={len(sensitive_hits)}",
        " | ".join(sensitive_hits[:5]),
    )

    # Check 20: text hygiene on selected evidence files
    hygiene_failures: List[str] = []
    for file_path in manifest["text_hygiene_files"]:
        p = Path(file_path)
        if not p.exists():
            hygiene_failures.append(f"missing:{file_path}")
            continue
        trailing, eof_single = check_text_hygiene(p)
        if trailing != 0 or not eof_single:
            hygiene_failures.append(f"{file_path}:trailing={trailing},eof_single={eof_single}")
    add_check(
        checks,
        "RG-020",
        "text_hygiene_gate",
        len(hygiene_failures) == 0,
        "all selected files trailing_whitespace=0 and eof_single_newline=true",
        "failures=0" if not hygiene_failures else f"failures={len(hygiene_failures)}",
        " | ".join(hygiene_failures[:5]),
    )

    # Check 21-27: git gates (readonly)
    rc, out, err = run_cmd(["git", "diff", "--cached", "--name-only"], repo_root)
    cached_list = [line for line in out.splitlines() if line.strip()]
    add_check(
        checks,
        "RG-021",
        "git_cached_diff_empty",
        rc == 0 and len(cached_list) == 0,
        "[]",
        cached_list if rc == 0 else f"cmd_error:{err.strip()}",
    )

    rc, out, err = run_cmd(["git", "diff", "--name-only", "--", "06_前端", "07_后端"], repo_root)
    product_diff = [line for line in out.splitlines() if line.strip()]
    add_check(
        checks,
        "RG-022",
        "git_product_backend_diff_empty",
        rc == 0 and len(product_diff) == 0,
        "[]",
        product_diff if rc == 0 else f"cmd_error:{err.strip()}",
    )

    rc_cached_check, _, err_cached_check = run_cmd(["git", "diff", "--cached", "--check"], repo_root)
    add_check(
        checks,
        "RG-023",
        "git_diff_cached_check_pass",
        rc_cached_check == 0,
        "exit_code=0",
        f"exit_code={rc_cached_check}",
        err_cached_check.strip(),
    )

    rc_check, _, err_check = run_cmd(["git", "diff", "--check"], repo_root)
    add_check(
        checks,
        "RG-024",
        "git_diff_check_pass",
        rc_check == 0,
        "exit_code=0",
        f"exit_code={rc_check}",
        err_check.strip(),
    )

    rc, out, err = run_cmd(["git", "tag", "--points-at", "HEAD"], repo_root)
    tag_lines = [line for line in out.splitlines() if line.strip()]
    add_check(
        checks,
        "RG-025",
        "git_tag_at_head_empty",
        rc == 0 and len(tag_lines) == 0,
        "[]",
        tag_lines if rc == 0 else f"cmd_error:{err.strip()}",
    )

    rc, out, err = run_cmd(["git", "branch", "-r", "--contains", "HEAD"], repo_root)
    remote_contains = [line.strip() for line in out.splitlines() if line.strip()]
    add_check(
        checks,
        "RG-026",
        "git_remote_contains_head_empty",
        rc == 0 and len(remote_contains) == 0,
        "[]",
        remote_contains if rc == 0 else f"cmd_error:{err.strip()}",
    )

    rc_branch, out_branch, err_branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if rc_branch != 0:
        add_check(
            checks,
            "RG-027",
            "gh_pr_list_empty",
            False,
            "[]",
            f"branch_detect_error:{err_branch.strip()}",
        )
    else:
        branch = out_branch.strip()
        rc_pr, out_pr, err_pr = run_cmd(
            ["gh", "pr", "list", "--head", branch, "--json", "number,title,state,url"],
            repo_root,
        )
        pr_list: Any
        if rc_pr == 0:
            try:
                pr_list = json.loads(out_pr) if out_pr.strip() else []
            except json.JSONDecodeError:
                pr_list = f"json_parse_error:{out_pr[:120]}"
        else:
            pr_list = f"cmd_error:{err_pr.strip()}"
        ok = rc_pr == 0 and isinstance(pr_list, list) and len(pr_list) == 0
        add_check(checks, "RG-027", "gh_pr_list_empty", ok, "[]", pr_list)

    regression_check_count = len(checks)
    pass_regression_count = sum(1 for c in checks if c["status"] == "PASS")
    block_regression_count = regression_check_count - pass_regression_count
    task_status = "PASS" if block_regression_count == 0 else "BLOCK"

    result = {
        "task_id": manifest["task_id"],
        "selected_candidate_id": manifest["selected_candidate_id"],
        "source_head": manifest["source_head"],
        "generated_at": now_cn(),
        "task_status": task_status,
        "regression_check_count": regression_check_count,
        "pass_regression_count": pass_regression_count,
        "block_regression_count": block_regression_count,
        "full_browser_route_smoke_closed": False,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "checks": checks,
    }
    dump_json(output_json_path, result)

    headers = [
        "check_id",
        "check_name",
        "status",
        "classification",
        "expected",
        "observed",
        "details",
    ]
    write_tsv(output_tsv_path, headers, checks)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
