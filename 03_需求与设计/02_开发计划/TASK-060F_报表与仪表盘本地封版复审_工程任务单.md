# TASK-060F 报表与仪表盘本地封版复审 工程任务单

## 1. 基本信息

- 任务编号：TASK-060F
- 任务名称：报表与仪表盘本地封版复审
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：报表与仪表盘 / dashboard + reports
- 优先级：P1
- 前置依赖：TASK-060E 审计通过（审计意见书第418份）
- 当前定位：对报表与仪表盘 `TASK-060A~060E` 任务链做本地封版复审证据汇总和核验。本任务只输出证据，不新增功能、不修改业务代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实复审证据、测试结果、扫描结果和证据路径前，不得回交 C。

## 2. 任务目标

输出一份可交给 C Auditor 审计的报表与仪表盘本地封版复审证据，证明以下链路均已闭环：

1. `TASK-060A`：报表与仪表盘只读总览基线，`GET /api/dashboard/overview`，`dashboard:read`。
2. `TASK-060B`：报表中心只读目录与权限基线，`GET /api/reports/catalog`、`GET /api/reports/catalog/{report_key}`，`report:read`。
3. `TASK-060C + FIX1 + FIX2`：报表目录 CSV 导出安全基线，`GET /api/reports/catalog/export`，`report:export`，CSV 注入防护，前端统一下载与错误提示闭环。
4. `TASK-060D`：报表诊断只读健康检查基线，`GET /api/reports/diagnostic`，`report:diagnostic`。
5. `TASK-060E`：报表与仪表盘本地收口验证。
6. `report:cache_refresh / recalculate / generate / sync / submit` 继续冻结。

本任务结论只能写：

```text
建议进入 C 本地封版审计
暂不建议进入 C 本地封版审计
```

不得自行宣布：

```text
报表与仪表盘已正式封版
生产发布通过
ERPNext 生产联调通过
GitHub required check 闭环
远端 push / PR / tag 完成
```

## 3. 允许范围

只允许新增或追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需临时命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终证据文档只摘录关键结论，不得灌入大段原始日志。

## 4. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/**` 后端业务代码、schema、router、service、main.py、adapter、model、migration。
2. 禁止修改 `07_后端/lingyi_service/tests/**` 后端测试代码。
3. 禁止修改 `06_前端/lingyi-pc/src/**` 前端源码。
4. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
5. 禁止修改审计日志、架构日志、控制面文件。
6. 禁止新增或修改 API 行为。
7. 禁止新增 `report:cache_refresh`、`report:recalculate`、`report:generate`、`report:sync`、`report:submit`。
8. 禁止新增写路由、ERPNext 访问、业务 DB 查询、outbox、worker、run-once、internal。
9. 禁止 commit、push、PR、tag、生产发布。
10. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核对的审计编号

证据文档必须逐项列出并核对以下审计编号：

| 任务 | 审计结论 |
| --- | --- |
| TASK-060A | 审计意见书第405份 阻塞；第406份 通过 |
| TASK-060B | 审计意见书第407份 阻塞；第408份 通过 |
| TASK-060C | 审计意见书第409份 阻塞；第410份 需修复 |
| TASK-060C_FIX1 | 审计意见书第411份 阻塞；第412份 需修复 |
| TASK-060C_FIX2 | 审计意见书第413份 阻塞；第414份 通过 |
| TASK-060D | 审计意见书第415份 阻塞；第416份 通过 |
| TASK-060E | 审计意见书第417份 阻塞；第418份 通过 |

要求：

1. 对 `阻塞/需修复` 项必须说明已由后续控制面对账或 fix pass 闭环。
2. 对最终通过项必须写清核心验证结果。
3. 不得遗漏第418份。

## 6. 必须执行验证命令

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
git tag --points-at HEAD
```

### 6.2 报表与仪表盘核心后端测试

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

期望：全通过。若数量不是 `44 passed, 1 warning`，必须说明差异原因。

### 6.3 Python 编译核验

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

### 6.4 前端 typecheck

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.5 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "dashboard:read|report:read|report:export|report:diagnostic|DASHBOARD_READ|REPORT_READ|REPORT_EXPORT|REPORT_DIAGNOSTIC|/api/dashboard/overview|/api/reports/catalog|/api/reports/catalog/export|/api/reports/diagnostic" \
  app/core/permissions.py app/main.py app/routers/dashboard.py app/routers/report.py tests/test_permissions_registry.py \
  tests/test_dashboard_overview_readonly.py tests/test_report_catalog_readonly.py tests/test_report_catalog_export.py tests/test_report_diagnostic.py
```

