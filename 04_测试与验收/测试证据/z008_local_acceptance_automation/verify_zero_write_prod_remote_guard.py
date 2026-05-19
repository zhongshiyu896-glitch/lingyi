#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify zero-write, production-account, and remote-lifecycle guard constraints."
    )
    parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    parser.add_argument("--output-json", required=True, help="Output result JSON path")
    parser.add_argument("--output-tsv", required=True, help="Output result TSV path")
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def parse_tsv_cell(raw: Optional[str]) -> Any:
    if raw is None:
        return None
    s = raw.strip()
    if s == "":
        return None
    lower = s.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    if s.startswith("[") and s.endswith("]"):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return s
    if ";" in s:
        return [item.strip() for item in s.split(";")]
    return s


def get_obj_by_path(root: Any, dot_path: Optional[str]) -> Any:
    if not dot_path:
        return root
    current = root
    for part in dot_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def text_hygiene(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    trailing_count = 0
    for line in text.splitlines():
        if line.rstrip(" \t") != line:
            trailing_count += 1
    eof_single_newline = text.endswith("\n") and not text.endswith("\n\n")
    return {
        "trailing_whitespace_count": trailing_count,
        "eof_single_newline": eof_single_newline,
    }


def run_cmd(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    output_json_path = Path(args.output_json).resolve()
    output_tsv_path = Path(args.output_tsv).resolve()

    ensure_parent(output_json_path)
    ensure_parent(output_tsv_path)

    manifest = load_json(manifest_path)
    source_head = manifest.get("source_head")
    selected_candidate_id = manifest.get("selected_candidate_id")
    repo_root = Path(manifest.get("repo_root", ".")).resolve()

    checks: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    json_cache: Dict[str, Any] = {}

    def record(
        guard_id: str,
        guard_name: str,
        status: str,
        observed: Any,
        expected: Any,
        command_exit_code: int = 0,
        source: str = "",
        detail: str = "",
    ) -> None:
        checks.append(
            {
                "guard_id": guard_id,
                "guard_name": guard_name,
                "status": status,
                "observed": observed,
                "expected": expected,
                "command_exit_code": command_exit_code,
                "source": source,
                "detail": detail,
            }
        )
        if status == "BLOCK":
            failures.append(
                {
                    "guard_id": guard_id,
                    "guard_name": guard_name,
                    "source": source,
                    "detail": detail,
                }
            )

    def get_json(path_str: str) -> Any:
        path = str(Path(path_str).resolve())
        if path not in json_cache:
            json_cache[path] = load_json(Path(path))
        return json_cache[path]

    # File existence / hygiene / JSON parse
    for entry in manifest.get("file_entries", []):
        entry_id = entry["entry_id"]
        file_path = Path(entry["path"]).resolve()
        kind = entry.get("kind", "text")

        if not file_path.exists():
            record(
                guard_id=f"{entry_id}-EXIST",
                guard_name="file_exists",
                status="BLOCK",
                observed="missing",
                expected="exists",
                command_exit_code=1,
                source=str(file_path),
                detail="file missing",
            )
            continue

        record(
            guard_id=f"{entry_id}-EXIST",
            guard_name="file_exists",
            status="PASS",
            observed="exists",
            expected="exists",
            source=str(file_path),
        )

        hygiene = text_hygiene(file_path)
        hygiene_ok = (
            hygiene["trailing_whitespace_count"] == 0
            and hygiene["eof_single_newline"] is True
        )
        record(
            guard_id=f"{entry_id}-HYGIENE",
            guard_name="text_hygiene",
            status="PASS" if hygiene_ok else "BLOCK",
            observed=hygiene,
            expected={"trailing_whitespace_count": 0, "eof_single_newline": True},
            command_exit_code=0 if hygiene_ok else 1,
            source=str(file_path),
            detail="" if hygiene_ok else "text hygiene violation",
        )

        if kind == "json":
            try:
                get_json(str(file_path))
                record(
                    guard_id=f"{entry_id}-JSON",
                    guard_name="json_parse",
                    status="PASS",
                    observed="parse_ok",
                    expected="parse_ok",
                    source=str(file_path),
                )
            except Exception as exc:
                record(
                    guard_id=f"{entry_id}-JSON",
                    guard_name="json_parse",
                    status="BLOCK",
                    observed=f"parse_error:{exc}",
                    expected="parse_ok",
                    command_exit_code=1,
                    source=str(file_path),
                    detail="json parse failed",
                )

    # JSON field checks
    for field_check in manifest.get("field_checks", []):
        check_id = field_check["check_id"]
        json_path = str(Path(field_check["json_path"]).resolve())
        object_path = field_check.get("object_path")
        key = field_check["key"]
        expected = field_check.get("expected")

        try:
            root = get_json(json_path)
            target_obj = get_obj_by_path(root, object_path)
            observed = None
            if isinstance(target_obj, dict):
                observed = target_obj.get(key)
            ok = observed == expected
            record(
                guard_id=check_id,
                guard_name="field_equals",
                status="PASS" if ok else "BLOCK",
                observed=observed,
                expected=expected,
                command_exit_code=0 if ok else 1,
                source=f"{json_path}::{object_path or '<root>'}.{key}",
                detail="" if ok else "field mismatch",
            )
        except Exception as exc:
            record(
                guard_id=check_id,
                guard_name="field_equals",
                status="BLOCK",
                observed=f"exception:{exc}",
                expected=expected,
                command_exit_code=1,
                source=f"{json_path}::{object_path or '<root>'}.{key}",
                detail="field check exception",
            )

    # Candidate status checks
    for check in manifest.get("candidate_status_checks", []):
        check_id = check["check_id"]
        json_path = str(Path(check["json_path"]).resolve())
        array_key = check["array_key"]
        candidate_key = check.get("candidate_key", "candidate_id")
        candidate_id = check["candidate_id"]
        expected_fields = check["expected_fields"]

        try:
            root = get_json(json_path)
            arr = root.get(array_key, [])
            target = None
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict) and item.get(candidate_key) == candidate_id:
                        target = item
                        break
            if target is None:
                record(
                    guard_id=check_id,
                    guard_name="candidate_status",
                    status="BLOCK",
                    observed="candidate_not_found",
                    expected={"candidate_id": candidate_id, **expected_fields},
                    command_exit_code=1,
                    source=json_path,
                    detail="candidate not found",
                )
                continue

            mismatch = {}
            for key, expected in expected_fields.items():
                observed = target.get(key)
                if observed != expected:
                    mismatch[key] = {"observed": observed, "expected": expected}
            ok = len(mismatch) == 0
            record(
                guard_id=check_id,
                guard_name="candidate_status",
                status="PASS" if ok else "BLOCK",
                observed={k: target.get(k) for k in expected_fields.keys()},
                expected=expected_fields,
                command_exit_code=0 if ok else 1,
                source=json_path,
                detail="" if ok else f"candidate mismatch:{json.dumps(mismatch, ensure_ascii=False)}",
            )
        except Exception as exc:
            record(
                guard_id=check_id,
                guard_name="candidate_status",
                status="BLOCK",
                observed=f"exception:{exc}",
                expected={"candidate_id": candidate_id, **expected_fields},
                command_exit_code=1,
                source=json_path,
                detail="candidate check exception",
            )

    # JSON/TSV pair consistency
    for pair in manifest.get("json_tsv_pairs", []):
        pair_id = pair["pair_id"]
        json_path = Path(pair["json_path"]).resolve()
        tsv_path = Path(pair["tsv_path"]).resolve()
        array_key = pair["json_array_key"]
        compare_fields = pair["compare_fields"]

        try:
            root = get_json(str(json_path))
            json_rows = root.get(array_key, [])
            with tsv_path.open("r", encoding="utf-8", newline="") as fh:
                tsv_rows = list(csv.DictReader(fh, delimiter="\t"))

            count_ok = len(json_rows) == len(tsv_rows)
            record(
                guard_id=f"{pair_id}-COUNT",
                guard_name="json_tsv_count",
                status="PASS" if count_ok else "BLOCK",
                observed={"json_count": len(json_rows), "tsv_count": len(tsv_rows)},
                expected="json_count==tsv_count",
                command_exit_code=0 if count_ok else 1,
                source=f"{json_path} <-> {tsv_path}",
                detail="" if count_ok else "row count mismatch",
            )

            mismatch_count = 0
            for idx in range(min(len(json_rows), len(tsv_rows))):
                jrow = json_rows[idx]
                trow = tsv_rows[idx]
                for field in compare_fields:
                    jv = normalize_value(jrow.get(field))
                    tv = normalize_value(parse_tsv_cell(trow.get(field)))
                    if jv != tv:
                        mismatch_count += 1

            ok = mismatch_count == 0 and count_ok
            record(
                guard_id=f"{pair_id}-FIELDS",
                guard_name="json_tsv_fields",
                status="PASS" if ok else "BLOCK",
                observed={"mismatch_count": mismatch_count},
                expected={"mismatch_count": 0},
                command_exit_code=0 if ok else 1,
                source=f"{json_path} <-> {tsv_path}",
                detail="" if ok else "json/tsv field mismatch",
            )
        except Exception as exc:
            record(
                guard_id=f"{pair_id}-ERROR",
                guard_name="json_tsv_pair",
                status="BLOCK",
                observed=f"exception:{exc}",
                expected="pair_check_pass",
                command_exit_code=1,
                source=f"{json_path} <-> {tsv_path}",
                detail="pair check exception",
            )

    # Git read-only gates
    gate = manifest.get("git_gate_expectations", {})
    product_paths = gate.get("product_paths", ["06_前端", "07_后端"])

    status_cmd = run_cmd(["git", "status", "--short", "--branch"], repo_root)
    record(
        guard_id="GIT-STATUS-BRANCH",
        guard_name="git_status_short_branch",
        status="PASS" if status_cmd["code"] == 0 else "BLOCK",
        observed=status_cmd["stdout"],
        expected="exit_code=0",
        command_exit_code=status_cmd["code"],
        source="git status --short --branch",
        detail=status_cmd["stderr"],
    )

    cached_names = run_cmd(["git", "diff", "--cached", "--name-only"], repo_root)
    cached_empty = cached_names["code"] == 0 and cached_names["stdout"] == ""
    record(
        guard_id="GIT-CACHED-NAME-EMPTY",
        guard_name="git_cached_name_empty",
        status="PASS" if cached_empty else "BLOCK",
        observed=cached_names["stdout"],
        expected="",
        command_exit_code=cached_names["code"],
        source="git diff --cached --name-only",
        detail=cached_names["stderr"],
    )

    product_cached = run_cmd(
        ["git", "diff", "--cached", "--name-only", "--", *product_paths], repo_root
    )
    product_cached_ok = product_cached["code"] == 0 and product_cached["stdout"] == ""
    record(
        guard_id="GIT-CACHED-PRODUCT-DIFF",
        guard_name="git_cached_product_diff_empty",
        status="PASS" if product_cached_ok else "BLOCK",
        observed=product_cached["stdout"],
        expected="",
        command_exit_code=product_cached["code"],
        source=f"git diff --cached --name-only -- {' '.join(product_paths)}",
        detail=product_cached["stderr"],
    )

    product_unstaged = run_cmd(
        ["git", "diff", "--name-only", "--", *product_paths], repo_root
    )
    product_unstaged_ok = (
        product_unstaged["code"] == 0 and product_unstaged["stdout"] == ""
    )
    record(
        guard_id="GIT-UNSTAGED-PRODUCT-DIFF",
        guard_name="git_unstaged_product_diff_empty",
        status="PASS" if product_unstaged_ok else "BLOCK",
        observed=product_unstaged["stdout"],
        expected="",
        command_exit_code=product_unstaged["code"],
        source=f"git diff --name-only -- {' '.join(product_paths)}",
        detail=product_unstaged["stderr"],
    )

    cached_check = run_cmd(["git", "diff", "--cached", "--check"], repo_root)
    cached_check_ok = cached_check["code"] == 0 and cached_check["stdout"] == ""
    record(
        guard_id="GIT-CACHED-CHECK",
        guard_name="git_diff_cached_check",
        status="PASS" if cached_check_ok else "BLOCK",
        observed=cached_check["stdout"],
        expected="exit_code=0 and empty",
        command_exit_code=cached_check["code"],
        source="git diff --cached --check",
        detail=cached_check["stderr"],
    )

    diff_check = run_cmd(["git", "diff", "--check"], repo_root)
    diff_check_ok = diff_check["code"] == 0 and diff_check["stdout"] == ""
    record(
        guard_id="GIT-DIFF-CHECK",
        guard_name="git_diff_check",
        status="PASS" if diff_check_ok else "BLOCK",
        observed=diff_check["stdout"],
        expected="exit_code=0 and empty",
        command_exit_code=diff_check["code"],
        source="git diff --check",
        detail=diff_check["stderr"],
    )

    tag_cmd = run_cmd(["git", "tag", "--points-at", "HEAD"], repo_root)
    tag_ok = tag_cmd["code"] == 0 and tag_cmd["stdout"] == ""
    record(
        guard_id="GIT-TAG-AT-HEAD",
        guard_name="tag_at_head_empty",
        status="PASS" if tag_ok else "BLOCK",
        observed=tag_cmd["stdout"],
        expected="",
        command_exit_code=tag_cmd["code"],
        source="git tag --points-at HEAD",
        detail=tag_cmd["stderr"],
    )

    remote_contains_cmd = run_cmd(
        ["git", "branch", "-r", "--contains", "HEAD"], repo_root
    )
    remote_contains_ok = (
        remote_contains_cmd["code"] == 0 and remote_contains_cmd["stdout"] == ""
    )
    record(
        guard_id="GIT-REMOTE-CONTAINS-HEAD",
        guard_name="remote_contains_head_empty",
        status="PASS" if remote_contains_ok else "BLOCK",
        observed=remote_contains_cmd["stdout"],
        expected="",
        command_exit_code=remote_contains_cmd["code"],
        source="git branch -r --contains HEAD",
        detail=remote_contains_cmd["stderr"],
    )

    branch_cmd = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    branch_name = branch_cmd["stdout"]
    branch_ok = branch_cmd["code"] == 0 and branch_name != ""
    record(
        guard_id="GIT-CURRENT-BRANCH",
        guard_name="current_branch_resolved",
        status="PASS" if branch_ok else "BLOCK",
        observed=branch_name,
        expected="non_empty",
        command_exit_code=branch_cmd["code"],
        source="git rev-parse --abbrev-ref HEAD",
        detail=branch_cmd["stderr"],
    )

    if branch_ok:
        pr_cmd = run_cmd(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch_name,
                "--json",
                "number,title,state,url",
            ],
            repo_root,
        )
        parsed_pr = None
        pr_ok = False
        detail = pr_cmd["stderr"]
        if pr_cmd["code"] == 0:
            try:
                parsed_pr = json.loads(pr_cmd["stdout"] or "[]")
                pr_ok = isinstance(parsed_pr, list) and len(parsed_pr) == 0
            except json.JSONDecodeError as exc:
                detail = f"{detail} json_decode_error:{exc}".strip()
        record(
            guard_id="GIT-PR-LIST-EMPTY",
            guard_name="pr_list_empty",
            status="PASS" if pr_ok else "BLOCK",
            observed=parsed_pr if parsed_pr is not None else pr_cmd["stdout"],
            expected=[],
            command_exit_code=pr_cmd["code"],
            source=f"gh pr list --head {branch_name} --json number,title,state,url",
            detail=detail,
        )
    else:
        record(
            guard_id="GIT-PR-LIST-EMPTY",
            guard_name="pr_list_empty",
            status="BLOCK",
            observed="branch_unresolved",
            expected=[],
            command_exit_code=1,
            source="gh pr list",
            detail="skip because branch resolve failed",
        )

    guard_check_count = len(checks)
    pass_guard_count = len([item for item in checks if item["status"] == "PASS"])
    violation_count = len([item for item in checks if item["status"] == "BLOCK"])

    result = {
        "task_id": manifest.get("task_id"),
        "source_head": source_head,
        "selected_candidate_id": selected_candidate_id,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "manifest_path": str(manifest_path),
        "task_status": "PASS" if violation_count == 0 else "BLOCK",
        "guard_check_count": guard_check_count,
        "pass_guard_count": pass_guard_count,
        "violation_count": violation_count,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "checks": checks,
        "failure_catalog": failures,
    }

    with output_json_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    tsv_fields = [
        "guard_id",
        "guard_name",
        "status",
        "source",
        "observed",
        "expected",
        "command_exit_code",
        "detail",
    ]
    with output_tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=tsv_fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for item in checks:
            writer.writerow(
                {
                    "guard_id": item["guard_id"],
                    "guard_name": item["guard_name"],
                    "status": item["status"],
                    "source": item["source"],
                    "observed": normalize_value(item["observed"]),
                    "expected": normalize_value(item["expected"]),
                    "command_exit_code": item["command_exit_code"],
                    "detail": item["detail"] or "null",
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
