# TASK-Z029B-36-IMPL CAND005 单文件验证报告

## 执行边界

- task_id: `TASK-Z029B-36-IMPL`
- role: `B Engineer`
- source_task: `TASK-Z029B-35-PREP`
- candidate_id: `Z029-CAND-005`
- current_head: `99434f1b9eacf47f75120c1144181a2004c10073`
- workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_workshop_ticket.py -q`
- command_run_count: `1`

## 验证结果

- exit_code: `1`
- result: `FAIL`
- pytest_summary: `15 failed, 1 warning in 1.11s`
- stdout_path: `03_需求与设计/02_开发计划/task_z029b_36_cand005_stdout.txt`
- target_test_path: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- target_test_dirty_diff: `false`
- cached_empty: `true`
- git_diff_check: `PASS`

## 失败用例

- `test_company_b_job_card_cannot_use_company_a_item_wage_rate`
- `test_register_employee_invalid_returns_400`
- `test_register_idempotency_conflict_returns_409`
- `test_register_idempotent_same_payload_returns_same_ticket`
- `test_register_invalid_qty_returns_400`
- `test_register_job_card_not_found_returns_400`
- `test_register_job_card_status_invalid_returns_409`
- `test_register_process_mismatch_returns_400`
- `test_register_ticket_success_and_wage_amount`
- `test_register_wage_rate_not_found_returns_400`
- `test_reversal_success_and_exceed_guard`
- `test_ticket_register_does_not_match_empty_company_item_rate`
- `test_ticket_register_does_not_match_item_rate_with_null_company`
- `test_ticket_register_empty_company_legacy_candidate_returns_scope_required`
- `test_ticket_register_fails_when_only_legacy_null_company_rate_exists`

## 禁止动作确认

- fix_attempt: `false`
- rerun_performed: `false`
- stage_performed: `false`
- commit_performed: `false`
- push_performed: `false`
- tag_performed: `false`
- pr_performed: `false`
- release_performed: `false`
- remote_lifecycle_parked: `true`
- production_readback_ready: `false`
- go_live_ready: `false`
- project_completion_claimed: `false`
