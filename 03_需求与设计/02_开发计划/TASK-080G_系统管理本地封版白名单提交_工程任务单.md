# TASK-080G 系统管理本地封版白名单提交 工程任务单

## 1. 基本信息

- 任务编号：TASK-080G
- 任务名称：系统管理本地封版白名单提交
- 模块：系统管理 / 本地封版
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 09:15 CST+8
- 前置依赖：TASK-080F 审计通过（审计意见书第450份）
- 当前定位：把 `TASK-080A~TASK-080F` 已通过审计的系统管理链路纳入本地 git 基线，形成可审计的本地封版 commit。

> 本任务只允许本地 commit，不允许 push / PR / tag / 生产发布 / ERPNext 生产联调声明 / GitHub required check 闭环声明。

## 2. 任务目标

完成一次严格白名单本地提交：

1. 复核当前分支、HEAD、脏工作树。
2. 复跑系统管理核心测试、Python 编译、前端 typecheck 与边界扫描。
3. 生成 `TASK-080G_系统管理本地封版提交证据.md`。
4. 只按白名单显式 `git add`。
5. 创建本地 commit。
6. 提交后由 A/C 按流程继续控制面对账与审计。
7. 回交 commit hash、parent hash、staged 清单、验证结果和证据路径给 C Auditor。

## 3. 允许新增或修改的证据文件

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 允许纳入本地 commit 的白名单

只能暂存以下文件。未列入的文件一律不得暂存。

### 4.1 后端代码

- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/routers/system_management.py`
- `07_后端/lingyi_service/app/schemas/system_management.py`
- `07_后端/lingyi_service/app/services/system_config_catalog_service.py`
- `07_后端/lingyi_service/app/services/system_dictionary_catalog_service.py`
- `07_后端/lingyi_service/app/services/system_health_summary_service.py`

### 4.2 后端测试

- `07_后端/lingyi_service/tests/test_permissions_registry.py`
- `07_后端/lingyi_service/tests/test_system_config_catalog_readonly.py`
- `07_后端/lingyi_service/tests/test_system_dictionary_catalog_readonly.py`
- `07_后端/lingyi_service/tests/test_system_health_summary_readonly.py`

### 4.3 前端代码

- `06_前端/lingyi-pc/src/api/system_management.ts`
- `06_前端/lingyi-pc/src/views/system/SystemManagement.vue`
- `06_前端/lingyi-pc/src/router/index.ts`

### 4.4 架构与任务证据文档

- `03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- `03_需求与设计/02_开发计划/TASK-080A_系统管理设计冻结_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080B_系统配置只读目录基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080C_数据字典只读目录基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080D_系统健康检查只读诊断基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md`
- `03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md`
- `03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版白名单提交_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版提交证据.md`
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
10. 禁止暂存 `TASK-021* / TASK-022* / TASK-023* / TASK-024*` 等非系统管理任务单。
11. 禁止暂存 `07_后端/lingyi_service/tests/test_permission_audit_baseline.py`，该文件属于历史继承背景，不属于本次封版白名单。
12. 禁止暂存 `2026-04-21_TASK-080F_A_B_C_可执行任务卡.md`、Sprint3 临时调度卡、截图、缓存、`__pycache__`、`.pyc`。
13. 禁止修改业务代码后再封版；如发现需要修复，立即 `BLOCKED`。
14. 禁止 push / PR / tag / 生产发布。

## 6. 必须执行验证

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
git tag --points-at HEAD
```

要求：当前分支应为 `codex/sprint4-seal`；当前 HEAD 应为 `1d7d2ff`；提交前不得已有本任务 tag。

### 6.2 系统管理后端测试

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_system_config_catalog_readonly.py \
  tests/test_system_dictionary_catalog_readonly.py \
  tests/test_system_health_summary_readonly.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

期望：`40 passed, 1 warning` 或等价全通过结果。

### 6.3 Python 编译

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile \
  app/core/permissions.py \
  app/main.py \
  app/routers/system_management.py \
  app/schemas/system_management.py \
  app/services/system_config_catalog_service.py \
  app/services/system_dictionary_catalog_service.py \
  app/services/system_health_summary_service.py
```

### 6.4 前端 typecheck

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.5 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "system:read|system:config_read|system:dictionary_read|system:diagnostic|SYSTEM_READ|SYSTEM_CONFIG_READ|SYSTEM_DICTIONARY_READ|SYSTEM_DIAGNOSTIC|/api/system/configs/catalog|/api/system/dictionaries/catalog|/api/system/health/summary|SystemConfigCatalog|SystemDictionaryCatalog|SystemHealthSummary" \
  app/core/permissions.py app/main.py app/routers/system_management.py app/schemas/system_management.py \
  tests/test_permissions_registry.py tests/test_system_config_catalog_readonly.py tests/test_system_dictionary_catalog_readonly.py tests/test_system_health_summary_readonly.py
```

要求：四类权限动作和三类 GET 路由映射均有证据。

### 6.6 后端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/system_management.py || true
rg -n "session\.(add|delete|commit|rollback)|\.query\(|session\.execute\(" \
  app/routers/system_management.py \
  app/services/system_config_catalog_service.py \
  app/services/system_dictionary_catalog_service.py \
  app/services/system_health_summary_service.py || true
rg -n "requests\.|httpx\.|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" \
  app/routers/system_management.py \
  app/services/system_config_catalog_service.py \
  app/services/system_dictionary_catalog_service.py \
  app/services/system_health_summary_service.py \
  app/schemas/system_management.py || true
rg -n "outbox|worker|run-once|internal|config_write|dictionary_write|platform_manage|cache_refresh|sync|import|export" \
  app/routers/system_management.py \
  app/services/system_config_catalog_service.py \
  app/services/system_dictionary_catalog_service.py \
  app/services/system_health_summary_service.py \
  app/schemas/system_management.py || true
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL" \
  app/routers/system_management.py \
  app/services/system_health_summary_service.py \
  app/schemas/system_management.py \
  tests/test_system_health_summary_readonly.py || true
```

