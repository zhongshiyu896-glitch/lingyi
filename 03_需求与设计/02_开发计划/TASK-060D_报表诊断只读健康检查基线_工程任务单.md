# TASK-060D 报表诊断只读健康检查基线 工程任务单

- 任务编号：TASK-060D
- 任务名称：报表诊断只读健康检查基线
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：报表与仪表盘 / reports
- 前置依据：`TASK-019_报表与仪表盘总体设计.md`、`TASK-019A_报表与仪表盘总体设计.md`、`TASK-060C_FIX2` 审计意见书第414份通过
- 当前定位：报表方向第四张实现任务。060B 已完成报表目录只读 API；060C 已完成目录 CSV 导出安全基线。本任务只实现报表模块管理员诊断健康检查基线，不实现缓存刷新、不实现业务报表计算、不实现普通前端入口。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实代码改动、测试结果、变更清单和证据路径前，不得回交 C。

## 1. 目标

新增报表模块只读诊断接口，用于管理员/诊断权限检查报表目录与导出基线的本地健康状态：

1. 新增 `GET /api/reports/diagnostic`。
2. 入口必须校验 `report:diagnostic`。
3. `report:read`、`report:export`、`dashboard:read`、`quality:read`、`sales_inventory:read`、`warehouse:read`、`inventory:read` 均不得替代 `report:diagnostic`。
4. 响应只返回安全健康摘要，不包含 token、cookie、secret、password、Authorization、DSN、DATABASE_URL、ERPNext 凭据或环境变量值。
5. 诊断只检查本地静态 report catalog / export service / permission registry / route mapping，不访问 ERPNext，不查询业务 DB，不触发缓存刷新，不生成业务事实。

## 2. 允许修改范围

### 后端允许

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/report.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_diagnostic_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_catalog_service.py`（仅允许新增只读 helper，禁止改变 060B 已审计 catalog 字段语义）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_export_service.py`（仅允许只读健康检查引用，禁止改变 CSV 字段和注入防护语义）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/report.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 测试允许

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_report_diagnostic.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

## 3. 禁止修改范围

1. 禁止修改任何前端文件，包括但不限于：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
2. 禁止新增普通前端诊断按钮、菜单、路由或 API 封装。
3. 禁止新增 `report:cache_refresh`、`report:recalculate`、`report:generate`、`report:sync`、`report:submit` 等动作。
4. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
5. 禁止访问 ERPNext `/api/resource`，禁止使用 `requests/httpx` 写调用。
6. 禁止新增 migration、model、outbox、worker、run-once、internal 接口。
7. 禁止改动 `.github`、`02_源码`、`04_生产`。
8. 禁止 commit / push / PR / tag / 生产发布。

## 4. 后端实现要求

### 4.1 权限注册

在 `app/core/permissions.py` 中新增并注册：

```python
REPORT_DIAGNOSTIC = "report:diagnostic"
```

要求：

1. `REPORT_DIAGNOSTIC` 必须进入 `ALL_REPORT_ACTIONS`。
2. `MODULE_ACTION_REGISTRY["report"]` 必须包含 `report:diagnostic`。
3. `tests/test_permissions_registry.py` 必须覆盖该动作。

### 4.2 路由

在 `app/routers/report.py` 新增：

```text
GET /api/reports/diagnostic
```

要求：

1. 必须使用 `REPORT_DIAGNOSTIC` 做入口动作权限。
2. 必须使用 `module="report"`。
3. `resource_type` 建议为 `report_diagnostic` 或等价稳定值。
4. 响应仍使用统一 `{code,message,data}` envelope。
5. 路由必须声明在 `/catalog/{report_key}` 无冲突位置；不得破坏 060B/060C 现有 catalog/export 路由。

### 4.3 诊断服务

新增 `app/services/report_diagnostic_service.py`。

服务职责：

1. 汇总本地 report catalog 条目数量。
2. 返回 catalog keys。
3. 返回支持的 `source_modules` 与 `report_types`。
4. 返回 export service 是否可用，例如 `export_enabled=true`。
5. 返回 permission registry 中 report 模块是否包含 `report:read/report:export/report:diagnostic`。
6. 返回 `generated_at` UTC ISO 字符串。
7. 返回 `status="ok"` 或明确失败状态。

