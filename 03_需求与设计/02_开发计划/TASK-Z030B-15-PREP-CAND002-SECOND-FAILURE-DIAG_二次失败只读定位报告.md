# TASK-Z030B-15-PREP-CAND002-SECOND-FAILURE-DIAG 二次失败只读定位报告

## 前置核对

- current HEAD: c35ffbb2b19bff7633b3a14a89c3476cae39be1e
- cached empty: true
- git diff --check: PASS
- B14 result: FAIL
- B14 command_run_count: 1
- B14 pytest_summary: 3 failed, 2 passed, 1 warning in 1.02s
- B14 required_fields_addressed: source_ref, warehouse, item_code, operation, quantity, business_date, status_action, scenario_tag
- B14 assertions_weakened: false
- B14 skip_xfail_deleted_cases: false

## 剩余失败摘要

- remaining_failed_cases_count: 3
- observed status: 409
- error code: WAREHOUSE_IDEMPOTENCY_CONFLICT
- error message: scenario_tag 载体缺失或格式非法

## 剩余失败用例

- `test_create_finished_goods_draft_candidate_disabled_fail_closed`: observed 409, expected 400 fail-closed branch
- `test_create_finished_goods_draft_fallback_mode`: observed 409, expected 201 branch
- `test_create_finished_goods_draft_strict_alloc`: observed 409, expected 201 branch

## 只读证据

- B14 stdout 显示三处断言均从原 schema `422` 推进为 `409 WAREHOUSE_IDEMPOTENCY_CONFLICT`。
- `warehouse.py` carrier gate 会逐个检查 `payload.scenario_tag`, `payload.idempotency_key`, `payload.source_ref`, `payload.source_id` 是否包含合法 `Z003-WAREHOUSE-YYYYMMDD-NNN` scenario tag。
- 当前目标测试已新增 `scenario_tag` 和 request id helper，但 `_draft_payload` 中 `source_id`, `source_ref`, `idempotency_key` 仍未携带 scenario tag。
- source_evidence_missing: []

## 当前目标测试修改范围

- target_test_dirty_status: untracked_allowed_target_file
- dirty summary: B14 仅在目标测试内新增 local warehouse env、request-id helper、schema payload fields、POST request id headers，并保留 `201/400` 显式状态断言。

## 分类与下一步

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py
- recommended_next_task: TASK-Z030B-16-FIX-CAND002-SECOND
- run_this_task: false

## 禁止动作

- 未运行 pytest/npm/browser/build/typecheck/verify。
- 未修改代码/测试/stdout/result。
- 未 stage/commit/push/tag/PR/release。
- 未 cleanup/reset/checkout/stash。
- 未直接修复剩余失败。

## Gate 状态

- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
- B15 artifacts staged: false
