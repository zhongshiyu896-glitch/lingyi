# TASK-050H 仓库管理增强本地封版复审证据

- 任务编号：TASK-050H
- 执行角色：B Engineer
- 执行时间：2026-04-20 21:34 CST+8
- 当前分支：`codex/sprint4-seal`
- 当前 HEAD：`f960443`
- 结论：**建议进入 C 本地封版审计**

## 1. 任务链路与审计闭环表

| 任务 | 审计结论 | 闭环状态 | 说明 |
| --- | --- | --- | --- |
| TASK-050A | 第378份 有问题 | 已闭环 | 由 TASK-050A_FIX1 修复权限口径 |
| TASK-050A_FIX1 | 第381份 通过 | 通过 | 仓库权限口径收敛完成 |
| TASK-050B | 第383份 通过 | 通过 | Stock Entry 草稿 + Outbox 本地基线 |
| TASK-050C | 第385份 通过 | 通过 | 盘点草稿/提交/复核/确认/取消状态机 |
| TASK-050D | 第387份 有问题 | 已闭环 | 由 TASK-050D_FIX1 收紧 run-once 契约 |
| TASK-050D_FIX1 | 第389份 通过 | 通过 | `batch_size` 与 `skipped_count` 契约通过 |
| TASK-050E | 第391份 有问题 | 已闭环 | 由后续 FIX1/FIX2 连续修复 |
| TASK-050E_FIX1 | 第393份 有问题 | 已闭环 | 由 TASK-050E_FIX2 完成详情读源修复 |
| TASK-050E_FIX2 | 第395份 通过 | 通过 | Batch/Serial 详情单资源读取通过 |
| TASK-050F | 第397份 通过 | 通过 | 仓库导出与诊断基线通过 |
| TASK-050G | 第398份 阻塞 | 已闭环 | 由 TASK-050G_FIX1 修复测试口径 |
| TASK-050G_FIX1 | 第400份 通过 | 通过 | 全链路收口复验通过 |

## 2. 已完成能力清单

1. 仓库只读台账与预警能力：已闭环（050A_FIX1）。
2. Stock Entry 草稿 + Outbox 状态链路：已闭环（050B）。
3. 库存盘点草稿与差异复核状态机：已闭环（050C）。
4. internal run-once worker 契约（default/le/skipped_count）：已闭环（050D_FIX1）。
5. Batch/Serial 只读追溯与详情单资源读取：已闭环（050E_FIX2）。
6. 仓库 CSV 导出与诊断：已闭环（050F）。
7. 仓库增强全链路收口验证与测试口径修复：已闭环（050G_FIX1）。

## 3. 后端测试结果

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

结果：`79 passed, 1 warning`。

## 4. Python 编译结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

结果：通过（无编译错误输出）。

## 5. 权限动作与 inventory 回退扫描结果

执行命令：

```bash
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

结果：
- `warehouse:*` 动作在权限常量、路由、main 映射、注册测试中命中完整。
- `inventory:*` 命中仅在测试负向输入（仅 inventory 权限访问仓库接口返回 403）场景，未发现将 inventory 权限作为 warehouse 授权回退的实现。

## 6. 写路由白名单扫描结果

执行命令：

```bash
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

结果命中仅为已审计继承 `POST` 路由：
- `/stock-entry-drafts`
- `/stock-entry-drafts/{draft_id}/cancel`
- `/internal/stock-entry-sync/run-once`
- `/inventory-counts`
- `/inventory-counts/{count_id}/submit`
- `/inventory-counts/{count_id}/variance-review`
- `/inventory-counts/{count_id}/confirm`
- `/inventory-counts/{count_id}/cancel`

结论：未命中 `PUT/PATCH/DELETE`；未发现未登记新增写路由。

## 7. ERPNext 写调用与高危写语义扫描结果

执行命令：

```bash
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
```

结果：
- 命中项为已审计继承路径中的 `POST` 路由与 `/submit` 路径字面量。
- 未发现本地任务链之外新增 ERPNext 同步写调用。
- 未发现新增 `Stock Reconciliation / Stock Ledger Entry 直接写入 / GL Entry / Payment Entry / Purchase Invoice` 写语义。

## 8. TASK-050D / 050E / 050F 契约保持扫描结果

执行命令：

```bash
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

结果：
- 050D 契约保持：`batch_size default=10, le=50` 与 `skipped_count` 保持。
- 050E 契约保持：Batch/Serial 详情读取仍走 `_get_resource_doc` 单资源路径。
- 050F 契约保持：`warehouse:export`、`warehouse:diagnostic` 与 `main.py` 动作映射保持。

## 9. 禁改目录与继承脏基线结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

结果：
- `.github / 02_源码 / 04_生产` diff 为空。
- `06_前端/lingyi-pc/src/router/index.ts` SHA-256 = `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`，与锁定值一致。
- `git status` 仍显示该前端文件与 `02_源码/` 的继承脏基线，不属于本任务新增改动。

## 10. 剩余风险

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交需另开白名单提交任务。
5. 当前 Stock Entry / 库存盘点仍属本地草稿与受控 outbox 能力，不代表生产库存写入已放行。

## 11. 是否建议进入 C 本地封版审计

**建议进入 C 本地封版审计**。
