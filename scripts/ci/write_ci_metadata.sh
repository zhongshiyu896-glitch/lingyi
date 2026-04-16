#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-.ci-reports}"
GATE_NAME="${2:-unknown-gate}"
mkdir -p "$OUT_DIR"

COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
RUN_URL="unavailable"
if [[ -n "${GITHUB_SERVER_URL:-}" && -n "${GITHUB_REPOSITORY:-}" && -n "${GITHUB_RUN_ID:-}" ]]; then
  RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
fi

{
  echo "gate_name=${GATE_NAME}"
  echo "run_url=${RUN_URL}"
  echo "commit_sha=${COMMIT_SHA}"
  echo "runner_os=${RUNNER_OS:-$(uname -s 2>/dev/null || echo unknown)}"
  echo "started_or_collected_at_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "node_version=$(node -v 2>/dev/null || echo unavailable)"
  echo "npm_version=$(npm -v 2>/dev/null || echo unavailable)"
  echo "python_version=$(python --version 2>/dev/null || python3 --version 2>/dev/null || echo unavailable)"
  echo "postgresql_version=$(psql --version 2>/dev/null || postgres --version 2>/dev/null || echo unavailable)"
  echo "sensitive_scan_result=see sensitive-scan.txt when present; metadata helper never prints credentials"
} > "${OUT_DIR}/ci-metadata.txt"
