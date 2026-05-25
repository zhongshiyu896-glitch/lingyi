# TASK-Z029B-08-LEDGER-CAND001 factory_statement_payable_api 提交候选账本报告

## 冻结摘要

- 当前 HEAD：`765441c1248ebb8e83f9835e7f7a1f931a1d0687`
- cached：空
- `git diff --check`：PASS
- 链路：B02 boundary -> B03 FAIL -> B03-FIX1 -> B04 classification -> B05 FAIL -> B06 classification -> B07 PASS -> B08 ledger
- B04 classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- B06 classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- B07 pytest summary：`15 passed, 56 warnings in 1.27s`

## 账本摘要

- ledger total：75
- YES count：29
- NO count：46
- YES/NO intersection：空
- backend YES paths：`07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- frontend YES paths：空
- historical dirty forbidden paths：19 条，全部列入 NO，未进入 YES
- YES 文件存在性：全部存在
- YES git ignore 检查：无命中

## 断言与范围

目标测试保留 `503` 与 `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE` 显式断言，未见 skip/xfail，未删除用例。

## 禁止动作

- pytest/npm/browser/build/typecheck/verify：未运行
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
- remote lifecycle：parked
- production readback / go-live / project completion：false
