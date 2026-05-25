# TASK-Z032B-37-PREP-CAND004-FAILURE-DIAG 失败定位边界报告

## 基本信息

- task_id: TASK-Z032B-37-PREP-CAND004-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z032B-36-IMPL
- candidate_id: Z032-CAND-004
- current_head: aedc2d39cca4d065a028ce42e325de17490d95b6

## Git 状态核对

- cached_empty: true
- git_diff_check: PASS
- target_test_dirty_diff: false
- historical_dirty_forbidden_staged: []

## B36 结果核对

- result: FAIL
- command_run_count: 1
- pytest_summary: `4 failed, 1 warning in 0.98s`
- stdout_path: `03_需求与设计/02_开发计划/task_z032b_36_cand004_stdout.txt`

## 失败用例

- `test_register_creates_pending_outbox_without_inline_erp_sync`
  - observed: HTTP 422
  - expected: HTTP 200
- `test_service_account_forbidden_marks_failed_without_losing_local_ticket`
  - observed: HTTP 422
  - expected: HTTP 200
- `test_worker_failure_can_retry_after_manual_sync_enqueue`
  - observed: HTTP 422
  - expected: HTTP 200
- `test_worker_success_marks_outbox_succeeded_and_ticket_synced`
  - observed: HTTP 422
  - expected: HTTP 200

## 失败模式

4 个失败均发生在 `/api/workshop/tickets/register` 注册调用前置阶段，旧测试 payload/header 未满足当前工票写入 carrier/schema 合同，导致 schema validation `422` 阻断原 job card outbox sync 业务分支。

## Source Evidence

- `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
- `07_后端/lingyi_service/app/models/workshop.py`
- `07_后端/lingyi_service/app/routers/workshop.py`
- source_evidence_missing: []

## 分类与下一步边界

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- next_task: TASK-Z032B-38-FIX-CAND004
- run_this_task: false

## 生命周期门禁

- stage: false
- commit: false
- push: false
- tag: false
- pr: false
- release: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false

## 本轮产物状态

- B37 report/json/tsv 未暂存
- 未运行 pytest/npm/browser/build/typecheck/verify
- 未修改代码、测试、stdout、result 或既有 evidence
- 未 stage/commit/push/tag/PR/release
