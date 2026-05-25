# TASK-Z030B-23-IMPL CAND003 单文件验证报告

- task_id: TASK-Z030B-23-IMPL
- role: B Engineer
- candidate_id: Z030-CAND-003
- source_task: TASK-Z030B-22-PREP
- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_issue_outbox.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `9 failed, 1 warning in 1.06s`
- stdout_path: `03_需求与设计/02_开发计划/task_z030b_23_cand003_stdout.txt`

## 执行后核对

- cached_empty: true
- target_test_dirty_diff: false
- git diff --check: PASS
- fix_attempt: false
- rerun_performed: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false

## FAIL Evidence

失败摘要仅记录为 evidence，未诊断、未修复、未重跑。

- `SubcontractIssueOutboxTest.test_issue_material_blocked_scope_order_rejected`
- `SubcontractIssueOutboxTest.test_issue_material_creates_material_rows_and_pending_outbox`
- `SubcontractIssueOutboxTest.test_issue_material_does_not_call_erpnext_before_commit`
- `SubcontractIssueOutboxTest.test_issue_material_full_issue_idempotent_retry_does_not_check_remaining_qty_first`
- `SubcontractIssueOutboxTest.test_issue_material_full_issue_idempotent_retry_returns_existing_outbox`
- `SubcontractIssueOutboxTest.test_issue_material_rejects_material_not_in_bom`
- `SubcontractIssueOutboxTest.test_issue_material_rejects_qty_exceeding_remaining_required_qty`
- `SubcontractIssueOutboxTest.test_issue_material_returns_outbox_without_fake_stock_entry_name`
- `SubcontractIssueOutboxTest.test_issue_material_settled_order_rejected`
