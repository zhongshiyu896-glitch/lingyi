# TASK-Z029B-15-PREP-CAND002-FAILURE-DIAG 失败只读定位报告

## 结论

- task_id: TASK-Z029B-15-PREP-CAND002-FAILURE-DIAG
- source_task: TASK-Z029B-14-IMPL
- candidate_id: Z029-CAND-002
- current_head: a487919d62f8838d683f50472bf09b8235d7da93
- cached_empty: true
- `git diff --check`: PASS
- B14 result: FAIL
- B14 command_run_count: 1
- B14 pytest_summary: `12 failed, 2 passed, 25 warnings in 1.19s`
- target_test_dirty_diff: false
- failed_cases_count: 12
- failed_pattern: `_create_confirmed_statement` confirm step expected `200`, observed `409`
- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: `07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py`
- recommended_next_task: TASK-Z029B-16-FIX-CAND002
- run_this_task: false

## Failed Cases

- test_failed_with_future_retry_is_not_claimed: expected confirm status 200, observed 409
- test_pending_or_failed_due_can_be_claimed: expected confirm status 200, observed 409
- test_pending_or_failed_with_future_retry_is_not_claimed: expected confirm status 200, observed 409
- test_stale_id_with_expired_processing_lease_can_be_claimed: expected confirm status 200, observed 409
- test_stale_id_with_unexpired_processing_lease_is_not_claimed: expected confirm status 200, observed 409
- test_worker_dry_run_does_not_call_erpnext_or_mutate_outbox: expected confirm status 200, observed 409
- test_worker_failed_outbox_reaches_dead_after_max_attempts: expected confirm status 200, observed 409
- test_worker_fails_when_erpnext_returns_non_draft_docstatus: expected confirm status 200, observed 409
- test_worker_processes_outbox_and_updates_statement_status: expected confirm status 200, observed 409
- test_worker_skips_erp_calls_when_statement_already_payable_draft_created: expected confirm status 200, observed 409
- test_worker_skips_erp_calls_when_statement_cancelled: expected confirm status 200, observed 409
- test_worker_skips_erp_calls_when_statement_draft: expected confirm status 200, observed 409

## Source Evidence

- `07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py`
- `07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
- `07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py`
- `07_后端/lingyi_service/app/models/factory_statement.py`
- `07_后端/lingyi_service/app/core/error_codes.py`
- source_evidence_missing: []

## 生命周期门禁

- stage_performed: false
- commit_performed: false
- push_performed: false
- tag_performed: false
- pr_performed: false
- release_performed: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false

本轮只做只读失败定位与修复边界冻结，未运行测试、未修复、未重跑。
