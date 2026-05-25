# TASK-Z027B-38-FIX-CAND005 workshop_wage 测试合同修复报告

## 修复范围

- candidate_id: `Z027-CAND-005`
- source_failure_task: `TASK-Z027B-37-PREP-CAND005-FAILURE-DIAG`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- fixed_file: `07_后端/lingyi_service/tests/test_workshop_wage.py`

## 本轮修改

- 补齐 workshop ticket register/reversal 的 `scenario_tag`、`idempotency_key`、`source_ref`、`batch_no` 与 `X-Request-ID` carrier。
- 补齐 wage-rate create/deactivate 的 `scenario_tag`、`idempotency_key`、`source_ref` 与 `X-Request-ID` carrier。
- 保留原目标语义：`test_daily_wage_formula_and_snapshot_not_changed` 仍进入并断言 `200` 成功分支；`test_wage_rate_overlap_returns_409` 仍断言 `409` 与 `WORKSHOP_WAGE_RATE_OVERLAP`。
- 未使用 skip/xfail，未删除测试用例，未弱化为任意 2xx/4xx。

## 验证结果

- command: `.venv/bin/python -m pytest tests/test_workshop_wage.py -q`
- workdir: `07_后端/lingyi_service`
- command_run_count: `1`
- exit_code: `1`
- result: `FAIL`
- pytest_summary: `1 failed, 46 passed, 24 warnings in 1.18s`

## 剩余失败

- failed_case: `WorkshopWageApiTest::test_daily_wage_formula_and_snapshot_not_changed`
- remaining_failure: `Decimal('90.0') != Decimal('45.000000')`
- note: 本轮已使测试越过原先 422 schema/local gate 阻断并进入目标 `200` 分支；剩余失败为 `wage_amount` 业务断言差异。按任务边界，pytest FAIL 后停止，未继续修复、未重跑。

## 禁止动作核对

- backend app edits: 未修改
- frontend edits: 未修改
- unrelated tests edits: 未修改
- stage/commit/push/tag/PR/release: 未执行
- cleanup/reset/checkout/stash: 未执行
- production readback/go-live/project completion: 未声明
