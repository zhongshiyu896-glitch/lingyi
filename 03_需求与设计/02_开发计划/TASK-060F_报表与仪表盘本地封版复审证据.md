# TASK-060F 报表与仪表盘本地封版复审证据

- 任务编号：TASK-060F
- 执行时间：2026-04-21 02:06 CST+8
- 当前分支：`codex/sprint4-seal`
- 当前 HEAD：`424a4b1`
- 结论：建议进入 C 本地封版审计

## 1. 任务链路与审计闭环

| 任务 | 审计结论 | 闭环说明 |
| --- | --- | --- |
| TASK-060A | 第405份阻塞；第406份通过 | 由第406份通过闭环 |
| TASK-060B | 第407份阻塞；第408份通过 | 由第408份通过闭环 |
| TASK-060C | 第409份阻塞；第410份需修复 | 由 FIX1/FIX2 后续闭环 |
| TASK-060C_FIX1 | 第411份阻塞；第412份需修复 | 由 FIX2 后续闭环 |
| TASK-060C_FIX2 | 第413份阻塞；第414份通过 | 由第414份通过闭环 |
| TASK-060D | 第415份阻塞；第416份通过 | 由第416份通过闭环 |
| TASK-060E | 第417份阻塞；第418份通过 | 由第418份通过闭环 |

## 2. 已完成能力清单

1. `TASK-060A`：`GET /api/dashboard/overview`，`dashboard:read`。
2. `TASK-060B`：`GET /api/reports/catalog`、`GET /api/reports/catalog/{report_key}`，`report:read`。
3. `TASK-060C + FIX1 + FIX2`：`GET /api/reports/catalog/export`，`report:export`，CSV 注入防护，前端统一下载与错误提示闭环。
4. `TASK-060D`：`GET /api/reports/diagnostic`，`report:diagnostic`。
5. `TASK-060E`：本地收口验证已通过（第418份）。
6. `report:cache_refresh / recalculate / generate / sync / submit` 仍冻结。

## 3. 后端测试结果

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_dashboard_overview_readonly.py \
  tests/test_report_catalog_readonly.py \
  tests/test_report_catalog_export.py \
  tests/test_report_diagnostic.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

结果：`44 passed, 1 warning`（与任务单期望一致）。

## 4. Python 编译结果

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile \
  app/routers/dashboard.py \
  app/services/dashboard_service.py \
  app/schemas/dashboard.py \
  app/routers/report.py \
  app/services/report_catalog_service.py \
  app/services/report_export_service.py \
  app/services/report_diagnostic_service.py \
  app/schemas/report.py
```

结果：通过（无报错输出）。

## 5. 前端 typecheck 结果

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

结果：通过（`vue-tsc --noEmit` 退出码 0）。

## 6. 权限动作与 main.py 路由映射

扫描命中结果显示以下项均存在：

- 权限动作：`dashboard:read`、`report:read`、`report:export`、`report:diagnostic`
- 常量：`DASHBOARD_READ`、`REPORT_READ`、`REPORT_EXPORT`、`REPORT_DIAGNOSTIC`
- 路由与映射：
  - `/api/dashboard/overview`
  - `/api/reports/catalog`
  - `/api/reports/catalog/export`
  - `/api/reports/diagnostic`
  - `main.py` 中对应 action mapping 分支

## 7. 后端只读边界扫描

1. 写路由扫描：`dashboard.py`、`report.py` 未命中 `@router.post/put/patch/delete`。
2. ERPNext/库存财务高危写语义扫描：未命中 `requests/httpx` 与 `/api/resource` 写调用，也未命中 `Stock Entry/Stock Reconciliation/GL Entry/Payment Entry/Purchase Invoice/Sales Invoice`。
3. 冻结能力扫描：仅命中 `generated_at` 字段（`dashboard_service.py`、`dashboard.py` schema），属于时间戳字段名，不构成 `generate` 动作能力；未发现 `cache_refresh/recalculate/sync/submit` 实现。
4. 敏感信息扫描：未命中 `Authorization/Cookie/token/secret/password/DSN/DATABASE_URL` 泄露项。

## 8. 前端边界扫描

1. 裸调用与越界动作扫描：
   - 未命中裸 `fetch/axios`。
   - 未命中 `/api/resource`。
   - 未命中 `report:diagnostic` 普通前端入口。
   - 未命中 `cache_refresh/recalculate/submit/sync` 动作。
   - 命中 `generated_at` 与“生成时间”展示文本，属于只读展示字段。
2. CSV 导出闭环扫描命中：
   - `src/api/request.ts`：`requestFile` 存在。
   - `src/api/report.ts`：`exportReportCatalogCsv` 调用 `requestFile`，并使用 `URL.createObjectURL` 下载 blob。
   - `src/views/reports/ReportCatalog.vue`：存在 `await reportApi.exportReportCatalogCsv(...)` 与 `ElMessage.error/ElMessage.warning` 错误提示闭环。

## 9. 禁改目录与继承脏基线

1. 禁改目录：

```bash
git diff --name-only -- .github 02_源码 04_生产
```

结果：空。

2. 业务代码区 diff 观察：

```bash
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
```

结果：存在继承脏基线（`request.ts`、`router/index.ts`、`permissions.py`、`main.py`、`test_permissions_registry.py`），为历史状态，不属于 TASK-060F 新增改动。

3. diff check：

```bash
git diff --check
```

结果：通过。

## 10. 剩余风险

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须另开白名单提交任务。
5. `report:cache_refresh / recalculate / generate / sync / submit` 仍冻结，未在本链路放行。
