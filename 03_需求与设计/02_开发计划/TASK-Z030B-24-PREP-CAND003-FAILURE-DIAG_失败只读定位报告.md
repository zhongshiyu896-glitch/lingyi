# TASK-Z030B-24-PREP-CAND003-FAILURE-DIAG 失败只读定位报告

- task_id: TASK-Z030B-24-PREP-CAND003-FAILURE-DIAG
- role: B Engineer
- candidate_id: Z030-CAND-003
- current_head: `7cbebc82d57a4b576e501236457e3a969705f625`
- cached_empty: true
- git diff --check: PASS

## B23 Evidence 核对

- result: FAIL
- command_run_count: 1
- pytest_summary: `9 failed, 1 warning in 1.06s`
- target_test_dirty_diff: false
- target test 当前 dirty diff: false

## 失败模式

9 个失败均在原目标业务分支前返回 `422`。目标测试 payload 只提供旧字段组合，如 `idempotency_key`、`warehouse`、`materials`；当前 `IssueMaterialRequest` 继承 `SubcontractWriteCarrierBase`，要求写入 carrier 字段：

- `request_id`
- `idempotency_key`
- `scenario_tag`
- `source_ref`
- `subcontract_ref`
- `supplier_ref`
- `work_order_ref`
- `operation`
- `item_code`
- `quantity`
- `status_action`

只读证据支持分类为 `TEST_CONTRACT_UPDATE_ALLOWED`，允许修复文件仅限目标测试。

## 冻结修复边界

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_issue_outbox.py`
- recommended_next_task: `TASK-Z030B-25-FIX-CAND003`
- run_this_task: false
- source_evidence_missing: `[]`
- historical_dirty_forbidden_staged: `[]`
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码、测试、stdout 或 result，未 stage/commit/push/tag/PR/release。
