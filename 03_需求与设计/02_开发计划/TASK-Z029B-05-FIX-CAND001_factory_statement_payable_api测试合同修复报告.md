# TASK-Z029B-05-FIX-CAND001 factory_statement_payable_api 测试合同修复报告

## 前置核对

- 当前 HEAD：`765441c1248ebb8e83f9835e7f7a1f931a1d0687`
- cached：空
- B04 classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- B04 allowed fix file：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- 冻结命令：`.venv/bin/python -m pytest tests/test_factory_statement_payable_api.py -q`
- 冻结 workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

## 修复范围

仅修改目标测试文件：

- `07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`

修复内容：

- 为 payable-draft payload 补齐 `scenario_tag`、`company`、`supplier`、`statement_no`、`source_type`、`status_action`、`source_ref`。
- 为 confirm/cancel payload 补齐 `scenario_tag`、`company`、`supplier`、`statement_no`。
- 保留原有状态码与错误码断言语义，未引入 skip/xfail，未删除测试用例。

## 验证结果

- command_run_count：1
- exit_code：1
- result：FAIL
- pytest summary：`1 failed, 14 passed, 57 warnings in 1.31s`
- stdout：`03_需求与设计/02_开发计划/task_z029b_05_cand001_fix_stdout.txt`

剩余失败：

- `FactoryStatementPayableApiTest::test_erpnext_unavailable_fail_closed`
- 关键差异：预期 `503`，实际 `200`

pytest 已按边界只运行一次。由于仍 FAIL，未继续修复，未重跑。

## 禁止动作

- `git diff --cached --name-only`：空
- `git diff --check`：PASS
- B05 产物 staged：false
- backend app / 前端 / 共享日志 / candidate pool / 其他测试：未修改
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle：parked
- production readback / go-live / project completion：false
