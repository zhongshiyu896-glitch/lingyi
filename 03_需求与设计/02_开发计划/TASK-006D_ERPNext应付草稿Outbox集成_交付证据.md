# TASK-006D 交付证据（ERPNext 应付草稿 Outbox 集成）

## 1. 任务结论
- 任务：TASK-006D ERPNext 应付草稿 Outbox 集成
- 结论：已完成后端本地实现与回归验证，可进入审计复核。
- 边界声明：
  - 未实现 `submit()` 提交 Purchase Invoice。
  - 未创建 Payment Entry。
  - 未写入 GL Entry。
  - 用户侧 `/payable-draft` 接口不直接创建 ERPNext Purchase Invoice。
  - 未修改前端、`.github`、`02_源码`。

## 2. 修改文件清单
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006d_factory_statement_payable_outbox.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_models.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/__init__.py`

## 3. 新增表、字段、索引
- 表：`ly_schema.ly_factory_statement_payable_outbox`
- 关键字段：
  - `id`, `company`, `statement_id`, `statement_no`, `supplier`
  - `idempotency_key`, `request_hash`, `event_key`
  - `payload_json`, `payload_hash`
  - `status`, `attempts`, `next_retry_at`, `locked_by`, `locked_until`
  - `erpnext_purchase_invoice`, `erpnext_docstatus`, `erpnext_status`
  - `last_error_code`, `last_error_message`
  - `created_by`, `created_at`, `updated_at`
- 索引：
  - `uk_ly_factory_statement_payable_event_key(event_key)`
  - `uk_ly_factory_statement_payable_idem(company, statement_id, idempotency_key)`
  - `idx_ly_factory_statement_payable_due(status, next_retry_at, id)`
  - `idx_ly_factory_statement_payable_statement(statement_id, status, id)`

## 4. 新增接口
- `POST /api/factory-statements/{id}/payable-draft`
- `POST /api/factory-statements/internal/payable-draft-sync/run-once`

## 5. ERPNext Purchase Invoice payload（示例）
- 由 outbox worker 调用 ERPNext 时写入，用户请求接口不直连创建。

```json
{
  "doctype": "Purchase Invoice",
  "docstatus": 0,
  "supplier": "S-001",
  "company": "C-001",
  "posting_date": "2026-04-15",
  "credit_to": "2202 - AP - C",
  "payable_account": "2202 - AP - C",
  "cost_center": "Main - C",
  "custom_ly_factory_statement_id": 123,
  "custom_ly_factory_statement_no": "FS202604150001",
  "custom_ly_payable_outbox_id": 456,
  "custom_ly_outbox_event_key": "evt_...",
  "amount": "4700.00",
  "remark": "task-006d"
}
```

## 6. 幂等与事件键口径
- `/payable-draft` 幂等唯一键：`company + statement_id + idempotency_key`
- `request_hash` 组成：`statement_id + payable_account + cost_center + posting_date + remark`
- `event_key`：outbox 事件唯一键，数据库唯一索引保护。
- 同 key 同 hash：replay 首次结果。
- 同 key 异 hash：`FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。

## 7. 权限动作与角色映射
- 新增动作：
  - `factory_statement:payable_draft_create`
  - `factory_statement:payable_draft_worker`
- 资源权限：`company + supplier`，权限源不可用 fail closed。
- worker 接口额外要求：
  - 必须服务账号（`is_service_account=true`）
  - 普通财务角色不可调用 internal worker 入口。

## 8. 服务账号最小权限策略
- 服务账号仅授予 `factory_statement:payable_draft_worker` 与必要资源范围（company/supplier）。
- 禁止以通配/全模块动作放行 worker。
- ERPNext 权限源异常时返回 `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE` 并拒绝执行。

## 9. Outbox worker 状态机
- `pending` -> `processing` -> `succeeded`
- 失败：`processing` -> `failed`（写 `next_retry_at`）
- 超过最大重试：`failed` -> `dead`
- 成功回写：
  - outbox `status=succeeded`
  - statement `status=payable_draft_created`
- dry_run：仅审计，不调 ERPNext，不改 outbox/statement。

## 10. 本轮关键修复（D 阶段补丁）
- 修复 `create_payable_draft_outbox` 中 `request_id` 被提前删除导致的 `UnboundLocalError`。
- 补齐 `POST /payable-draft` 权限拒绝分支失败审计（`factory_statement:payable_draft_create`）。
- 保持统一错误信封与事务回滚语义。

## 11. 自测命令与结果
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `pytest -q tests/test_factory_statement*.py`
- 结果：`59 passed`

2. `python -m pytest -q`
- 结果：`700 passed, 13 skipped`

3. `python -m unittest discover`
- 结果：`Ran 683 tests ... OK (skipped=1)`

4. `python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

5. 禁入扫描（聚焦 factory_statement 相关）
- 命令：
  - `rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app/services/factory_statement* app/services/erpnext_purchase_invoice_adapter.py app/routers/factory_statement.py tests/test_factory_statement*`
- 结果：仅命中负向测试中用于断言失败场景的 `docstatus=1`，未命中提交/付款/总账实现。

6. 禁改扫描
- 命令：
  - `git diff --name-only -- '06_前端' '.github' '02_源码'`
- 结果：空输出

## 12. 审计关注点说明
- `/payable-draft` 为本地 outbox 创建，不直接写 ERPNext PI。
- PI 创建仅在 internal worker 执行，且强校验 `docstatus=0`。
- `docstatus=1/2` 或缺失 `docstatus` 视为异常并 fail closed。
- 权限拒绝与幂等冲突均有失败审计记录。
