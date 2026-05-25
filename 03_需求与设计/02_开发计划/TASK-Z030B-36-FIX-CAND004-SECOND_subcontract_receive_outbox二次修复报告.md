# TASK-Z030B-36-FIX-CAND004-SECOND subcontract_receive_outbox二次修复报告

## 执行边界

- candidate_id: `Z030-CAND-004`
- source_task: `TASK-Z030B-35-PREP-CAND004-SECOND-FAILURE-DIAG`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py`
- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_receive_outbox.py -q`
- command_run_count: 1
- 未运行其他 pytest/npm/browser/build/typecheck/verify。
- 未 stage/commit/push/tag/PR/release。

## 修改摘要

- 仅修改授权目标测试文件与本轮 B36 evidence 产物。
- 将剩余 `pending`/`None` 旧 outbox 断言更新为当前 local-dev receive 合同：
  - `sync_status == "succeeded"`
  - `stock_entry_name` 使用 `LOCAL-RECEIPT-SRB-1-` 前缀
- 保留显式 `200/403/409/503` 业务状态断言。
- 未新增 skip/xfail；未删除用例；未改成任意 2xx/4xx 弱断言。

## 验证结果

- exit_code: 0
- result: PASS
- pytest_summary: `15 passed, 41 warnings in 1.15s`
- stdout: `03_需求与设计/02_开发计划/task_z030b_36_cand004_second_fix_stdout.txt`

## 门禁状态

- cached_empty: true
- git_diff_check: PASS
- status_contract_updated: true
- stock_entry_name_contract_updated: true
- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- shared_log_changed: false
- candidate_pool_changed: false
- unrelated_tests_changed: false
