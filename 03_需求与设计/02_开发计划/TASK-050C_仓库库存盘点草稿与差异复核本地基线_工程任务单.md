# TASK-050C 仓库库存盘点草稿与差异复核本地基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-050C
- 任务名称：仓库库存盘点草稿与差异复核本地基线
- 执行角色：B Engineer
- 审计角色：C Auditor
- 输出角色：A Technical Architect
- 优先级：P1
- 前置依赖：TASK-050B 审计通过；TASK-018A 仓库管理增强边界设计
- 当前定位：仓库管理增强方向第三张实现任务，仅允许本地盘点草稿、盘点明细、差异复核与状态机，不允许 Stock Reconciliation 或 ERPNext 写入

## 2. 任务目标

实现仓库库存盘点的本地草稿与差异复核基线。

本任务只允许：

1. 本地盘点单草稿创建。
2. 盘点明细录入与差异计算。
3. 差异复核状态推进。
4. 盘点单取消。
5. 只读查询盘点单详情与列表。
6. 权限与资源范围校验。
7. 本地 migration 与测试。

本任务禁止：

1. 创建 ERPNext Stock Reconciliation。
2. 创建或提交 ERPNext Stock Entry。
3. 直接写 Stock Ledger Entry。
4. 自动调账、自动财务落账、自动采购或调拨建议。
5. push / PR / tag / 生产发布。

## 3. 允许修改范围

后端允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_050c_*.py
```

测试允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_inventory_count.py
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
ERPNext Stock Reconciliation
ERPNext Stock Entry submit
直接写 Stock Ledger Entry
ERPNext GL Entry
ERPNext Payment Entry
ERPNext Purchase Invoice
同步 ERPNext 写调用
自动调账
自动财务落账
自动采购建议
自动调拨建议
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
/api/resource/Stock Reconciliation
/api/resource/Stock Entry
/api/resource/Stock Ledger Entry
```

## 5. 数据模型要求

新增本地盘点单表，建议命名：

```text
LyWarehouseInventoryCount
```

字段至少包含：

```text
id
company
warehouse
status
count_no
count_date
created_by
created_at
submitted_by
submitted_at
reviewed_by
reviewed_at
cancelled_by
cancelled_at
cancel_reason
remark
```

状态枚举：

```text
draft
counted
variance_review
confirmed
cancelled
```

新增盘点明细表，建议命名：

```text
LyWarehouseInventoryCountItem
```

字段至少包含：

```text
id
count_id
item_code
batch_no
serial_no
system_qty
counted_qty
variance_qty
variance_reason
review_status
```

差异复核状态枚举：

```text
pending
accepted
rejected
```

## 6. 必须实现接口

### 6.1 创建盘点草稿

```text
POST /api/warehouse/inventory-counts
```

请求字段：

```text
company
warehouse
count_date
items[]
remark
```

`items[]` 字段：

```text
item_code
batch_no
serial_no
system_qty
counted_qty
variance_reason
```

要求：

1. 必须校验 `warehouse:inventory_count`。
2. 必须校验 `company / warehouse / item_code` 资源范围。
3. `counted_qty < 0` 返回 400。
4. 自动计算 `variance_qty = counted_qty - system_qty`。
5. 有差异时 `variance_reason` 必填。
6. 初始状态为 `draft`。
7. 不得调用 ERPNext。

### 6.2 提交盘点结果

```text
POST /api/warehouse/inventory-counts/{count_id}/submit
```

要求：

1. 必须校验 `warehouse:inventory_count`。
2. 仅允许 `draft -> counted`。
3. 已 `cancelled / confirmed` 返回 409。
4. 不得调用 ERPNext。

### 6.3 进入差异复核

```text
POST /api/warehouse/inventory-counts/{count_id}/variance-review
```

要求：

1. 必须校验 `warehouse:inventory_count`。
2. 仅允许 `counted -> variance_review`。
3. 无差异行时可直接返回 400，提示无需差异复核。
4. 不得调用 ERPNext。

### 6.4 确认盘点单

```text
POST /api/warehouse/inventory-counts/{count_id}/confirm
```

要求：

1. 必须校验 `warehouse:inventory_count`。
2. 仅允许 `variance_review -> confirmed`。
3. 有未复核差异行时返回 409。
4. 确认后不得修改数量字段。
5. 不得创建 Stock Reconciliation。
6. 不得调用 ERPNext。

