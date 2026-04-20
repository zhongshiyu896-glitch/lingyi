# TASK-050G 仓库管理增强全链路收口验证 工程任务单

## 1. 基本信息

- 任务编号：TASK-050G
- 任务名称：仓库管理增强全链路收口验证
- 模块：仓库管理增强
- 角色：B Engineer
- 优先级：P1
- 前置依赖：TASK-050A_FIX1、TASK-050B、TASK-050C、TASK-050D_FIX1、TASK-050E_FIX2、TASK-050F 均已通过 C 审计
- 当前定位：对仓库管理增强链路做全量本地收口验证和证据归档；本任务不新增功能、不修改业务代码、不提交、不 push、不 PR、不 tag、不生产发布。

## 2. 已通过审计基线

B 必须在收口报告中逐项核对以下审计编号：

| 任务 | 审计结论 |
| --- | --- |
| TASK-050A_FIX1 | 审计意见书第381份 通过 |
| TASK-050B | 审计意见书第383份 通过 |
| TASK-050C | 审计意见书第385份 通过 |
| TASK-050D_FIX1 | 审计意见书第389份 通过 |
| TASK-050E_FIX2 | 审计意见书第395份 通过 |
| TASK-050F | 审计意见书第397份 通过 |

## 3. 任务目标

输出仓库管理增强链路收口验证报告，证明以下能力在当前本地工作树中同时成立：

1. 仓库只读台账、预警、权限过滤基线可用。
2. Stock Entry 草稿本地基线、取消、Outbox 状态可用。
3. 库存盘点草稿、提交、差异复核、确认、取消、详情、列表可用。
4. Stock Entry Outbox internal run-once 契约保持：`batch_size default=10/le=50`，响应包含 `skipped_count`。
5. Batch / Serial No 只读追溯字段契约与详情单资源读取可用。
6. 仓库只读 CSV 导出、CSV 公式注入防护、诊断接口与 main.py 动作映射可用。
7. 权限动作 `warehouse:*` 口径不回退到 `inventory:*`。
8. 未发现本轮新增 ERPNext 同步写调用、Stock Entry submit、Stock Reconciliation、Stock Ledger Entry 直接写入、GL/Payment/Purchase Invoice 写入。
9. 禁改目录 `.github / 02_源码 / 04_生产` 无 diff。
10. 继承脏基线 `06_前端/lingyi-pc/src/router/index.ts` 如仍有 diff，SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 4. 允许范围

只允许新增或追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止修改 `07_后端/**` 业务代码、测试代码、migration、model、router、service、schema、main.py。
2. 禁止修改 `06_前端/**`。
3. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
4. 禁止新增 outbox、worker、权限常量、ERPNext adapter 写能力。
5. 禁止新增或修改任何 API 行为。
6. 禁止提交 commit、push、PR、tag、生产发布。
7. 如验证失败，不得在本任务内直接修代码；必须回报失败证据，由 A 另开 fix pass。

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

### 6.2 权限动作与回退扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "warehouse:read|warehouse:alert_read|warehouse:stock_entry_draft|warehouse:stock_entry_cancel|warehouse:inventory_count|warehouse:worker|warehouse:export|warehouse:diagnostic|WAREHOUSE_" app/core/permissions.py app/routers/warehouse.py app/main.py tests/test_permissions_registry.py
rg -n "INVENTORY_READ|INVENTORY_WRITE|inventory:read|inventory:write" app/routers/warehouse.py app/services/warehouse_service.py tests/test_warehouse_*.py
```

说明：第二条若命中测试中的负向断言，必须说明为“仅 inventory 权限访问仓库接口应 403”的测试证据，不得作为授权回退。

### 6.3 ERPNext 写调用与高危写语义扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
```

说明：`@router.post` 如命中 TASK-050B/TASK-050C/TASK-050D 已审计继承写路由，不直接构成本任务失败；B 必须说明未新增写路由。

### 6.4 TASK-050D / TASK-050E / TASK-050F 契约保持扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "batch_size.*default=10|le=50|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "_get_resource_doc|doctype=\"Batch\"|doctype=\"Serial No\"|Batch/|Serial No/" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
```

### 6.5 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '06_前端/lingyi-pc/src/router/index.ts'
git status --short -- .github 02_源码 04_生产 06_前端/lingyi-pc/src/router/index.ts
```

## 7. 必须输出报告

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md`

报告必须包含：

1. 任务链审计编号核对表。
2. 后端测试命令与完整结果摘要。
3. 权限动作与 `inventory:*` 回退扫描结论。
4. ERPNext 写调用与高危写语义扫描结论。
5. TASK-050D run-once 契约保持结论。
6. TASK-050E Batch/Serial No 详情单资源读取保持结论。
7. TASK-050F export/diagnostic 契约保持结论。
8. 禁改目录与继承脏基线结论。
9. 剩余风险。
10. 是否建议进入 C 最终收口审计。

## 8. 回交硬门禁

1. 本任务单是 `A -> B` 执行指令，不是 `B -> C` 审计输入。
2. 未生成报告、未追加工程师日志、未执行验证命令前，禁止回交 C。
3. 任何验证失败、权限回退、写调用新增、禁改目录 diff、新增业务代码改动，必须回报为 `BLOCKED` 或 `NEEDS_FIX`，不得自行修复。
4. 回交 C 前必须包含真实 `CHANGED_FILES`、报告路径、验证结果和边界扫描结果。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050G
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-050G_仓库管理增强全链路收口验证报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 审计编号核对表：报告章节
- 核心测试结果：报告章节
- 权限动作与回退扫描：报告章节
- ERPNext 写调用与高危写语义扫描：报告章节
- TASK-050D/E/F 契约保持：报告章节
- 禁改目录与继承脏基线：报告章节

VERIFICATION:
- pytest 仓库增强核心测试：结果
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
