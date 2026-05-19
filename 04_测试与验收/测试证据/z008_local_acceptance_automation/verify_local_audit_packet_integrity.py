#!/usr/bin/env python3
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify local audit packet integrity.")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    parser.add_argument("--output-json", required=True, help="Result JSON path")
    parser.add_argument("--output-tsv", required=True, help="Result TSV path")
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_json_like(value: Any) -> str:
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
        return ""
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


def check_single_newline_and_trailing_ws(path: Path) -> Tuple[bool, int]:
    data = path.read_bytes()
    eof_single_newline = data.endswith(b"\n") and not data.endswith(b"\n\n")
    trailing_count = 0
    for line in data.decode("utf-8", errors="replace").splitlines():
        if line.rstrip(" \t") != line:
            trailing_count += 1
    return eof_single_newline, trailing_count


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

    checks: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    json_cache: Dict[str, Any] = {}
    checked_file_count = 0
    sensitive_pattern_hit_count = 0
    state_misjudge_count = 0

    def record(
        check_id: str,
        check_type: str,
        target: str,
        status: str,
        observed: Any,
        expected: Any,
        error_count: int = 0,
        detail: str = "",
    ) -> None:
        checks.append(
            {
                "check_id": check_id,
                "check_type": check_type,
                "target": target,
                "status": status,
                "observed": observed,
                "expected": expected,
                "error_count": error_count,
                "detail": detail,
            }
        )
        if status == "BLOCK":
            failures.append(
                {
                    "check_id": check_id,
                    "check_type": check_type,
                    "target": target,
                    "detail": detail,
                }
            )

    # File checks
    for file_entry in manifest.get("file_entries", []):
        checked_file_count += 1
        entry_id = file_entry["entry_id"]
        file_path = Path(file_entry["path"]).resolve()
        kind = file_entry.get("kind", "text")

        if not file_path.exists():
            record(
                entry_id,
                "file_exists",
                str(file_path),
                "BLOCK",
                "missing",
                "exists",
                error_count=1,
                detail="file missing",
            )
            continue

        eof_single, trailing_count = check_single_newline_and_trailing_ws(file_path)
        hygiene_ok = eof_single and trailing_count == 0
        record(
            f"{entry_id}-HYGIENE",
            "text_hygiene",
            str(file_path),
            "PASS" if hygiene_ok else "BLOCK",
            {
                "eof_single_newline": eof_single,
                "trailing_whitespace_count": trailing_count,
            },
            {"eof_single_newline": True, "trailing_whitespace_count": 0},
            error_count=0 if hygiene_ok else 1,
            detail="" if hygiene_ok else "text hygiene violation",
        )

        if kind == "json":
            try:
                parsed = load_json(file_path)
                json_cache[str(file_path)] = parsed
                record(
                    entry_id,
                    "json_parse",
                    str(file_path),
                    "PASS",
                    "parse_ok",
                    "parse_ok",
                )
            except Exception as exc:
                record(
                    entry_id,
                    "json_parse",
                    str(file_path),
                    "BLOCK",
                    f"parse_error:{exc}",
                    "parse_ok",
                    error_count=1,
                    detail="json parse failed",
                )
        else:
            record(entry_id, "file_exists", str(file_path), "PASS", "exists", "exists")

    # JSON/TSV pair checks
    for pair in manifest.get("json_tsv_pairs", []):
        pair_id = pair["pair_id"]
        json_path = Path(pair["json_path"]).resolve()
        tsv_path = Path(pair["tsv_path"]).resolve()
        array_key = pair["json_array_key"]
        compare_fields = pair["compare_fields"]

        if not json_path.exists() or not tsv_path.exists():
            record(
                pair_id,
                "json_tsv_pair",
                f"{json_path} <-> {tsv_path}",
                "BLOCK",
                "missing_file",
                "both_exist",
                error_count=1,
                detail="json/tsv pair file missing",
            )
            continue

        try:
            data = json_cache.get(str(json_path))
            if data is None:
                data = load_json(json_path)
                json_cache[str(json_path)] = data
            arr = data.get(array_key, [])
            if not isinstance(arr, list):
                raise TypeError(f"{array_key} is not list")

            with tsv_path.open("r", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh, delimiter="\t"))

            mismatch_count = 0
            detail_parts = []

            if len(arr) != len(rows):
                mismatch_count += abs(len(arr) - len(rows))
                detail_parts.append(f"count mismatch json={len(arr)} tsv={len(rows)}")

            for idx, (item, row) in enumerate(zip(arr, rows), start=1):
                for field in compare_fields:
                    left = normalize_json_like(item.get(field))
                    right = normalize_json_like(parse_tsv_cell(row.get(field)))
                    if left != right:
                        mismatch_count += 1
                        detail_parts.append(
                            f"row{idx} field={field} json={left} tsv={right}"
                        )

            status = "PASS" if mismatch_count == 0 else "BLOCK"
            record(
                pair_id,
                "json_tsv_pair",
                f"{json_path.name}<->{tsv_path.name}",
                status,
                {"json_count": len(arr), "tsv_count": len(rows), "mismatch_count": mismatch_count},
                {"mismatch_count": 0},
                error_count=mismatch_count,
                detail="; ".join(detail_parts[:8]),
            )
        except Exception as exc:
            record(
                pair_id,
                "json_tsv_pair",
                f"{json_path.name}<->{tsv_path.name}",
                "BLOCK",
                f"exception:{exc}",
                "pair_consistent",
                error_count=1,
                detail="pair check exception",
            )

    # State anchor checks
    for state_check in manifest.get("state_checks", []):
        check_id = state_check["check_id"]
        json_path = Path(state_check["json_path"]).resolve()
        object_path = state_check.get("object_path")
        expected = state_check["expected"]

        if not json_path.exists():
            state_misjudge_count += 1
            record(
                check_id,
                "state_check",
                str(json_path),
                "BLOCK",
                "missing_file",
                expected,
                error_count=1,
                detail="state check file missing",
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data

        obj = get_obj_by_path(data, object_path)
        mismatches = []
        for key, exp_value in expected.items():
            got = None
            if isinstance(obj, dict):
                got = obj.get(key)
            if got != exp_value:
                mismatches.append((key, got, exp_value))

        if mismatches:
            state_misjudge_count += len(mismatches)
            record(
                check_id,
                "state_check",
                str(json_path),
                "BLOCK",
                {k: g for k, g, _ in mismatches},
                expected,
                error_count=len(mismatches),
                detail="; ".join([f"{k}={g} expected={e}" for k, g, e in mismatches]),
            )
        else:
            record(check_id, "state_check", str(json_path), "PASS", expected, expected)

    # Blocker status checks
    for blocker_check in manifest.get("blocker_checks", []):
        check_id = blocker_check["check_id"]
        json_path = Path(blocker_check["json_path"]).resolve()
        array_key = blocker_check["array_key"]
        id_field = blocker_check["id_field"]
        status_field = blocker_check["status_field"]
        expected = blocker_check["expected"]

        if not json_path.exists():
            record(
                check_id,
                "blocker_check",
                str(json_path),
                "BLOCK",
                "missing_file",
                expected,
                error_count=1,
                detail="blocker check file missing",
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data

        arr = data.get(array_key, [])
        mapping = {}
        for item in arr:
            if isinstance(item, dict) and id_field in item:
                mapping[str(item[id_field])] = item.get(status_field)

        mismatches = []
        for cid, exp_status in expected.items():
            got = mapping.get(cid)
            if got != exp_status:
                mismatches.append((cid, got, exp_status))

        if mismatches:
            record(
                check_id,
                "blocker_check",
                str(json_path),
                "BLOCK",
                {cid: got for cid, got, _ in mismatches},
                expected,
                error_count=len(mismatches),
                detail="; ".join([f"{cid}={got} expected={exp}" for cid, got, exp in mismatches]),
            )
        else:
            record(check_id, "blocker_check", str(json_path), "PASS", expected, expected)

    # Local closure policy checks
    for policy in manifest.get("local_closure_policy_checks", []):
        check_id = policy["check_id"]
        json_path = Path(policy["json_path"]).resolve()
        array_key = policy["array_key"]
        id_field = policy["id_field"]
        status_field = policy["status_field"]
        forbidden_keywords = [x.upper() for x in policy.get("forbidden_status_keywords", [])]

        if not json_path.exists():
            record(
                check_id,
                "local_closure_policy",
                str(json_path),
                "BLOCK",
                "missing_file",
                "policy_respected",
                error_count=1,
                detail="policy check file missing",
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data

        arr = data.get(array_key, [])
        violations = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            cid = str(item.get(id_field, ""))
            status = str(item.get(status_field, ""))
            upper_status = status.upper()
            if "CLOSED" in upper_status and not upper_status.startswith("LOCAL_"):
                violations.append(f"{cid}:{status}")
                continue
            for keyword in forbidden_keywords:
                if keyword in upper_status:
                    violations.append(f"{cid}:{status}")
                    break

        if violations:
            record(
                check_id,
                "local_closure_policy",
                str(json_path),
                "BLOCK",
                violations,
                "no production/go-live closure statuses",
                error_count=len(violations),
                detail="; ".join(violations),
            )
        else:
            record(
                check_id,
                "local_closure_policy",
                str(json_path),
                "PASS",
                "policy_ok",
                "policy_ok",
            )

    # HTML sensitive pattern checks
    for html_check in manifest.get("html_sensitive_checks", []):
        check_id = html_check["check_id"]
        html_path = Path(html_check["html_path"]).resolve()
        patterns = html_check["patterns"]

        if not html_path.exists():
            record(
                check_id,
                "html_sensitive_check",
                str(html_path),
                "BLOCK",
                "missing_file",
                "exists_and_clean",
                error_count=1,
                detail="html file missing",
            )
            continue

        content = html_path.read_text(encoding="utf-8", errors="replace")
        hits = []
        for pattern in patterns:
            if re.search(pattern, content, flags=re.IGNORECASE):
                hits.append(pattern)

        sensitive_pattern_hit_count += len(hits)
        if hits:
            record(
                check_id,
                "html_sensitive_check",
                str(html_path),
                "BLOCK",
                hits,
                "no sensitive patterns",
                error_count=len(hits),
                detail="; ".join(hits),
            )
        else:
            record(
                check_id,
                "html_sensitive_check",
                str(html_path),
                "PASS",
                "clean",
                "clean",
            )

    pass_check_count = sum(1 for c in checks if c["status"] == "PASS")
    block_check_count = sum(1 for c in checks if c["status"] == "BLOCK")
    task_status = "PASS" if block_check_count == 0 else "BLOCK"

    result = {
        "task_id": manifest.get("task_id", "TASK-Z008B-27-IMPL"),
        "source_head": source_head,
        "selected_candidate_id": selected_candidate_id,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "manifest_path": str(manifest_path),
        "task_status": task_status,
        "checked_file_count": checked_file_count,
        "pass_check_count": pass_check_count,
        "block_check_count": block_check_count,
        "sensitive_pattern_hit_count": sensitive_pattern_hit_count,
        "state_misjudge_count": state_misjudge_count,
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

    with output_tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "check_id",
                "check_type",
                "status",
                "target",
                "error_count",
                "detail",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for item in checks:
            writer.writerow(
                {
                    "check_id": item["check_id"],
                    "check_type": item["check_type"],
                    "status": item["status"],
                    "target": item["target"],
                    "error_count": item["error_count"],
                    "detail": item["detail"] if item["detail"] else "null",
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
