# TASK-Z030B-13-PREP-CAND002-FAILURE-DIAG 失败只读定位报告

## 前置核对

- current HEAD: c35ffbb2b19bff7633b3a14a89c3476cae39be1e
- cached empty: true
- git diff --check: PASS
- B12 result: FAIL
- B12 command_run_count: 1
- B12 pytest_summary: 3 failed, 2 passed, 1 warning in 1.04s
- target_test_dirty_diff: false

## 失败摘要

- failed_cases_count: 3
- observed status: 422
- intended branches: two create draft `201` branches and one candidate-disabled fail-closed branch
- missing schema fields:
  - source_ref
  - warehouse
  - item_code
  - operation
  - quantity
  - business_date
  - status_action
  - scenario_tag

## 失败用例

- `test_create_finished_goods_draft_candidate_disabled_fail_closed`: observed 422, expected 400 fail-closed branch
- `test_create_finished_goods_draft_fallback_mode`: observed 422, expected 201 branch
- `test_create_finished_goods_draft_strict_alloc`: observed 422, expected 201 branch

## 只读证据

- target payload helper `test_warehouse_finished_goods_inbound.py` lines 85-106 lacks the current required carrier/schema fields.
- `WarehouseStockEntryDraftCreateRequest` requires `source_ref`, `warehouse`, `item_code`, `operation`, `quantity`, `business_date`, `status_action`, and `scenario_tag`.
- `/api/warehouse/stock-entry-drafts` binds request body to `WarehouseStockEntryDraftCreateRequest` before entering business branch logic.
- source_evidence_missing: []

## 分类与下一步

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py
- recommended_next_task: TASK-Z030B-14-FIX-CAND002
- run_this_task: false

## 禁止动作

- 未运行 pytest/npm/browser/build/typecheck/verify。
- 未修改代码/测试/stdout/result。
- 未 stage/commit/push/tag/PR/release。
- 未 cleanup/reset/checkout/stash。
- 未直接修复失败。

## Gate 状态

- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
- B13 artifacts staged: false
