# TASK-Z028B-40-FIX-CAND005 修复报告

## Scope

- candidate_id: `Z028-CAND-005`
- source_failure_task: `TASK-Z028B-39-PREP-CAND005-FAILURE-DIAG`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`

## Change

- 仅修改允许测试文件 `07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`。
- 为 warehouse stock-entry draft worker 测试补齐当前 schema/local gate 所需 payload 字段：`source_ref`、`warehouse`、`item_code`、`operation`、`quantity`、`business_date`、`status_action`、`scenario_tag`。
- 为 create/cancel 请求补齐 `X-Request-ID` carrier，使测试请求与当前本地 warehouse write gate 合同一致。
- 保留 5 个 draft 创建路径的 `201` 成功分支断言；未使用 skip/xfail，未删除测试用例，未弱化状态码断言。

## Validation

- command: `.venv/bin/python -m pytest tests/test_warehouse_stock_entry_worker.py -q`
- workdir: `07_后端/lingyi_service`
- command_run_count: `1`
- exit_code: `0`
- result: `PASS`
- pytest_summary: `5 passed, 1 warning in 1.10s`
- stdout_log: `03_需求与设计/02_开发计划/task_z028b_40_cand005_fix_stdout.txt`

## Gates

- cached_empty: `true`
- historical_dirty_forbidden_staged: `[]`
- backend_app_changed: `false`
- frontend_changed: `false`
- unrelated_tests_changed: `false`
- stage/commit/push/tag/PR/release: `false`
- remote_lifecycle_parked: `true`
- production_readback_ready/go_live_ready/project_completion_claimed: `false`
