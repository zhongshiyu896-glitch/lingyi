# TASK-050B 仓库 Stock Entry 草稿 Outbox 本地基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-050B
- 任务名称：仓库 Stock Entry 草稿 Outbox 本地基线
- 执行角色：B Engineer
- 审计角色：C Auditor
- 输出角色：A Technical Architect
- 优先级：P0
- 前置依赖：TASK-050A_FIX1 审计通过；TASK-018A 仓库管理增强边界设计
- 当前定位：仓库管理增强方向第二张实现任务，仅允许本地草稿与 Outbox 入队，不允许真实 ERPNext submit 或生产发布

## 2. 任务目标

在 `TASK-050A` 仓库只读基线通过后，实现仓库 Stock Entry 草稿写入的本地 Outbox 基线。

本任务只允许：

1. 本地 Stock Entry 草稿落库。
2. 本地 Stock Entry Outbox 入队。
3. 草稿创建、草稿取消、草稿详情、Outbox 状态查询。
4. 权限与资源范围校验。
5. 本地 migration 与测试。

本任务禁止：

1. 同步调用 ERPNext 写接口。
2. submit ERPNext Stock Entry。
3. Stock Reconciliation / GL / Payment / Purchase Invoice 写入。
4. push / PR / tag / 生产发布。

## 3. 允许修改范围

后端允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_050b_*.py
```

测试允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py
```

