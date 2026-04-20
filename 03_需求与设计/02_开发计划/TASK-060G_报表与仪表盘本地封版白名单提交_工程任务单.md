# TASK-060G 报表与仪表盘本地封版白名单提交 工程任务单

## 1. 基本信息

- 任务编号：TASK-060G
- 任务名称：报表与仪表盘本地封版白名单提交
- 模块：报表与仪表盘 / 本地封版
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-060F 审计通过（审计意见书第420份）
- 当前定位：把 TASK-060A~TASK-060F 已通过审计的报表与仪表盘链路纳入本地 git 基线，形成可审计的本地封版 commit。

## 2. 任务目标

完成一次严格白名单本地提交：

1. 复核当前分支、HEAD、脏工作树。
2. 复跑报表与仪表盘核心测试、Python 编译、前端 typecheck 与边界扫描。
3. 生成 `TASK-060G_报表与仪表盘本地封版提交证据.md`。
4. 只按白名单显式 `git add`。
5. 创建本地 commit。
6. 提交后再把控制面切到 `READY_FOR_AUDIT / C Auditor / TASK-060G`。
7. 回交 commit hash、staged 清单、验证结果和证据路径给 C Auditor。

本任务只允许本地 commit，不允许：

```text
push / PR / tag / 生产发布 / ERPNext 生产联调声明 / GitHub required check 闭环声明
```

## 3. 允许新增或修改的证据文件

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 允许纳入本地 commit 的白名单

只能暂存以下文件。未列入的文件一律不得暂存。

### 4.1 后端代码

- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/routers/dashboard.py`
- `07_后端/lingyi_service/app/routers/report.py`
- `07_后端/lingyi_service/app/schemas/dashboard.py`
- `07_后端/lingyi_service/app/schemas/report.py`
- `07_后端/lingyi_service/app/services/dashboard_service.py`
- `07_后端/lingyi_service/app/services/report_catalog_service.py`
- `07_后端/lingyi_service/app/services/report_export_service.py`
- `07_后端/lingyi_service/app/services/report_diagnostic_service.py`

### 4.2 后端测试

- `07_后端/lingyi_service/tests/test_permissions_registry.py`
- `07_后端/lingyi_service/tests/test_dashboard_overview_readonly.py`
- `07_后端/lingyi_service/tests/test_report_catalog_readonly.py`
- `07_后端/lingyi_service/tests/test_report_catalog_export.py`
- `07_后端/lingyi_service/tests/test_report_diagnostic.py`

### 4.3 前端代码

- `06_前端/lingyi-pc/src/api/request.ts`
- `06_前端/lingyi-pc/src/api/dashboard.ts`
- `06_前端/lingyi-pc/src/api/report.ts`
- `06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
- `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
- `06_前端/lingyi-pc/src/router/index.ts`

### 4.4 任务与证据文档

- `03_需求与设计/02_开发计划/TASK-060A_报表与仪表盘只读总览基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060B_报表中心只读目录与权限基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060C_报表目录CSV导出安全基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060C_FIX1_报表目录CSV导出前端统一客户端修复_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060C_FIX2_报表目录CSV导出错误提示闭环_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060D_报表诊断只读健康检查基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md`
- `03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md`
- `03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版白名单提交_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版提交证据.md`
- `03_需求与设计/02_开发计划/工程师会话日志.md`

### 4.5 控制与审计日志

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
10. 禁止暂存 `TASK-021* / TASK-022* / TASK-023* / TASK-024*` 等非报表与仪表盘任务单。
11. 禁止暂存 `07_后端/lingyi_service/tests/test_permission_audit_baseline.py`，该文件属于历史继承背景，不属于本次封版白名单。
12. 禁止修改业务代码后再封版；如发现需要修复，立即 `BLOCKED`。
13. 禁止 push / PR / tag / 生产发布。

## 6. 必须执行验证

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
git tag --points-at HEAD
```

要求：当前分支应为 `codex/sprint4-seal`；当前 HEAD 应为 `424a4b1` 或其后继本地提交；提交前不得已有本任务 tag。

### 6.2 报表与仪表盘后端测试

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

期望：`44 passed, 1 warning` 或等价全通过结果。

