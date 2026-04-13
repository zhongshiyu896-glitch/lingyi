from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSERT_SCRIPT = ROOT / "scripts" / "assert_pytest_junit_no_skip.py"
RUN_GATE_SCRIPT = ROOT / "scripts" / "run_postgresql_ci_gate.sh"
PYTHON_BIN = ROOT / ".venv" / "bin" / "python"


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
