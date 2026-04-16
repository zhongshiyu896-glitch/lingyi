# TASK-009B1 event_key 运行态字段禁用整改 交付证据

- 任务编号：TASK-009B1
- 执行日期：2026-04-16
- 结论：待审计

## 1. 修复字段清单

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 的 `FORBIDDEN_EVENT_KEY_FIELDS` 中新增以下运行态字段禁用：

1. `attempts`
2. `locked_by`
3. `locked_until`
4. `next_retry_at`
5. `status`
6. `error_code`
7. `error_message`
8. `last_error`
9. `last_error_at`
10. `retry_after`
11. `processing_started_at`
12. `succeeded_at`
13. `failed_at`
14. `dead_at`
15. `cancelled_at`
16. `external_docname`
17. `external_docstatus`

说明：这些字段均属于 outbox 运行态或外部回写态，不允许进入 event_key 业务事实计算，避免因重试/lease/错误状态变化导致 event_key 漂移。

## 2. 禁用字段测试清单

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py` 新增参数化用例：

- `test_build_event_key_rejects_runtime_fields`

该测试覆盖以上 17 个运行态字段，逐项断言：

1. `build_event_key()` fail closed
2. 异常类型统一为 `OutboxStateMachineError`
3. 错误码统一为 `OUTBOX_EVENT_KEY_INVALID`
4. 错误信息不泄露传入 runtime 值原文

同时保留并通过原有测试：

1. 同业务事实生成同 key
2. 不同业务事实生成不同 key
3. `idempotency_key/request_id/outbox_id/created_at/operator/created_by` 仍 fail closed
4. 长字段先 hash 后拼接
5. 空业务事实 fail closed

## 3. 测试结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_outbox_state_machine.py
.venv/bin/python -m py_compile app/services/outbox_state_machine.py tests/test_outbox_state_machine.py
```

结果：

- `test_outbox_state_machine.py`：`59 passed`
- `py_compile`：通过

## 4. 禁改扫描结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/migrations
git diff --name-only -- \
  07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py \
  07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py \
  07_后端/lingyi_service/app/services/workshop_outbox_service.py \
  07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py \
  07_后端/lingyi_service/app/services/production_work_order_outbox_service.py \
  07_后端/lingyi_service/app/services/production_work_order_worker.py \
  07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py \
  07_后端/lingyi_service/app/services/factory_statement_payable_worker.py
git diff --cached --name-only
```

结果：上述命令均空输出。

结论：

1. 前端/.github/02_源码：无改动
2. migrations：无改动
3. 旧业务 outbox/worker：无改动
4. 暂存区：空

## 5. 剩余风险

1. 本次仅修复公共模板的运行态字段禁用，尚未自动回迁到所有历史 outbox 构建点。
2. 旧模块如未接入模板，仍可能保留各自 event_key 口径差异，需在后续接入任务中逐模块收口。
