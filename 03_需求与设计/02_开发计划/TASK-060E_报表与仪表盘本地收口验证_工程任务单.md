# TASK-060E 报表与仪表盘本地收口验证 工程任务单

- 任务编号：TASK-060E
- 任务名称：报表与仪表盘本地收口验证
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：报表与仪表盘 / dashboard + reports
- 前置依据：`TASK-019_报表与仪表盘总体设计.md`、`TASK-019A_报表与仪表盘总体设计.md`、`TASK-060A` 审计意见书第406份通过、`TASK-060B` 第408份通过、`TASK-060C_FIX2` 第414份通过、`TASK-060D` 第416份通过
- 当前定位：对 `TASK-060A~060D` 报表与仪表盘本地实现链路做收口验证与证据汇总。不新增功能、不修代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实验证报告、测试结果、扫描结果和证据路径前，不得回交 C。

## 1. 目标

输出一份可交给 C Auditor 审计的报表与仪表盘本地收口验证报告，证明以下链路均已闭环：

1. `TASK-060A`：`GET /api/dashboard/overview` 只读总览，`dashboard:read` 独立权限。
2. `TASK-060B`：`GET /api/reports/catalog` 与 `GET /api/reports/catalog/{report_key}` 只读目录，`report:read` 独立权限。
3. `TASK-060C` + FIX1 + FIX2：`GET /api/reports/catalog/export` CSV 导出，`report:export` 独立权限，CSV 公式注入防护，前端统一下载 client 与错误提示闭环。
4. `TASK-060D`：`GET /api/reports/diagnostic` 安全健康摘要，`report:diagnostic` 独立权限。
5. `report:cache_refresh`、`recalculate`、`generate`、`sync`、`submit` 继续冻结。
6. 未新增普通前端诊断入口、写路由、ERPNext 写调用、业务 DB 查询、outbox、worker、run-once、internal。

## 2. 允许修改范围

仅允许新增或更新以下证据文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需要临时保存命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终报告必须摘录关键结论，不得把大段原始日志灌入文档。

## 3. 禁止修改范围

1. 禁止修改任何后端业务代码：`07_后端/lingyi_service/app/**`。
2. 禁止修改任何后端测试代码：`07_后端/lingyi_service/tests/**`。
3. 禁止修改任何前端代码：`06_前端/lingyi-pc/src/**`。
4. 禁止修改 `03_需求与设计/01_架构设计/**`、`03_需求与设计/05_审计记录/**`。
5. 禁止修改 `.github`、`02_源码`、`04_生产`。
6. 禁止新增或启用 `report:cache_refresh`、`recalculate`、`generate`、`sync`、`submit`。
7. 禁止新增 write route、migration、model、outbox、worker、run-once、internal、ERPNext 写调用。
8. 禁止 commit / push / PR / tag / 生产发布。

## 4. 必须核验的任务闭环

验证报告必须逐项列出：

| 任务 | 审计意见书 | 必须核验证据 |
|---|---:|---|
| TASK-060A | 第406份 | dashboard overview 路由、权限、测试、只读边界 |
| TASK-060B | 第408份 | report catalog 路由、七类目录、权限、静态目录边界 |
| TASK-060C | 第410份、414份 | export 路由、CSV 安全、前端统一下载、错误提示闭环 |
| TASK-060D | 第416份 | diagnostic 路由、权限、敏感信息排除、安全健康摘要 |

## 5. 必跑验证命令

### 5.1 后端核心测试

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

### 5.2 Python 编译

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

### 5.3 前端类型检查

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 5.4 后端只读边界扫描

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

### 5.5 前端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|report:diagnostic|/api/reports/diagnostic|cache_refresh|recalculate|generate|submit" \
  src/api/dashboard.ts src/views/dashboard/DashboardOverview.vue \
  src/api/report.ts src/views/reports/ReportCatalog.vue src/router/index.ts || true
rg -n "\bsync\b|sync\(" \
  src/api/dashboard.ts src/views/dashboard/DashboardOverview.vue \
  src/api/report.ts src/views/reports/ReportCatalog.vue src/router/index.ts || true
```

### 5.6 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "dashboard:read|report:read|report:export|report:diagnostic|DASHBOARD_READ|REPORT_READ|REPORT_EXPORT|REPORT_DIAGNOSTIC|/api/dashboard/overview|/api/reports/catalog|/api/reports/catalog/export|/api/reports/diagnostic" \
  app/core/permissions.py app/main.py app/routers/dashboard.py app/routers/report.py tests/test_permissions_registry.py \
  tests/test_dashboard_overview_readonly.py tests/test_report_catalog_readonly.py tests/test_report_catalog_export.py tests/test_report_diagnostic.py
```

### 5.7 禁改目录与报告文件 diff

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

## 6. 报告必须包含的章节

在 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md` 中至少包含：

1. 结论：建议进入 C 收口审计 / 暂不建议。
2. 任务链路：`TASK-060A~060D` 与审计意见书编号。
3. 测试结果：pytest、py_compile、npm typecheck。
4. 权限闭环：`dashboard:read`、`report:read`、`report:export`、`report:diagnostic`。
5. 路由闭环：四类 GET 路由与 main.py 映射。
6. 前端闭环：dashboard 页面、report catalog 页面、CSV 导出统一下载、错误提示闭环。
7. 禁止能力扫描：写路由、ERPNext、DB 业务查询、outbox/worker/internal、cache_refresh/recalculate/generate/sync/submit。
8. 敏感信息扫描：Authorization/Cookie/token/secret/password/DSN/DATABASE_URL。
9. 禁改目录检查。
10. 工作树残余风险：如存在继承脏差异或未跟踪目录，必须说明不属于本任务新增业务改动。
11. 明确声明：本地收口验证不等同 commit / push / PR / tag / 生产发布。

## 7. 回交格式

B 完成后回交 C，必须使用以下格式：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060E
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- TASK-060A~060D 审计闭环编号
- pytest / py_compile / npm typecheck 结果
- 权限动作与路由映射扫描结果
- 后端只读边界扫描结果
- 前端边界扫描结果
- 敏感信息扫描结果
- 禁改目录 diff 结果
- 未修改业务代码证据

VERIFICATION:
- 逐条列出命令和结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 8. 完成定义

1. 收口验证报告已生成。
2. `TASK-060A~060D` 审计编号与能力闭环完整。
3. 后端核心测试、Python 编译、前端 typecheck 均通过。
4. 权限与路由映射扫描可证明四类动作闭环。
5. 负向扫描未发现新增写路由、ERPNext 访问、业务 DB 查询、outbox/worker/run-once/internal/cache_refresh/recalculate/generate/sync/submit。
6. 前端未暴露普通诊断入口，未直连 ERPNext，未裸 `fetch/axios`。
7. 敏感信息扫描无泄露。
8. 禁改目录 diff 为空。
9. 本任务未修改业务代码、测试代码或前端源码。
