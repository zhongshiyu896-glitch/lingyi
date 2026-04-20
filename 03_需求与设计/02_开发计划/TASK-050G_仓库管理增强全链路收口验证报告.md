# TASK-050G 仓库管理增强全链路收口验证报告

- 任务编号：TASK-050G
- 执行角色：B Engineer
- 生成时间：2026-04-20 20:57 CST+8
- 结论：`BLOCKED`（按任务门禁，不修代码，仅回报失败证据）

## 1. 任务链审计编号核对表

| 任务 | 审计结论 | 核对结果 |
| --- | --- | --- |
| TASK-050A_FIX1 | 审计意见书第381份 通过 | 已核对 |
| TASK-050B | 审计意见书第383份 通过 | 已核对 |
| TASK-050C | 审计意见书第385份 通过 | 已核对 |
| TASK-050D_FIX1 | 审计意见书第389份 通过 | 已核对 |
| TASK-050E_FIX2 | 审计意见书第395份 通过 | 已核对 |
| TASK-050F | 审计意见书第397份 通过 | 已核对 |

## 2. 后端测试命令与结果摘要

执行命令：

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

结果摘要：
- 总计：`79` 项
- 通过：`78`
- 失败：`1`
- 失败用例：`tests/test_warehouse_readonly_baseline.py::WarehouseReadonlyApiTest::test_no_write_route_registered`
- 失败原因：该用例断言 `/api/warehouse` 下路由方法必须是 `GET/HEAD/OPTIONS` 子集；当前仓库存在已审计继承写路由（来自 TASK-050B/050C/050D），断言不成立。

## 3. 权限动作与 inventory 回退扫描结论

执行命令：

```bash
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" \
  app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py

rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" \
  app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

结论：
- `warehouse:*` 权限动作在 `app/core/permissions.py`、`app/routers/warehouse.py`、`app/main.py`、`tests/test_permissions_registry.py` 均有命中。
- `inventory:*` 命中仅出现在测试负向断言（例如仅 `inventory:read` 访问仓库接口应 `403`、仅 `inventory:write` 不可创建草稿），未发现授权回退路径。

## 4. ERPNext 写调用与高危写语义扫描结论

执行命令：

```bash
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" \
  app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py

rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

结论：
- 命中项以 `app/routers/warehouse.py` 的既有 `@router.post` 路由为主（如 `stock-entry-drafts`、`inventory-counts`、`internal run-once`）。
- 未发现本任务新增 ERPNext 同步写调用证据。
- 未发现本任务新增 `Stock Reconciliation / GL Entry / Payment Entry / Purchase Invoice` 写语义证据。

## 5. TASK-050D run-once 契约保持结论

执行命令：

```bash
rg -n "batch_size.*default=10|le=50|skipped_count" \
  app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
```

结论：
- `batch_size`：`Field(default=10, ge=1, le=50)` 保持。
- 响应字段 `skipped_count` 在 schema/service/tests 均保持并有覆盖。

## 6. TASK-050E Batch/Serial 详情单资源读取保持结论

执行命令：

```bash
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" \
  app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
```

结论：
- 详情读取仍走 `_get_resource_doc(doctype="Batch"|"Serial No")`。
- 测试中存在单资源读取断言（如 `/api/resource/Batch/BATCH-001`）。

## 7. TASK-050F export/diagnostic 契约保持结论

执行命令：

```bash
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" \
  app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

结论：
- `warehouse:export`、`warehouse:diagnostic` 在 router/main/tests 命中保持。
- `/api/warehouse/export` 与 `/api/warehouse/diagnostic` 的映射与测试保持。

## 8. 禁改目录与继承脏基线结论

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

结论：
- `.github / 02_源码 / 04_生产` 的 `git diff`：空。
- `06_前端/lingyi-pc/src/router/index.ts` SHA-256：
  - `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
  - 与任务单锁定值一致。
- `git status` 显示该前端路由文件为继承脏基线改动，本任务未触碰。

## 9. 剩余风险

1. `tests/test_warehouse_readonly_baseline.py::test_no_write_route_registered` 的断言口径与当前仓库已通过审计的写路由现实冲突，导致全链路收口测试无法全绿。
2. 在本任务禁止改业务/测试代码的前提下无法消除此冲突。

## 10. 是否建议进入 C 最终收口审计

建议：`否（BLOCKED）`

原因：核心后端测试存在 1 个失败，且按 TASK-050G 门禁不得在本任务内修复代码；需要 A 另开 fix pass 收敛该测试口径后再复跑收口。
