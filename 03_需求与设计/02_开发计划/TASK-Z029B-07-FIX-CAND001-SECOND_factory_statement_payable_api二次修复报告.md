# TASK-Z029B-07-FIX-CAND001-SECOND factory_statement_payable_api 二次修复报告

## 前置核对

- 当前 HEAD：`765441c1248ebb8e83f9835e7f7a1f931a1d0687`
- cached：空
- B06 classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- B06 allowed fix file：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- B06 剩余失败：expected `503`，observed `200`
- 冻结命令：`.venv/bin/python -m pytest tests/test_factory_statement_payable_api.py -q`
- 冻结 workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

## 修复范围

仅修改目标测试文件：

- `07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`

二次修复内容：

- 在 `test_erpnext_unavailable_fail_closed` 中显式 patch `FactoryStatementService._is_local_dev_sqlite_mode` 为 `False`，使测试进入非本地 fail-closed 分支。
- 保留该用例的 `503` 显式断言与 `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE` 错误码断言。
- 未新增 skip/xfail，未删除用例，未将断言弱化为任意 2xx/4xx/5xx。

## 验证结果

- command_run_count：1
- exit_code：0
- result：PASS
- pytest summary：`15 passed, 56 warnings in 1.27s`
- stdout：`03_需求与设计/02_开发计划/task_z029b_07_cand001_second_fix_stdout.txt`

## 禁止动作

- `git diff --cached --name-only`：空
- `git diff --check`：PASS
- B07 产物 staged：false
- backend app / 前端 / 共享日志 / candidate pool / 其他测试：未修改
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle：parked
- production readback / go-live / project completion：false
