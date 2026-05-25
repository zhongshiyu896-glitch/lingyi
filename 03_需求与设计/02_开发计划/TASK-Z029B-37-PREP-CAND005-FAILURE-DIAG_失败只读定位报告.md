# TASK-Z029B-37-PREP-CAND005-FAILURE-DIAG 失败只读定位报告

## 基本结论

- task_id: `TASK-Z029B-37-PREP-CAND005-FAILURE-DIAG`
- role: `B Engineer`
- candidate_id: `Z029-CAND-005`
- source task: `TASK-Z029B-36-IMPL`
- current HEAD: `99434f1b9eacf47f75120c1144181a2004c10073`
- cached: empty
- `git diff --check`: PASS
- target test: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- target test dirty diff: false
- B36 command_run_count: 1
- B36 result: FAIL
- B36 pytest summary: `15 failed, 1 warning in 1.11s`

## 失败模式

B36 stdout 显示 15 个失败用例均在目标业务分支前返回 `422`，而用例原目标覆盖 `200` 成功分支、`400` 合同校验分支与 `409` 冲突分支。

失败用例：

- `test_company_b_job_card_cannot_use_company_a_item_wage_rate`: observed `422`, expected `400`
- `test_register_employee_invalid_returns_400`: observed `422`, expected `400`
- `test_register_idempotency_conflict_returns_409`: observed `422`, expected `409`
- `test_register_idempotent_same_payload_returns_same_ticket`: observed `422`, expected `200`
- `test_register_invalid_qty_returns_400`: observed `422`, expected `400`
- `test_register_job_card_not_found_returns_400`: observed `422`, expected `400`
- `test_register_job_card_status_invalid_returns_409`: observed `422`, expected `409`
- `test_register_process_mismatch_returns_400`: observed `422`, expected `400`
- `test_register_ticket_success_and_wage_amount`: observed `422`, expected `200`
- `test_register_wage_rate_not_found_returns_400`: observed `422`, expected `400`
- `test_reversal_success_and_exceed_guard`: observed `422`, expected `200/409`
- `test_ticket_register_does_not_match_empty_company_item_rate`: observed `422`, expected `200`
- `test_ticket_register_does_not_match_item_rate_with_null_company`: observed `422`, expected `200`
- `test_ticket_register_empty_company_legacy_candidate_returns_scope_required`: observed `422`, expected `409`
- `test_ticket_register_fails_when_only_legacy_null_company_rate_exists`: observed `422`, expected `409`

## 只读证据

- `WorkshopTicketRegisterRequest` 当前要求 `scenario_tag`、`idempotency_key`、`source_ref`、`batch_no` 等 carrier/schema 字段。
- `WorkshopTicketReversalRequest` 当前要求 `scenario_tag`、`idempotency_key`、`source_ref`、`batch_no` 等 carrier/schema 字段。
- 目标测试 helper `_register_payload` 仍使用旧载体，缺少 `scenario_tag`、`idempotency_key`、`batch_no`，且 `ticket_key/source_ref` 未按当前本地 gate 的 scenario tag carrier 一致性组织。
- 目标测试 helper `_reversal_payload` 缺少 `scenario_tag`、`idempotency_key`、`source_ref`、`batch_no`。
- workshop router 的本地写入 gate 会检查 `scenario_tag`、`idempotency_key`、`ticket_key`、`job_card`、`source_ref`、`batch_no`、`operation`、request id 载体一致性。

## 边界冻结

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file: `07_后端/lingyi_service/tests/test_workshop_ticket.py`
- recommended next task: `TASK-Z029B-38-FIX-CAND005`
- run_this_task: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码/测试/stdout/result，未 stage/commit/push/tag/PR/release。
