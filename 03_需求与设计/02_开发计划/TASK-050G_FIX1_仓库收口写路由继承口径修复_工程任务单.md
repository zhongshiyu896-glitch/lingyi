# TASK-050G_FIX1 仓库收口写路由继承口径修复 工程任务单

## 1. 基本信息

- 任务编号：TASK-050G_FIX1
- 任务名称：仓库收口写路由继承口径修复
- 模块：仓库管理增强 / 全链路收口验证
- 角色：B Engineer
- 优先级：P1
- 前置依赖：TASK-050G 审计意见书第398份 `BLOCKED / 高危1`
- 当前定位：只修复仓库全链路收口测试中的旧口径断言，让测试识别 `TASK-050B / TASK-050C / TASK-050D_FIX1` 已审计通过的继承写路由；不修改业务代码、不新增能力。

## 2. 阻塞背景

C 第398份已确认：

- `TASK-050G` 收口验证报告显示核心 pytest：`79 collected / 78 passed / 1 failed`。
- 失败用例：`tests/test_warehouse_readonly_baseline.py::WarehouseReadonlyApiTest::test_no_write_route_registered`。
- 失败原因：该测试仍按早期“warehouse router 不存在写路由”的只读基线断言；但当前仓库已有经审计通过的继承写路由：
  - `TASK-050B` Stock Entry 草稿与取消，审计意见书第383份通过。
  - `TASK-050C` 库存盘点草稿、提交、差异复核、确认、取消，审计意见书第385份通过。
  - `TASK-050D_FIX1` Stock Entry Outbox internal run-once，审计意见书第389份通过。
- `TASK-050G` 任务单禁止 B 在收口验证任务内直接修测试，因此必须另开本 FIX1。

## 3. 任务目标

只做测试口径收敛与复验报告：

1. 将 `test_no_write_route_registered` 从“仓库模块不得存在任何写路由”改为“不得存在未审计/未登记的写路由”。
2. 明确允许的继承写路由白名单，且必须绑定审计编号。
3. 禁止允许 `PUT / PATCH / DELETE`。
4. 禁止新增业务写能力、ERPNext 写调用、Stock Reconciliation、Stock Ledger Entry 直接写入、GL/Payment/Purchase Invoice 写语义。
5. 复跑 TASK-050G 仓库增强核心测试并输出 FIX1 复验报告。

## 4. 允许范围

只允许修改或新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/**` 任何业务代码。
2. 禁止修改 migration、model、router、service、schema、main.py、adapter、export service。
3. 禁止修改 `06_前端/**`。
4. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
5. 禁止新增或修改 API 行为。
6. 禁止放宽权限校验，禁止把 `inventory:*` 作为 warehouse 写能力通过条件。
7. 禁止新增 ERPNext 写调用、Stock Entry submit、Stock Reconciliation、Stock Ledger Entry 直接写入、GL/Payment/Purchase Invoice 写语义。
8. 禁止 commit、push、PR、tag、生产发布。

## 6. 必须修改测试口径

目标文件：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py`

将 `test_no_write_route_registered` 改为以下语义之一：

- 保留原测试名但改为检查“无未登记写路由”。
- 或改名为 `test_no_unexpected_write_route_registered`。

必须实现：

1. 收集 `app.routes` 中 path 以 `/api/warehouse` 开头的路由。
2. 将 `GET / HEAD / OPTIONS` 视为只读方法。
3. 对所有非只读方法形成集合：`(method, path)`。
4. 该集合必须等于或被严格校验为以下白名单，不得多出任何项：

```text
POST /api/warehouse/stock-entry-drafts                                      # TASK-050B 审计意见书第383份
POST /api/warehouse/stock-entry-drafts/{draft_id}/cancel                    # TASK-050B 审计意见书第383份
POST /api/warehouse/internal/stock-entry-sync/run-once                      # TASK-050D_FIX1 审计意见书第389份
POST /api/warehouse/inventory-counts                                        # TASK-050C 审计意见书第385份
POST /api/warehouse/inventory-counts/{count_id}/submit                      # TASK-050C 审计意见书第385份
POST /api/warehouse/inventory-counts/{count_id}/variance-review             # TASK-050C 审计意见书第385份
POST /api/warehouse/inventory-counts/{count_id}/confirm                     # TASK-050C 审计意见书第385份
POST /api/warehouse/inventory-counts/{count_id}/cancel                      # TASK-050C 审计意见书第385份
```

必须额外断言：

- 白名单中不允许 `PUT / PATCH / DELETE`。
- 若未来新增任何 warehouse 写路由，测试必须失败。
- 该测试不得扫描或依赖前端。

## 7. 必须输出复验报告

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md`

报告必须包含：

1. 第398份阻塞原因复述。
2. 测试口径修复说明。
3. 已审计继承写路由白名单及对应审计编号。
4. pytest 复验结果。
5. 权限动作与 `inventory:*` 回退扫描结果。
6. ERPNext 写调用与高危写语义扫描结果。
7. TASK-050D/E/F 契约保持扫描结果。
8. 禁改目录与继承脏基线结果。
9. 是否建议回交 C 最终收口审计。

## 8. 必须执行验证命令

### 8.1 单点失败测试复验

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_readonly_baseline.py::WarehouseReadonlyApiTest::test_no_write_route_registered -v --tb=short
```

如测试改名，执行改名后的单点测试。

### 8.2 仓库增强核心全量复验

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

### 8.3 权限动作与回退扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

### 8.4 ERPNext 写调用与高危写语义扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

说明：`@router.post` 命中白名单继承写路由不构成本任务失败；必须在报告中按审计编号说明。

### 8.5 TASK-050D / TASK-050E / TASK-050F 契约保持扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

### 8.6 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

## 9. 回交硬门禁

1. 本任务单是 `A -> B` 执行指令，不是 `B -> C` 审计输入。
2. B 未完成测试修复、复验报告、工程师日志、验证命令前，禁止回交 C。
3. 若需要修改允许范围之外文件，立即 `BLOCKED` 回 A。
4. 若复验仍失败，回报 `NEEDS_FIX` 或 `BLOCKED`，不得自行扩大边界。

## 10. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050G_FIX1
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 测试口径修复：路径 + 行号
- 白名单继承写路由：报告章节
- pytest 复验：报告章节
- 权限/写调用/禁改边界扫描：报告章节

VERIFICATION:
- 单点测试：结果
- 仓库增强核心全量测试：结果
- 权限动作与回退扫描：结果
- ERPNext 写调用与高危写语义扫描：结果
- TASK-050D/E/F 契约扫描：结果
- 禁改目录 diff：结果
- router 继承脏基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
