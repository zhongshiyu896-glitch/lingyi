# TASK-Z027B-21-FIX-CAND003 security audit 测试合同修复报告

## 范围

- 角色：B Engineer
- 候选：Z027-CAND-003
- 来源失败定位：TASK-Z027B-20-PREP-CAND003-FAILURE-DIAG
- 分类：TEST_CONTRACT_UPDATE_ALLOWED
- 允许修改文件：`07_后端/lingyi_service/tests/test_security_audit.py`

## 修复内容

- 为 BOM explode 403 场景补齐当前 schema 所需的 `scenario_tag`、`idempotency_key`、`source_ref`、`bom_no`、`item_code`。
- 为 workshop ticket register 403 场景补齐本地写入 gate 所需的 `scenario_tag`、`idempotency_key`、`source_ref`、`batch_no` 与 `X-Request-ID` carrier。
- 保留两个失败用例进入 403 security-audit 分支的目标断言。
- 未使用 skip/xfail，未删除测试用例，未弱化为任意 2xx/4xx。

## 单次验证

- workdir：`07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_security_audit.py -q`
- command_run_count：1
- exit_code：1
- result：FAIL
- pytest_summary：`1 failed, 4 passed, 1 warning in 1.07s`

## 失败摘要

- 剩余失败用例：`SecurityAuditTest::test_workshop_resource_forbidden_writes_security_audit`
- 当前请求已进入目标 403 分支。
- 剩余断言差异：`row.resource_no` 期望 `ITEM-A`，实际 `DEMO-TEE`。
- 已按任务要求停止，未继续修复，未重跑。

## 禁止动作确认

- backend app edits：NO
- frontend edits：NO
- unrelated tests edits：NO
- tests/build/typecheck/npm/browser beyond allowed command：NO
- stage/commit/push/tag/PR/release：NO
- reset/checkout/stash/cleanup：NO
- production readback/go-live/project completion：NO
