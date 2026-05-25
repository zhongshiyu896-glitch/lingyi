# TASK-Z029B-04-PREP-CAND001-FAILURE-DIAG 失败只读定位报告

## 只读核对

- 当前 HEAD：`765441c1248ebb8e83f9835e7f7a1f931a1d0687`
- cached：空
- `git diff --check`：PASS
- B03-FIX1 后 B03 result：FAIL
- B03 summary：`15 failed, 31 warnings in 1.26s`
- B03 command_run_count：1
- B03 target_test_dirty_diff：false
- 当前目标测试 dirty diff：false

## 冻结边界

- candidate_id：`Z029-CAND-001`
- source task：`TASK-Z029B-03-IMPL`
- fix1 source：`TASK-Z029B-03-IMPL-FIX1`
- frozen command：`.venv/bin/python -m pytest tests/test_factory_statement_payable_api.py -q`
- frozen workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- target test：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`

## 失败定位

B03 的 15 个失败均来自 `test_factory_statement_payable_api.py`。主要失败模式为：

- 14 个用例在 confirm/cancel 或 payable setup 阶段进入 `409`，而测试原目标断言为 `200`。
- `test_draft_statement_cannot_create_payable_outbox` 当前仍为 `409`，但错误码从预期 `FACTORY_STATEMENT_INVALID_STATUS` 变为 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。

只读 source evidence 显示当前 `factory_statement` 本地写入 gate 会校验 `X-Request-ID`、`scenario_tag` carrier，以及 confirm/cancel/payable-draft payload 中的 chain 字段。当前目标测试的 `_payable_payload` 与 confirm/cancel payload 未补齐 `scenario_tag`、`source_ref`、`status_action` 等当前合同要求字段，因此 409 local/idempotency gate 先于原目标业务分支触发。

## 分类结论

- classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- recommended next task：`TASK-Z029B-05-FIX-CAND001`
- run_this_task：false

## 禁止动作

- pytest/npm/browser/build/typecheck/verify：未运行
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle：parked
- production readback / go-live / project completion：false
