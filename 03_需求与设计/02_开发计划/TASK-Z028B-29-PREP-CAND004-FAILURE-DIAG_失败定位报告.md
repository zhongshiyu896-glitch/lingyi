# TASK-Z028B-29-PREP-CAND004-FAILURE-DIAG 失败定位报告

## 范围

- 角色：B Engineer
- 候选：Z028-CAND-004
- source boundary：TASK-Z028B-27-PREP
- source impl：TASK-Z028B-28-IMPL
- 当前 HEAD：8b2536babda1780764407c6da2fa96a6313952d9
- 本轮未运行 pytest，未修复，未 stage/commit/push/tag/PR/release。

## 只读核对

- cached 区：空
- B28 result：command_run_count=1，result=FAIL
- B28 summary：6 failed, 10 passed, 30 warnings in 1.11s
- 目标测试：07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- 目标测试 dirty diff：无
- historical dirty forbidden staged：[]
- source evidence missing：[]
- git diff --check：PASS

## 失败用例

| failed case | expected | observed | assertion |
| --- | ---: | ---: | --- |
| ProductionWorkOrderOutboxTest::test_create_work_order_audit_write_failed_returns_audit_write_failed | 500 | 409 | tests/test_production_work_order_outbox.py:242 |
| ProductionWorkOrderOutboxTest::test_create_work_order_commit_failure_does_not_call_erpnext | 500 | 409 | tests/test_production_work_order_outbox.py:258 |
| ProductionWorkOrderOutboxTest::test_create_work_order_outbox_is_idempotent_for_same_plan | 200 | 409 | tests/test_production_work_order_outbox.py:175 |
| ProductionWorkOrderOutboxTest::test_create_work_order_returns_existing_pending_outbox_without_duplicate | 200 | 409 | tests/test_production_work_order_outbox.py:209 |
| ProductionWorkOrderOutboxTest::test_create_work_order_returns_existing_work_order_when_link_succeeded | 200 | 409 | tests/test_production_work_order_outbox.py:232 |
| ProductionWorkOrderOutboxTest::test_create_work_order_same_idempotency_different_payload_returns_conflict | 200 | 409 | tests/test_production_work_order_outbox.py:194 |

## 只读定位

- 测试 helper `tests/test_production_work_order_outbox.py:124-130` 仅发送 `fg_warehouse`、`wip_warehouse`、`start_date`、`idempotency_key`。
- 当前 `ProductionCreateWorkOrderRequest` 已包含 `scenario_tag`、`operation`、`plan_id`、`sales_order`、`sales_order_item`、`item_code`、`bom_id`、`request_id` 等 carrier 字段。
- `ProductionService.create_work_order_outbox` 在进入 outbox 分支前先调用 `_validate_plan_carriers`。
- `_validate_plan_carriers` 要求 local dev gate、合法 `scenario_tag`、包含 scenario 的 `idempotency_key`、operation、plan_id、业务 carrier 与 request id 对齐。
- gate 失败会抛出 `PRODUCTION_IDEMPOTENCY_CONFLICT`，并以 `LOCAL_GATE_FAIL_CLOSED:` 前缀映射为 409。

## 分类

- classification：TEST_CONTRACT_UPDATE_ALLOWED
- 归因：测试合同/fixture/outbox payload carrier 漂移。6 个 create-work-order 用例仍在验证原目标 200/500 分支，但 payload 未补齐当前 local gate 所需 carrier，因此在目标分支前统一返回 409。
- allowed_fix_file：07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- next_task：TASK-Z028B-30-FIX-CAND004
- run_this_task：false
