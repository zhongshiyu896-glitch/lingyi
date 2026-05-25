# TASK-Z032B-26-PREP-CAND003-SECOND-FAILURE-DIAG 二次失败定位边界报告

## 任务边界

- Task: `TASK-Z032B-26-PREP-CAND003-SECOND-FAILURE-DIAG`
- Role: `B Engineer`
- Source task: `TASK-Z032B-25-FIX-CAND003`
- Candidate: `Z032-CAND-003`
- Operation: read-only second failure diagnosis and next boundary freeze
- Run this task: `false`

## 只读核对

- Current HEAD: `f1ee52224ea1a4615db30f51cb234eba023b1fb8`
- Cached: empty
- `git diff --check`: `PASS`
- B25 result: `FAIL`
- B25 command_run_count: `1`
- B25 pytest summary: `6 failed, 1 warning in 1.04s`
- Target test: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- Current target dirty diff limited to allowed file: `true`
- B25 business assertions preserved before diag: `true`
- Source evidence missing: `[]`
- Historical dirty forbidden staged scan: `[]`

## 剩余失败摘要

- Previous failed cases count: `6`
- Remaining failed cases count: `6`
- Failure pattern: all six tests now observe `409`, after B25 moved past the previous `422` schema validation gate, but still before the expected workshop batch business branches.
- Read-only evidence:
  - B25 target diff only changes request helper/payload construction in the target test.
  - Original explicit status assertions remain `500/503/200`.
  - Router source evidence shows local batch validation still raises `WORKSHOP_IDEMPOTENCY_CONFLICT` for request/carrier mismatches before permission, row processing, audit write, database write, or row-level failure handling.

## Remaining Failed Cases

- `test_audit_write_failed_returns_500_not_failed_items`: observed `409`, expected `500` and `AUDIT_WRITE_FAILED`.
- `test_database_write_failed_returns_500_not_failed_items`: observed `409`, expected `500` and `DATABASE_WRITE_FAILED`.
- `test_permission_source_unavailable_returns_503_not_failed_items`: observed `409`, expected `503` and `PERMISSION_SOURCE_UNAVAILABLE`.
- `test_row_business_error_can_enter_failed_items`: observed `409`, expected `200`, `code=0`, one success, one failed item with `WORKSHOP_INVALID_QTY`.
- `test_row_resource_forbidden_can_enter_failed_items_and_write_security_audit`: observed `409`, expected `200`, `code=0`, failed item `AUTH_FORBIDDEN`, and security audit write.
- `test_unknown_error_returns_500_not_failed_items`: observed `409`, expected `500` and `WORKSHOP_INTERNAL_ERROR`.

## Classification

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Rationale: current failures still point to target-test helper/payload/request carrier contract drift. The dirty diff is limited to the target test and can be continued inside the same file to reach the original business branches without backend app changes.
- Allowed fix file: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- Next task: `TASK-Z032B-27-FIX-CAND003-SECOND`

## Gates

- Stage/commit/push/tag/PR/release: `false`
- Remote lifecycle parked: `true`
- Production readback/go-live/project completion: `false`

## 本轮产物状态

- B26 report/json/tsv staged: `false`
