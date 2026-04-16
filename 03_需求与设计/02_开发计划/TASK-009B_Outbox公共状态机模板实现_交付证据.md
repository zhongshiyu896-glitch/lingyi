# TASK-009B Outbox 公共状态机模板实现交付证据

- 任务编号：TASK-009B
- 执行日期：2026-04-16
- 结论：待审计

## 1. 修改文件清单

### 新增文件
1. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-009B_Outbox公共状态机模板实现_交付证据.md`

### 修改文件
- 无（未修改既有业务 outbox/worker 文件）

## 2. 公共 API 清单

`outbox_state_machine.py` 对外提供：

1. 状态/动作常量：
   - `OUTBOX_STATUS_PENDING/PROCESSING/SUCCEEDED/FAILED/DEAD/CANCELLED`
   - `OUTBOX_ACTION_STOCK_ISSUE/OUTBOX_ACTION_STOCK_RECEIPT/OUTBOX_ACTION_JOB_CARD_SYNC/OUTBOX_ACTION_WORK_ORDER_CREATE/OUTBOX_ACTION_PURCHASE_INVOICE_DRAFT/OUTBOX_ACTION_GENERIC`
2. event_key：
   - `normalize_event_key_parts()`
   - `build_event_key()`
3. payload hash：
   - `canonical_payload_json()`
   - `build_payload_hash()`
4. 状态迁移：
   - `can_transition()`
   - `validate_transition()`
   - `is_terminal_status()`
5. claim/lease：
   - `is_due()`
   - `is_lease_expired()`
   - `can_claim()`
   - `evaluate_claim_lease()`
   - `build_claim_update_guard()`
6. retry：
   - `is_retryable_error()`
   - `compute_next_retry_at()`
   - `decide_retry_transition()`
7. dry-run / diagnostic：
   - `build_dry_run_preview()`
   - `evaluate_diagnostic_window()`
8. 数据结构：
   - `ClaimLeaseEvaluation`
   - `RetryDecision`
   - `DryRunPreview`
   - `DiagnosticWindow`

## 3. event_key 规则验证

已实现并测试：

1. 同业务事实（即使 key 顺序不同）生成同 event_key。
2. 业务事实变更时 event_key 变化。
3. 禁止字段 fail closed：
   - `idempotency_key`
   - `request_id`
   - `outbox_id`
   - `created_at`
   - `updated_at`
   - `operator`
   - `created_by`
4. 长字段先 hash 再拼接（`sha256:<digest>`），不拼接原始长文本。
5. 空业务事实或空字段值 fail closed。

## 4. payload_hash 规则验证

已实现并测试：

1. JSON key 顺序无关（同语义同 hash）。
2. `Decimal`、`date`、`datetime` 稳定序列化。
3. `Decimal` 与 `float`、`string` 不混淆（hash 不同）。
4. `None` 与缺字段不混淆（hash 不同）。
5. payload 内容变化 -> hash 变化。
6. 不支持类型 fail closed（`OUTBOX_PAYLOAD_INVALID`）。

## 5. 状态迁移矩阵

### 合法迁移
1. `pending -> processing`
2. `processing -> succeeded`
3. `processing -> failed`
4. `failed -> pending`
5. `failed -> dead`
6. `pending -> cancelled`
7. `failed -> cancelled`

### 终态
1. `succeeded`：终态，不可重新 processing。
2. `cancelled`：终态，不可重新 pending。
3. `dead`：终态，不自动 retry。

非法迁移统一 fail closed：`OUTBOX_TRANSITION_INVALID`。

## 6. claim/lease 测试结果

已覆盖并通过：

1. `pending` 且 due 可 claim。
2. `failed` 且 due 可 claim。
3. `pending` 未到 `next_retry_at` 不可 claim。
4. `processing` 且 lease 过期可 claim。
5. `processing` 且 lease 未过期不可 claim。
6. stale 场景通过 `build_claim_update_guard` 保持不可抢占未过期 lease。

## 7. retry 测试结果

已覆盖并通过：

1. retryable 外部错误（如 `EXTERNAL_SERVICE_UNAVAILABLE`）可重试并生成 `next_retry_at`。
2. 非 retryable 错误（如 `ERPNEXT_AUTH_FAILED`）直接 dead。
3. 达到 `max_attempts` 后进入 dead。
4. backoff 计算符合上限封顶策略。

## 8. dry-run/diagnostic 测试结果

已覆盖并通过：

1. `build_dry_run_preview()` 返回 `will_mutate=False`（只预览，不改状态）。
2. `evaluate_diagnostic_window()` 在 cooldown 内抑制重复放大。
3. cooldown 到期后可再次 emit。
4. `seen_count` 连续递增。

## 9. 测试命令与结果

### 定向
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_outbox_state_machine.py
```
结果：`42 passed`。

### outbox/worker 相关回归
```bash
.venv/bin/python -m pytest -q tests/test_*outbox*.py tests/test_*worker*.py tests/test_factory_statement*.py tests/test_subcontract*.py tests/test_workshop*.py tests/test_production*.py
```
结果：`648 passed, 5 skipped`。

### 全量 pytest
```bash
.venv/bin/python -m pytest -q
```
结果：`798 passed, 13 skipped`。

### unittest
```bash
.venv/bin/python -m unittest discover
```
结果：`Ran 720 tests ... OK (skipped=1)`。

### py_compile
```bash
.venv/bin/python -m py_compile app/services/outbox_state_machine.py tests/test_outbox_state_machine.py
```
结果：通过。

## 10. 禁改扫描结果

执行：

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
```

结果：均空输出（无改动）。

## 11. 未接入旧 outbox 的说明

本任务只新增公共模板与测试，未接入以下既有业务 outbox/worker：

1. subcontract stock outbox/worker
2. workshop outbox/worker
3. production work order outbox/worker
4. factory statement payable outbox/worker

说明：保持与任务边界一致，后续接入应在独立任务中进行并逐模块回归。

## 12. 剩余风险

1. 现网业务 outbox 尚未逐个接入本模板，当前收益主要是“公共规范 + 可复用实现 + 单测基线”。
2. 仓库中既有模块仍有大量 `datetime.utcnow()` deprecation warning（本任务未触碰）。
3. `unittest discover` 有数据库连接 `ResourceWarning`（历史行为，本任务未引入）。
