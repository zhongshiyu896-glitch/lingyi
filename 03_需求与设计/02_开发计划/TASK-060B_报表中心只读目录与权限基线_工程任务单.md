# TASK-060B 报表中心只读目录与权限基线 工程任务单

- 任务编号：TASK-060B
- 任务名称：报表中心只读目录与权限基线
- 角色：B Engineer
- 派发时间：2026-04-20 23:06 CST+8
- 派发人：A Technical Architect
- 模块：报表与仪表盘 / reports
- 前置依据：`TASK-019_报表与仪表盘总体设计.md`、`TASK-060A` 审计意见书第406份通过
- 当前定位：报表方向第二张任务。060A 已完成 dashboard overview；本任务只建立报表中心只读目录、权限动作与前端最小入口，不实现具体报表数据聚合、导出、缓存、诊断。

## 0. 强制说明

本任务单是 A -> B 执行指令，不是 B -> C 审计输入。

未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

本任务不允许 commit、push、PR、tag、生产发布。

## 1. 目标

实现报表中心只读目录基线：

1. 新增 `GET /api/reports/catalog`。
2. 新增 `GET /api/reports/catalog/{report_key}`。
3. 注册并校验 `report:read`。
4. 返回 TASK-019 已冻结的报表目录、来源模块、类型、所需过滤字段、口径摘要、状态。
5. 不查询业务明细，不触发重算，不生成报表事实，不导出。
6. 前端新增最小只读报表目录页面。

## 2. 报表目录范围

目录必须至少包含以下 report_key：

| report_key | 名称 | 来源 | 类型 |
|---|---|---|---|
| `production_progress` | 生产进度看板 | Work Order / Job Card / Production records | 只读 |
| `inventory_trend` | 库存趋势 | Stock Ledger Entry / Bin | 只读 |
| `style_profit_trend` | 款式利润趋势 | Style Profit Snapshot | 只读快照 |
| `factory_statement_summary` | 加工厂对账统计 | Factory Statement | 只读汇总 |
| `sales_inventory_view` | 销售库存视图 | Sales Inventory | 只读 |
| `quality_statistics` | 质量统计 | Quality Inspection | 只读 |
| `financial_summary` | 财务摘要 | TASK-016 后续设计 | 只读 |

## 3. 允许修改文件

### 3.1 后端允许新增

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/report.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_catalog_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/report.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_report_catalog_readonly.py`

### 3.2 后端允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
  - 仅允许新增 `REPORT_READ = "report:read"`、`ALL_REPORT_ACTIONS`、`MODULE_ACTION_REGISTRY["report"]`。
  - 禁止在本任务注册 `report:export / report:diagnostic / report:cache_refresh`，这些必须留给后续独立任务。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
  - 仅允许注册 report router，并补 `/api/reports` 安全审计 fallback：`module=report / action=report:read`。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`（仅允许补充 report:read 注册测试；如已有覆盖则不要改）

