#!/usr/bin/env python3
import argparse
import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple


PREFERRED_LIST_KEYS = [
    "entries",
    "candidates",
    "matrix",
    "checklist",
    "items",
    "rows",
    "results",
    "remaining_candidates",
    "evidence_index_entries",
    "coverage_matrix_entries",
    "blocker_matrix_entries",
    "gate_command_template_entries",
    "readable_evidence_index_entries",
    "readable_coverage_summary_entries",
    "readable_blocker_summary_entries",
    "readable_gate_command_checklist_entries",
]

DEFAULT_IDENTIFIER_KEYS = [
    "entry_id",
    "candidate_id",
    "task_id",
    "command_id",
    "coverage_domain",
    "blocker_domain",
    "path",
    "order",
]

DEFAULT_CORE_KEYS = [
    "entry_id",
    "candidate_id",
    "task_id",
    "order",
    "status",
    "candidate_status",
    "coverage_status",
    "blocker_status",
    "path",
    "include",
    "local_actionable",
    "block_on_fail",
]


def now_cn() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def normalize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return ";".join(normalize(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    text = str(value).strip()
    if text.lower() in {"true", "false"}:
        return text.lower()
    if text.lower() == "null":
        return "null"
    return text


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tsv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def find_json_entries(data: Any, key_hint: str = "") -> Tuple[str, List[Dict[str, Any]]]:
    if key_hint and isinstance(data, dict) and isinstance(data.get(key_hint), list):
        raw = data.get(key_hint) or []
        return key_hint, [row for row in raw if isinstance(row, dict)]
    if isinstance(data, list):
        return "<root_list>", [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return "<none>", []

    for key in PREFERRED_LIST_KEYS:
        raw = data.get(key)
        if isinstance(raw, list):
            return key, [row for row in raw if isinstance(row, dict)]

    list_candidates: List[Tuple[str, List[Any]]] = []
    for key, val in data.items():
        if isinstance(val, list):
            list_candidates.append((key, val))
    if list_candidates:
        list_candidates.sort(key=lambda kv: len(kv[1]), reverse=True)
        key, raw = list_candidates[0]
        return key, [row for row in raw if isinstance(row, dict)]
    return "<none>", []


def choose_identifier_key(
    json_fields: List[str], tsv_headers: List[str], preferred: List[str]
) -> str:
    header_set = set(tsv_headers)
    json_set = set(json_fields)
    for key in preferred:
        if key in header_set and key in json_set:
            return key
    return ""


def choose_core_keys(
    json_fields: List[str], tsv_headers: List[str], configured: List[str]
) -> List[str]:
    header_set = set(tsv_headers)
    json_set = set(json_fields)
    keys: List[str] = []
    for key in configured:
        if key in header_set and key in json_set:
            keys.append(key)
    if keys:
        return keys
    intersection = [h for h in tsv_headers if h in json_set]
    return intersection[:8]


def verify_pair(pair: Dict[str, Any]) -> Dict[str, Any]:
    pair_id = pair["pair_id"]
    json_path = Path(pair["json_path"])
    tsv_path = Path(pair["tsv_path"])
    key_hint = pair.get("json_array_key", "")
    identifier_keys = pair.get("identifier_keys", DEFAULT_IDENTIFIER_KEYS)
    core_keys = pair.get("core_keys", DEFAULT_CORE_KEYS)

    errors: List[str] = []
    mismatches: List[str] = []

    if not json_path.exists():
        errors.append(f"json_missing:{json_path}")
    if not tsv_path.exists():
        errors.append(f"tsv_missing:{tsv_path}")
    if errors:
        return {
            "pair_id": pair_id,
            "json_path": str(json_path),
            "tsv_path": str(tsv_path),
            "status": "FAIL",
            "json_count": 0,
            "tsv_count": 0,
            "mismatch_count": len(errors),
            "order_match": False,
            "identifier_field": "",
            "core_fields_checked": [],
            "json_array_key": key_hint or "<unknown>",
            "error_count": len(errors),
            "errors": errors,
            "mismatches": [],
        }

    try:
        data = load_json(json_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"json_parse_error:{exc}")
        data = {}

    try:
        tsv_headers, tsv_rows = load_tsv(tsv_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tsv_parse_error:{exc}")
        tsv_headers, tsv_rows = [], []

    json_array_key, json_entries = find_json_entries(data, key_hint=key_hint)

    json_count = len(json_entries)
    tsv_count = len(tsv_rows)
    if json_count != tsv_count:
        mismatches.append(f"count_mismatch:json={json_count},tsv={tsv_count}")

    json_fields = list(json_entries[0].keys()) if json_entries else []
    identifier_field = choose_identifier_key(json_fields, tsv_headers, identifier_keys)
    core_fields_checked = choose_core_keys(json_fields, tsv_headers, core_keys)

    order_match = True
    if identifier_field:
        json_order = [normalize(row.get(identifier_field)) for row in json_entries]
        tsv_order = [normalize(row.get(identifier_field, "")) for row in tsv_rows]
        if json_order != tsv_order:
            order_match = False
            mismatches.append(f"order_mismatch_by:{identifier_field}")
    elif "order" in json_fields and "order" in tsv_headers:
        json_order = [normalize(row.get("order")) for row in json_entries]
        tsv_order = [normalize(row.get("order", "")) for row in tsv_rows]
        if json_order != tsv_order:
            order_match = False
            mismatches.append("order_mismatch_by:order")

    compare_len = min(json_count, tsv_count)
    for idx in range(compare_len):
        jrow = json_entries[idx]
        trow = tsv_rows[idx]
        for field in core_fields_checked:
            jval = normalize(jrow.get(field))
            tval = normalize(trow.get(field, ""))
            if jval != tval:
                marker = f"row={idx + 1},field={field},json={jval},tsv={tval}"
                mismatches.append(marker)

    status = "PASS" if not errors and not mismatches else "FAIL"
    mismatch_count = len(errors) + len(mismatches)
    return {
        "pair_id": pair_id,
        "json_path": str(json_path),
        "tsv_path": str(tsv_path),
        "status": status,
        "json_count": json_count,
        "tsv_count": tsv_count,
        "mismatch_count": mismatch_count,
        "order_match": order_match,
        "identifier_field": identifier_field,
        "core_fields_checked": core_fields_checked,
        "json_array_key": json_array_key,
        "error_count": len(errors),
        "errors": errors,
        "mismatches": mismatches,
    }


def write_result_tsv(path: Path, rows: List[Dict[str, Any]]) -> None:
    headers = [
        "pair_id",
        "status",
        "json_path",
        "tsv_path",
        "json_count",
        "tsv_count",
        "mismatch_count",
        "order_match",
        "identifier_field",
        "json_array_key",
        "core_fields_checked",
        "error_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        for row in rows:
            payload = {k: row.get(k, "") for k in headers}
            payload["core_fields_checked"] = ";".join(row.get("core_fields_checked", []))
            payload["order_match"] = "true" if row.get("order_match") else "false"
            writer.writerow(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify JSON/TSV consistency.")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    parser.add_argument("--output-json", required=True, help="Path to output JSON.")
    parser.add_argument("--output-tsv", required=True, help="Path to output TSV.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_json_path = Path(args.output_json)
    out_tsv_path = Path(args.output_tsv)

    manifest = load_json(manifest_path)
    pair_entries = manifest.get("pair_entries", [])

    results = [verify_pair(pair) for pair in pair_entries]
    pair_count = len(results)
    pass_pair_count = sum(1 for r in results if r["status"] == "PASS")
    mismatch_pair_count = pair_count - pass_pair_count
    task_status = "PASS" if mismatch_pair_count == 0 else "BLOCK"

    result_payload = {
        "task_id": manifest.get("task_id", "TASK-Z008B-02-IMPL"),
        "source_head": manifest.get("source_head"),
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "generated_at": now_cn(),
        "manifest_path": str(manifest_path),
        "pair_count": pair_count,
        "pass_pair_count": pass_pair_count,
        "mismatch_pair_count": mismatch_pair_count,
        "task_status": task_status,
        "runtime_request_count": 0,
        "write_request_count": 0,
        "production_account_used": False,
        "remote_lifecycle_action_executed": False,
        "results": results,
    }

    out_json_path.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_result_tsv(out_tsv_path, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
