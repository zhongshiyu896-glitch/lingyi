# TASK-Z030B-12-IMPL CAND002 单文件验证报告

## 执行边界

- candidate_id: Z030-CAND-002
- source task: TASK-Z030B-11-PREP
- workdir: 07_后端/lingyi_service
- command: `.venv/bin/python -m pytest tests/test_warehouse_finished_goods_inbound.py -q`
- command_run_count: 1

## 执行结果

- exit_code: 1
- result: FAIL
- pytest_summary: 3 failed, 2 passed, 1 warning in 1.04s
- stdout path: 03_需求与设计/02_开发计划/task_z030b_12_cand002_stdout.txt

## 失败用例摘要

- `test_create_finished_goods_draft_candidate_disabled_fail_closed`
- `test_create_finished_goods_draft_fallback_mode`
- `test_create_finished_goods_draft_strict_alloc`

## 执行后核对

- target_test_dirty_diff: false
- cached_empty: true
- git diff --check: PASS
- fix_attempt: false
- rerun_performed: false

## 禁止动作

- 未修复代码/测试。
- 未重跑 pytest，未运行其他测试/build/typecheck/npm/browser/verify。
- 未 stage/commit/push/tag/PR/release。
- 未 cleanup/reset/checkout/stash。
- 未修改 B10/B11 产物或 candidate pool。

## Gate 状态

- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
- B12 artifacts staged: false
