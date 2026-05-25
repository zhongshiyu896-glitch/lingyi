# TASK-Z029B-39-PREP-CAND005-SECOND-FAILURE-DIAG 二次失败只读定位报告

## 基本结论

- task_id: `TASK-Z029B-39-PREP-CAND005-SECOND-FAILURE-DIAG`
- role: `B Engineer`
- candidate_id: `Z029-CAND-005`
- source task: `TASK-Z029B-38-FIX-CAND005`
- current HEAD: `99434f1b9eacf47f75120c1144181a2004c10073`
- cached: empty
- `git diff --check`: PASS
- B38 result: FAIL
- B38 command_run_count: 1
- B38 pytest summary: `11 failed, 4 passed, 65 warnings in 1.20s`
- B38 assertions_weakened: false
- B38 skip_xfail_deleted_cases: false

## 当前目标测试 dirty diff

- target test: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- diff scope: B38 允许目标测试修改范围
- diff stat: `1 file changed, 113 insertions(+), 47 deletions(-)`
- 主要变更：development/local DB gate 环境、scenario tag/carrier helper、payload carrier 字段、按 payload 生成 `X-Request-ID`
- skip/xfail: none

## 剩余失败模式

B38 已消除 B36 的 `422` schema validation 失败，剩余失败进入当前 local synthetic workshop contract 后暴露为测试 fixture/expectation drift。

剩余失败用例：

- `test_company_b_job_card_cannot_use_company_a_item_wage_rate`: observed `200`, expected `400`
- `test_register_employee_invalid_returns_400`: observed `200`, expected `400`
- `test_register_job_card_not_found_returns_400`: observed `200`, expected `400`
- `test_register_job_card_status_invalid_returns_409`: observed `200`, expected `409`
- `test_register_process_mismatch_returns_400`: observed `200`, expected `400`
- `test_register_ticket_success_and_wage_amount`: observed `Decimal('100.0')`, expected `Decimal('50.000000')`
- `test_register_wage_rate_not_found_returns_400`: observed `200`, expected `400`
- `test_ticket_register_does_not_match_empty_company_item_rate`: observed `Decimal('1.0')`, expected `Decimal('0.500000')`
- `test_ticket_register_does_not_match_item_rate_with_null_company`: observed `Decimal('1.0')`, expected `Decimal('0.500000')`
- `test_ticket_register_empty_company_legacy_candidate_returns_scope_required`: observed `200`, expected `409`
- `test_ticket_register_fails_when_only_legacy_null_company_rate_exists`: observed `200`, expected `409`

## 只读证据

- `WorkshopService.resolve_job_card_resource` 在 `local_scenario_tag` 且 local synthetic context 开启时返回 synthetic resource，不再使用 ERP job-card mock 分支。
- `WorkshopService._require_employee` 在 `local_scenario_tag` 且 local synthetic context 开启时放行 synthetic employee。
- `WorkshopService._resolve_unit_wage` 在 `local_scenario_tag` 且 local synthetic context 开启时返回 `WORKSHOP_LOCAL_DEFAULT_UNIT_WAGE`，当前值为 `Decimal("1")`。
- B38 目标测试为了满足 local write gate 使用 `Z003-WORKSHOP-TICKET-20260412-001` scenario tag，因此剩余断言需要按当前 local synthetic 合同继续收敛。

## 边界冻结

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- recommended next task: `TASK-Z029B-40-FIX-CAND005-SECOND`
- run_this_task: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码/测试/stdout/result，未 stage/commit/push/tag/PR/release。