### 6.5 取消盘点单

```text
POST /api/warehouse/inventory-counts/{count_id}/cancel
```

请求字段：

```text
reason
```

要求：

1. 必须校验 `warehouse:inventory_count`。
2. 仅允许 `draft / counted / variance_review` 取消。
3. 已 `confirmed / cancelled` 返回 409。
4. 不得调用 ERPNext。

### 6.6 查询盘点详情

```text
GET /api/warehouse/inventory-counts/{count_id}
```

要求：

1. 必须校验 `warehouse:read`。
2. 必须执行 company / warehouse 范围校验。
3. 返回盘点单、明细、差异统计。

### 6.7 查询盘点列表

```text
GET /api/warehouse/inventory-counts
```

查询参数：

```text
company
warehouse
status
from_date
to_date
item_code
```

要求：

1. 必须校验 `warehouse:read`。
2. 必须执行 company / warehouse 范围过滤。
3. `from_date > to_date` 返回 400。

## 7. 权限注册要求

确保统一权限注册表包含：

```text
warehouse:inventory_count
```

不得复用：

```text
inventory:write
inventory:read
```

作为盘点写动作授权。

## 8. 迁移要求

新增 Alembic migration：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_050c_*.py
```

要求：

1. 只新增盘点单与盘点明细表。
2. 不改历史 migration。
3. `upgrade()` 和 `downgrade()` 必须完整。
4. 需要索引：`company / warehouse / status / count_date / count_id / item_code`。
5. `count_no` 在同 company 范围内唯一。

## 9. 测试要求

新增测试：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_inventory_count.py
```

必须覆盖：

1. 有 `warehouse:inventory_count` 可创建盘点草稿。
2. 仅有 `inventory:write` 不得创建盘点草稿，返回 403。
3. `counted_qty < 0` 返回 400。
4. 有差异但无 `variance_reason` 返回 400。
5. `draft -> counted` 成功。
6. `counted -> variance_review` 成功。
7. 有未复核差异行时确认返回 409。
8. 差异复核完成后 `variance_review -> confirmed` 成功。
9. confirmed 后不得修改数量字段。
10. cancel 成功，重复 cancel 返回 409。
11. 列表 company / warehouse 过滤生效。
12. 非法日期范围返回 400。
13. 负向扫描证明无 ERPNext 写调用。
14. 负向扫描证明无 Stock Reconciliation / Stock Entry submit / GL / Payment / Purchase Invoice 语义。

更新权限注册测试：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py
```

必须覆盖：

```text
warehouse:inventory_count
```

## 10. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f 07_后端/lingyi_service/tests/test_warehouse_inventory_count.py

rg -n 'inventory-counts|warehouse:inventory_count|variance_review|confirmed|cancelled' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py \
  07_后端/lingyi_service/app/core/permissions.py \
  07_后端/lingyi_service/tests/test_warehouse_inventory_count.py

rg -n 'LyWarehouseInventoryCount|LyWarehouseInventoryCountItem|count_no|variance_qty' \
  07_后端/lingyi_service/app/models/warehouse.py \
  07_后端/lingyi_service/migrations/versions

! rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource/Stock Reconciliation|/api/resource/Stock Entry|/api/resource/Stock Ledger Entry' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py

! rg -n 'submit_stock_entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|docstatus.*1' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py \
  07_后端/lingyi_service/app/models/warehouse.py

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_warehouse_inventory_count.py \
  tests/test_permissions_registry.py \
  -v --tb=short

cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
```

## 11. 完成回报模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050C
ROLE: B Engineer

CHANGED_FILES:
- 列出真实变更文件

EVIDENCE:
- 盘点单模型已实现：路径 + 行号
- 盘点明细模型已实现：路径 + 行号
- 创建盘点草稿接口已实现：路径 + 行号
- 提交/差异复核/确认/取消状态机已实现：路径 + 行号
- warehouse:inventory_count 已注册：路径 + 行号
- 仅 inventory:write 无法创建盘点草稿测试已覆盖：路径 + 行号
- pytest 结果：
- ERPNext 写调用负向扫描结果：
- Stock Reconciliation / Stock Entry submit / GL / Payment / Purchase Invoice 负向扫描结果：
- 禁改目录 diff 结果：

BLOCKERS:
- 无；如有必须写明

NEXT_ROLE:
- C Auditor
```