### 6.3 Python 编译

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile \
  app/routers/dashboard.py \
  app/routers/report.py \
  app/services/dashboard_service.py \
  app/services/report_catalog_service.py \
  app/services/report_export_service.py \
  app/services/report_diagnostic_service.py \
  app/schemas/dashboard.py \
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
rg -n "dashboard:read|report:read|report:export|report:diagnostic|DASHBOARD_READ|REPORT_" app/core/permissions.py app/main.py app/routers/dashboard.py app/routers/report.py tests/test_permissions_registry.py tests/test_dashboard_overview_readonly.py tests/test_report_*.py
```

要求：必须命中四类权限动作及 `main.py` 对应映射。

### 6.6 后端只读边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/dashboard.py app/routers/report.py
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|Stock Entry|Stock Reconciliation|Stock Ledger Entry|GL Entry|Payment Entry|Purchase Invoice" app/routers/dashboard.py app/routers/report.py app/services/dashboard_service.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py
rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit" app/routers/dashboard.py app/routers/report.py app/services/dashboard_service.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/dashboard.py app/schemas/report.py
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL" app/routers/dashboard.py app/routers/report.py app/services/dashboard_service.py app/services/report_catalog_service.py app/services/report_export_service.py app/services/report_diagnostic_service.py app/schemas/dashboard.py app/schemas/report.py
```

要求：无写路由、无 ERPNext/库存/财务高危写语义、无 outbox/worker/internal 等冻结能力、无敏感信息泄露。`generated_at` 字段名不视为 `generate` 动作能力，但必须在证据中说明。

### 6.7 前端边界与下载闭环扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios|/api/resource|/api/reports/diagnostic|cache_refresh|recalculate|generate|sync|submit" src/api/dashboard.ts src/api/report.ts src/views/dashboard/DashboardOverview.vue src/views/reports/ReportCatalog.vue
rg -n "requestFile|exportReportCatalogCsv|URL\.createObjectURL|ElMessage\.error|ElMessage\.warning|await reportApi\.exportReportCatalogCsv" src/api/request.ts src/api/report.ts src/views/reports/ReportCatalog.vue
```

要求：无裸 `fetch/axios`、无直连 `/api/resource`、无普通前端诊断入口、无 `sync/submit`；CSV 下载链路必须命中统一下载 helper、blob 下载与错误提示。

### 6.8 禁改目录检查

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
git diff --check
```

要求：禁改目录 diff 为空；`git diff --check` 通过。

