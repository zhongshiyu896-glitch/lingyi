# TASK-006E2 Payable Draft 同 Statement Active Outbox 防重整改交付证据

- 任务编号：TASK-006E2
- 前置审计：审计意见书第 168 份
- 完成时间：2026-04-15

## 1. 修改文件清单

后端代码：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`

迁移：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006e2_factory_statement_payable_active_scope.py`

测试：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_models.py`

证据：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_交付证据.md`

---

## 2. active payable outbox 防重策略

本次落地策略：`409 conflict + 明确 existing outbox 信息`。

优先级与处理顺序：
1. 同 `idempotency_key` + 同 `request_hash`：replay（返回首次 outbox，`idempotent_replay=true`）。
2. 同 `idempotency_key` + 异 `request_hash`：`FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
3. 不同 `idempotency_key` 但同 statement 已有 active outbox：`FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE`（不新增 outbox）。

响应 data 补充：
- `existing_outbox_id`
- `existing_status`

并发冲突（唯一约束命中）处理：
- 捕获 `IntegrityError`。
- rollback。
- 先按 idempotency 兜底 replay/conflict。
- 再按 statement active outbox 兜底 `FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE`。
- 不再落成 `FACTORY_STATEMENT_DATABASE_WRITE_FAILED`。

---

## 3. active 状态集合

定义并落地到服务与数据库索引口径：
- `pending`
- `processing`
- `succeeded`

inactive：
- `failed`
- `dead`

---

## 4. failed/dead 重新创建策略

本次实现策略：
- `failed/dead` 不属于 active，不直接阻断新建。
- 当新请求业务口径可形成新的 `event_key`（例如 `posting_date` 变化）时，允许创建新 outbox。
- 若业务口径相同导致 `event_key` 冲突，返回 `FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE`（并返回 existing outbox 信息）。

---

## 5. event_key 新口径（不含 idempotency_key）

`event_key` 公式：

`fspi:sha256(company|statement_id|statement_no|supplier|net_amount|payable_account|cost_center|posting_date)`

实现要点：
- 不包含 `idempotency_key`。
- 不包含 `outbox_id`、`request_id`、`created_at`、`operator`、`attempts`。
- 同业务口径（即使不同 idempotency_key）得到同一 `event_key`。

---

## 6. 数据库层并发防重

新增 partial unique index：
- 名称：`uk_ly_factory_statement_payable_one_active`
- 表：`ly_factory_statement_payable_outbox`
- 键：`(statement_id)`
- 条件：`status IN ('pending','processing','succeeded')`

迁移文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006e2_factory_statement_payable_active_scope.py`

同时模型层 `LyFactoryStatementPayableOutbox.__table_args__` 已同步该唯一约束定义。

---

## 7. 新增/调整测试与覆盖点

### `test_factory_statement_payable_api.py`

新增：
1. `test_different_key_cannot_create_second_active_outbox`
- 覆盖：不同 key 同 statement 防重（active 冲突），active 数量保持 1。

2. `test_failed_outbox_allows_new_request_with_new_business_payload`
- 覆盖：failed 非 active，允许按新业务口径重建新 outbox。

3. `test_event_key_is_stable_and_excludes_idempotency`
- 覆盖：event_key 稳定性与去 idempotency 化。

4. `test_integrity_conflict_reloads_existing_active_outbox`
- 覆盖：模拟 `IntegrityError`，服务层兜底返回 active conflict，而非 DATABASE_WRITE_FAILED。

保留验证：
- 同 key 同 hash replay。
- 同 key 异 hash conflict。
- draft/cancelled 状态拦截。
- `/payable-draft` 不直接创建 ERPNext PI。

### `test_factory_statement_models.py`

新增：
1. `test_payable_outbox_one_active_unique_constraint`
- 覆盖：同 statement 两条 active（pending/processing）被数据库唯一约束拦截。

2. `test_payable_outbox_failed_status_allows_new_pending_row`
- 覆盖：failed 与 pending 可并存（failed 不属于 active）。

3. 迁移断言补充
- 覆盖：`task_006e2_factory_statement_payable_active_scope.py` 存在并包含 active partial unique 约束。

---

## 8. 自测命令与结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. 定向模型+payable API：
```bash
.venv/bin/python -m pytest -q tests/test_factory_statement_payable_api.py tests/test_factory_statement_models.py
```
结果：`24 passed`

2. 全 factory-statement 测试：
```bash
.venv/bin/python -m pytest -q tests/test_factory_statement*.py
```
结果：`77 passed`

3. 语法编译：
```bash
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果：通过

4. 风险关键字扫描（限定 factory-statement 相关文件）：
```bash
rg -n "submit\(|Payment Entry|GL Entry|create_payment|submit_purchase_invoice|/api/resource/Purchase Invoice" app/services/factory_statement_service.py app/services/factory_statement_payable_outbox_service.py app/services/factory_statement_payable_worker.py app/services/erpnext_purchase_invoice_adapter.py app/routers/factory_statement.py tests/test_factory_statement_payable*.py tests/test_factory_statement*.py
```
结果：无命中

5. 任务单要求的全量关键字扫描（app/tests 全范围）：
```bash
rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests
```
结果：存在命中，但均位于既有 `production/subcontract` 模块或测试用 `docstatus=1` 模拟，不在本次 factory-statement 新增实现路径中。

6. 禁改扫描：
```bash
git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/06_前端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```
结果：输出存在历史前端改动（`package.json`、`src/router/index.ts`、`src/stores/permission.ts`），本任务未对这些文件做新增改动。

---

## 9. 合规声明

- 未新增前端功能。
- 未新增 internal worker 调用入口。
- 未提交 ERPNext Purchase Invoice（未调用 submit/docstatus=1 流程）。
- 未创建 Payment Entry / GL Entry。
- 未修改 `.github/**`、`02_源码/**`。

---

## 10. 结论

TASK-006E2 已完成：
- 同 statement active outbox 防重已在服务层 + DB 层双重收口。
- 不同 idempotency_key 重复创建 active outbox 已被阻断。
- event_key 已移除 idempotency 依赖并固定业务口径。
- 并发唯一冲突已收口为业务可读错误，不再裸回 DATABASE_WRITE_FAILED。

结论：建议进入 TASK-006E2 审计复核；TASK-006F 仍需单独任务单下发，不自动进入。
