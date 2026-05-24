# TASK-Z022B-38-FIX-CAND004-SCHEMA-FIELDS

## Scope

- Role: B Engineer
- Candidate: Z022-CAND-004
- Source task: TASK-Z022B-37-PREP-CAND004-FAILURE-DIAG
- Fixed file: `07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
- Business source edit: not performed
- Backend app edit: not performed
- Frontend edit: not performed
- Stage/commit/push: not performed

## Fix

The confirm baseline tests now build request bodies that satisfy `QualityInspectionConfirmRequest` and current router carrier checks.

Added test-only helpers:

- `_local_gate_env()` for isolated local gate environment:
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- `_carrier_code()` and `_request_id()` for confirm `QI-F` carrier IDs.
- `_confirm_payload()` to keep payload and `X-Request-ID` consistent.

The request payloads now include:

- `request_id`
- `idempotency_key`
- `scenario_tag`
- `source_ref`
- `inspection_ref`
- `source_type`
- `source_doc`
- `item_code`
- `operation`
- `result`
- `remark`

Valid scenario tags used:

- `Z003-QUALITY-INSPECTION-20260524-004`
- `Z003-QUALITY-INSPECTION-20260524-005`
- `Z003-QUALITY-INSPECTION-20260524-006`

The original assertion semantics are preserved:

- Draft confirm success still asserts `200`.
- Confirmed/cancelled confirm still assert `409` and `QUALITY_INVALID_STATUS`.
- No `skip`, `xfail`, deleted cases, or weakened 2xx/4xx assertion was added.

## Validation

- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Command: `.venv/bin/python -m pytest tests/test_quality_confirm_baseline.py -q`
- Command run count: 1
- Exit code: 0
- Result: PASS
- Pytest summary: `2 passed, 2 warnings in 1.09s`
- Stdout log: `03_需求与设计/02_开发计划/task_z022b_38_cand004_schema_fields_fix_stdout.txt`

## Forbidden Actions

- Other pytest/full pytest: not run
- npm/browser/build/typecheck/verify: not run
- Product code edits: not performed
- Backend app edits: not performed
- Frontend edits: not performed
- Unrelated tests edits: not performed
- Existing artifact edits: not performed
- Engineer shared log edit: not performed
- Stage/commit/push: not performed
- Reset/checkout/cleanup: not performed
- PR/tag/release: not performed
- Production account / ERPNext production / real business write: not performed
- Parked blockers released: not performed
- Project completion claimed: not performed
