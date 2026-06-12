#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SETTLEMENT_TEST_TARGET="tests/test_subcontract_settlement_postgresql.py"
STYLE_PROFIT_TEST_TARGET="tests/test_style_profit_subcontract_postgresql.py"
SETTLEMENT_JUNIT_FILE=".pytest-postgresql-subcontract-settlement.xml"
STYLE_PROFIT_JUNIT_FILE=".pytest-postgresql-style-profit-subcontract.xml"

rm -f "$SETTLEMENT_JUNIT_FILE" "$STYLE_PROFIT_JUNIT_FILE"

write_junit_status() {
  local output_path="$1"
  local suite_name="$2"
  local testcase_name="$3"
  local status="$4"
  local message="$5"

  case "$status" in
    skipped)
      cat >"$output_path" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="$suite_name" tests="1" skipped="1" failures="0" errors="0">
  <testcase classname="$suite_name" name="$testcase_name">
    <skipped message="$message" />
  </testcase>
</testsuite>
EOF
      ;;
    blocked)
      cat >"$output_path" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="$suite_name" tests="1" skipped="0" failures="0" errors="1">
  <testcase classname="$suite_name" name="$testcase_name">
    <error message="$message" />
  </testcase>
</testsuite>
EOF
      ;;
    *)
      echo "unsupported junit status: $status" >&2
      exit 1
      ;;
  esac
}

emit_status() {
  local status="$1"
  local message="$2"
  echo "POSTGRESQL_CI_GATE_STATUS=$status"
  echo "POSTGRESQL_CI_GATE_REASON=$message"
}

if [[ -z "${POSTGRES_TEST_DSN:-}" ]]; then
  message="POSTGRES_TEST_DSN is not set; skipping PostgreSQL CI gate in local/dev context."
  write_junit_status "$SETTLEMENT_JUNIT_FILE" "postgresql-ci-gate" "settlement-postgresql-gate" "skipped" "$message"
  write_junit_status "$STYLE_PROFIT_JUNIT_FILE" "postgresql-ci-gate" "style-profit-postgresql-gate" "skipped" "$message"
  emit_status "skipped" "$message"
  exit 0
fi

if [[ "${POSTGRES_TEST_ALLOW_DESTRUCTIVE:-}" != "true" ]]; then
  message="POSTGRES_TEST_ALLOW_DESTRUCTIVE must be true before destructive PostgreSQL CI gate can run."
  write_junit_status "$SETTLEMENT_JUNIT_FILE" "postgresql-ci-gate" "settlement-postgresql-gate" "blocked" "$message"
  write_junit_status "$STYLE_PROFIT_JUNIT_FILE" "postgresql-ci-gate" "style-profit-postgresql-gate" "blocked" "$message"
  emit_status "blocked" "$message"
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  message=".venv/bin/python not found. create venv and install dependencies first."
  write_junit_status "$SETTLEMENT_JUNIT_FILE" "postgresql-ci-gate" "settlement-postgresql-gate" "blocked" "$message"
  write_junit_status "$STYLE_PROFIT_JUNIT_FILE" "postgresql-ci-gate" "style-profit-postgresql-gate" "blocked" "$message"
  emit_status "blocked" "$message"
  exit 1
fi

.venv/bin/python -m pytest -q -m postgresql "$SETTLEMENT_TEST_TARGET" --junitxml="$SETTLEMENT_JUNIT_FILE"
.venv/bin/python scripts/assert_pytest_junit_no_skip.py "$SETTLEMENT_JUNIT_FILE" --expected-tests 4 --expected-skipped 0

.venv/bin/python -m pytest -q -m postgresql "$STYLE_PROFIT_TEST_TARGET" --junitxml="$STYLE_PROFIT_JUNIT_FILE"
.venv/bin/python scripts/assert_pytest_junit_no_skip.py "$STYLE_PROFIT_JUNIT_FILE" --expected-tests 4 --expected-skipped 0

emit_status "ready" "PostgreSQL CI hard gate passed: settlement + style-profit gates are both non-skip and green."
echo "PostgreSQL CI hard gate passed: settlement + style-profit gates are both non-skip and green."