## 7. 生成封版提交证据

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版提交证据.md`

必须包含：

1. 当前分支、提交前 HEAD。
2. 前置审计：第420份 `TASK-060F PASS`。
3. 报表与仪表盘审计闭环摘要：第405~420份关键结论。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射扫描结果。
8. 后端只读边界扫描结果。
9. 前端边界与 CSV 下载闭环扫描结果。
10. 禁改目录与 diff check 结果。
11. staged 白名单清单。
12. 残余风险。

注意：本证据文件内不要在 commit 后回填 commit hash。commit hash 只在 B 回交正文中报告，避免封版 commit 后产生 post-commit 脏改动。如 B 认为必须把 commit hash 写入文件，必须停止并回报 `BLOCKED`，不得自行创建第二个 metadata commit。

## 8. 白名单暂存要求

必须从项目根目录执行显式路径暂存。示例：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add -- \
  '07_后端/lingyi_service/app/core/permissions.py' \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/routers/dashboard.py' \
  '07_后端/lingyi_service/app/routers/report.py' \
  '07_后端/lingyi_service/app/schemas/dashboard.py' \
  '07_后端/lingyi_service/app/schemas/report.py' \
  '07_后端/lingyi_service/app/services/dashboard_service.py' \
  '07_后端/lingyi_service/app/services/report_catalog_service.py' \
  '07_后端/lingyi_service/app/services/report_export_service.py' \
  '07_后端/lingyi_service/app/services/report_diagnostic_service.py' \
  '07_后端/lingyi_service/tests/test_permissions_registry.py' \
  '07_后端/lingyi_service/tests/test_dashboard_overview_readonly.py' \
  '07_后端/lingyi_service/tests/test_report_catalog_readonly.py' \
  '07_后端/lingyi_service/tests/test_report_catalog_export.py' \
  '07_后端/lingyi_service/tests/test_report_diagnostic.py' \
  '06_前端/lingyi-pc/src/api/request.ts' \
  '06_前端/lingyi-pc/src/api/dashboard.ts' \
  '06_前端/lingyi-pc/src/api/report.ts' \
  '06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue' \
  '06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '03_需求与设计/02_开发计划/TASK-060A_报表与仪表盘只读总览基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060B_报表中心只读目录与权限基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060C_报表目录CSV导出安全基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060C_FIX1_报表目录CSV导出前端统一客户端修复_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060C_FIX2_报表目录CSV导出错误提示闭环_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060D_报表诊断只读健康检查基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060E_报表与仪表盘本地收口验证报告.md' \
  '03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060F_报表与仪表盘本地封版复审证据.md' \
  '03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版白名单提交_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-060G_报表与仪表盘本地封版提交证据.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md' \
  '00_交接与日志/HANDOVER_STATUS.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

暂存后必须检查：

```bash
git diff --cached --name-only | sort
git diff --cached --name-only | rg '(^\.github/|^\.ci-reports/|^01_|^02_|^03_环境|^04_|^05_|TASK-021|TASK-022|TASK-023|TASK-024|test_permission_audit_baseline\.py)' && exit 1 || true
```

要求：暂存清单只能包含第 4 节白名单文件；禁止模式扫描必须无命中。

## 9. 创建本地 commit

```bash
cd /Users/hh/Desktop/领意服装管理系统
git commit -m "chore: seal report dashboard baseline"
```

提交后必须验证：

```bash
git rev-parse --short HEAD
git show --stat --oneline --name-only HEAD
git diff --cached --name-only
git tag --points-at HEAD
git status --short --branch
```

要求：

- `git diff --cached --name-only` 为空。
- `git tag --points-at HEAD` 为空。
- 未 push、未 PR、未 tag、未生产发布。
- 如出现非白名单文件进入 commit，立即 `NEEDS_FIX` 回交，不得继续操作。

## 10. 提交后控制面写回

本地 commit 成功后，再写回：

- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`：`READY_FOR_AUDIT / C Auditor / TASK-060G`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`：`TASK-060G / 状态=待审计`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`：追加本任务完成记录

注意：提交后控制面写回可能产生 post-commit 工作树差异，这是共享流程状态，不得为此创建第二个 commit。C 审计时以本地封版 commit 与控制面状态分别核验。

## 11. 回交模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060G
ROLE: B Engineer

CHANGED_FILES:
- TASK-060G_报表与仪表盘本地封版提交证据.md
- 工程师会话日志.md
- 本地 commit: <hash> chore: seal report dashboard baseline

EVIDENCE:
- 当前分支：codex/sprint4-seal
- 提交前 HEAD：<old_hash>
- 提交后 HEAD：<new_hash>
- parent：<parent_hash>
- staged 白名单清单：<文件数量与清单>
- pytest：<结果>
- py_compile：<结果>
- npm run typecheck：<结果>
- 权限动作与路由映射扫描：<结果>
- 后端只读边界扫描：<结果>
- 前端边界与 CSV 下载闭环扫描：<结果>
- 禁改目录 diff：<结果>
- git diff --cached --name-only：空
- git tag --points-at HEAD：空
- 未 push / 未 PR / 未 tag / 未生产发布

VERIFICATION:
- 列出实际执行命令与关键输出

BLOCKERS:
- 无

NEXT_ROLE:
- C Auditor
```

## 12. 完成定义

同时满足才算完成：

1. `TASK-060G_报表与仪表盘本地封版提交证据.md` 已生成。
2. 后端 pytest、py_compile、前端 typecheck、边界扫描均通过。
3. 暂存清单严格等于白名单子集，且无禁止模式命中。
4. 本地 commit 已创建，message 为 `chore: seal report dashboard baseline`。
5. 未 push / 未 PR / 未 tag / 未生产发布。
6. commit 后未创建第二个 metadata commit。
7. 控制面已切到 `READY_FOR_AUDIT / C Auditor / TASK-060G`。
8. 回交正文包含 commit hash、证据文件路径、测试结果、扫描结果与白名单清单。