建议响应字段：

```text
module: report
status: ok
catalog_count: number
catalog_keys: string[]
supported_source_modules: string[]
supported_report_types: string[]
registered_actions: string[]
checks: list[{name,status,message?}]
export_enabled: boolean
generated_at: string
```

硬性限制：

1. 不读取环境变量值。
2. 不返回数据库连接串、ERPNext URL、token、cookie、Authorization、secret、password、DSN。
3. 不查询业务 DB。
4. 不访问 ERPNext。
5. 不触发导出下载，只检查导出服务类/方法存在或用安全本地静态数据做内存级检查。

### 4.4 main.py 动作映射

在 `app/main.py` 的路径动作映射中补充：

```text
/api/reports/diagnostic -> module=report / action=report:diagnostic / resource_type=ReportDiagnostic
```

要求：

1. 不影响 `/api/reports/catalog`。
2. 不影响 `/api/reports/catalog/export`。
3. 不影响 `/api/reports/catalog/{report_key}`。

## 5. 测试要求

新增或补充测试必须覆盖：

1. 持有 `report:diagnostic` 可访问 `GET /api/reports/diagnostic`。
2. 仅持有 `report:read` 访问诊断接口返回 403。
3. 仅持有 `report:export` 访问诊断接口返回 403。
4. 仅持有 `dashboard:read` 访问诊断接口返回 403。
5. 响应字段包含 `module/status/catalog_count/catalog_keys/supported_source_modules/supported_report_types/registered_actions/checks/export_enabled/generated_at` 或等价字段。
6. 响应不包含 `token/cookie/secret/password/Authorization/DSN/dsn/DATABASE_URL` 等敏感字段名和值。
7. `report:diagnostic` 已在 `MODULE_ACTION_REGISTRY["report"]` 中注册。
8. `main.py` 动作映射可识别 `/api/reports/diagnostic` 为 `report:diagnostic`。
9. 060B/060C 既有 catalog/export 测试继续通过。

## 6. 验证命令

### 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_report_diagnostic.py tests/test_report_catalog_readonly.py tests/test_report_catalog_export.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/report.py
rg -n "@router\.(post|put|patch|delete)" app/routers/report.py || true
rg -n "requests\.|httpx\.|/api/resource|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/report.py || true
rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/report.py || true
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL" app/routers/report.py app/services/report_diagnostic_service.py app/schemas/report.py || true
```

### 前端回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
rg -n "report:diagnostic|/api/reports/diagnostic|diagnostic|cache_refresh|recalculate|generate|sync|submit|fetch\(|axios\.|/api/resource" src/api/report.ts src/views/reports/ReportCatalog.vue src/router/index.ts || true
```

### 禁改目录

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
```

## 7. 回交格式

B 完成后回交 C，必须使用以下格式：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060D
ROLE: B Engineer

CHANGED_FILES:
- <真实改动文件绝对路径>

EVIDENCE:
- report:diagnostic 权限注册证据
- GET /api/reports/diagnostic 路由证据
- 诊断响应字段与敏感信息排除证据
- main.py 动作映射证据
- 仅 report:read/report:export/dashboard:read 访问诊断接口返回 403 的测试证据
- 未修改前端文件证据
- 未新增写路由、ERPNext 访问、outbox/worker/internal/cache_refresh/recalculate/generate/sync/submit 证据

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 负向扫描结果
- 禁改目录 diff 结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 8. 完成定义

1. `GET /api/reports/diagnostic` 可用。
2. `report:diagnostic` 是唯一入口动作权限。
3. `report:read/report:export/dashboard:read` 不能替代诊断权限。
4. 响应只包含安全健康摘要，不泄露敏感字段和值。
5. 未新增普通前端入口。
6. 未新增写路由、ERPNext 访问、DB 业务查询、outbox、worker、run-once、internal、cache_refresh、recalculate、generate、sync、submit。
7. 060B/060C 既有 catalog/export 测试不回退。
8. 禁改目录 diff 为空。
