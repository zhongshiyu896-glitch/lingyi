# TASK-Z028B-31-PREP-CAND004-SECOND-FAILURE-DIAG 二次失败定位报告

## 范围

- 角色：B Engineer
- 候选：Z028-CAND-004
- source failure task：TASK-Z028B-30-FIX-CAND004
- previous boundary：TASK-Z028B-29-PREP-CAND004-FAILURE-DIAG
- 当前 HEAD：8b2536babda1780764407c6da2fa96a6313952d9
- 本轮只读定位，未运行 pytest，未修复，未 stage/commit/push/tag/PR/release。

## 只读核对

- cached 区：空
- B30 result：command_run_count=1，result=FAIL
- B30 summary：1 failed, 15 passed, 30 warnings in 1.12s
- 剩余失败用例：ProductionWorkOrderOutboxTest::test_create_work_order_same_idempotency_different_payload_returns_conflict
- expected：409
- observed：200
- 目标测试 dirty diff：仅 B30 允许的 carrier/fixture 修复范围
- historical dirty forbidden staged：[]
- source evidence missing：[]
- git diff --check：PASS

## 只读定位

- B30 后，create-work-order 请求已通过 local gate；剩余失败不再是 409 gate 阻断。
- `ProductionService.create_work_order_outbox` 在已有 `LyProductionWorkOrderLink.work_order` 时会先返回 existing work-order data。
- 该 existing-link 返回发生在 `existing_by_idempotency` payload-hash 冲突检查之前。
- 当前两次真实 POST fixture 的第一次成功请求会创建 outbox 并 upsert local work-order link。
- 因此第二次请求虽然保留 same-idempotency/different-payload 场景，但被 existing-link 分支短路为 200。
- 服务中仍存在 payload-hash mismatch 的 `PRODUCTION_IDEMPOTENCY_CONFLICT` 分支；当前测试 fixture 未进入该分支。

## 分类

- classification：TEST_CONTRACT_UPDATE_ALLOWED
- 归因：测试 fixture/idempotency-payload conflict expectation drift。
- allowed_fix_file：07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- next_task：TASK-Z028B-32-FIX-CAND004-SECOND
- run_this_task：false
