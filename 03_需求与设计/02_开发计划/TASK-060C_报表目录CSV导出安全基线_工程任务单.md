# TASK-060C 报表目录 CSV 导出安全基线 工程任务单

- 任务编号：TASK-060C
- 任务名称：报表目录 CSV 导出安全基线
- 角色：B Engineer
- 派发时间：2026-04-20 23:39 CST+8
- 派发人：A Technical Architect
- 模块：报表与仪表盘 / reports
- 前置依据：`TASK-019_报表与仪表盘总体设计.md`、`TASK-060B` 审计意见书第408份通过
- 当前定位：报表方向第三张任务。060B 已完成报表目录只读 API；本任务只补报表目录 CSV 导出安全基线，不实现具体业务报表数据导出、不实现诊断、不实现缓存刷新。

## 0. 强制说明

本任务单是 A -> B 执行指令，不是 B -> C 审计输入。

未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

本任务不允许 commit、push、PR、tag、生产发布。

## 1. 目标

在 `TASK-060B` 的报表目录基础上，新增只读 CSV 导出能力：

1. 新增 `GET /api/reports/catalog/export`。
2. 注册并校验 `report:export`。
3. 导出内容仅限 060B 的报表目录元数据，不查询业务明细。
4. CSV 输出必须防公式注入。
5. 固定安全文件名，不允许用户输入进入文件名。
6. 前端在 `ReportCatalog.vue` 增加“导出目录 CSV”只读按钮。

## 2. 允许修改文件

### 2.1 后端允许新增

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_export_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_report_catalog_export.py`

### 2.2 后端允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
  - 仅允许新增 `REPORT_EXPORT = "report:export"` 并加入 `ALL_REPORT_ACTIONS`。
  - 禁止注册 `report:diagnostic / report:cache_refresh`。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/report.py`
  - 仅允许新增 `GET /api/reports/catalog/export`。
  - 注意：必须把 `/catalog/export` 路由声明在 `/catalog/{report_key}` 之前，避免被动态详情路由吞掉。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
  - 仅允许补 `/api/reports/catalog/export` 安全审计 fallback：`module=report / action=report:export / resource=ReportCatalogExport`。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_catalog_service.py`
  - 仅允许复用已有 catalog/filter 逻辑供导出读取静态目录；不得改动 060B 已审计字段语义。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`（仅允许补充 `report:export` 注册测试；如已有覆盖则不要改）

### 2.3 前端允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`

### 2.4 前端禁止修改

