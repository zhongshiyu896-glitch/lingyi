#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def run_cmd(repo_root: Path, argv: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def nonempty_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_current_branch(status_output: str) -> str:
    lines = status_output.splitlines()
    if not lines:
        return ""
    first = lines[0].strip()
    if not first.startswith("## "):
        return ""
    branch_part = first[3:]
    return branch_part.split("...")[0].strip()


def normalize_remote_contains(lines: List[str]) -> List[str]:
    normalized: List[str] = []
    for line in lines:
        if "->" in line:
            continue
        stripped = line.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def run_command_key(
    repo_root: Path, command_key: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    if command_key == "git_status_short_branch":
        argv = ["git", "status", "--short", "--branch"]
    elif command_key == "git_rev_parse_head":
        argv = ["git", "rev-parse", "HEAD"]
    elif command_key == "git_log_subject":
        argv = ["git", "log", "-1", "--pretty=%s"]
    elif command_key == "git_diff_cached_name_only":
        argv = ["git", "diff", "--cached", "--name-only"]
    elif command_key == "git_diff_cached_name_only_product_backend":
        argv = ["git", "diff", "--cached", "--name-only", "--", "06_前端", "07_后端"]
    elif command_key == "git_diff_name_only_product_backend":
        argv = ["git", "diff", "--name-only", "--", "06_前端", "07_后端"]
    elif command_key == "git_diff_cached_check":
        argv = ["git", "diff", "--cached", "--check"]
    elif command_key == "git_diff_check":
        argv = ["git", "diff", "--check"]
    elif command_key == "git_tag_points_at_head":
        argv = ["git", "tag", "--points-at", "HEAD"]
    elif command_key == "git_branch_r_contains_head":
        argv = ["git", "branch", "-r", "--contains", "HEAD"]
    elif command_key == "gh_pr_list_head_json":
        current_branch = context.get("current_branch", "")
        argv = [
            "gh",
            "pr",
            "list",
            "--head",
            current_branch,
            "--json",
            "number,title,state,url",
        ]
    else:
        raise ValueError(f"Unsupported command_key: {command_key}")

    code, stdout, stderr = run_cmd(repo_root, argv)
    return {
        "command": " ".join(argv),
        "command_exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
    }


def evaluate_gate(
    gate: Dict[str, Any], command_result: Dict[str, Any], manifest: Dict[str, Any]
) -> Tuple[str, Any]:
    eval_type = gate.get("evaluation", "capture_only")
    code = command_result["command_exit_code"]
    stdout = command_result["stdout"]

    if eval_type == "capture_only":
        status = "PASS" if code == 0 else "BLOCK"
        observed = {
            "stdout_line_count": len(nonempty_lines(stdout)),
            "stderr_line_count": len(nonempty_lines(command_result["stderr"])),
        }
        return status, observed

    if eval_type == "head_equals_source_head":
        observed = stdout.strip()
        expected = manifest.get("source_head", "")
        status = "PASS" if code == 0 and observed == expected else "BLOCK"
        return status, observed

    if eval_type == "must_be_empty_lines":
        lines = nonempty_lines(stdout)
        status = "PASS" if code == 0 and len(lines) == 0 else "BLOCK"
        return status, lines

    if eval_type == "remote_contains_must_be_empty":
        lines = normalize_remote_contains(stdout.splitlines())
        status = "PASS" if code == 0 and len(lines) == 0 else "BLOCK"
        return status, lines

    if eval_type == "gh_pr_list_must_be_empty":
        observed_raw = stdout.strip() or "[]"
        parsed: Any = None
        parse_ok = False
        try:
            parsed = json.loads(observed_raw)
            parse_ok = isinstance(parsed, list)
        except json.JSONDecodeError:
            parsed = observed_raw
            parse_ok = False
        status = "PASS" if code == 0 and parse_ok and len(parsed) == 0 else "BLOCK"
        return status, parsed

    if eval_type == "must_exit_zero":
        status = "PASS" if code == 0 else "BLOCK"
        observed = {
            "stdout_line_count": len(nonempty_lines(stdout)),
            "stderr_line_count": len(nonempty_lines(command_result["stderr"])),
        }
        return status, observed

    return "BLOCK", {"error": f"Unsupported evaluation: {eval_type}"}


def write_tsv(path: Path, gates: List[Dict[str, Any]]) -> None:
    headers = [
        "gate_id",
        "gate_name",
        "status",
        "observed",
        "expected",
        "command_exit_code",
        "command",
        "block_on_fail",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in gates:
            writer.writerow(
                {
                    "gate_id": row["gate_id"],
                    "gate_name": row["gate_name"],
                    "status": row["status"],
                    "observed": json.dumps(row["observed"], ensure_ascii=False, separators=(",", ":")),
                    "expected": row["expected"],
                    "command_exit_code": row["command_exit_code"],
                    "command": row["command"],
                    "block_on_fail": "true" if row["block_on_fail"] else "false",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify local git gates in read-only mode.")
    parser.add_argument("--repo-root", required=True, help="Repository root path.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parser.add_argument("--output-json", required=True, help="Result JSON path.")
    parser.add_argument("--output-tsv", required=True, help="Result TSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root)
    manifest_path = Path(args.manifest)
    output_json = Path(args.output_json)
    output_tsv = Path(args.output_tsv)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gate_defs = manifest.get("gates", [])

    context: Dict[str, Any] = {}
    gate_rows: List[Dict[str, Any]] = []
    block_count = 0

    for gate in gate_defs:
        result = run_command_key(repo_root, gate["command_key"], context)
        if gate["command_key"] == "git_status_short_branch":
            context["current_branch"] = parse_current_branch(result["stdout"])

        status, observed = evaluate_gate(gate, result, manifest)
        row = {
            "gate_id": gate["gate_id"],
            "gate_name": gate["gate_name"],
            "status": status,
            "observed": observed,
            "expected": gate.get("expected", ""),
            "command_exit_code": result["command_exit_code"],
            "command": result["command"],
            "block_on_fail": bool(gate.get("block_on_fail", True)),
        }
        if row["status"] == "BLOCK" and row["block_on_fail"]:
            block_count += 1
        gate_rows.append(row)

    gate_count = len(gate_rows)
    pass_gate_count = sum(1 for row in gate_rows if row["status"] == "PASS")
    block_gate_count = sum(1 for row in gate_rows if row["status"] == "BLOCK")
    task_status = "PASS" if block_count == 0 else "BLOCK"

    payload = {
        "task_id": manifest.get("task_id", "TASK-Z008B-12-IMPL"),
        "source_head": manifest.get("source_head"),
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "generated_at": now_cn(),
        "repo_root": str(repo_root),
        "manifest_path": str(manifest_path),
        "task_status": task_status,
        "gate_count": gate_count,
        "pass_gate_count": pass_gate_count,
        "block_gate_count": block_gate_count,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "results": gate_rows,
    }

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_tsv(output_tsv, gate_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
