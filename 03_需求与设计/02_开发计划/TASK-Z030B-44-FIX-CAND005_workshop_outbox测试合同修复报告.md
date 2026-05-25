# TASK-Z030B-44-FIX-CAND005 workshop_outbox 测试合同修复报告

## 修复范围

- candidate id: `Z030-CAND-005`
- source task: `TASK-Z030B-43-PREP-CAND005-FAILURE-DIAG`
- allowed fix file: `07_后端/lingyi_service/tests/test_workshop_outbox.py`
- changed code/test file: `07_后端/lingyi_service/tests/test_workshop_outbox.py`

本轮只修复目标测试的请求 payload/carrier 合同：补齐 `scenario_tag`、`idempotency_key`、`batch_no`、`operation`，并为两个 500 分支用例提供与 payload 匹配的 `X-Request-ID`。

## 验证命令

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_workshop_outbox.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: `11 passed, 17 warnings in 1.05s`
- stdout: `03_需求与设计/02_开发计划/task_z030b_44_cand005_fix_stdout.txt`

## 断言保持

- `response.status_code == 500`: 保留
- `DATABASE_WRITE_FAILED`: 保留
- `AUDIT_WRITE_FAILED`: 保留
- assertions_weakened: false
- skip_xfail_deleted_cases: false

## 执行后核对

- cached: 空
- `git diff --check`: PASS
- backend_app_changed: false
- frontend_changed: false
- shared_log_changed: false
- candidate_pool_changed: false
- other_tests_changed: false
- unexpected_tracked_dirty_excluding_allowed_and_historical: []
- backend_app_dirty_excluding_historical: []
- frontend_dirty_excluding_historical: []
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready/go_live_ready/project_completion_claimed: false
