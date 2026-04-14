from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSERT_SCRIPT = ROOT / "scripts" / "assert_pytest_junit_no_skip.py"
RUN_GATE_SCRIPT = ROOT / "scripts" / "run_postgresql_ci_gate.sh"
WORKFLOW_FILE = ROOT.parent.parent / ".github" / "workflows" / "backend-postgresql.yml"
SETTLEMENT_FIXTURE_FILE = ROOT / "tests" / "test_subcontract_settlement_postgresql.py"
PYTHON_BIN = ROOT / ".venv" / "bin" / "python"
SETTLEMENT_TARGET = "tests/test_subcontract_settlement_postgresql.py"
STYLE_PROFIT_TARGET = "tests/test_style_profit_subcontract_postgresql.py"
SETTLEMENT_JUNIT = ".pytest-postgresql-subcontract-settlement.xml"
STYLE_PROFIT_JUNIT = ".pytest-postgresql-style-profit-subcontract.xml"
LEGACY_JUNIT = ".pytest-postgresql.xml"


def _write_junit(path: Path, *, tests: int, skipped: int, failures: int = 0, errors: int = 0) -> None:
    path.write_text(
        (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<testsuite name="pytest" tests="{tests}" skipped="{skipped}" failures="{failures}" errors="{errors}"/>\n'
        ),
        encoding="utf-8",
    )


