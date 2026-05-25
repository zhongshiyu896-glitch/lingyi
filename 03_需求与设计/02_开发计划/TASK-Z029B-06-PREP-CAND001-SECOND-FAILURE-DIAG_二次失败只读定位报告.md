# TASK-Z029B-06-PREP-CAND001-SECOND-FAILURE-DIAG 二次失败只读定位报告

## 只读核对

- 当前 HEAD：`765441c1248ebb8e83f9835e7f7a1f931a1d0687`
- cached：空
- `git diff --check`：PASS
- B05 result：FAIL
- B05 command_run_count：1
- B05 pytest summary：`1 failed, 14 passed, 57 warnings in 1.31s`
- 剩余失败：`FactoryStatementPayableApiTest::test_erpnext_unavailable_fail_closed`
- 状态差异：expected `503`，observed `200`

## 当前目标测试 dirty diff 摘要

B05 后目标测试 dirty diff 仅为允许目标测试 `07_后端/lingyi_service/tests/test_factory_statement_payable_api.py` 内的测试合同补齐：

- 新增 scenario tag idempotency helper。
- confirm/cancel payload 补齐 `scenario_tag`、`company`、`supplier`、`statement_no`。
- payable-draft payload 补齐 `scenario_tag`、`company`、`supplier`、`statement_no`、`source_type`、`status_action`、`source_ref`。
- 未新增 skip/xfail，未删除用例，未将状态码断言弱化为任意 2xx/4xx/5xx。

## 二次定位

B05 已将首轮 15 个失败收敛为 1 个失败。剩余用例仍 mock `ERPNextPurchaseInvoiceAdapter.validate_payable_account` 抛出 `ERPNextServiceUnavailableError` 并断言 `503` / `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE`。

只读 source evidence 显示当前 `FactoryStatementService.create_payable_draft_outbox` 在捕获 `ERPNextServiceUnavailableError` 时，只有在非本地 dev sqlite 模式下才转换为 `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE`；本地 dev sqlite 模式下会继续创建 payable outbox，因此 B05 observed `200` 与当前本地合同一致。

## 分类结论

- classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- recommended next task：`TASK-Z029B-07-FIX-CAND001-SECOND`
- run_this_task：false

## 禁止动作

- pytest/npm/browser/build/typecheck/verify：未运行
- 代码/测试/stdout/result：未修改
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle：parked
- production readback / go-live / project completion：false
