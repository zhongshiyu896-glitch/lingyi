# TASK-Z027B-37-PREP-CAND005-FAILURE-DIAG 失败定位报告

## 基本结论

- candidate_id: `Z027-CAND-005`
- source_boundary_task: `TASK-Z027B-35-PREP`
- source_impl_task: `TASK-Z027B-36-IMPL`
- current_head: `bc3aa7f1a1c78ccd48e3c911bee619df0f65ce74`
- failed_summary: `2 failed, 45 passed, 12 warnings in 1.18s`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_wage.py`
- next_task: `TASK-Z027B-38-FIX-CAND005`
- run_this_task: `false`

## 失败用例

| case | expected | observed | failure point |
| --- | ---: | ---: | --- |
| `WorkshopWageApiTest::test_daily_wage_formula_and_snapshot_not_changed` | 200 | 422 | `_register("WAGE-RG-001", "100")` |
| `WorkshopWageApiTest::test_wage_rate_overlap_returns_409` | 409 | 422 | `POST /api/workshop/wage-rates` |

## 只读证据

- B36 result/stdout 记录 `command_run_count=1`、`result=FAIL`，失败摘要为 `2 failed, 45 passed, 12 warnings in 1.18s`。
- `test_workshop_wage.py` 的 `_register` payload 当前缺少 `scenario_tag`、`idempotency_key`、`batch_no` 等当前 `WorkshopTicketRegisterRequest` 必填字段。
- `test_wage_rate_overlap_returns_409` 的 `/api/workshop/wage-rates` payload 当前缺少 `scenario_tag`、`idempotency_key`、`source_ref` 等当前 `OperationWageRateCreateRequest` 必填字段。
- `workshop.py` 在进入 ticket register 与 wage-rate business 分支前会执行本地 write gate / request carrier 校验；因此两个用例均在原目标断言分支前被 422 拦截。

## 边界冻结

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- reason: 当前失败由测试 fixture/schema payload 与本地 request carrier 合同漂移导致，证据支持只修改目标测试文件补齐合同字段。
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_wage.py`
- next_task: `TASK-Z027B-38-FIX-CAND005`

## 禁止动作核对

- pytest/npm/browser/build/typecheck/verify: 未运行
- code/test edits: 未执行
- stage/commit/push/tag/PR/release: 未执行
- reset/checkout/stash/cleanup: 未执行
- production readback/go-live/project completion: 未声明
