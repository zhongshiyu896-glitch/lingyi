#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"
mkdir -p .ci-reports
REPORT_FILE=".ci-reports/docs-boundary-report.txt"
BASE_SHA="${1:-${BASE_SHA:-}}"

if [[ -z "$BASE_SHA" || "$BASE_SHA" == "0000000000000000000000000000000000000000" ]]; then
  if git rev-parse HEAD~1 >/dev/null 2>&1; then
    BASE_SHA="HEAD~1"
  else
    BASE_SHA=""
  fi
fi

CHANGED_FILES=()
if [[ -n "$BASE_SHA" ]]; then
  while IFS= read -r file; do
    CHANGED_FILES+=("$file")
  done < <(git diff --name-only "$BASE_SHA"...HEAD)
else
  while IFS= read -r file; do
    CHANGED_FILES+=("$file")
  done < <(git ls-files)
fi

{
  echo "Docs Boundary Gate"
  echo "base_sha=${BASE_SHA:-<none>}"
  echo "head_sha=$(git rev-parse HEAD)"
  echo "changed_files=${#CHANGED_FILES[@]}"
} > "$REPORT_FILE"

failures=()
for file in "${CHANGED_FILES[@]}"; do
  [[ -z "$file" ]] && continue
  echo "$file" >> "$REPORT_FILE"
  case "$file" in
    06_前端/*|07_后端/*|.github/*|02_源码/*)
      failures+=("docs-only boundary forbids non-doc path changed: $file")
      ;;
  esac
  if [[ "$file" =~ (^|/)(node_modules|dist|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)(/|$) ]]; then
    failures+=("generated/runtime artifact changed: $file")
  fi
  if [[ "$file" =~ \.pytest-postgresql.*\.xml$ || "$file" =~ \.pyc$ ]]; then
    failures+=("generated test/cache artifact changed: $file")
  fi
  if [[ "$file" =~ (^|/)\.env(\.|$) && "$file" != *".env.example" ]]; then
    failures+=("environment secret file changed: $file")
  fi
 done

SCAN_TARGETS=()
for file in "${CHANGED_FILES[@]}"; do
  [[ -f "$file" ]] && SCAN_TARGETS+=("$file")
 done
if [[ ${#SCAN_TARGETS[@]} -gt 0 ]]; then
  if scripts/ci/assert_no_sensitive_values.py "${SCAN_TARGETS[@]}" > .ci-reports/sensitive-scan.txt 2>&1; then
    echo "sensitive_scan=passed" >> "$REPORT_FILE"
  else
    echo "sensitive_scan=failed" >> "$REPORT_FILE"
    failures+=("sensitive scan failed; see .ci-reports/sensitive-scan.txt")
  fi
else
  echo "Sensitive scan skipped: no changed text files." > .ci-reports/sensitive-scan.txt
  echo "sensitive_scan=skipped_no_changed_files" >> "$REPORT_FILE"
fi

if [[ ${#failures[@]} -gt 0 ]]; then
  printf '\nFailures:\n' >> "$REPORT_FILE"
  printf '%s\n' "${failures[@]}" >> "$REPORT_FILE"
  printf 'Docs boundary check failed:\n' >&2
  printf '%s\n' "${failures[@]}" >&2
  exit 1
fi

echo "Docs boundary check passed." | tee -a "$REPORT_FILE"
