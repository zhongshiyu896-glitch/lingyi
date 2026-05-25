# TASK-Z032B-39-PREP-CAND004-SECOND-FAILURE-DIAG 二次失败定位边界报告

## 基本信息

- 任务: TASK-Z032B-39-PREP-CAND004-SECOND-FAILURE-DIAG
- 角色: B Engineer
- 候选: Z032-CAND-004
- 来源任务: TASK-Z032B-38-FIX-CAND004
- 当前 HEAD: aedc2d39cca4d065a028ce42e325de17490d95b6
- cached 状态: 为空
- git diff --check: PASS
- 本轮执行类型: 只读失败定位与下一步边界冻结
- 本轮未运行 pytest/npm/browser/build/typecheck/verify
- 本轮未 stage/commit/push/tag/PR/release

## 已核对证据

- B35 boundary 已存在并冻结 Z032-CAND-004 readonly pytest 边界。
- B36 result/stdout/report/TSV 已读取。
- B37 failure boundary 已读取。
- B38 fix result/stdout/report/TSV 已读取。
- B38 result 为 FAIL，command_run_count=1。
- B38 pytest summary 为 `3 failed, 1 passed, 31 warnings in 1.01s`。
- B38 已记录:
  - register_payload_header_contract_addressed=true
  - business_200_assertions_preserved=true
  - assertions_weakened=false
  - skip_xfail_deleted_cases=false
- 当前目标测试 dirty diff 仅限:
  - `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- source evidence 全部存在，source_evidence_missing=[]。
- historical dirty forbidden paths 未 staged。

## 剩余失败用例

1. `test_service_account_forbidden_marks_failed_without_losing_local_ticket`
   - observed: `result.processed == 0`
   - expected: `result.processed >= 1`
   - 差异摘要: register 阶段已进入 200 分支，但 worker 未处理任何 outbox row，导致后续 forbidden 业务断言未进入。

2. `test_worker_failure_can_retry_after_manual_sync_enqueue`
   - observed: `fail_result.processed == 0`
   - expected: `fail_result.processed >= 1`
   - 差异摘要: register 阶段已进入 200 分支，但 worker 首次失败路径未 claim/process outbox row，阻断 retry 场景。

3. `test_worker_success_marks_outbox_succeeded_and_ticket_synced`
   - observed: `result.processed == 0`
   - expected: `result.processed >= 1`
   - 差异摘要: register 阶段已进入 200 分支，但 worker success 路径未 claim/process outbox row，阻断 ticket synced 业务断言。

## 失败模式

B38 已修正旧 register payload/header 合同导致的 422 前置阻断，且保留了显式 200 业务断言。剩余失败集中在 worker `run_once` 未处理新建或手工入队 outbox：三个用例均 observed `processed=0`，expected `processed>=1`。结合 source evidence，`run_once` 依赖 due rows 与 outbox claim 结果才会递增 processed，因此当前证据支持继续在目标测试内调整 fixture/payload/header/mock/断言合同或本地 outbox 可处理状态，使测试进入原 200 后的 worker 业务分支。

## 分类与下一步边界

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- next_task: TASK-Z032B-40-FIX-CAND004-SECOND
- run_this_task: false

## Gate

- stage=false
- commit=false
- push=false
- tag=false
- PR=false
- release=false
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false

## 本轮产物状态

B39 report/json/tsv 为本轮新增证据产物，未 staged。
