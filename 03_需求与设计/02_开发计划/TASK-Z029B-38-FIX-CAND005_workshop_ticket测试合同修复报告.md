# TASK-Z029B-38-FIX-CAND005 workshop_ticket 测试合同修复报告

## 执行边界

- task_id: `TASK-Z029B-38-FIX-CAND005`
- role: `B Engineer`
- candidate_id: `Z029-CAND-005`
- source task: `TASK-Z029B-37-PREP-CAND005-FAILURE-DIAG`
- current HEAD: `99434f1b9eacf47f75120c1144181a2004c10073`
- allowed fix file: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_workshop_ticket.py -q`
- command_run_count: 1

## 修复内容

仅修改目标测试文件：

- `07_后端/lingyi_service/tests/test_workshop_ticket.py`

修复范围：

- 将测试环境切到当前本地 workshop write gate 允许的 development/local DB 标识。
- 为 register/reversal payload helper 补齐 `scenario_tag`、`idempotency_key`、`source_ref`、`operation`、`operator_id`、`batch_no` 等当前 schema/local gate carrier 字段。
- 为每次请求生成与 payload carrier 一致的 `X-Request-ID`。
- 保留原测试的显式 `200/400/409` 断言；未新增 skip/xfail；未删除用例；未改成任意 2xx/4xx 弱断言。

## 单文件验证结果

- exit_code: 1
- result: FAIL
- pytest_summary: `11 failed, 4 passed, 65 warnings in 1.20s`
- stdout: `03_需求与设计/02_开发计划/task_z029b_38_cand005_fix_stdout.txt`

剩余失败用例：

- `test_company_b_job_card_cannot_use_company_a_item_wage_rate`
- `test_register_employee_invalid_returns_400`
- `test_register_job_card_not_found_returns_400`
- `test_register_job_card_status_invalid_returns_409`
- `test_register_process_mismatch_returns_400`
- `test_register_ticket_success_and_wage_amount`
- `test_register_wage_rate_not_found_returns_400`
- `test_ticket_register_does_not_match_empty_company_item_rate`
- `test_ticket_register_does_not_match_item_rate_with_null_company`
- `test_ticket_register_empty_company_legacy_candidate_returns_scope_required`
- `test_ticket_register_fails_when_only_legacy_null_company_rate_exists`

按任务边界，pytest FAIL 后已停止，未继续修复，未重跑。

## Gate 复核

- `git diff --cached --name-only`: empty
- `git diff --check`: PASS
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready/go_live_ready/project_completion_claimed: false
