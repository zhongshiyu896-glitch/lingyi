# TASK-050I 仓库管理增强本地封版白名单提交 工程任务单

## 1. 基本信息

- 任务编号：TASK-050I
- 任务名称：仓库管理增强本地封版白名单提交
- 模块：仓库管理增强 / 本地封版
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-050H 审计通过（审计意见书第402份）
- 当前定位：把 TASK-050A~TASK-050H 已通过审计的仓库管理增强链路纳入本地 git 基线，形成可审计的本地封版 commit。

## 2. 任务目标

完成一次严格白名单本地提交：

1. 复核当前分支、HEAD、脏工作树。
2. 复跑仓库增强核心测试、Python 编译、前端 typecheck 与边界扫描。
3. 生成 `TASK-050I_仓库管理增强本地封版提交证据.md`。
4. 只按白名单显式 `git add`。
5. 创建本地 commit。
6. 回交 commit hash、staged 清单、验证结果和证据路径给 C Auditor。

本任务只允许本地 commit，不允许：

```text
push / PR / tag / 生产发布 / ERPNext 生产联调声明 / GitHub required check 闭环声明
```

## 3. 允许新增或修改的证据文件

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 允许纳入本地 commit 的白名单

只能暂存以下文件或目录。未列入的文件一律不得暂存。

### 4.1 仓库后端代码

- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/models/warehouse.py`
- `07_后端/lingyi_service/app/routers/warehouse.py`
- `07_后端/lingyi_service/app/schemas/warehouse.py`
- `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `07_后端/lingyi_service/app/services/warehouse_export_service.py`
- `07_后端/lingyi_service/app/services/warehouse_service.py`

### 4.2 仓库迁移

- `07_后端/lingyi_service/migrations/versions/task_050b_create_warehouse_stock_entry_outbox.py`
- `07_后端/lingyi_service/migrations/versions/task_050c_create_warehouse_inventory_count.py`

### 4.3 仓库测试

- `07_后端/lingyi_service/tests/test_permissions_registry.py`
- `07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py`
- `07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py`
- `07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- `07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`
- `07_后端/lingyi_service/tests/test_warehouse_worker_permissions.py`
- `07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py`
- `07_后端/lingyi_service/tests/test_warehouse_export_diagnostic.py`

### 4.4 仓库前端

- `06_前端/lingyi-pc/src/api/warehouse.ts`
- `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- `06_前端/lingyi-pc/src/router/index.ts`

### 4.5 仓库任务与证据文档

- `03_需求与设计/02_开发计划/TASK-050A_仓库库存只读台账与预警基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050B_仓库StockEntry草稿Outbox本地基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050C_仓库库存盘点草稿与差异复核本地基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050D_仓库StockEntryOutboxWorker草稿创建_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050D_FIX1_run_once契约收紧_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050E_仓库批次序列号只读追溯基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050E_FIX1_BatchSerial原始字段契约修复_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050E_FIX2_BatchSerial详情单资源读取_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050F_仓库只读导出与诊断基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md`
- `03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库收口写路由继承口径修复_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md`
- `03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md`
- `03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版白名单提交_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md`
- `03_需求与设计/02_开发计划/工程师会话日志.md`

### 4.6 控制与审计日志

仅允许暂存当前任务链已产生的共享记录，不允许额外编辑历史内容：

- `00_交接与日志/HANDOVER_STATUS.md`
- `03_需求与设计/01_架构设计/架构师会话日志.md`
- `03_需求与设计/05_审计记录/审计官会话日志.md`

说明：`/Users/hh/Documents/Playground 2/LOOP_STATE.md` 位于项目 git 仓库外，不纳入本地 commit。B 不得尝试把它加入项目仓库。

## 5. 禁止范围

1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 禁止暂存 `.github/**`。
4. 禁止暂存 `.ci-reports/**`。
5. 禁止暂存 `01_需求与资料/**`。
6. 禁止暂存 `02_源码/**`。
7. 禁止暂存 `03_环境与部署/**`。
8. 禁止暂存 `04_测试与验收/**`。
9. 禁止暂存 `05_交付物/**`。
10. 禁止暂存 `TASK-021* / TASK-022* / TASK-023* / TASK-024*` 等非仓库增强历史任务单。
11. 禁止暂存 `test_permission_audit_baseline.py`，该文件属于 TASK-007B 继承背景，不属于本次仓库封版白名单。
12. 禁止修改业务代码后再封版；如发现需要修复，立即 `BLOCKED`。
13. 禁止 push / PR / tag / 生产发布。

## 6. 必须执行验证

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
```

### 6.2 仓库增强核心后端测试

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

期望：`79 passed, 1 warning` 或等价全通过结果。

### 6.3 Python 编译

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 6.4 前端 typecheck

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.5 权限与 inventory 回退扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

要求：`inventory:*` 只能作为负向测试输入命中，不得作为仓库授权回退实现命中。

### 6.6 写路由白名单扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

要求：

- 仅允许 8 条已审计继承 `POST` 路由。
- 不得出现 `PUT / PATCH / DELETE`。
- 不得出现未审计新增写路由。

### 6.7 ERPNext 写调用与高危写语义扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
```

