# TASK-Z028B-28-IMPL CAND004 单文件验证报告

## 结论

- selected_candidate: Z028-CAND-004
- command: `.venv/bin/python -m pytest tests/test_production_work_order_outbox.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: 6 failed, 10 passed, 30 warnings in 1.11s

## 失败摘要

6 个 create-work-order 用例在进入原目标成功或写失败分支前返回 409：

- `test_create_work_order_audit_write_failed_returns_audit_write_failed`: expected 500, observed 409
- `test_create_work_order_commit_failure_does_not_call_erpnext`: expected 500, observed 409
- `test_create_work_order_outbox_is_idempotent_for_same_plan`: expected 200, observed 409
- `test_create_work_order_returns_existing_pending_outbox_without_duplicate`: expected 200, observed 409
- `test_create_work_order_returns_existing_work_order_when_link_succeeded`: expected 200, observed 409
- `test_create_work_order_same_idempotency_different_payload_returns_conflict`: first request expected 200, observed 409

## 边界保持

- fix_attempt: false
- rerun_performed: false
- target_test_dirty_diff: false
- cached_empty: true
- historical_dirty_forbidden_staged: []

## 禁止动作

- stage/commit/push/tag/PR/release: false
- other tests/build/typecheck/npm/browser: false
- cleanup/reset/checkout/stash: false
