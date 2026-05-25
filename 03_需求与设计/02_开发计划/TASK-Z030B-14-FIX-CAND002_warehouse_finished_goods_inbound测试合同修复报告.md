# TASK-Z030B-14-FIX-CAND002 测试合同修复报告

## 修复范围

- candidate_id: Z030-CAND-002
- source task: TASK-Z030B-13-PREP-CAND002-FAILURE-DIAG
- allowed fix file: 07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py
- changed_files:
  - 07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py
  - 03_需求与设计/02_开发计划/TASK-Z030B-14-FIX-CAND002_warehouse_finished_goods_inbound测试合同修复报告.md
  - 03_需求与设计/02_开发计划/task_z030b_14_cand002_fix_result.json
  - 03_需求与设计/02_开发计划/task_z030b_14_cand002_fix_result.tsv
  - 03_需求与设计/02_开发计划/task_z030b_14_cand002_fix_stdout.txt

## 字段补齐

- required_fields_addressed:
  - source_ref
  - warehouse
  - item_code
  - operation
  - quantity
  - business_date
  - status_action
  - scenario_tag

## 执行结果

- workdir: 07_后端/lingyi_service
- command: `.venv/bin/python -m pytest tests/test_warehouse_finished_goods_inbound.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: 3 failed, 2 passed, 1 warning in 1.02s
- stdout path: 03_需求与设计/02_开发计划/task_z030b_14_cand002_fix_stdout.txt

## 断言保持

- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- 目标测试仍保留原 `201/400` 显式状态断言。

## 执行后核对

- cached_empty: true
- git diff --check: PASS
- backend_app_changed: false
- frontend_changed: false
- shared_log_changed: false
- unrelated_tests_changed: false
- fix_attempt_after_failure: false
- rerun_performed: false

## 禁止动作

- 未继续修复，未重跑 pytest。
- 未运行其他测试/build/typecheck/npm/browser/verify。
- 未 stage/commit/push/tag/PR/release。
- 未 cleanup/reset/checkout/stash。

## Gate 状态

- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
- B14 artifacts staged: false
