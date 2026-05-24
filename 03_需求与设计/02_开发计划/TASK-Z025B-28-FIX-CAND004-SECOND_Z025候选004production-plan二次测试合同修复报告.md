# TASK-Z025B-28-FIX-CAND004-SECOND Z025候选004 production-plan 二次测试合同修复报告

## Scope

- selected_candidate: Z025-CAND-004
- source_task: TASK-Z025B-27-PREP-CAND004-SECOND-FAILURE-DIAG
- fixed_file: `07_后端/lingyi_service/tests/test_production_plan.py`
- failure_classification: TEST_CONTRACT_UPDATE_ALLOWED

## Fix

只修改目标测试文件，处理 B27 定位的 4 个剩余合同问题：

- 将 `PRODUCTION_SO_ITEM_NOT_FOUND` 的状态码断言对齐到当前 error code 映射的 404。
- 在测试 `setUp` 中清理 `LyProductionWorkOrderLink`，避免跨用例 stale `plan_id` 状态导致 `outbox_id=0` 与唯一约束冲突。
- 将 frozen reason 的历史 `TASK-015E` 字面量断言对齐到当前 `受控写门禁` 文案，同时保留 `sync-job-cards` 与 `create-work-order` 核心冻结语义断言。

未修改 backend app、前端或其他测试文件。未 skip、xfail 或删除用例。

## Validation

- command: `.venv/bin/python -m pytest tests/test_production_plan.py -q`
- workdir: `07_后端/lingyi_service`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: `17 passed, 18 warnings in 1.15s`
- stdout_log: `03_需求与设计/02_开发计划/task_z025b_28_cand004_second_fix_stdout.txt`

## Forbidden Actions

- backend app edits: NO
- frontend edits: NO
- unrelated tests edits: NO
- tests/build/typecheck/npm/browser beyond allowed command: NO
- stage/commit/push/tag/pr/release: NO
- reset/checkout/stash/cleanup: NO
- production readback/go-live/project completion: NO