日志允许追加：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
```

## 4. 禁止范围

禁止修改：

```text
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/04_生产/**
```

禁止执行：

```text
git push
gh auth refresh
gh auth login
gh pr create
git tag
生产发布
```

禁止实现：

```text
ERPNext Stock Entry submit
ERPNext Stock Reconciliation
ERPNext GL Entry
ERPNext Payment Entry
ERPNext Purchase Invoice
同步 ERPNext 写调用
自动调拨
自动采购建议
自动生产入库
自动财务落账
```

禁止出现写调用：

```text
requests.post
requests.put
requests.patch
requests.delete
httpx.post
httpx.put
httpx.patch
httpx.delete
/api/resource/Stock Entry
/api/resource/Stock Reconciliation
/api/resource/Stock Ledger Entry
```

## 5. 数据模型要求

新增本地草稿表，建议命名：

```text
LyWarehouseStockEntryDraft
```

字段至少包含：

```text
id
company
purpose
source_type
source_id
source_warehouse
target_warehouse
status
created_by
created_at
cancelled_by
cancelled_at
cancel_reason
idempotency_key
event_key
```

状态枚举：

```text
draft
pending_outbox
cancelled
```

新增明细表，建议命名：

```text
LyWarehouseStockEntryDraftItem
```

字段至少包含：

```text
id
draft_id
item_code
qty
uom
batch_no
serial_no
source_warehouse
target_warehouse
```

新增 Outbox 表，建议命名：

```text
LyWarehouseStockEntryOutboxEvent
```

字段至少包含：

```text
id
draft_id
event_type
event_key
payload
status
retry_count
external_ref
error_message
created_at
processed_at
```

Outbox 状态枚举：

```text
in_pending
processing
succeeded
failed
dead
cancelled
```

## 6. 必须实现接口

### 6.1 创建 Stock Entry 草稿

```text
POST /api/warehouse/stock-entry-drafts
```

请求字段：

```text
company
purpose
source_type
source_id
source_warehouse
target_warehouse
items[]
idempotency_key
```

`items[]` 字段：

```text
item_code
qty
uom
batch_no
serial_no
source_warehouse
target_warehouse
```

要求：

1. 必须校验 `warehouse:stock_entry_draft`。
2. 必须校验 `company / warehouse / item_code` 资源范围。
3. `qty <= 0` 返回 400。
4. `purpose` 只允许 `Material Issue / Material Receipt / Material Transfer`。
5. `Material Issue` 必须有 `source_warehouse`。
6. `Material Receipt` 必须有 `target_warehouse`。
7. `Material Transfer` 必须同时有 `source_warehouse / target_warehouse`。
8. 创建本地草稿。
9. 同步创建本地 Outbox 事件，状态为 `in_pending`。
10. 不得调用 ERPNext。
11. 返回草稿详情和 Outbox 状态。

### 6.2 取消 Stock Entry 草稿

```text
POST /api/warehouse/stock-entry-drafts/{draft_id}/cancel
```

请求字段：

```text
reason
```

要求：

1. 必须校验 `warehouse:stock_entry_cancel`。
2. 仅允许取消 `draft / pending_outbox`。
3. 已 `cancelled` 再次取消返回 409。
4. 取消草稿时同步将未处理 Outbox 事件标记为 `cancelled`。
5. 不得调用 ERPNext。

### 6.3 查询草稿详情

```text
GET /api/warehouse/stock-entry-drafts/{draft_id}
```

要求：

1. 必须校验 `warehouse:read`。
2. 必须执行 company / warehouse 范围校验。
3. 返回草稿、明细、Outbox 状态。

### 6.4 查询 Outbox 状态

```text
GET /api/warehouse/stock-entry-drafts/{draft_id}/outbox-status
```

要求：

1. 必须校验 `warehouse:read`。
2. 返回 `draft_id / event_id / event_type / status / retry_count / external_ref / error_message / created_at / processed_at`。

## 7. 权限注册要求

在统一权限注册表中补齐：

```text
warehouse:stock_entry_draft
warehouse:stock_entry_cancel
```

不得复用：

```text
inventory:read
inventory:write
```

作为仓库写动作授权。

## 8. 迁移要求

新增 Alembic migration：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_050b_*.py
```

要求：

1. 只新增仓库草稿 / 明细 / Outbox 表。
2. 不改历史 migration。
3. `upgrade()` 和 `downgrade()` 必须完整。
4. 需要索引：`company / status / event_key / idempotency_key / draft_id`。
5. `event_key` 必须唯一。
6. `idempotency_key` 在同 company 范围内必须可防重。

## 9. 测试要求

新增测试：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py
```

必须覆盖：

1. 有 `warehouse:stock_entry_draft` 可创建草稿。
2. 创建草稿后自动生成 `in_pending` Outbox。
3. `qty <= 0` 返回 400。
4. 无 `warehouse:stock_entry_draft` 返回 403。
5. 仅有 `inventory:write` 不得创建草稿，返回 403。
6. company 越权返回 403 或 404。
7. warehouse 越权返回 403 或 404。
8. `cancel` 成功后草稿为 `cancelled`。
9. `cancel` 后未处理 Outbox 为 `cancelled`。
10. 重复 cancel 返回 409。
11. outbox-status 正确返回。
12. 负向扫描证明无 ERPNext 写调用。
13. 负向扫描证明无 submit 语义。

更新权限注册测试：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py
```

必须覆盖：

```text
warehouse:stock_entry_draft
warehouse:stock_entry_cancel
```

## 10. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f 07_后端/lingyi_service/app/models/warehouse.py
test -f 07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py

rg -n 'stock-entry-drafts|outbox-status|warehouse:stock_entry_draft|warehouse:stock_entry_cancel' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py \
  07_后端/lingyi_service/app/core/permissions.py \
  07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py

rg -n 'LyWarehouseStockEntryDraft|LyWarehouseStockEntryOutboxEvent|event_key|idempotency_key' \
  07_后端/lingyi_service/app/models/warehouse.py \
  07_后端/lingyi_service/migrations/versions

! rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource/Stock Entry|/api/resource/Stock Reconciliation|/api/resource/Stock Ledger Entry' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py

! rg -n 'submit|submit_stock_entry|docstatus.*1|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py \
  07_后端/lingyi_service/app/models/warehouse.py

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_warehouse_stock_entry_draft.py \
  tests/test_permissions_registry.py \
  -v --tb=short

cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
```

## 11. 完成回报模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050B
ROLE: B Engineer

CHANGED_FILES:
- 列出真实变更文件

EVIDENCE:
- Stock Entry 草稿模型已实现：路径 + 行号
- Stock Entry Outbox 模型已实现：路径 + 行号
- 创建草稿接口已实现：路径 + 行号
- 取消草稿接口已实现：路径 + 行号
- outbox-status 接口已实现：路径 + 行号
- warehouse:stock_entry_draft / warehouse:stock_entry_cancel 已注册：路径 + 行号
- 仅 inventory 权限无法创建草稿的测试已覆盖：路径 + 行号
- pytest 结果：
- ERPNext 写调用负向扫描结果：
- submit / Stock Reconciliation / GL / Payment / Purchase Invoice 负向扫描结果：
- 禁改目录 diff 结果：

BLOCKERS:
- 无；如有必须写明

NEXT_ROLE:
- C Auditor
```