要求：不得发现新增 ERPNext 同步写调用、生产库存落账、财务写入或 submit 语义。

### 6.8 TASK-050D / TASK-050E / TASK-050F 契约保持扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

### 6.9 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

锁定值：

```text
06_前端/lingyi-pc/src/router/index.ts = 0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a
```

## 7. 生成封版提交证据

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md`

必须包含：

1. 当前分支、提交前 HEAD。
2. 前置审计：第402份 `TASK-050H PASS`。
3. 仓库增强审计闭环摘要：第378~402份关键结论。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限与回退扫描结果。
8. 写路由白名单扫描结果。
9. ERPNext 写调用与高危写语义扫描结果。
10. TASK-050D/E/F 契约保持扫描结果。
11. 禁改目录与 router 哈希结果。
12. staged 白名单清单。
13. 残余风险。

注意：本证据文件内不要在 commit 后回填 commit hash。commit hash 只在 B 回交正文中报告，避免封版 commit 后产生 post-commit 脏改动。如 B 认为必须把 commit hash 写入文件，必须停止并回报 `BLOCKED`，不得自行创建第二个 metadata commit。

## 8. 白名单暂存要求

必须从项目根目录执行显式路径暂存。示例：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add -- \
  '07_后端/lingyi_service/app/core/permissions.py' \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/models/warehouse.py' \
  '07_后端/lingyi_service/app/routers/warehouse.py' \
  '07_后端/lingyi_service/app/schemas/warehouse.py' \
  '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' \
  '07_后端/lingyi_service/app/services/warehouse_export_service.py' \
  '07_后端/lingyi_service/app/services/warehouse_service.py' \
  '07_后端/lingyi_service/migrations/versions/task_050b_create_warehouse_stock_entry_outbox.py' \
  '07_后端/lingyi_service/migrations/versions/task_050c_create_warehouse_inventory_count.py' \
  '07_后端/lingyi_service/tests/test_permissions_registry.py' \
  '07_后端/lingyi_service/tests/test_warehouse_readonly_baseline.py' \
  '07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py' \
  '07_后端/lingyi_service/tests/test_warehouse_inventory_count.py' \
  '07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py' \
  '07_后端/lingyi_service/tests/test_warehouse_worker_permissions.py' \
  '07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py' \
  '07_后端/lingyi_service/tests/test_warehouse_export_diagnostic.py' \
  '06_前端/lingyi-pc/src/api/warehouse.ts' \
  '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '03_需求与设计/02_开发计划/TASK-050A_仓库库存只读台账与预警基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050B_仓库StockEntry草稿Outbox本地基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050C_仓库库存盘点草稿与差异复核本地基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050D_仓库StockEntryOutboxWorker草稿创建_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050D_FIX1_run_once契约收紧_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050E_仓库批次序列号只读追溯基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050E_FIX1_BatchSerial原始字段契约修复_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050E_FIX2_BatchSerial详情单资源读取_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050F_仓库只读导出与诊断基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md' \
  '03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库收口写路由继承口径修复_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050G_FIX1_仓库管理增强全链路收口复验报告.md' \
  '03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md' \
  '03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版白名单提交_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md' \
  '00_交接与日志/HANDOVER_STATUS.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

暂存后必须执行：

```bash
git diff --cached --name-only
git status --short --branch
```

若 staged 清单出现白名单外文件，必须停止并回报 `BLOCKED`，不得 commit。

## 9. 创建本地 commit

白名单核验通过后执行：

```bash
git commit -m "chore: seal warehouse management enhancement baseline"
```

提交后执行：

```bash
git rev-parse --short HEAD
git status --short --branch
git tag --points-at HEAD
```

要求：

- 必须生成本地 commit。
- `git tag --points-at HEAD` 必须为空。
- 仍禁止 push / PR / tag / 生产发布。
- 不得在 commit 后修改证据文件或工程师日志来回填 hash。

## 10. 失败处理

任一门禁失败时：

1. 停止。
2. 不修代码。
3. 不 commit。
4. 回报 `STATUS: BLOCKED`。
5. 写明失败命令、失败摘要、涉及文件、建议下一步。

## 11. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050I
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050I_仓库管理增强本地封版提交证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 本地封版 commit 中纳入的白名单文件清单

EVIDENCE:
- 前置审计：第402份 PASS
- 后端测试结果：...
- Python 编译结果：...
- 前端 typecheck：...
- 权限与回退扫描：...
- 写路由白名单扫描：...
- ERPNext 写调用与高危写语义扫描：...
- TASK-050D/E/F 契约保持：...
- 禁改目录与 router 哈希：...
- staged 白名单清单：...
- 本地 commit hash：...
- tag 检查：无

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE:
- C Auditor
```
