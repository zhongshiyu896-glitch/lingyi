#!/usr/bin/env python3
import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify cross-phase evidence consistency gate.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Result JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Result TSV path.")
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(argv: Sequence[str], cwd: Path) -> Tuple[int, str, str]:
    proc = subprocess.run(
        list(argv),
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def norm_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ";".join(norm_value(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def parse_tsv(path: Path) -> List[Dict[str, str]]:
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(1 << 30)
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path: Path, headers: List[str], rows: List[Dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: norm_value(row.get(h)) for h in headers})


def get_by_dot_path(root: Any, dot_path: str) -> Any:
    current = root
    for part in dot_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def extract_records(payload: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return payload
        return [{"value": item} for item in payload]
    if isinstance(payload, dict):
        preferred = [
            "entries",
            "candidates",
            "checks",
            "policies",
            "results",
            "gates",
            "tests",
            "overview",
            "matrix",
            "artifacts",
            "items",
            "access_packet_template_entries",
            "authorization_entries",
        ]
        for key in preferred:
            value = payload.get(key)
            if isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    return value
                return [{"value": item} for item in value]
        for value in payload.values():
            if isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    return value
                return [{"value": item} for item in value]
    return None


def pick_order_key(records: List[Dict[str, Any]], tsv_headers: Sequence[str]) -> Optional[str]:
    preferred = [
        "entry_id",
        "candidate_id",
        "check_id",
        "policy_id",
        "risk_id",
        "task_id",
        "script_id",
        "id",
        "path",
    ]
    for key in preferred:
        if key in tsv_headers and all(key in item for item in records):
            return key
    return None


def text_hygiene_ok(path: Path) -> Tuple[int, bool]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    trailing_count = sum(1 for line in text.splitlines() if line.rstrip(" \t") != line)
    eof_single_newline = data.endswith(b"\n") and not data.endswith(b"\n\n")
    return trailing_count, eof_single_newline


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    output_json_path = Path(args.output_json).resolve()
    output_tsv_path = Path(args.output_tsv).resolve()

    manifest = load_json(manifest_path)
    repo_root = Path(manifest["repo_root"]).resolve()
    source_head = manifest["source_head"]

    checks: List[Dict[str, Any]] = []
    check_id_counter = 1
    sensitive_pattern_hit_count = 0
    full_browser_route_smoke_closed_value: Optional[bool] = None

    def add_check(
        category: str,
        target_path: str,
        status: str,
        expected: Any,
        observed: Any,
        severity: str,
        residual_note: str = "",
    ) -> None:
        nonlocal check_id_counter
        checks.append(
            {
                "check_id": f"CP-{check_id_counter:03d}",
                "category": category,
                "target_path": target_path,
                "status": status,
                "expected": expected,
                "observed": observed,
                "severity": severity,
                "residual_note": residual_note,
            }
        )
        check_id_counter += 1

    # Gate 1: HEAD check
    rc, out, err = run_cmd(["git", "rev-parse", "HEAD"], repo_root)
    observed_head = out.strip() if rc == 0 else f"cmd_error:{err.strip()}"
    add_check(
        category="source_head",
        target_path=str(repo_root),
        status="PASS" if rc == 0 and observed_head == source_head else "BLOCK",
        expected=source_head,
        observed=observed_head,
        severity="BLOCKING",
    )

    # Gate 2: Z010 file map exists=true paths remain present
    file_map_path = Path(manifest["file_map_json"]).resolve()
    file_map = load_json(file_map_path)
    entries = file_map.get("entries", [])
    for entry in entries:
        if entry.get("exists") is True:
            path = Path(entry["path"]).resolve()
            ok = path.exists()
            add_check(
                category="file_existence",
                target_path=str(path),
                status="PASS" if ok else "BLOCK",
                expected="exists=true",
                observed=f"exists={ok}",
                severity="BLOCKING",
                residual_note=entry.get("entry_id", ""),
            )

    # Gate 3: JSON/TSV pair consistency (file map + additional paths)
    json_paths: List[Path] = []
    for entry in entries:
        path = Path(entry["path"]).resolve()
        if path.suffix == ".json" and path.exists():
            json_paths.append(path)
    for extra in manifest.get("additional_json_paths", []):
        path = Path(extra).resolve()
        if path.exists():
            json_paths.append(path)
    dedup_json_paths = sorted({str(path) for path in json_paths})

    for json_path_str in dedup_json_paths:
        json_path = Path(json_path_str)
        tsv_path = json_path.with_suffix(".tsv")
        if not tsv_path.exists():
            continue

        try:
            payload = load_json(json_path)
            records = extract_records(payload)
            rows = parse_tsv(tsv_path)
            mismatch_count = 0
            notes: List[str] = []

            if records is None:
                mismatch_count += 1
                notes.append("json records not extractable")
                record_count = 0
            else:
                record_count = len(records)

            if records is not None and record_count != len(rows):
                mismatch_count += abs(record_count - len(rows))
                notes.append(f"count mismatch json={record_count} tsv={len(rows)}")

            if records is not None:
                order_key = pick_order_key(records, rows[0].keys() if rows else [])
                if order_key:
                    json_seq = [norm_value(item.get(order_key)) for item in records]
                    tsv_seq = [norm_value(row.get(order_key, "")) for row in rows]
                    if json_seq != tsv_seq:
                        mismatch_count += 1
                        notes.append(f"order mismatch by {order_key}")
                else:
                    notes.append("order key not found; order check skipped")

                core_fields = [order_key] if order_key else []
                for field in [
                    "status",
                    "path",
                    "candidate_id",
                    "entry_id",
                    "check_id",
                    "policy_id",
                    "task_id",
                    "script_id",
                    "risk_id",
                ]:
                    if records and field in records[0] and rows and field in rows[0]:
                        core_fields.append(field)
                core_fields = [f for f in core_fields if f]

                for idx, (item, row) in enumerate(zip(records, rows), start=1):
                    for field in core_fields:
                        left = norm_value(item.get(field))
                        right = norm_value(row.get(field, ""))
                        if left != right:
                            mismatch_count += 1
                            notes.append(f"row{idx}:{field} json={left} tsv={right}")
                            if len(notes) >= 8:
                                break
                    if len(notes) >= 8:
                        break

            add_check(
                category="json_tsv_alignment",
                target_path=f"{json_path} <-> {tsv_path}",
                status="PASS" if mismatch_count == 0 else "BLOCK",
                expected="count/order/core_fields_consistent",
                observed=f"json_count={record_count if records is not None else 0},tsv_count={len(rows)},mismatch_count={mismatch_count}",
                severity="BLOCKING",
                residual_note="; ".join(notes[:8]),
            )
        except Exception as exc:
            add_check(
                category="json_tsv_alignment",
                target_path=f"{json_path} <-> {tsv_path}",
                status="BLOCK",
                expected="pair_check_success",
                observed=f"exception:{exc}",
                severity="BLOCKING",
            )

    # Gate 4: state anchor checks
    for anchor in manifest.get("state_anchor_checks", []):
        path = Path(anchor["path"]).resolve()
        if not path.exists():
            add_check(
                category="state_anchor",
                target_path=str(path),
                status="BLOCK",
                expected="anchor_file_exists",
                observed="missing",
                severity="BLOCKING",
            )
            continue
        try:
            payload = load_json(path)
            ok = True
            observed_parts: List[str] = []
            expected_parts: List[str] = []
            for item in anchor.get("expect", []):
                key_path = item["key_path"]
                expected_value = item["value"]
                observed_value = get_by_dot_path(payload, key_path)
                expected_parts.append(f"{key_path}={norm_value(expected_value)}")
                observed_parts.append(f"{key_path}={norm_value(observed_value)}")
                if observed_value != expected_value:
                    ok = False
                if key_path == "full_browser_route_smoke_closed" and observed_value is not None:
                    full_browser_route_smoke_closed_value = bool(observed_value)
            add_check(
                category="state_anchor",
                target_path=str(path),
                status="PASS" if ok else "BLOCK",
                expected=",".join(expected_parts),
                observed=",".join(observed_parts),
                severity="BLOCKING",
            )
        except Exception as exc:
            add_check(
                category="state_anchor",
                target_path=str(path),
                status="BLOCK",
                expected="anchor_parse_success",
                observed=f"exception:{exc}",
                severity="BLOCKING",
            )

    # Gate 5: keyword presence in Z010/Z011 docs
    for keyword_check in manifest.get("keyword_checks", []):
        path = Path(keyword_check["path"]).resolve()
        keyword = keyword_check["keyword"]
        if not path.exists():
            add_check(
                category="keyword_presence",
                target_path=str(path),
                status="BLOCK",
                expected=f"contains:{keyword}",
                observed="missing_file",
                severity="BLOCKING",
            )
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        ok = keyword in content
        add_check(
            category="keyword_presence",
            target_path=str(path),
            status="PASS" if ok else "BLOCK",
            expected=f"contains:{keyword}",
            observed=f"contains={ok}",
            severity="BLOCKING",
            residual_note=keyword,
        )

    # Gate 6: sensitive pattern scan
    scan_extensions = set(manifest.get("sensitive_scan_extensions", [".md", ".html", ".json", ".tsv"]))
    scan_paths: List[Path] = []
    for entry in entries:
        path = Path(entry["path"]).resolve()
        if path.exists() and path.suffix in scan_extensions:
            scan_paths.append(path)
    for path_str in manifest.get("sensitive_scan_extra_paths", []):
        path = Path(path_str).resolve()
        if path.exists() and path.suffix in scan_extensions:
            scan_paths.append(path)
    dedup_scan_paths = sorted({str(path) for path in scan_paths})

    patterns = [
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/=]{20,}"),
        re.compile(r"(?i)\b(api[_-]?key|access[_-]?key|secret[_-]?key)\b\s*[:=]\s*[\"']?[A-Za-z0-9\-._~+/=]{16,}[\"']?"),
        re.compile(r"(?i)\b(token|access_token|refresh_token)\b\s*[:=]\s*[\"']?[A-Za-z0-9\-._~+/=]{20,}[\"']?"),
        re.compile(r"(?i)\bcookie\b\s*[:=]\s*[\"']?[A-Za-z0-9\-._~%]{20,}[\"']?"),
    ]
    hits: List[str] = []
    for path_str in dedup_scan_paths:
        content = Path(path_str).read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            for match in pattern.finditer(content):
                hits.append(f"{path_str}:{pattern.pattern}:{match.group(0)[:80]}")
                if len(hits) >= 10:
                    break
            if len(hits) >= 10:
                break
        if len(hits) >= 10:
            break
    sensitive_pattern_hit_count = len(hits)
    add_check(
        category="sensitive_scan",
        target_path=";".join(dedup_scan_paths[:5]) + ("..." if len(dedup_scan_paths) > 5 else ""),
        status="PASS" if sensitive_pattern_hit_count == 0 else "BLOCK",
        expected="sensitive_pattern_hit_count=0",
        observed=f"sensitive_pattern_hit_count={sensitive_pattern_hit_count}",
        severity="BLOCKING",
        residual_note=" | ".join(hits),
    )

    # Gate 7: git checks
    git_checks = [
        ("git_cached_diff_empty", ["git", "diff", "--cached", "--name-only"], "", "BLOCKING"),
        ("git_product_backend_diff_empty", ["git", "diff", "--name-only", "--", "06_前端", "07_后端"], "", "BLOCKING"),
        ("git_cached_check_pass", ["git", "diff", "--cached", "--check"], "", "BLOCKING"),
        ("git_worktree_check_pass", ["git", "diff", "--check"], "", "BLOCKING"),
        ("tag_at_head_empty", ["git", "tag", "--points-at", "HEAD"], "", "BLOCKING"),
        ("remote_contains_head_empty", ["git", "branch", "-r", "--contains", "HEAD"], "", "BLOCKING"),
    ]
    for name, cmd, expected, severity in git_checks:
        rc, out, err = run_cmd(cmd, repo_root)
        observed = out.strip() if out.strip() else ""
        ok = rc == 0 and observed == expected
        add_check(
            category="git_gate",
            target_path=" ".join(cmd),
            status="PASS" if ok else "BLOCK",
            expected=expected if expected != "" else "<empty>",
            observed=observed if observed != "" else ("cmd_error:" + err.strip() if rc != 0 else "<empty>"),
            severity=severity,
            residual_note=name,
        )

    # PR list check on current branch
    rc, out, err = run_cmd(["git", "symbolic-ref", "--short", "HEAD"], repo_root)
    branch = out.strip() if rc == 0 else ""
    if rc != 0 or branch == "":
        add_check(
            category="git_gate",
            target_path="git symbolic-ref --short HEAD",
            status="BLOCK",
            expected="branch_name",
            observed=f"cmd_error:{err.strip()}",
            severity="BLOCKING",
            residual_note="current_branch_resolve",
        )
    else:
        pr_cmd = ["gh", "pr", "list", "--head", branch, "--json", "number,title,state,url"]
        pr_rc, pr_out, pr_err = run_cmd(pr_cmd, repo_root)
        observed = pr_out.strip()
        ok = pr_rc == 0 and observed == "[]"
        add_check(
            category="git_gate",
            target_path=" ".join(pr_cmd),
            status="PASS" if ok else "BLOCK",
            expected="[]",
            observed=observed if observed else (f"cmd_error:{pr_err.strip()}" if pr_rc != 0 else "[]"),
            severity="BLOCKING",
            residual_note="pr_list",
        )

    # Summaries
    pass_count = sum(1 for item in checks if item["status"] == "PASS")
    block_count = sum(1 for item in checks if item["status"] == "BLOCK")
    task_status = "PASS" if block_count == 0 else "BLOCK"

    if full_browser_route_smoke_closed_value is None:
        full_browser_route_smoke_closed_value = False

    result = {
        "task_id": manifest["task_id"],
        "source_head": source_head,
        "generated_at": now_cn(),
        "task_status": task_status,
        "check_count": len(checks),
        "pass_check_count": pass_count,
        "block_check_count": block_count,
        "sensitive_pattern_hit_count": sensitive_pattern_hit_count,
        "full_browser_route_smoke_closed": full_browser_route_smoke_closed_value,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "checks": checks,
    }

    dump_json(output_json_path, result)
    tsv_headers = [
        "check_id",
        "category",
        "target_path",
        "status",
        "expected",
        "observed",
        "residual_note",
        "severity",
    ]
    write_tsv(output_tsv_path, tsv_headers, checks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
