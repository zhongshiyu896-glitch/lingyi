# TASK-Z028B-30-FIX-CAND004 production_work_order_outbox 修复报告

## 范围

- 角色：B Engineer
- 候选：Z028-CAND-004
- source failure task：TASK-Z028B-29-PREP-CAND004-FAILURE-DIAG
- classification：TEST_CONTRACT_UPDATE_ALLOWED
- 允许修改文件：07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- 当前 HEAD：8b2536babda1780764407c6da2fa96a6313952d9

## 修复内容

- 仅修改目标测试文件。
- 为 create-work-order 测试 payload 补齐当前 local gate 所需 carrier：
  - scenario_tag
  - operation=create_work_order
  - plan_id
  - sales_order
  - sales_order_item
  - item_code
  - bom_id
  - 包含 scenario_tag 的 idempotency_key
- 为对应请求 header 补齐包含 scenario_tag 的 X-Request-ID。
- 使用局部环境 patch 仅包裹 create-work-order 请求，使其满足当前 local-dev gate。
- 原 500/200/409 断言语义保留。
- 未使用 skip/xfail，未删除测试用例。

## 单文件 pytest

- command：`.venv/bin/python -m pytest tests/test_production_work_order_outbox.py -q`
- workdir：`07_后端/lingyi_service`
- command_run_count：1
- exit_code：1
- result：FAIL
- pytest_summary：`1 failed, 15 passed, 30 warnings in 1.12s`

## 剩余失败

- failed case：`ProductionWorkOrderOutboxTest::test_create_work_order_same_idempotency_different_payload_returns_conflict`
- preserved assertion：`second.status_code == 409`
- observed：`200`
- 说明：carrier 修复后，该用例已进入原目标分支之后的行为判断；原 409 断言未弱化。本轮按任务要求在 FAIL 后停止，未继续修复，未重跑。

## 门禁

- cached 区：空
- historical dirty forbidden staged：[]
- backend app changed：false
- frontend changed：false
- unrelated tests changed：false
- stage/commit/push/tag/PR/release：false
- production readback/go-live/project completion：false
