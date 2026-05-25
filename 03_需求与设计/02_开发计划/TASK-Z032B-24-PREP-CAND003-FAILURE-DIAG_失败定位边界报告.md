# TASK-Z032B-24-PREP-CAND003-FAILURE-DIAG 失败定位边界报告

## 任务边界

- Task: `TASK-Z032B-24-PREP-CAND003-FAILURE-DIAG`
- Role: `B Engineer`
- Source task: `TASK-Z032B-23-IMPL`
- Candidate: `Z032-CAND-003`
- Operation: read-only failure diagnosis and next boundary freeze
- Run this task: `false`

## 只读核对

- Current HEAD: `f1ee52224ea1a4615db30f51cb234eba023b1fb8`
- Cached: empty
- `git diff --check`: `PASS`
- B23 result: `FAIL`
- B23 command_run_count: `1`
- B23 pytest summary: `6 failed, 1 warning in 1.04s`
- Target test: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- Target test dirty diff: `false`
- Source evidence missing: `[]`
- Historical dirty forbidden staged scan: `[]`

## 失败摘要

- Failed cases count: `6`
- Failure pattern: all six tests observed `422` before reaching the expected workshop batch business branches.
- Read-only evidence:
  - Target test `_row()` supplies legacy row fields only and request bodies use `{"tickets": [...]}`.
  - Current `WorkshopTicketBatchRequest` requires top-level carrier fields including `scenario_tag`, `idempotency_key`, `source_ref`, `batch_no`, `ticket_key`, and `job_card`.
  - Current `WorkshopTicketBatchItem` requires row carrier fields including `scenario_tag`, `idempotency_key`, `source_ref`, `operation`, and `batch_no`.
  - Router validates those carriers before permission, row processing, audit write, database write, and row-level failure handling.

## Failed Cases

- `test_audit_write_failed_returns_500_not_failed_items`: observed `422`, expected `500` and `AUDIT_WRITE_FAILED`.
- `test_database_write_failed_returns_500_not_failed_items`: observed `422`, expected `500` and `DATABASE_WRITE_FAILED`.
- `test_permission_source_unavailable_returns_503_not_failed_items`: observed `422`, expected `503` and `PERMISSION_SOURCE_UNAVAILABLE`.
- `test_row_business_error_can_enter_failed_items`: observed `422`, expected `200`, `code=0`, one success, one failed item with `WORKSHOP_INVALID_QTY`.
- `test_row_resource_forbidden_can_enter_failed_items_and_write_security_audit`: observed `422`, expected `200`, `code=0`, failed item `AUTH_FORBIDDEN`, and security audit write.
- `test_unknown_error_returns_500_not_failed_items`: observed `422`, expected `500` and `WORKSHOP_INTERNAL_ERROR`.

## Classification

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Rationale: the failure is consistent with target-test fixture/payload contract drift against current request schemas and local carrier gate, and can be addressed within the target test without modifying backend app code.
- Allowed fix file: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- Next task: `TASK-Z032B-25-FIX-CAND003`

## Gates

- Stage/commit/push/tag/PR/release: `false`
- Remote lifecycle parked: `true`
- Production readback/go-live/project completion: `false`

## 本轮产物状态

- B24 report/json/tsv staged: `false`
