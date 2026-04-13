#!/usr/bin/env python3
"""Assert pytest JUnit XML metrics for PostgreSQL CI hard gate."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _to_int(value: str | None, field_name: str) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).strip())
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"invalid integer field `{field_name}`: {value!r}") from exc


def _read_metrics(report_path: Path) -> tuple[int, int, int, int]:
    if not report_path.exists():
        raise FileNotFoundError(f"JUnit report not found: {report_path}")

    try:
        root = ET.parse(report_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"failed to parse JUnit report: {report_path}") from exc

    tests = failures = errors = skipped = 0
    if root.tag == "testsuite":
        tests = _to_int(root.get("tests"), "tests")
        failures = _to_int(root.get("failures"), "failures")
        errors = _to_int(root.get("errors"), "errors")
        skipped = _to_int(root.get("skipped"), "skipped")
    elif root.tag == "testsuites":
        for suite in root.findall("testsuite"):
            tests += _to_int(suite.get("tests"), "tests")
            failures += _to_int(suite.get("failures"), "failures")
            errors += _to_int(suite.get("errors"), "errors")
            skipped += _to_int(suite.get("skipped"), "skipped")
    else:
        raise ValueError(f"unexpected JUnit XML root tag: {root.tag!r}")
    return tests, failures, errors, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert pytest JUnit XML metrics.")
    parser.add_argument("junit_xml", help="Path to pytest JUnit XML file.")
    parser.add_argument("--expected-tests", type=int, required=True, help="Expected total executed tests.")
    parser.add_argument(
        "--expected-skipped",
        type=int,
        required=True,
        help="Expected skipped tests count.",
    )
    parser.add_argument("--expected-failures", type=int, default=0, help="Expected failures count. Default: 0.")
    parser.add_argument("--expected-errors", type=int, default=0, help="Expected errors count. Default: 0.")
    args = parser.parse_args()

    report_path = Path(args.junit_xml)
    tests, failures, errors, skipped = _read_metrics(report_path)

    mismatches: list[str] = []
    if tests != args.expected_tests:
        mismatches.append(f"tests={tests} (expected {args.expected_tests})")
    if skipped != args.expected_skipped:
        mismatches.append(f"skipped={skipped} (expected {args.expected_skipped})")
    if failures != args.expected_failures:
        mismatches.append(f"failures={failures} (expected {args.expected_failures})")
    if errors != args.expected_errors:
        mismatches.append(f"errors={errors} (expected {args.expected_errors})")

    if mismatches:
        print("JUnit gate failed: " + ", ".join(mismatches), file=sys.stderr)
        return 1

    print(
        f"JUnit gate passed: tests={tests}, skipped={skipped}, failures={failures}, errors={errors}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