- 本任务不允许修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`。

## 3. 禁止修改范围

1. 禁止修改 `.github/**`。
2. 禁止修改 `02_源码/**`。
3. 禁止修改 `04_生产/**`。
4. 禁止新增或修改 migration。
5. 禁止新增或修改 `app/models/**`。
6. 禁止修改 dashboard、quality、sales_inventory、warehouse 既有业务语义。
7. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
8. 禁止新增 ERPNext 访问或 ERPNext 写调用。
9. 禁止新增 DB 业务查询；导出数据只能来自 `report_catalog_service.py` 的静态目录。
10. 禁止新增 `outbox`、`worker`、`run-once`、`internal` 接口。
11. 禁止新增 diagnostic、cache_refresh、recalculate、generate、sync、submit 能力。
12. 禁止 commit、push、PR、tag、生产发布。

## 4. 后端接口契约

### 4.1 路由

```text
GET /api/reports/catalog/export
```

### 4.2 权限

必须校验：

```text
report:export
```

不得接受以下权限作为通过条件：

```text
report:read
dashboard:read
quality:read
sales_inventory:read
warehouse:read
inventory:read
```

### 4.3 查询参数

复用 060B catalog 的本地过滤参数：

- `company`：可选，只进入导出元数据或审计上下文，不触发业务查询。
- `source_module`：可选，只能在目录元数据中本地过滤。
- `report_type`：可选，只能在目录元数据中本地过滤。

非法 `source_module` 或 `report_type` 必须返回 `400 / INVALID_QUERY_PARAMETER`，不得静默降级。

### 4.4 CSV 字段

CSV 至少包含以下列：

```text
report_key,name,source_modules,report_type,required_filters,optional_filters,metric_summary,permission_action,status
```

数组字段使用 `|` 连接。

### 4.5 响应头

- `Content-Type` 必须以 `text/csv` 开头，并使用 UTF-8。
- `Content-Disposition` 必须包含固定安全文件名前缀：`report_catalog_export_`。
- 文件名不得包含用户输入的 `company/source_module/report_type`。

### 4.6 CSV 公式注入防护

任何单元格值如果去除左侧空白后以以下字符开头，必须加单引号前缀或等价安全转义：

```text
= + - @ \t \r \n
```

测试必须覆盖至少以下恶意值：

```text
=cmd|'/C calc'!A0
+SUM(1,2)
-10
@HYPERLINK("http://evil")
```

## 5. 后端实现要求

1. `app/services/report_export_service.py` 只负责 CSV 构造、单元格安全转义、固定文件名与 content_type。
2. `app/routers/report.py` 新增 `/catalog/export` 路由，调用 `ReportCatalogService` 的静态目录结果。
3. `app/core/permissions.py` 注册 `report:export`。
4. `app/main.py` 补安全审计 fallback 映射。
5. 可复用 `warehouse_export_service.py` 的思路，但不要改 warehouse 文件。
6. 不得把用户输入拼进文件名。
7. 不得导出业务明细或访问 ERPNext/DB 业务表。

## 6. 前端实现要求

1. `src/api/report.ts` 增加 `exportReportCatalogCsv(query)`。
2. 必须通过统一 `request` 或项目既有下载 client；不得裸 `fetch` / `axios`。
3. `ReportCatalog.vue` 增加“导出目录 CSV”按钮。
4. 按钮只调用 `/api/reports/catalog/export`，不得调用任何业务报表导出接口。
5. 不得新增诊断、刷新、重算、生成、同步、提交按钮。
6. 不得修改路由文件。

## 7. 测试要求

新增或补充测试必须覆盖：

1. 仅 `report:export` 可访问 `/api/reports/catalog/export`。
2. 只有 `report:read` 但无 `report:export` 时返回 403。
3. 只有其他模块 read/export 权限时返回 403。
4. 导出 CSV 包含 TASK-019 七类报表目录。
5. `source_module / report_type` 本地过滤有效。
6. 非法 `source_module / report_type` 返回 400。
7. CSV 公式注入值被安全转义。
8. `Content-Disposition` 文件名不包含用户输入。
9. report router 中不存在新增 `POST/PUT/PATCH/DELETE`。
10. report export 相关文件中不存在 ERPNext 访问、DB 业务查询、outbox、worker、run-once、internal、diagnostic、cache_refresh、recalculate、generate、sync、submit。
11. 前端 typecheck 通过。

## 8. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_report_catalog_export.py tests/test_report_catalog_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py
rg -n "@router\.(post|put|patch|delete)" app/routers/report.py || true
rg -n "requests\.|httpx\.|/api/resource|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py || true
rg -n "outbox|worker|run-once|internal|diagnostic|cache_refresh|recalculate|generate|sync|submit" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py || true
rg -n "Session\(|query\(|select\(|execute\(" app/services/report_export_service.py app/services/report_catalog_service.py || true
git diff --name-only -- .github 02_源码 04_生产
```

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource|diagnostic|cache_refresh|recalculate|generate|sync|submit" src/api/report.ts src/views/reports/ReportCatalog.vue || true
git diff --name-only -- src/router/index.ts
```

说明：`src/api/report.ts` 出现 TypeScript `export` 关键字不算违规；C 审计时应区分语法 export 与业务导出能力。

## 9. 回交格式

B 完成后回交给 C，必须包含：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060C
ROLE: B Engineer

CHANGED_FILES:
- 真实改动文件列表

EVIDENCE:
- report:export 权限注册和校验证据
- /api/reports/catalog/export 落点
- CSV 字段与七类目录覆盖证据
- CSV 公式注入防护证据
- 前端导出按钮/API 落点
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

## 10. 完成定义

满足以下条件才算完成：

1. `/api/reports/catalog/export` 可用。
2. `report:export` 注册并作为唯一入口权限生效。
3. CSV 覆盖七类 TASK-019 报表目录。
4. CSV 公式注入防护测试通过。
5. 前端 ReportCatalog 页面可触发目录 CSV 导出，且 typecheck 通过。
6. 无新增写路由、无 ERPNext 访问、无 DB 业务查询、无 outbox/worker/internal/diagnostic/cache_refresh/recalculate/generate/sync/submit。
7. 禁改目录 diff 为空。
8. B 回交包含真实验证命令与证据路径。
