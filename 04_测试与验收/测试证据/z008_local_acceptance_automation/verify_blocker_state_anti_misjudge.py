#!/usr/bin/env python3
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify blocker state anti-misjudge constraints for local evidence."
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
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    trailing = 0
    for line in text.splitlines():
        if line.rstrip(" \t") != line:
            trailing += 1
    eof_single_newline = text.endswith("\n") and not text.endswith("\n\n")
    return {
        "trailing_whitespace_count": trailing,
        "eof_single_newline": eof_single_newline,
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

    checks: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    json_cache: Dict[str, Any] = {}
    checked_file_count = 0
    misjudge_count = 0

    def record(
        check_id: str,
        check_type: str,
        target: str,
        status: str,
        observed: Any,
        expected: Any,
        error_count: int = 0,
        detail: str = "",
        is_misjudge: bool = False,
    ) -> None:
        nonlocal misjudge_count
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
            if is_misjudge:
                misjudge_count += max(1, error_count)

    # File presence and hygiene
    for entry in manifest.get("file_entries", []):
        checked_file_count += 1
        entry_id = entry["entry_id"]
        file_path = Path(entry["path"]).resolve()
        kind = entry.get("kind", "text")

        if not file_path.exists():
            record(
                check_id=f"{entry_id}-EXIST",
                check_type="file_exists",
                target=str(file_path),
                status="BLOCK",
                observed="missing",
                expected="exists",
                error_count=1,
                detail="file missing",
                is_misjudge=True,
            )
            continue

        record(
            check_id=f"{entry_id}-EXIST",
            check_type="file_exists",
            target=str(file_path),
            status="PASS",
            observed="exists",
            expected="exists",
        )

        hygiene = text_hygiene(file_path)
        hygiene_ok = (
            hygiene["trailing_whitespace_count"] == 0
            and hygiene["eof_single_newline"] is True
        )
        record(
            check_id=f"{entry_id}-HYGIENE",
            check_type="text_hygiene",
            target=str(file_path),
            status="PASS" if hygiene_ok else "BLOCK",
            observed=hygiene,
            expected={"trailing_whitespace_count": 0, "eof_single_newline": True},
            error_count=0 if hygiene_ok else 1,
            detail="" if hygiene_ok else "text hygiene violation",
            is_misjudge=True,
        )

        if kind == "json":
            try:
                parsed = load_json(file_path)
                json_cache[str(file_path)] = parsed
                record(
                    check_id=f"{entry_id}-JSON",
                    check_type="json_parse",
                    target=str(file_path),
                    status="PASS",
                    observed="parse_ok",
                    expected="parse_ok",
                )
            except Exception as exc:
                record(
                    check_id=f"{entry_id}-JSON",
                    check_type="json_parse",
                    target=str(file_path),
                    status="BLOCK",
                    observed=f"parse_error:{exc}",
                    expected="parse_ok",
                    error_count=1,
                    detail="json parse failed",
                    is_misjudge=True,
                )

    # JSON/TSV consistency checks
    for pair in manifest.get("json_tsv_pairs", []):
        pair_id = pair["pair_id"]
        json_path = Path(pair["json_path"]).resolve()
        tsv_path = Path(pair["tsv_path"]).resolve()
        json_array_key = pair["json_array_key"]
        compare_fields = pair["compare_fields"]

        if not json_path.exists() or not tsv_path.exists():
            record(
                check_id=pair_id,
                check_type="json_tsv_pair",
                target=f"{json_path} <-> {tsv_path}",
                status="BLOCK",
                observed="missing_file",
                expected="both_exist",
                error_count=1,
                detail="pair file missing",
                is_misjudge=True,
            )
            continue

        try:
            data = json_cache.get(str(json_path))
            if data is None:
                data = load_json(json_path)
                json_cache[str(json_path)] = data
            arr = data.get(json_array_key, [])
            if not isinstance(arr, list):
                raise TypeError(f"{json_array_key} is not list")

            with tsv_path.open("r", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh, delimiter="\t"))

            mismatch = 0
            details: List[str] = []
            if len(arr) != len(rows):
                mismatch += abs(len(arr) - len(rows))
                details.append(f"count json={len(arr)} tsv={len(rows)}")

            for idx, (left_item, right_row) in enumerate(zip(arr, rows), start=1):
                for field in compare_fields:
                    left = normalize_value(left_item.get(field))
                    right = normalize_value(parse_tsv_cell(right_row.get(field)))
                    if left != right:
                        mismatch += 1
                        details.append(f"row{idx}.{field}:{left}!={right}")

            status = "PASS" if mismatch == 0 else "BLOCK"
            record(
                check_id=pair_id,
                check_type="json_tsv_pair",
                target=f"{json_path.name}<->{tsv_path.name}",
                status=status,
                observed={
                    "json_count": len(arr),
                    "tsv_count": len(rows),
                    "mismatch_count": mismatch,
                },
                expected={"mismatch_count": 0},
                error_count=mismatch,
                detail="; ".join(details[:8]),
                is_misjudge=True,
            )
        except Exception as exc:
            record(
                check_id=pair_id,
                check_type="json_tsv_pair",
                target=f"{json_path.name}<->{tsv_path.name}",
                status="BLOCK",
                observed=f"exception:{exc}",
                expected="pair_consistent",
                error_count=1,
                detail="pair check exception",
                is_misjudge=True,
            )

    # State anchor checks
    for state_check in manifest.get("state_checks", []):
        check_id = state_check["check_id"]
        json_path = Path(state_check["json_path"]).resolve()
        object_path = state_check.get("object_path")
        expected = state_check["expected"]

        if not json_path.exists():
            record(
                check_id=check_id,
                check_type="state_check",
                target=str(json_path),
                status="BLOCK",
                observed="missing_file",
                expected=expected,
                error_count=1,
                detail="state check file missing",
                is_misjudge=True,
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data

        obj = get_obj_by_path(data, object_path)
        mismatches = []
        for key, exp in expected.items():
            got = obj.get(key) if isinstance(obj, dict) else None
            if got != exp:
                mismatches.append((key, got, exp))

        if mismatches:
            record(
                check_id=check_id,
                check_type="state_check",
                target=str(json_path),
                status="BLOCK",
                observed={k: g for k, g, _ in mismatches},
                expected=expected,
                error_count=len(mismatches),
                detail="; ".join(f"{k}={g} expected={e}" for k, g, e in mismatches),
                is_misjudge=True,
            )
        else:
            record(
                check_id=check_id,
                check_type="state_check",
                target=str(json_path),
                status="PASS",
                observed=expected,
                expected=expected,
            )

    # Candidate status checks
    for ccheck in manifest.get("candidate_status_checks", []):
        check_id = ccheck["check_id"]
        json_path = Path(ccheck["json_path"]).resolve()
        array_key = ccheck["array_key"]
        id_field = ccheck["id_field"]
        status_field = ccheck["status_field"]
        expected = ccheck["expected"]

        if not json_path.exists():
            record(
                check_id=check_id,
                check_type="candidate_status_check",
                target=str(json_path),
                status="BLOCK",
                observed="missing_file",
                expected=expected,
                error_count=1,
                detail="candidate status file missing",
                is_misjudge=True,
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data
        arr = data.get(array_key, [])
        mapping: Dict[str, Any] = {}
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and id_field in item:
                    mapping[str(item[id_field])] = item.get(status_field)

        mismatches = []
        for cid, exp in expected.items():
            got = mapping.get(cid)
            if got != exp:
                mismatches.append((cid, got, exp))

        if mismatches:
            record(
                check_id=check_id,
                check_type="candidate_status_check",
                target=str(json_path),
                status="BLOCK",
                observed={cid: got for cid, got, _ in mismatches},
                expected=expected,
                error_count=len(mismatches),
                detail="; ".join(f"{cid}={got} expected={exp}" for cid, got, exp in mismatches),
                is_misjudge=True,
            )
        else:
            record(
                check_id=check_id,
                check_type="candidate_status_check",
                target=str(json_path),
                status="PASS",
                observed=expected,
                expected=expected,
            )

    # Local closure semantics checks
    for lcheck in manifest.get("local_closure_checks", []):
        check_id = lcheck["check_id"]
        json_path = Path(lcheck["json_path"]).resolve()
        array_key = lcheck["array_key"]
        id_field = lcheck["id_field"]
        status_field = lcheck["status_field"]
        candidate_ids = lcheck["candidate_ids"]
        required_prefix = lcheck.get("required_prefix", "LOCAL_")

        if not json_path.exists():
            record(
                check_id=check_id,
                check_type="local_closure_check",
                target=str(json_path),
                status="BLOCK",
                observed="missing_file",
                expected=f"{required_prefix}*",
                error_count=1,
                detail="local closure check file missing",
                is_misjudge=True,
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data
        arr = data.get(array_key, [])
        mapping: Dict[str, Any] = {}
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and id_field in item:
                    mapping[str(item[id_field])] = item.get(status_field)

        violations = []
        for cid in candidate_ids:
            status = str(mapping.get(cid, ""))
            if not status.upper().startswith(required_prefix.upper()):
                violations.append((cid, status))

        if violations:
            record(
                check_id=check_id,
                check_type="local_closure_check",
                target=str(json_path),
                status="BLOCK",
                observed={cid: status for cid, status in violations},
                expected=f"{required_prefix}*",
                error_count=len(violations),
                detail="; ".join(f"{cid}={status}" for cid, status in violations),
                is_misjudge=True,
            )
        else:
            record(
                check_id=check_id,
                check_type="local_closure_check",
                target=str(json_path),
                status="PASS",
                observed="prefix_ok",
                expected=f"{required_prefix}*",
            )

    # Compute blocker counters from canonical remaining-candidate file
    counter_cfg = manifest.get("blocked_counter_source", {})
    blocked_external_dependency_count = 0
    blocked_remote_lifecycle_count = 0
    if counter_cfg:
        json_path = Path(counter_cfg["json_path"]).resolve()
        array_key = counter_cfg["array_key"]
        id_field = counter_cfg["id_field"]
        status_field = counter_cfg["status_field"]
        external_ids = set(counter_cfg.get("external_dependency_ids", []))
        remote_ids = set(counter_cfg.get("remote_lifecycle_ids", []))
        external_status = counter_cfg.get("external_status", "BLOCKED_EXTERNAL_DEPENDENCY")
        remote_status = counter_cfg.get("remote_status", "BLOCKED_REMOTE_LIFECYCLE")
        if json_path.exists():
            data = json_cache.get(str(json_path))
            if data is None:
                data = load_json(json_path)
                json_cache[str(json_path)] = data
            arr = data.get(array_key, [])
            if isinstance(arr, list):
                for item in arr:
                    if not isinstance(item, dict):
                        continue
                    cid = str(item.get(id_field))
                    status = item.get(status_field)
                    if cid in external_ids and status == external_status:
                        blocked_external_dependency_count += 1
                    if cid in remote_ids and status == remote_status:
                        blocked_remote_lifecycle_count += 1

    # Threshold checks for blocker counters
    for threshold in manifest.get("blocked_counter_thresholds", []):
        check_id = threshold["check_id"]
        metric = threshold["metric"]
        op = threshold["operator"]
        expected = int(threshold["expected"])
        observed = (
            blocked_external_dependency_count
            if metric == "blocked_external_dependency_count"
            else blocked_remote_lifecycle_count
        )
        passed = observed >= expected if op == ">=" else observed == expected
        record(
            check_id=check_id,
            check_type="blocked_counter_threshold",
            target=metric,
            status="PASS" if passed else "BLOCK",
            observed=observed,
            expected=f"{op}{expected}",
            error_count=0 if passed else 1,
            detail="" if passed else f"{metric}={observed} not {op} {expected}",
            is_misjudge=True,
        )

    # Forbidden value checks (top-level flags)
    for forbid in manifest.get("forbidden_value_checks", []):
        check_id = forbid["check_id"]
        json_path = Path(forbid["json_path"]).resolve()
        key = forbid["key"]
        forbidden_value = forbid["forbidden_value"]

        if not json_path.exists():
            record(
                check_id=check_id,
                check_type="forbidden_value_check",
                target=str(json_path),
                status="BLOCK",
                observed="missing_file",
                expected=f"{key}!={forbidden_value}",
                error_count=1,
                detail="forbidden value file missing",
                is_misjudge=True,
            )
            continue

        data = json_cache.get(str(json_path))
        if data is None:
            data = load_json(json_path)
            json_cache[str(json_path)] = data

        got = data.get(key) if isinstance(data, dict) else None
        passed = got != forbidden_value
        record(
            check_id=check_id,
            check_type="forbidden_value_check",
            target=f"{json_path.name}:{key}",
            status="PASS" if passed else "BLOCK",
            observed=got,
            expected=f"!= {forbidden_value}",
            error_count=0 if passed else 1,
            detail="" if passed else f"forbidden value hit: {key}={got}",
            is_misjudge=True,
        )

    pass_check_count = sum(1 for item in checks if item["status"] == "PASS")
    block_check_count = sum(1 for item in checks if item["status"] == "BLOCK")
    check_count = len(checks)
    task_status = "PASS" if block_check_count == 0 else "BLOCK"

    result = {
        "task_id": manifest.get("task_id", "TASK-Z008B-32-IMPL"),
        "source_head": source_head,
        "selected_candidate_id": selected_candidate_id,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "manifest_path": str(manifest_path),
        "task_status": task_status,
        "check_count": check_count,
        "pass_check_count": pass_check_count,
        "block_check_count": block_check_count,
        "misjudge_count": misjudge_count,
        "blocked_external_dependency_count": blocked_external_dependency_count,
        "blocked_remote_lifecycle_count": blocked_remote_lifecycle_count,
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
                "observed",
                "expected",
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
                    "observed": normalize_value(item["observed"]),
                    "expected": normalize_value(item["expected"]),
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
