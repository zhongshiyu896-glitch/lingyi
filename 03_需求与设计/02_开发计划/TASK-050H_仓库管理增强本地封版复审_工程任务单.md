# TASK-050H 仓库管理增强本地封版复审 工程任务单

## 1. 基本信息

- 任务编号：TASK-050H
- 任务名称：仓库管理增强本地封版复审
- 模块：仓库管理增强
- 角色：B Engineer
- 优先级：P1
- 前置依赖：TASK-050G_FIX1 审计通过（审计意见书第400份）
- 当前定位：对仓库管理增强任务链做本地封版复审证据汇总和核验；本任务只输出证据，不新增功能、不修改业务代码、不提交、不 push、不 PR、不 tag、不生产发布。

## 2. 任务目标

输出一份可交给 C Auditor 审计的仓库管理增强本地封版复审证据，证明以下链路均已闭环：

1. 仓库只读台账与预警基线：TASK-050A_FIX1。
2. Stock Entry 草稿 Outbox 本地基线：TASK-050B。
3. 库存盘点草稿与差异复核本地基线：TASK-050C。
4. Stock Entry Outbox Worker 草稿创建与 run-once 契约：TASK-050D_FIX1。
5. Batch / Serial No 只读追溯与详情单资源读取：TASK-050E_FIX2。
6. 仓库只读导出与诊断基线：TASK-050F。
7. 仓库管理增强全链路收口验证与测试口径修复：TASK-050G_FIX1。

本任务结论只能写：

```text
建议进入 C 本地封版审计
暂不建议进入 C 本地封版审计
```

不得自行宣布：

```text
仓库管理增强已正式封版
生产发布通过
ERPNext 生产联调通过
GitHub required check 闭环
远端 push / PR / tag 完成
```

## 3. 允许范围

只允许新增或追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改 `07_后端/**` 业务代码、测试代码、migration、model、router、service、schema、main.py、adapter。
2. 禁止修改 `06_前端/**`。
3. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
4. 禁止修改审计日志、架构日志、控制面文件。
5. 禁止新增或修改 API 行为。
6. 禁止新增 outbox、worker、权限常量、ERPNext adapter 写能力。
7. 禁止 ERPNext 同步写调用、Stock Entry submit、Stock Reconciliation、Stock Ledger Entry 直接写入、GL Entry、Payment Entry、Purchase Invoice。
8. 禁止 commit、push、PR、tag、生产发布。
9. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核对的审计编号

证据文档必须逐项列出并核对以下审计编号：

| 任务 | 审计结论 |
| --- | --- |
| TASK-050A | 审计意见书第378份 有问题 |
| TASK-050A_FIX1 | 审计意见书第381份 通过 |
| TASK-050B | 审计意见书第383份 通过 |
| TASK-050C | 审计意见书第385份 通过 |
| TASK-050D | 审计意见书第387份 有问题 |
| TASK-050D_FIX1 | 审计意见书第389份 通过 |
| TASK-050E | 审计意见书第391份 有问题 |
| TASK-050E_FIX1 | 审计意见书第393份 有问题 |
| TASK-050E_FIX2 | 审计意见书第395份 通过 |
| TASK-050F | 审计意见书第397份 通过 |
| TASK-050G | 审计意见书第398份 阻塞 |
| TASK-050G_FIX1 | 审计意见书第400份 通过 |

要求：

1. 对 `有问题/阻塞` 项必须说明已由后续 fix pass 闭环。
2. 对最终通过项必须写清核心验证结果。
3. 不得遗漏第400份。

## 6. 必须执行验证命令

### 6.1 仓库增强核心后端测试

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

### 6.2 Python 编译核验

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 6.3 权限动作与 inventory 回退扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

说明：`inventory:*` 如仅命中负向测试输入，必须说明为“库存权限不可替代仓库权限”的测试证据。

### 6.4 写路由白名单扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

要求：

- 只能命中第383/385/389份已审计继承写路由。
- 不得出现 `PUT / PATCH / DELETE`。
- 不得出现未登记新增写路由。

### 6.5 ERPNext 写调用与高危写语义扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
```

要求：

- 若命中已审计继承本地写路由或测试断言，必须逐项解释。
- 不得出现 ERPNext 同步写调用。
- 不得出现生产库存落账、财务写入、submit 语义。

### 6.6 TASK-050D / TASK-050E / TASK-050F 契约保持扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

### 6.7 禁改目录与继承脏基线

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

## 7. 证据文档要求

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md`

必须包含：

1. 基本信息：任务编号、执行时间、当前分支、当前 HEAD、结论。
2. 任务链路与审计闭环表。
3. 已完成能力清单：只读、预警、草稿、盘点、worker、Batch/Serial、导出、诊断、全链路收口。
4. 后端测试结果。
5. Python 编译结果。
6. 权限动作与 `inventory:*` 回退扫描结果。
7. 写路由白名单扫描结果。
8. ERPNext 写调用与高危写语义扫描结果。
9. TASK-050D/E/F 契约保持扫描结果。
10. 禁改目录与继承脏基线结果。
11. 剩余风险。
12. 是否建议进入 C 本地封版审计。

## 8. 剩余风险必须至少披露

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须另开白名单提交任务。
5. 当前 Stock Entry / 库存盘点仍属于本地草稿与受控 outbox 能力，不代表生产库存写入已放行。

## 9. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050H
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050H_仓库管理增强本地封版复审证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 审计闭环表：证据章节
- 核心测试结果：证据章节
- 权限与回退扫描：证据章节
- 写路由白名单扫描：证据章节
- ERPNext 写调用与高危写语义扫描：证据章节
- TASK-050D/E/F 契约保持：证据章节
- 禁改目录与继承脏基线：证据章节
- 剩余风险：证据章节

VERIFICATION:
- pytest：结果
- py_compile：结果
- 权限动作与回退扫描：结果
- 写路由白名单扫描：结果
- ERPNext 写调用与高危写语义扫描：结果
- TASK-050D/E/F 契约扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
