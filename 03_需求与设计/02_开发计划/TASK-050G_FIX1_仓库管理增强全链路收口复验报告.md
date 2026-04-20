# TASK-050G_FIX1 仓库管理增强全链路收口复验报告

- 任务编号：TASK-050G_FIX1
- 执行角色：B Engineer
- 复验时间：2026-04-20 21:11 CST+8
- 结论：`READY_FOR_AUDIT`

## 1. 第398份阻塞原因复述

- 第398份结论：`BLOCKED / 高危1`。
- 阻塞点：`tests/test_warehouse_readonly_baseline.py::WarehouseReadonlyApiTest::test_no_write_route_registered` 仍沿用早期“warehouse 不得存在任何写路由”的断言。
- 与现状冲突：`TASK-050B / TASK-050C / TASK-050D_FIX1` 已审计通过并引入继承写路由，导致该旧断言误报。

## 2. 测试口径修复说明

修复文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py`

修复要点：
- 保留测试名 `test_no_write_route_registered`，语义改为“只允许已审计白名单写路由”。
- 收集 `/api/warehouse` 路由中的所有非只读方法 `(method, path)`。
- 断言非只读集合必须与白名单完全一致。
- 额外断言不允许 `PUT / PATCH / DELETE`。
- 因为使用集合严格比对，未来新增未登记写路由将直接触发失败。

关键代码位置：
- `tests/test_warehouse_readonly_baseline.py:273-296`

## 3. 已审计继承写路由白名单（含审计编号）

- `POST /api/warehouse/stock-entry-drafts`（TASK-050B，审计意见书第383份）
- `POST /api/warehouse/stock-entry-drafts/{draft_id}/cancel`（TASK-050B，审计意见书第383份）
- `POST /api/warehouse/internal/stock-entry-sync/run-once`（TASK-050D_FIX1，审计意见书第389份）
- `POST /api/warehouse/inventory-counts`（TASK-050C，审计意见书第385份）
- `POST /api/warehouse/inventory-counts/{count_id}/submit`（TASK-050C，审计意见书第385份）
- `POST /api/warehouse/inventory-counts/{count_id}/variance-review`（TASK-050C，审计意见书第385份）
- `POST /api/warehouse/inventory-counts/{count_id}/confirm`（TASK-050C，审计意见书第385份）
- `POST /api/warehouse/inventory-counts/{count_id}/cancel`（TASK-050C，审计意见书第385份）

## 4. pytest 复验结果

### 4.1 单点复验

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_readonly_baseline.py::WarehouseReadonlyApiTest::test_no_write_route_registered -v --tb=short
```

结果：
- `1 passed`。

### 4.2 仓库增强核心全量复验

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_warehouse_readonly_baseline.py \
  tests/test_warehouse_stock_entry_draft.py \
  tests/test_warehouse_inventory_count.py \
  tests/test_warehouse_stock_entry_worker.py \
  tests/test_warehouse_worker_permissions.py \
  tests/test_warehouse_traceability_readonly.py \
  tests/test_warehouse_export_diagnostic.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

结果：
- `79 passed, 1 warning`。

## 5. 权限动作与 inventory 回退扫描结果

命令：

```bash
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

结果：
- `warehouse:*` 权限动作在 `core/permissions.py`、`routers/warehouse.py`、`main.py`、`test_permissions_registry.py` 均命中。
- `inventory:*` 命中仅在负向测试输入（例如仅 `inventory:read` 访问仓库接口应 403），未发现授权回退实现。

## 6. ERPNext 写调用与高危写语义扫描结果

命令：

```bash
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

结果：
- 命中 `@router.post` 为已审计继承写路由（见第3节白名单），无新增越界写路由。
- 未发现本次修复引入 ERPNext 同步写调用。
- 未发现新增 `Stock Reconciliation / Stock Ledger Entry 直接写入 / GL Entry / Payment Entry / Purchase Invoice` 写语义。

## 7. TASK-050D / TASK-050E / TASK-050F 契约保持扫描结果

命令：

```bash
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

结果：
- TASK-050D 契约保持：`batch_size default=10, le=50` 与 `skipped_count` 命中保持。
- TASK-050E 契约保持：Batch/Serial 详情走单资源读取 `_get_resource_doc` 命中保持。
- TASK-050F 契约保持：`warehouse:export`、`warehouse:diagnostic` 与 main 映射命中保持。

## 8. 禁改目录与继承脏基线结果

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

结果：
- `.github / 02_源码 / 04_生产` diff：空。
- 继承脏基线路由文件 SHA-256：
  - `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 与任务单锁定值一致。

## 9. 回交建议

- 建议状态：`READY_FOR_AUDIT`
- 建议：回交 C 执行最终收口审计。