要求：四类权限动作和四类路由映射均有证据。

### 6.6 后端只读边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/dashboard.py app/routers/report.py || true
rg -n "requests\.|httpx\.|/api/resource|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" \
  app/routers/dashboard.py app/services/dashboard_service.py app/schemas/dashboard.py \
  app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/report.py || true
rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit" \
  app/routers/dashboard.py app/services/dashboard_service.py app/schemas/dashboard.py \
  app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/report.py || true
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL" \
  app/routers/report.py app/services/report_diagnostic_service.py app/schemas/report.py || true
```

要求：

1. 不得出现 dashboard/report 写路由。
2. 不得出现 ERPNext 同步访问或库存财务高危写语义。
3. `generated_at` 只可作为字段名命中，必须说明不构成 `generate` 动作能力。
4. 敏感字段扫描不得命中泄露。

### 6.7 前端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|report:diagnostic|/api/reports/diagnostic|cache_refresh|recalculate|generate|submit" \
  src/api/dashboard.ts src/views/dashboard/DashboardOverview.vue \
  src/api/report.ts src/views/reports/ReportCatalog.vue src/router/index.ts || true
rg -n "\bsync\b|sync\(" \
  src/api/dashboard.ts src/views/dashboard/DashboardOverview.vue \
  src/api/report.ts src/views/reports/ReportCatalog.vue src/router/index.ts || true
rg -n "requestFile|exportReportCatalogCsv|ElMessage\.error|ElMessage\.warning|URL\.createObjectURL" \
  src/api/request.ts src/api/report.ts src/views/reports/ReportCatalog.vue || true
```

要求：

1. 不得出现裸 `fetch/axios` 或 `/api/resource`。
2. 不得出现普通前端诊断入口。
3. 不得出现 `sync/submit/cache_refresh/recalculate/generate` 业务动作。
4. 必须能证明 CSV 导出仍走统一下载 client、blob 下载和错误提示闭环。

### 6.8 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
git diff --check
```

要求：

1. `.github / 02_源码 / 04_生产` diff 必须为空。
2. 若业务代码区存在继承脏差异，必须列明为历史背景，不得认定为 TASK-060F 新增改动。
3. diff check 必须通过。

## 7. 证据文档要求

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md`

必须包含：

1. 基本信息：任务编号、执行时间、当前分支、当前 HEAD、结论。
2. 任务链路与审计闭环表。
3. 已完成能力清单：dashboard overview、report catalog、catalog export、report diagnostic、TASK-060E 收口验证。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射结果。
8. 后端只读边界扫描结果。
9. 前端边界扫描结果。
10. CSV 导出统一下载与错误提示闭环证据。
11. 敏感信息扫描结果。
12. 禁改目录与继承脏基线结果。
13. 剩余风险。
14. 是否建议进入 C 本地封版审计。

## 8. 剩余风险必须至少披露

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须另开白名单提交任务。
5. `report:cache_refresh / recalculate / generate / sync / submit` 仍冻结，未在本链路放行。

## 9. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060F
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 审计闭环表：证据章节
- 核心测试结果：证据章节
- 权限与路由映射：证据章节
- 后端只读边界扫描：证据章节
- 前端边界扫描：证据章节
- CSV 下载闭环：证据章节
- 敏感信息扫描：证据章节
- 禁改目录与继承脏基线：证据章节
- 剩余风险：证据章节

VERIFICATION:
- 逐条列出命令和结果

BLOCKERS:
- 无；如有，说明阻塞原因和停止位置

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

1. `TASK-060F_报表与仪表盘本地封版复审证据.md` 已生成。
2. `TASK-060A~060E` 审计编号与闭环路径完整。
3. 后端核心测试、Python 编译、前端 typecheck 均通过。
4. 权限、路由、只读边界、前端边界、CSV 下载闭环、敏感信息扫描均有证据。
5. 禁改目录 diff 为空。
6. 本任务未修改业务代码、测试代码或前端源码。
7. 本任务未 commit / push / PR / tag / 生产发布。