def _run_assert(report: Path, *, expected_tests: int = 4, expected_skipped: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(PYTHON_BIN),
            str(ASSERT_SCRIPT),
            str(report),
            "--expected-tests",
            str(expected_tests),
            "--expected-skipped",
            str(expected_skipped),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _validate_gate_script_content(content: str) -> list[str]:
    errors: list[str] = []
    if SETTLEMENT_TARGET not in content:
        errors.append("missing settlement postgresql target")
    if STYLE_PROFIT_TARGET not in content:
        errors.append("missing style-profit postgresql target")
    if SETTLEMENT_JUNIT not in content:
        errors.append("missing settlement junit file")
    if STYLE_PROFIT_JUNIT not in content:
        errors.append("missing style-profit junit file")
    if SETTLEMENT_JUNIT == STYLE_PROFIT_JUNIT:
        errors.append("junit files must be different")

    expected_assert = "--expected-tests 4 --expected-skipped 0"
    if content.count(expected_assert) < 2:
        errors.append("expected per-suite junit assertions are missing")
    return errors


def _validate_workflow_junit_upload_content(content: str) -> list[str]:
    errors: list[str] = []
    if "bash scripts/run_postgresql_ci_gate.sh" not in content:
        errors.append("workflow must run PostgreSQL hard gate script")
    if "services:" not in content or "postgres:" not in content:
        errors.append("workflow must keep postgres service")
    if SETTLEMENT_JUNIT not in content:
        errors.append("workflow missing settlement junit artifact path")
    if STYLE_PROFIT_JUNIT not in content:
        errors.append("workflow missing style-profit junit artifact path")
    if "postgresql-settlement-junit" not in content:
        errors.append("workflow missing settlement artifact name")
    if "postgresql-style-profit-junit" not in content:
        errors.append("workflow missing style-profit artifact name")
    if f"path: 07_后端/lingyi_service/{LEGACY_JUNIT}" in content:
        errors.append("workflow still uploads legacy single junit path")
    return errors


def _validate_settlement_postgresql_fixture_content(content: str) -> list[str]:
    errors: list[str] = []
    required_tokens = [
        "task_005f2_subcontract_profit_scope_bridge as migration_005f2",
        "_run_migration_upgrade(engine, migration_005f2)",
        "def _assert_subcontract_profit_scope_columns(",
        "_assert_subcontract_profit_scope_columns(engine)",
    ]
    for token in required_tokens:
        if token not in content:
            errors.append(f"missing token in settlement fixture: {token}")

    required_columns = {
        "ly_subcontract_order": {"sales_order", "work_order", "profit_scope_status"},
        "ly_subcontract_inspection": {"sales_order", "work_order", "profit_scope_status"},
    }
    for table_name, columns in required_columns.items():
        pattern = rf'["\']{table_name}["\']\s*:\s*\((?P<body>.*?)\)\s*,'
        match = re.search(pattern, content, flags=re.DOTALL)
        if not match:
            errors.append(f"missing schema assertion tuple for table: {table_name}")
            continue
        values = set(re.findall(r'["\']([^"\']+)["\']', match.group("body")))
        missing = sorted(columns - values)
        if missing:
            errors.append(
                f"missing schema assertion columns for {table_name}: {', '.join(missing)}"
            )
    return errors


def test_assert_junit_passes_when_four_tests_zero_skipped(tmp_path: Path) -> None:
    report = tmp_path / "ok.xml"
    _write_junit(report, tests=4, skipped=0, failures=0, errors=0)
    result = _run_assert(report, expected_tests=4, expected_skipped=0)
    assert result.returncode == 0, result.stderr


def test_assert_junit_fails_when_all_skipped(tmp_path: Path) -> None:
    report = tmp_path / "all_skipped.xml"
    _write_junit(report, tests=4, skipped=4, failures=0, errors=0)
    result = _run_assert(report, expected_tests=4, expected_skipped=0)
    assert result.returncode != 0
    assert "skipped=4" in result.stderr


def test_assert_junit_fails_when_test_count_is_zero(tmp_path: Path) -> None:
    report = tmp_path / "zero.xml"
    _write_junit(report, tests=0, skipped=0, failures=0, errors=0)
    result = _run_assert(report, expected_tests=4, expected_skipped=0)
    assert result.returncode != 0
    assert "tests=0" in result.stderr


def test_assert_junit_fails_when_test_count_is_not_four(tmp_path: Path) -> None:
    report = tmp_path / "three.xml"
    _write_junit(report, tests=3, skipped=0, failures=0, errors=0)
    result = _run_assert(report, expected_tests=4, expected_skipped=0)
    assert result.returncode != 0
    assert "tests=3" in result.stderr


def test_assert_junit_fails_when_report_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    result = _run_assert(missing, expected_tests=4, expected_skipped=0)
    assert result.returncode != 0
    assert "not found" in result.stderr.lower()


def test_run_postgresql_ci_gate_requires_envs() -> None:
    env = os.environ.copy()
    env.pop("POSTGRES_TEST_DSN", None)
    env.pop("POSTGRES_TEST_ALLOW_DESTRUCTIVE", None)
    result = subprocess.run(
        ["bash", str(RUN_GATE_SCRIPT)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode != 0
    assert "POSTGRES_TEST_DSN is required" in result.stderr


def test_run_postgresql_ci_gate_includes_both_postgresql_targets_and_junit_files() -> None:
    content = RUN_GATE_SCRIPT.read_text(encoding="utf-8")
    errors = _validate_gate_script_content(content)
    assert not errors, "; ".join(errors)


def test_run_postgresql_ci_gate_fails_validation_if_settlement_target_missing() -> None:
    content = f"""
#!/usr/bin/env bash
set -euo pipefail
.venv/bin/python -m pytest -q -m postgresql {STYLE_PROFIT_TARGET} --junitxml={STYLE_PROFIT_JUNIT}
.venv/bin/python scripts/assert_pytest_junit_no_skip.py {STYLE_PROFIT_JUNIT} --expected-tests 4 --expected-skipped 0
"""
    errors = _validate_gate_script_content(content)
    assert errors
    assert any("settlement postgresql target" in message for message in errors)


def test_subcontract_settlement_postgresql_fixture_keeps_f2_bridge_and_schema_assertions() -> None:
    content = SETTLEMENT_FIXTURE_FILE.read_text(encoding="utf-8")
    errors = _validate_settlement_postgresql_fixture_content(content)
    assert not errors, "; ".join(errors)


def test_subcontract_settlement_postgresql_fixture_validation_fails_when_bridge_or_assertions_removed() -> None:
    content = """
from migrations.versions import task_002h1_subcontract_settlement_operation_idempotency as migration_002h1

def _run_settlement_chain(engine):
    _run_migration_upgrade(engine, migration_002h1)
"""
    errors = _validate_settlement_postgresql_fixture_content(content)
    assert errors
    assert any("migration_005f2" in message for message in errors)
    assert any("_assert_subcontract_profit_scope_columns" in message for message in errors)


def test_backend_postgresql_workflow_uploads_both_junit_artifacts() -> None:
    content = WORKFLOW_FILE.read_text(encoding="utf-8")
    errors = _validate_workflow_junit_upload_content(content)
    assert not errors, "; ".join(errors)


def test_backend_postgresql_workflow_validation_fails_for_legacy_single_junit_upload() -> None:
    content = f"""
name: Backend PostgreSQL Hard Gate
jobs:
  subcontract-postgresql-gate:
    services:
      postgres:
        image: postgres:16-alpine
    steps:
      - run: bash scripts/run_postgresql_ci_gate.sh
      - uses: actions/upload-artifact@v4
        with:
          name: postgresql-gate-junit
          path: 07_后端/lingyi_service/{LEGACY_JUNIT}
"""
    errors = _validate_workflow_junit_upload_content(content)
    assert errors
    assert any("legacy single junit path" in message for message in errors)
