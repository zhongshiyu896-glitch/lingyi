# TASK-Z030B-32-IMPL CAND004 单文件验证报告

## 结论

- 状态：READY_FOR_REVIEW
- 候选：Z030-CAND-004
- source task：TASK-Z030B-31-PREP
- workdir：07_后端/lingyi_service
- command：.venv/bin/python -m pytest tests/test_subcontract_receive_outbox.py -q
- command_run_count：1
- exit_code：1
- result：FAIL
- pytest_summary：13 failed, 2 passed, 1 warning in 1.21s

## 失败用例摘要

- test_receive_blocked_scope_order_rejected
- test_receive_creates_receipt_rows_and_pending_outbox
- test_receive_does_not_call_erpnext_before_commit
- test_receive_forbidden_when_receipt_warehouse_not_allowed
- test_receive_idempotency_key_different_payload_returns_conflict
- test_receive_idempotent_retry_after_full_receipt_does_not_check_remaining_qty_first
- test_receive_idempotent_same_payload_returns_existing_result
- test_receive_permission_source_unavailable_fails_closed
- test_receive_rejects_draft_order
- test_receive_rejects_qty_exceeding_remaining_receivable_qty
- test_receive_returns_outbox_without_fake_stock_entry_name
- test_receive_settled_order_rejected
- test_receive_waiting_inspection_allows_additional_batch_receipt

## gate

- target_test_dirty_diff：false
- cached：空
- git diff --check：PASS
- fix_attempt：false
- rerun_performed：false

## 禁止动作

- pytest 重跑/其他测试/npm/browser/build/typecheck/verify：未执行
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle parked：true
- production readback/go-live/project completion：false