### 3.3 前端允许新增

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`

### 3.4 前端允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

注意：`router/index.ts` 已包含前序任务继承改动。修改前记录 SHA-256；修改后必须说明本任务仅新增 `/reports/catalog` 路由，不得混入其他路由改动。

## 4. 禁止修改范围

1. 禁止修改 `.github/**`。
2. 禁止修改 `02_源码/**`。
3. 禁止修改 `04_生产/**`。
4. 禁止新增或修改 migration。
5. 禁止新增或修改 `app/models/**`。
6. 禁止修改 dashboard、quality、sales_inventory、warehouse 既有业务语义。
7. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
8. 禁止新增 ERPNext 写调用。
9. 禁止新增 ERPNext 直连查询；本任务目录数据必须来自本地静态目录服务，不访问 ERPNext。
10. 禁止新增 `outbox`、`worker`、`run-once`、`internal` 接口。
11. 禁止新增导出、诊断、缓存刷新、重算、生成、同步、提交能力。
12. 禁止 commit、push、PR、tag、生产发布。

## 5. 后端接口契约

### 5.1 路由

```text
GET /api/reports/catalog
GET /api/reports/catalog/{report_key}
```

### 5.2 权限

两个接口必须校验：

```text
report:read
```

不得接受以下权限作为通过条件：

```text
dashboard:read
quality:read
sales_inventory:read
warehouse:read
inventory:read
```

### 5.3 查询参数

`GET /api/reports/catalog` 支持可选过滤：

- `company`：可选，返回时进入 `requested_scope.company`，不做业务查询。
- `source_module`：可选，只能在目录元数据中做本地过滤。
- `report_type`：可选，只能在目录元数据中做本地过滤。

非法 `source_module` 或 `report_type` 不允许静默降级，返回 `400 / INVALID_QUERY_PARAMETER`。

### 5.4 响应字段

成功响应统一使用既有信封：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "items": [
      {
        "report_key": "inventory_trend",
        "name": "库存趋势",
        "source_modules": ["warehouse", "inventory"],
        "report_type": "readonly",
        "required_filters": ["company", "from_date", "to_date"],
        "optional_filters": ["item_code", "warehouse"],
        "metric_summary": ["opening_qty", "in_qty", "out_qty", "closing_qty"],
        "permission_action": "report:read",
        "status": "designed"
      }
    ],
    "requested_scope": {
      "company": "LY",
      "source_module": null,
      "report_type": null
    }
  }
}
```

`GET /api/reports/catalog/{report_key}` 返回单个 `item`。不存在的 `report_key` 返回 `404 / REPORT_NOT_FOUND`，不得返回空对象伪成功。

### 5.5 Fail-closed 规则

1. 无 `report:read` 返回 403。
2. `report_key` 不存在返回 404。
3. 非法过滤参数返回 400。
4. 不得把异常详情、token、Authorization、Cookie、DSN、password、secret 回传前端。

## 6. 后端实现要求

1. `app/schemas/report.py` 定义 catalog item、catalog response、scope 等模型。
2. `app/services/report_catalog_service.py` 内置 TASK-019 冻结目录，纯本地只读，不访问数据库、不访问 ERPNext。
3. `app/routers/report.py` 只暴露两个 GET 接口。
4. `app/core/permissions.py` 注册 `report:read`。
5. `app/main.py` 注册 report router，并补安全审计 fallback 映射。
6. 不得在本任务实现 `report:export / report:diagnostic / report:cache_refresh`。

## 7. 前端实现要求

1. 新增 `src/api/report.ts`，通过统一 `request` client 调用 `/api/reports/catalog` 与 `/api/reports/catalog/{report_key}`。
2. 新增 `ReportCatalog.vue`，展示报表目录、来源模块、类型、过滤字段、指标摘要、状态。
3. 修改 `router/index.ts` 增加：

```text
path: /reports/catalog
name: ReportCatalog
meta.module: report
```

4. 前端不得直连 ERPNext。
5. 前端不得裸 `fetch` / `axios` 绕过统一 API client。
6. 前端不得新增导出按钮、刷新按钮、重算按钮、生成按钮、同步按钮或写动作。

## 8. 测试要求

新增或补充测试必须覆盖：

1. `report:read` 可访问 catalog。
2. 仅持有 `dashboard:read / quality:read / sales_inventory:read / warehouse:read / inventory:read` 但没有 `report:read` 时返回 403。
3. catalog 至少返回 7 个 TASK-019 冻结报表。
4. `source_module` / `report_type` 本地过滤有效。
5. 非法 `source_module` / `report_type` 返回 400。
6. 单报表详情存在时返回 item，不存在时返回 404 / `REPORT_NOT_FOUND`。
7. report router 中不存在 `POST/PUT/PATCH/DELETE`。
8. report 文件中不存在 ERPNext 写调用、ERPNext 直连、outbox、worker、run-once、internal、export、diagnostic、cache_refresh。
9. 前端 typecheck 通过。

## 9. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_report_catalog_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/report.py app/services/report_catalog_service.py app/schemas/report.py
rg -n "@router\.(post|put|patch|delete)" app/routers/report.py || true
rg -n "requests\.|httpx\.|/api/resource|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/report.py app/services/report_catalog_service.py app/schemas/report.py || true
rg -n "outbox|worker|run-once|internal|export|diagnostic|cache_refresh|recalculate|generate|sync|submit" app/routers/report.py app/services/report_catalog_service.py app/schemas/report.py || true
git diff --name-only -- .github 02_源码 04_生产
```

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource|export|diagnostic|cache_refresh|recalculate|generate|sync|submit" src/api/report.ts src/views/reports/ReportCatalog.vue || true
```

## 10. 回交格式

B 完成后回交给 C，必须包含：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060B
ROLE: B Engineer

CHANGED_FILES:
- 真实改动文件列表

EVIDENCE:
- report:read 权限注册和校验证据
- /api/reports/catalog 与 /api/reports/catalog/{report_key} 落点
- TASK-019 七类报表目录覆盖证据
- 前端 API / 页面 / 路由落点
- 只读边界扫描结果
- 禁改目录 diff 结果

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 负向扫描结果

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE:
- C Auditor
```

## 11. 完成定义

满足以下条件才算完成：

1. `/api/reports/catalog` 和 `/api/reports/catalog/{report_key}` 可用。
2. `report:read` 注册并作为唯一入口权限生效。
3. 七类 TASK-019 报表目录完整返回。
4. 前端 `/reports/catalog` 最小只读页面可 typecheck。
5. 无新增写路由、无 ERPNext 访问、无 outbox/worker/internal/export/diagnostic/cache_refresh。
6. 禁改目录 diff 为空。
7. B 回交包含真实验证命令与证据路径。
