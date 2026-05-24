# TASK-Z022B-37-PREP-CAND004-FAILURE-DIAG

## Scope

- Role: B Engineer
- Candidate: Z022-CAND-004
- Source task: TASK-Z022B-36-IMPL-CAND004-FIX1
- Action: quality-confirm-baseline 失败只读定位与下一步边界冻结
- Pytest this task: not run
- Code/test edit this task: not performed
- Stage/commit/push: not performed

## B36 Evidence Readback

- Command: `.venv/bin/python -m pytest tests/test_quality_confirm_baseline.py -q`
- Result: FAIL
- Exit code: 1
- Pytest summary: `2 failed, 1 warning in 1.16s`
- Failed cases:
  - `tests/test_quality_confirm_baseline.py::QualityConfirmBaselineTest::test_confirm_draft_success`: expected `200`, actual `422`
  - `tests/test_quality_confirm_baseline.py::QualityConfirmBaselineTest::test_confirm_on_confirmed_or_cancelled_returns_409`: expected `409`, actual `422`
- Missing fields:
  - `request_id`
  - `idempotency_key`
  - `scenario_tag`
  - `source_ref`
  - `inspection_ref`
  - `source_type`
  - `item_code`
  - `operation`
  - `result`

## Read-Only Diagnosis

The current tests post only `remark` to the confirm endpoint:

- `07_后端/lingyi_service/tests/test_quality_confirm_baseline.py:40-44`
- `07_后端/lingyi_service/tests/test_quality_confirm_baseline.py:96-105`

The confirm endpoint binds the request body to `QualityInspectionConfirmRequest` before entering the handler body:

- `07_后端/lingyi_service/app/routers/quality.py:790-794`

`QualityInspectionConfirmRequest` currently requires these body fields:

- `request_id`
- `idempotency_key`
- `scenario_tag`
- `source_ref`
- `inspection_ref`
- `source_type`
- `item_code`
- `operation`
- `result`

Schema source:

- `07_后端/lingyi_service/app/schemas/quality.py:94-106`

Therefore the `422` is caused by request body schema validation before permission, status, or service branch logic can run. This is a test payload contract drift, not evidence of a business source defect.

## Boundary Decision

- Failure classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file:
  - `07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
- Recommended next task:
  - `TASK-Z022B-38-FIX-CAND004-SCHEMA-FIELDS`
- Recommended command after the next fix:
  - `.venv/bin/python -m pytest tests/test_quality_confirm_baseline.py -q`
- This task did not run pytest and did not edit code.

## Validation Summary

- Current HEAD confirmed as `e4efb57410ec0643153741fc7260c40b0e1f536e`
- Cached area confirmed empty before writing B37 evidence.
- `test_quality_confirm_baseline.py` was not dirty before this task.
- Quality confirm related backend app files were not dirty before this task.
- Existing backend app dirty diff is unrelated report/catalog work:
  - `07_后端/lingyi_service/app/schemas/report.py`
  - `07_后端/lingyi_service/app/services/report_catalog_service.py`
  - `07_后端/lingyi_service/app/services/system_config_catalog_service.py`
- No `skip` or `xfail` evidence was found in `test_quality_confirm_baseline.py`.

## Forbidden Actions

- pytest/npm/browser/build/typecheck/verify: not run
- Product code edits: not performed
- Backend app edits: not performed
- Test edits: not performed
- Existing artifact edits: not performed
- Engineer shared log edit: not performed
- Stage/commit/push: not performed
- Reset/checkout/cleanup: not performed
- PR/tag/release: not performed
- Production account / ERPNext production / real business write: not performed
- Parked blockers released: not performed
- Project completion claimed: not performed