要求：无系统管理写路由；无 direct DB query / execute / session 写入；无 ERPNext / `/api/resource` / 高危写语义；无 outbox/worker/internal 与冻结动作落点；敏感信息命中只能是测试负向断言。

### 6.7 前端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|config_write|dictionary_write|platform_manage|cache_refresh|sync|import|export" \
  src/api/system_management.ts src/views/system/SystemManagement.vue src/router/index.ts || true
rg -n "/system/management|system:read|system:config_read|system:dictionary_read|system:diagnostic" \
  src/api/system_management.ts src/views/system/SystemManagement.vue src/router/index.ts || true
```

要求：无裸 `fetch/axios`、无新系统管理写能力入口、路由仍仅复用既有 `/system/management`。

### 6.8 禁改目录检查

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
git diff --check
```

要求：禁改目录 diff 为空；`git diff --check` 通过。

## 7. 生成封版提交证据

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版提交证据.md`

必须包含：

1. 当前分支、提交前 HEAD。
2. 前置审计：第450份 `TASK-080F PASS`。
3. 系统管理审计闭环摘要：第439~450份关键结论。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射扫描结果。
8. 后端边界扫描结果。
9. 前端边界扫描结果。
10. 禁改目录与 diff check 结果。
11. 预提交 staged 白名单清单。
12. 残余风险。
13. 提交后记录策略：不得在 commit 后为了回填 hash 修改已提交证据；commit hash 与 parent 只在回交正文中提供。

## 8. 显式暂存要求

必须逐个或按明确路径列表暂存白名单文件。示例：

```bash
git add -- \
  '07_后端/lingyi_service/app/core/permissions.py' \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/routers/system_management.py' \
  '07_后端/lingyi_service/app/schemas/system_management.py' \
  '07_后端/lingyi_service/app/services/system_config_catalog_service.py' \
  '07_后端/lingyi_service/app/services/system_dictionary_catalog_service.py' \
  '07_后端/lingyi_service/app/services/system_health_summary_service.py' \
  '07_后端/lingyi_service/tests/test_permissions_registry.py' \
  '07_后端/lingyi_service/tests/test_system_config_catalog_readonly.py' \
  '07_后端/lingyi_service/tests/test_system_dictionary_catalog_readonly.py' \
  '07_后端/lingyi_service/tests/test_system_health_summary_readonly.py' \
  '06_前端/lingyi-pc/src/api/system_management.ts' \
  '06_前端/lingyi-pc/src/views/system/SystemManagement.vue' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '03_需求与设计/01_架构设计/TASK-080_系统管理设计.md' \
  '03_需求与设计/02_开发计划/TASK-080A_系统管理设计冻结_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080B_系统配置只读目录基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080C_数据字典只读目录基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080D_系统健康检查只读诊断基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md' \
  '03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md' \
  '03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版白名单提交_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版提交证据.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md' \
  '00_交接与日志/HANDOVER_STATUS.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

暂存后必须执行：

```bash
git diff --cached --name-only | sort
git diff --cached --name-only | rg '(^\.github/|^\.ci-reports/|^01_|^02_|^03_环境|^04_|^05_|TASK-021|TASK-022|TASK-023|TASK-024|test_permission_audit_baseline\.py|2026-04-21_TASK-080F_A_B_C_可执行任务卡\.md)' && exit 1 || true
```

要求：暂存清单只能包含第 4 节白名单文件；禁止模式扫描必须无命中。

## 9. 本地 commit

暂存清单核验通过后执行：

```bash
git commit -m "chore: seal system management baseline"
```

提交后执行：

```bash
git rev-parse --short HEAD
git rev-parse --short HEAD^1
git show --name-only --pretty=format:'%h %s' HEAD
git diff --cached --name-only
git tag --points-at HEAD
```

要求：

- 新 HEAD 为本次本地封版 commit。
- parent 必须为 `1d7d2ff`。
- `git diff --cached --name-only` 为空。
- `git tag --points-at HEAD` 为空。
- 不得对证据文件做 post-commit 回填修改；如出现 post-commit 元数据脏改动，按阻塞回报。

## 10. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080G
ROLE: B Engineer

CHANGED_FILES:
- 列出本次 commit 内实际文件清单
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080G_系统管理本地封版提交证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- commit hash
- parent hash
- staged 白名单清单
- pytest / py_compile / npm typecheck 结果
- 权限动作与路由映射扫描结果
- 后端边界扫描结果
- 前端边界扫描结果
- 禁改目录与 diff check 结果
- 未出现 post-commit 元数据脏改动证据

VERIFICATION:
- 逐条列出命令和结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 11. 完成定义

1. `TASK-080G_系统管理本地封版提交证据.md` 已生成。
2. `TASK-080A~080F` 审计编号与能力闭环完整。
3. 后端核心测试、Python 编译、前端 typecheck 均通过。
4. 权限与路由映射扫描可证明系统管理只读链路闭环。
5. 后端边界扫描未发现新增写路由、direct DB query/execute/session 写入、ERPNext 访问、outbox / worker / run-once / internal / 写入能力。
6. 前端未新增新路由，仍复用既有 `/system/management`。
7. 禁改目录 diff 为空。
8. 已完成显式白名单暂存与本地 commit。
9. commit message 为 `chore: seal system management baseline`。
10. 未执行 push / PR / tag / 生产发布。
