#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${POSTGRES_TEST_DSN:-}" ]]; then
  echo "POSTGRES_TEST_DSN is required for PostgreSQL CI gate" >&2
  exit 1
fi

if [[ "${POSTGRES_TEST_ALLOW_DESTRUCTIVE:-}" != "true" ]]; then
  echo "POSTGRES_TEST_ALLOW_DESTRUCTIVE must be true for PostgreSQL CI gate" >&2
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo ".venv/bin/python not found. create venv and install dependencies first." >&2
  exit 1
fi

SETTLEMENT_TEST_TARGET="tests/test_subcontract_settlement_postgresql.py"
STYLE_PROFIT_TEST_TARGET="tests/test_style_profit_subcontract_postgresql.py"
SETTLEMENT_JUNIT_FILE=".pytest-postgresql-subcontract-settlement.xml"
STYLE_PROFIT_JUNIT_FILE=".pytest-postgresql-style-profit-subcontract.xml"

rm -f "$SETTLEMENT_JUNIT_FILE" "$STYLE_PROFIT_JUNIT_FILE"

.venv/bin/python -m pytest -q -m postgresql "$SETTLEMENT_TEST_TARGET" --junitxml="$SETTLEMENT_JUNIT_FILE"
.venv/bin/python scripts/assert_pytest_junit_no_skip.py "$SETTLEMENT_JUNIT_FILE" --expected-tests 4 --expected-skipped 0

.venv/bin/python -m pytest -q -m postgresql "$STYLE_PROFIT_TEST_TARGET" --junitxml="$STYLE_PROFIT_JUNIT_FILE"
.venv/bin/python scripts/assert_pytest_junit_no_skip.py "$STYLE_PROFIT_JUNIT_FILE" --expected-tests 4 --expected-skipped 0

echo "PostgreSQL CI hard gate passed: settlement + style-profit gates are both non-skip and green."
