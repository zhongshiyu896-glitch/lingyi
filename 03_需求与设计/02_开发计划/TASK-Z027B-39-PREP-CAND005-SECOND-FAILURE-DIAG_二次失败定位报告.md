# TASK-Z027B-39-PREP-CAND005-SECOND-FAILURE-DIAG 二次失败定位报告

## 基本结论

- candidate_id: `Z027-CAND-005`
- source_failure_task: `TASK-Z027B-38-FIX-CAND005`
- previous_boundary_task: `TASK-Z027B-37-PREP-CAND005-FAILURE-DIAG`
- current_head: `bc3aa7f1a1c78ccd48e3c911bee619df0f65ce74`
- failed_summary: `1 failed, 46 passed, 24 warnings in 1.18s`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_wage.py`
- next_task: `TASK-Z027B-40-FIX-CAND005-SECOND`
- run_this_task: `false`

## 剩余失败

| case | expected status | observed status | expected wage_amount | observed wage_amount |
| --- | ---: | ---: | --- | --- |
| `WorkshopWageApiTest::test_daily_wage_formula_and_snapshot_not_changed` | 200 | 200 | `Decimal('45.000000')` | `Decimal('90.0')` |

## 只读证据

- B38 result/stdout 记录 `command_run_count=1`、`result=FAIL`，失败摘要为 `1 failed, 46 passed, 24 warnings in 1.18s`。
- B38 已进入 `daily.status_code == 200` 原目标分支，剩余失败发生在 `wage_amount` 断言。
- 当前 `test_workshop_wage.py` dirty diff 仅限 B38 允许的目标测试合同/fixture 修改范围。
- `WorkshopService._resolve_unit_wage` 在 `local_scenario_tag` 存在且本地 synthetic context 启用时返回 `WORKSHOP_LOCAL_DEFAULT_UNIT_WAGE`。
- `WORKSHOP_LOCAL_DEFAULT_UNIT_WAGE` 为 `Decimal("1")`；`_refresh_daily_wage` 按 ticket 的 register/reversal amount 汇总，因此当前 local synthetic 合同下 `net_qty=90` 对应 `wage_amount=90.0`。

## 边界冻结

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- reason: 原 `200` 状态目标已满足，剩余失败是测试 fixture/formula expectation drift；证据支持只在目标测试文件中更新当前合法 local synthetic wage 期望，同时保留 `200` 和 `409` 业务断言。
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_wage.py`
- next_task: `TASK-Z027B-40-FIX-CAND005-SECOND`

## 禁止动作核对

- pytest/npm/browser/build/typecheck/verify: 未运行
- code/test edits: 未执行
- stage/commit/push/tag/PR/release: 未执行
- reset/checkout/stash/cleanup: 未执行
- production readback/go-live/project completion: 未声明
