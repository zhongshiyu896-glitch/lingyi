# TASK-050I 仓库管理增强本地封版提交证据

- 任务编号：TASK-050I
- 任务名称：仓库管理增强本地封版白名单提交
- 执行角色：B Engineer
- 执行时间：2026-04-20 21:34 CST+8
- 当前分支：`codex/sprint4-seal`
- 提交前 HEAD：`f960443`

## 1. 前置审计结论

- 前置审计：审计意见书第402份，`TASK-050H PASS`。
- 当前任务目标：在不 push/PR/tag/发布前提下，按固定白名单生成本地封版 commit。

## 2. 仓库增强审计闭环摘要（第378~402份关键结论）

1. `TASK-050A` 第378份有问题，已由 `TASK-050A_FIX1`（第381份）闭环通过。
2. `TASK-050B`（第383份）通过。
3. `TASK-050C`（第385份）通过。
4. `TASK-050D` 第387份有问题，已由 `TASK-050D_FIX1`（第389份）闭环通过。
5. `TASK-050E` 第391份有问题、`TASK-050E_FIX1` 第393份有问题，已由 `TASK-050E_FIX2`（第395份）闭环通过。
6. `TASK-050F`（第397份）通过。
7. `TASK-050G` 第398份阻塞，已由 `TASK-050G_FIX1`（第400份）闭环通过。
8. `TASK-050H` 本地封版复审通过（第402份）。

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

结果：通过（无错误输出）。

## 5. 前端 typecheck 结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

结果：通过（`vue-tsc --noEmit` 正常返回）。

## 6. 权限与回退扫描结果

执行命令：

```bash
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

结果：
- `warehouse:*` 动作命中完整。
- `inventory:*` 命中仅见于负向测试输入（验证 inventory 权限不可替代 warehouse 权限），无授权回退实现证据。

## 7. 写路由白名单扫描结果

执行命令：

```bash
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

结果：
- 仅命中 8 条已审计继承 `POST` 路由（050B/050C/050D_FIX1）。
- 未命中 `PUT/PATCH/DELETE`。
- 未发现未审计新增写路由。

## 8. ERPNext 写调用与高危写语义扫描结果

执行命令：

```bash
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
```

结果：
- 命中为继承写路由与既有 `/submit` 路径字面量。
- 未发现新增 ERPNext 同步写调用。
- 未发现新增 `Stock Reconciliation / Stock Ledger Entry 直接写入 / GL Entry / Payment Entry / Purchase Invoice` 写语义。

## 9. TASK-050D / TASK-050E / TASK-050F 契约保持结果

执行命令：

```bash
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

结果：
- 050D 契约保持：`batch_size default=10, le=50` 与 `skipped_count` 保持。
- 050E 契约保持：Batch/Serial 详情读取保持单资源 `_get_resource_doc`。
- 050F 契约保持：`warehouse:export/warehouse:diagnostic` 与 `main.py` 动作映射保持。

## 10. 禁改目录与 router 哈希结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

结果：
- `.github / 02_源码 / 04_生产` diff 为空。
- `06_前端/lingyi-pc/src/router/index.ts` SHA-256 = `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`（锁定值一致）。

## 11. staged 白名单清单

以下清单由 `git diff --cached --name-only` 在显式 `git add -- <白名单>` 后生成（见本文件最终版本）。

## 12. 残余风险

1. 本地封版提交不等同远端 push/PR 完成。
2. 本地封版提交不等同生产发布。
3. 本地封版提交不等同 ERPNext 生产联调完成。
4. 工作树仍存在历史未跟踪目录与继承脏基线，后续任何提交需继续白名单控制。


### 11.1 staged 实际清单（git diff --cached --name-only）
```text
00_交接与日志/HANDOVER_STATUS.md
03_需求与设计/01_架构设计/架构师会话日志.md
03_需求与设计/02_开发计划/TASK-050A_仓库库存只读台账与预警基线_工程任务单.md
03_需求与设计/02_开发计划/TASK-050B_仓库StockEntry草稿Outbox本地基线_工程任务单.md
03_需求与设计/02_开发计划/TASK-050C_仓库库存盘点草稿与差异复核本地基线_工程任务单.md
03_需求与设计/02_开发计划/TASK-050D_FIX1_run_once契约收紧_工程任务单.md
03_需求与设计/02_开发计划/TASK-050D_仓库StockEntryOutboxWorker草稿创建_工程任务单.md
03_需求与设计/02_开发计划/TASK-050E_FIX1_BatchSerial原始字段契约修复_工程任务单.md
03_需求与设计/02_开发计划/TASK-050E_FIX2_BatchSerial详情单资源读取_工程任务单.md
03_需求与设计/02_开发计划/TASK-050E_仓库批次序列号只读追溯基线_工程任务单.md
03_需求与设计/02_开发计划/TASK-050F_仓库只读导出与诊断基线_工程任务单.md
03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库收口写路由继承口径修复_工程任务单.md
03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md
03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证_工程任务单.md
03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md
03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审_工程任务单.md
03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md
03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md
03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版白名单提交_工程任务单.md
03_需求与设计/02_开发计划/工程师会话日志.md
03_需求与设计/05_审计记录/审计官会话日志.md
06_前端/lingyi-pc/src/api/warehouse.ts
06_前端/lingyi-pc/src/router/index.ts
06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue
07_后端/lingyi_service/app/core/permissions.py
07_后端/lingyi_service/app/main.py
07_后端/lingyi_service/app/models/warehouse.py
07_后端/lingyi_service/app/routers/warehouse.py
07_后端/lingyi_service/app/schemas/warehouse.py
07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py
07_后端/lingyi_service/app/services/warehouse_export_service.py
07_后端/lingyi_service/app/services/warehouse_service.py
07_后端/lingyi_service/migrations/versions/task_050b_create_warehouse_stock_entry_outbox.py
07_后端/lingyi_service/migrations/versions/task_050c_create_warehouse_inventory_count.py
07_后端/lingyi_service/tests/test_permissions_registry.py
07_后端/lingyi_service/tests/test_warehouse_export_diagnostic.py
07_后端/lingyi_service/tests/test_warehouse_inventory_count.py
07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py
07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py
07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py
07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py
07_后端/lingyi_service/tests/test_warehouse_worker_permissions.py
```
