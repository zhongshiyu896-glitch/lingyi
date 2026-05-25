# TASK-Z030B-34-FIX-CAND004 subcontract_receive_outbox测试合同修复报告

## 执行边界

- candidate_id: `Z030-CAND-004`
- source_task: `TASK-Z030B-33-PREP-CAND004-FAILURE-DIAG`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py`
- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_receive_outbox.py -q`
- command_run_count: 1
- 未运行其他 pytest/npm/browser/build/typecheck/verify。
- 未 stage/commit/push/tag/PR/release。

## 修改摘要

- 仅修改授权目标测试文件与本轮 B34 evidence 产物。
- 在 receive 测试 payload 中补齐当前 carrier/schema gate 所需字段：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`subcontract_ref`、`supplier_ref`、`work_order_ref`、`operation`、`item_code`、`quantity`、`status_action`。
- 为 receive 请求补齐匹配的 `X-Request-ID` header。
- 保留原 `200/403/409/503` 显式业务状态断言；未新增 skip/xfail；未删除用例；未改成任意 2xx/4xx 弱断言。

## 验证结果

- exit_code: 1
- result: FAIL
- pytest_summary: `2 failed, 13 passed, 41 warnings in 1.15s`
- stdout: `03_需求与设计/02_开发计划/task_z030b_34_cand004_fix_stdout.txt`

## 剩余失败

- `test_receive_creates_receipt_rows_and_pending_outbox`
  - expected: `data["sync_status"] == "pending"`
  - observed: `data["sync_status"] == "succeeded"`
- `test_receive_returns_outbox_without_fake_stock_entry_name`
  - expected: `payload["stock_entry_name"] is None`
  - observed: `LOCAL-RECEIPT-SRB-1-20260525121250222151`

## 门禁状态

- cached_empty: true
- git_diff_check: PASS
- payload_carrier_contract_addressed: true
- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- shared_log_changed: false
- candidate_pool_changed: false
- unrelated_tests_changed: false
- rerun_performed: false
- stop_on_fail: true
