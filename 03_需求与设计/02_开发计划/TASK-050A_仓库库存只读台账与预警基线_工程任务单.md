# TASK-050A 仓库库存只读台账与预警基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-050A
- 任务名称：仓库库存只读台账与预警基线
- 执行角色：B Engineer
- 审计角色：C Auditor
- 输出角色：A Technical Architect
- 优先级：P1
- 当前阶段：Sprint 4 封版后按规划表进入方向 3「仓库管理增强」的第一张实现任务
- 前置依据：`Sprint4_规划草案.md` 方向 3；`TASK-018A_仓库管理增强边界设计.md`；`TASK-018_仓库管理增强边界设计.md`

## 2. 任务目标

实现仓库管理增强第一阶段只读基线：

1. 新增仓库库存台账只读接口。
2. 新增库存预警只读接口。
3. 新增仓库维度聚合接口。
4. 保持 `company / warehouse / item_code` 范围过滤。
5. 严禁 `Stock Entry / Stock Reconciliation / Stock Ledger Entry` 写入。
6. 严禁 ERPNext 同步写调用。
7. 严禁 push / PR / tag / 生产发布。

## 3. 允许修改范围

后端允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
```

前端允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
```

测试允许新增或修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py
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

禁止行为：

```text
git push
gh auth refresh
gh auth login
gh pr create
git tag
生产发布
新增 Stock Entry 写接口
新增 Stock Reconciliation 写接口
直接写 Stock Ledger Entry
直接调用 ERPNext 写接口
新增 outbox
新增 worker
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
/api/resource/Stock Entry 写入
/api/resource/Stock Reconciliation 写入
/api/resource/Stock Ledger Entry 写入
```

## 5. 必须实现接口

### 5.1 库存台账只读接口

```text
GET /api/warehouse/stock-ledger
```

查询参数：

```text
company
warehouse
item_code
from_date
to_date
page
page_size
```

返回字段：

```text
company
warehouse
item_code
posting_date
voucher_type
voucher_no
actual_qty
qty_after_transaction
valuation_rate
```

要求：

1. 仅只读。
2. 必须执行 `company` 过滤。
3. 必须执行 `warehouse` 权限过滤。
4. `from_date > to_date` 返回 400。
5. ERPNext 不可用或返回字段 malformed 时 fail-closed。

### 5.2 仓库库存聚合接口

```text
GET /api/warehouse/stock-summary
```

查询参数：

```text
company
warehouse
item_code
```

返回字段：

```text
company
warehouse
item_code
actual_qty
projected_qty
reserved_qty
ordered_qty
reorder_level
safety_stock
is_below_reorder
is_below_safety
threshold_missing
```

要求：

1. 按 `company + warehouse + item_code` 聚合。
2. 不得包含无 `company` 或无 `warehouse` 的数据。
3. 阈值缺失时不得伪造安全库存结论，返回 `threshold_missing=true`。

### 5.3 库存预警接口

```text
GET /api/warehouse/alerts
```

查询参数：

```text
company
warehouse
item_code
alert_type
```

支持预警类型：

```text
low_stock
below_safety
overstock
stale_stock
```

返回字段：

```text
company
warehouse
item_code
alert_type
current_qty
threshold_qty
gap_qty
last_movement_date
severity
```

要求：

1. 只读计算。
2. 不自动创建采购建议。
3. 不自动创建调拨建议。
4. 不写 ERPNext。
5. 不写本地业务表。

## 6. 前端要求

新增仓库看板页面：

```text
/warehouse
```

页面包含：

1. 库存台账表格。
2. 库存聚合表格。
3. 库存预警列表。
4. 过滤条件：`company / warehouse / item_code / from_date / to_date`。
5. 低库存和安全库存不足需要高亮。
6. 页面只允许查询，不显示任何“创建 / 确认 / 调拨 / 盘点 / 写入”按钮。

## 7. 权限要求

后端必须校验：

```text
warehouse:read
warehouse:alert_read
```

资源范围必须包含：

```text
company
warehouse
item_code
```

无权限时返回：

```text
403
```

越权仓库数据不得返回。

## 8. 测试要求

测试文件：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py
```

必须覆盖：

1. `GET /api/warehouse/stock-ledger` 正常返回。
2. `GET /api/warehouse/stock-summary` 正常聚合。
3. `GET /api/warehouse/alerts` 正常返回低库存预警。
4. `company` 过滤生效。
5. `warehouse` 权限过滤生效。
6. 非法日期范围返回 400。
7. ERPNext malformed 数据 fail-closed。
8. 不存在任何写接口。
9. 不存在 ERPNext 写调用。

## 9. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f 07_后端/lingyi_service/app/routers/warehouse.py
test -f 07_后端/lingyi_service/app/services/warehouse_service.py
test -f 07_后端/lingyi_service/app/schemas/warehouse.py
test -f 07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py

rg -n 'stock-ledger|stock-summary|alerts|warehouse:read|warehouse:alert_read' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py

! rg -n '@router\.(post|put|patch|delete)' \
  07_后端/lingyi_service/app/routers/warehouse.py

! rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource/Stock Entry|/api/resource/Stock Reconciliation|/api/resource/Stock Ledger Entry' \
  07_后端/lingyi_service/app/routers/warehouse.py \
  07_后端/lingyi_service/app/services/warehouse_service.py \
  07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_readonly_baseline.py -v --tb=short

cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
```

## 10. 完成回报模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050A
ROLE: B Engineer

CHANGED_FILES:
- 列出真实变更文件

EVIDENCE:
- 仓库库存台账只读接口已实现：路径 + 行号
- 仓库库存聚合接口已实现：路径 + 行号
- 库存预警接口已实现：路径 + 行号
- company / warehouse / item_code 过滤已实现：路径 + 行号
- 前端仓库看板已实现：路径 + 行号
- 后端测试结果：pytest 输出
- 前端 typecheck 结果：输出
- 写接口负向扫描：0 命中
- ERPNext 写调用负向扫描：0 命中
- 禁改目录 diff：空

BLOCKERS:
- 无；如有必须写明

NEXT_ROLE:
- C Auditor
```
