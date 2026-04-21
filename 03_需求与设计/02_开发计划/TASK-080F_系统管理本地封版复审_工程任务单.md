# TASK-080F 系统管理本地封版复审 工程任务单

## 1. 基本信息

- 任务编号：TASK-080F
- 任务名称：系统管理本地封版复审
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：系统管理 / system management
- 优先级：P1
- 派发时间：2026-04-21 09:05 CST+8
- 前置依赖：TASK-080E 审计通过（审计意见书第448份）
- 当前定位：对系统管理 `TASK-080A~080E` 任务链做本地封版复审证据汇总和核验。本任务只输出证据，不新增功能、不修改业务代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实复审证据、测试结果、扫描结果和证据路径前，不得回交 C。

## 2. 任务目标

输出一份可交给 C Auditor 审计的系统管理本地封版复审证据，证明以下链路均已闭环：

1. `TASK-080A`：系统管理设计冻结，作为唯一合同。
2. `TASK-080B`：系统配置只读目录基线，`GET /api/system/configs/catalog`，`system:read + system:config_read`。
3. `TASK-080C`：数据字典只读目录基线，`GET /api/system/dictionaries/catalog`，`system:read + system:dictionary_read`。
4. `TASK-080D`：系统健康检查只读诊断基线，`GET /api/system/health/summary`，`system:read + system:diagnostic`。
5. `TASK-080E`：系统管理本地收口验证。
6. `system:config_write / system:dictionary_write / system:platform_manage / system:cache_refresh / system:sync / system:import / system:export` 继续冻结。

本任务结论只能写：

```text
建议进入 C 本地封版审计
暂不建议进入 C 本地封版审计
```

不得自行宣布：

```text
系统管理已正式封版
生产发布通过
ERPNext 生产联调通过
GitHub required check 闭环
远端 push / PR / tag 完成
```

## 3. 允许范围

只允许新增或追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需临时命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终证据文档只摘录关键结论，不得灌入大段原始日志。

## 4. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/**` 后端业务代码、schema、router、service、main.py、adapter、model、migration。
2. 禁止修改 `07_后端/lingyi_service/tests/**` 后端测试代码。
3. 禁止修改 `06_前端/lingyi-pc/src/**` 前端源码。
4. 禁止修改 `.github/**`、`.ci-reports/**`、`01_需求与资料/**`、`02_源码/**`、`03_环境与部署/**`、`04_测试与验收/**`、`05_交付物/**`。
5. 禁止修改审计日志、架构日志、控制面文件。
6. 禁止新增或修改 API 行为。
7. 禁止新增 `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export`。
8. 禁止新增写路由、direct DB query/execute/session 写入、ERPNext 访问、outbox、worker、run-once、internal。
9. 禁止 commit、push、PR、tag、生产发布。
10. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核对的审计编号

证据文档必须逐项列出并核对以下审计编号：

| 任务 | 审计结论 |
| --- | --- |
| TASK-080A | 审计意见书第439份 阻塞；第440份 通过 |
| TASK-080B | 审计意见书第441份 阻塞；第442份 通过 |
| TASK-080C | 审计意见书第443份 阻塞；第444份 通过 |
| TASK-080D | 审计意见书第445份 阻塞；第446份 通过 |
| TASK-080E | 审计意见书第447份 阻塞；第448份 通过 |

要求：

1. 对 `阻塞` 项必须说明已由后续控制面对账闭环。
2. 对最终通过项必须写清核心验证结果。
3. 不得遗漏第448份。

## 6. 必须执行验证命令

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
git tag --points-at HEAD
```

要求：当前分支应为 `codex/sprint4-seal`；当前 HEAD 应为 `1d7d2ff` 或其后继本地提交；本任务不得已有 tag。

### 6.2 系统管理核心后端测试

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_system_config_catalog_readonly.py \
  tests/test_system_dictionary_catalog_readonly.py \
  tests/test_system_health_summary_readonly.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

期望：全通过。若数量不是 `40 passed, 1 warning`，必须说明差异原因。

### 6.3 Python 编译核验

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

要求：四类权限动作和三类路由映射均有证据。

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

要求：

1. 不得出现系统管理写路由。
2. 不得出现 direct DB query / execute / session 写入。
3. 不得出现 ERPNext 访问、`/api/resource` 或库存财务高危写语义。
4. 不得出现 outbox / worker / run-once / internal / 写权限动作 / 同步导入导出平台管理能力。
5. 敏感信息扫描如命中，只能是测试负向断言，不得是响应泄露。

### 6.7 前端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|config_write|dictionary_write|platform_manage|cache_refresh|sync|import|export" \
  src/api/system_management.ts src/views/system/SystemManagement.vue src/router/index.ts || true
rg -n "/system/management|system:read|system:config_read|system:dictionary_read|system:diagnostic" \
  src/api/system_management.ts src/views/system/SystemManagement.vue src/router/index.ts || true
```

要求：

1. 不得出现裸 `fetch/axios` 或 `/api/resource`。
2. 不得出现新的系统管理写能力入口。
3. 路由仍仅允许既有 `/system/management`；不得新增其他系统管理页面路由。
4. 必须能证明配置目录、字典目录、诊断摘要共用同一入口，且无权限时不发对应请求。

### 6.8 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  '03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'
git diff --check
```

要求：

1. 禁改目录 diff 必须为空。
2. 若业务代码区存在继承脏差异，必须按文件列明并说明“不属于 TASK-080F 新增改动”。
3. diff check 必须通过。

## 7. 证据文档要求

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md`

必须包含：

1. 基本信息：任务编号、执行时间、当前分支、当前 HEAD、结论。
2. 任务链路与审计闭环表。
3. 已完成能力清单：设计冻结、配置目录、字典目录、诊断摘要、收口验证。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射结果。
8. 后端边界扫描结果。
9. 前端边界扫描结果。
10. 敏感信息扫描结果。
11. 禁改目录与继承脏基线结果。
12. 剩余风险。
13. 是否建议进入 C 本地封版审计。

## 8. 剩余风险必须至少披露

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须另开白名单提交任务。
5. `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 仍冻结，未在本链路放行。

## 9. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080F
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080F_系统管理本地封版复审证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 审计闭环表：证据章节
- 核心测试结果：证据章节
- 权限与路由映射：证据章节
- 后端只读边界扫描：证据章节
- 前端边界扫描：证据章节
- 敏感信息扫描：证据章节
- 禁改目录与继承脏基线：证据章节
- 剩余风险：证据章节

VERIFICATION:
- 逐条列出命令和结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

1. `TASK-080F_系统管理本地封版复审证据.md` 已生成。
2. `TASK-080A~080E` 审计编号与能力闭环完整。
3. 后端核心测试、Python 编译、前端 typecheck 均通过。
4. 权限与路由映射扫描可证明系统管理只读链路闭环。
5. 后端边界扫描未发现新增写路由、direct DB query/execute/session 写入、ERPNext 访问、outbox / worker / run-once / internal / 写入能力。
6. 前端未新增新路由，仍复用既有 `/system/management`。
7. 敏感信息扫描无真实泄露。
8. 禁改目录 diff 为空。
9. 本任务未修改业务代码、测试代码或前端源码。
10. 证据文档明确声明：本地封版复审不等同 commit / push / PR / tag / 生产发布。
