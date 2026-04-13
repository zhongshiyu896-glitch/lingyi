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

JUNIT_FILE=".pytest-postgresql.xml"
rm -f "$JUNIT_FILE"

.venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py --junitxml="$JUNIT_FILE"
.venv/bin/python scripts/assert_pytest_junit_no_skip.py "$JUNIT_FILE" --expected-tests 4 --expected-skipped 0
