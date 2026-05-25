# TASK-Z028B-32-FIX-CAND004-SECOND production_work_order_outbox 二次修复报告

## 范围

- 角色：B Engineer
- 候选：Z028-CAND-004
- source failure task：TASK-Z028B-31-PREP-CAND004-SECOND-FAILURE-DIAG
- classification：TEST_CONTRACT_UPDATE_ALLOWED
- 允许修改文件：07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- 当前 HEAD：8b2536babda1780764407c6da2fa96a6313952d9

## 二次修复内容

- 仅调整 `test_create_work_order_same_idempotency_different_payload_returns_conflict` 的测试 fixture。
- 第一次请求仍断言 `200`，保留创建 outbox 的成功语义。
- 在第二次请求前，仅删除该测试内第一次请求生成的 `LyProductionWorkOrderLink`，避免 existing-link 分支短路。
- 第二次请求仍使用相同 idempotency key 且不同 payload，保留显式 `409` 与 `PRODUCTION_IDEMPOTENCY_CONFLICT` 断言。
- 其他 `500/200` 用例断言语义未弱化。
- 未使用 skip/xfail，未删除测试用例。

## 单文件 pytest

- command：`.venv/bin/python -m pytest tests/test_production_work_order_outbox.py -q`
- workdir：`07_后端/lingyi_service`
- command_run_count：1
- exit_code：0
- result：PASS
- pytest_summary：`16 passed, 30 warnings in 1.07s`

## 门禁

- cached 区：空
- historical dirty forbidden staged：[]
- backend app changed：false
- frontend changed：false
- unrelated tests changed：false
- stage/commit/push/tag/PR/release：false
- production readback/go-live/project completion：false
