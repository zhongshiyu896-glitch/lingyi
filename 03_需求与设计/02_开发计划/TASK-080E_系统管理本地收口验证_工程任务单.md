# TASK-080E 系统管理本地收口验证 工程任务单

## 1. 基本信息

- 任务编号：TASK-080E
- 任务名称：系统管理本地收口验证
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：系统管理 / system management
- 前置依据：`TASK-080_系统管理设计.md`、`TASK-080A` 审计意见书第440份通过、`TASK-080B` 第442份通过、`TASK-080C` 第444份通过、`TASK-080D` 第446份通过
- 当前定位：对 `TASK-080A~080D` 系统管理本地实现链路做收口验证与证据汇总。不新增功能、不修代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实验证报告、测试结果、扫描结果和证据路径前，不得回交 C。

## 2. 目标

输出一份可交给 C Auditor 审计的系统管理本地收口验证报告，证明以下链路均已闭环：

1. `TASK-080A`：系统管理设计冻结已落盘，并为后续只读实现提供唯一合同。
2. `TASK-080B`：`GET /api/system/configs/catalog`、`system:read + system:config_read`、最小 `/system/management` 只读入口已闭环。
3. `TASK-080C`：`GET /api/system/dictionaries/catalog`、`system:read + system:dictionary_read`、复用 `/system/management` 的字典目录区域已闭环。
4. `TASK-080D`：`GET /api/system/health/summary`、`system:read + system:diagnostic`、本地 4 项安全检查、复用 `/system/management` 的诊断摘要区域已闭环。
5. `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 继续冻结。
6. 未新增写路由、direct DB query/execute/session 写入、ERPNext `/api/resource`、outbox、worker、run-once、internal、平台管理或生产发布链路。

## 3. 允许修改范围

仅允许新增或更新以下证据文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需要临时保存命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终报告必须摘录关键结论，不得把大段原始日志灌入文档。

## 4. 禁止修改范围

1. 禁止修改任何后端业务代码：`07_后端/lingyi_service/app/**`。
2. 禁止修改任何后端测试代码：`07_后端/lingyi_service/tests/**`。
3. 禁止修改任何前端代码：`06_前端/lingyi-pc/src/**`。
4. 禁止修改 `03_需求与设计/01_架构设计/**`、`03_需求与设计/05_审计记录/**`。
5. 禁止修改 `LOOP_STATE.md`、`HANDOVER_STATUS.md`。
6. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
7. 禁止新增或启用 `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export`。
8. 禁止新增 write route、migration、model、outbox、worker、run-once、internal、ERPNext 写调用。
9. 禁止 commit / push / PR / tag / 生产发布。
10. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核验的任务闭环

验证报告必须逐项列出：

| 任务 | 审计意见书 | 必须核验证据 |
|---|---:|---|
| TASK-080A | 第440份 | 设计冻结文档落盘、冻结动作与接口草案、后续拆分建议 |
| TASK-080B | 第442份 | 配置目录路由、权限、最小前端入口、只读边界 |
| TASK-080C | 第444份 | 字典目录路由、权限、字段白名单、复用现有页面 |
| TASK-080D | 第446份 | 诊断摘要路由、权限、本地 4 项安全检查、前端无权限不请求 |

要求：

1. 报告必须明确 `TASK-080A~080D` 的审计编号与最终通过状态。
2. 报告必须明确 `TASK-080B~080D` 已实现能力与 `TASK-080A` 设计合同一致。
3. 报告必须明确冻结动作仍未放行。

## 6. 必跑验证命令

### 6.1 后端核心测试

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_system_config_catalog_readonly.py \
  tests/test_system_dictionary_catalog_readonly.py \
  tests/test_system_health_summary_readonly.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

期望：通过；若结果不是 `40 passed, 1 warning`，必须说明差异原因。

### 6.2 Python 编译核验

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

### 6.3 前端类型检查

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.4 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "system:read|system:config_read|system:dictionary_read|system:diagnostic|SYSTEM_READ|SYSTEM_CONFIG_READ|SYSTEM_DICTIONARY_READ|SYSTEM_DIAGNOSTIC|/api/system/configs/catalog|/api/system/dictionaries/catalog|/api/system/health/summary|SystemConfigCatalog|SystemDictionaryCatalog|SystemHealthSummary" \
  app/core/permissions.py app/main.py app/routers/system_management.py app/schemas/system_management.py \
  tests/test_permissions_registry.py tests/test_system_config_catalog_readonly.py tests/test_system_dictionary_catalog_readonly.py tests/test_system_health_summary_readonly.py
```

要求：四类权限动作和三类 GET 路由/映射均有证据。

### 6.5 后端只读边界扫描

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

### 6.6 前端边界扫描

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

### 6.7 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  '03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'
git diff --check
```

要求：

1. 禁改目录 diff 必须为空。
2. 若业务代码区存在继承脏差异，必须逐项列明并说明“不属于 TASK-080E 新增改动”。
3. diff check 必须通过。

## 7. 证据文档要求

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md`

必须包含：

1. 基本信息：任务编号、生成时间、执行角色、结论。
2. 任务链路与审计闭环表。
3. 设计冻结合同核验：`TASK-080A` 文档与后续实现一致性。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射结果。
8. 后端只读边界扫描结果。
9. 前端边界扫描结果。
10. 敏感信息扫描结果。
11. 禁改目录与继承脏基线结果。
12. 剩余风险。
13. 是否建议进入 C 收口审计。

## 8. 剩余风险必须至少披露

1. 本地收口验证不等同 commit / push / PR / tag / 生产发布。
2. 前端未做浏览器交互级人工验收。
3. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须继续白名单控制。
4. `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 仍冻结，未在本链路放行。

## 9. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080E
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080E_系统管理本地收口验证报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- TASK-080A~080D 审计闭环编号与能力链路
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

## 10. 完成定义

1. 收口验证报告已生成。
2. `TASK-080A~080D` 审计编号与能力闭环完整。
3. 后端核心测试、Python 编译、前端 typecheck 均通过。
4. 权限与路由映射扫描可证明四类系统管理动作闭环。
5. 负向扫描未发现新增写路由、direct DB query / execute / session 写入、ERPNext 访问、outbox / worker / run-once / internal / 写入能力。
6. 前端未新增新路由，仍复用既有 `/system/management`。
7. 敏感信息扫描无真实泄露。
8. 禁改目录 diff 为空。
9. 本任务未修改业务代码、测试代码或前端源码。
10. 报告明确声明：本地收口验证不等同 commit / push / PR / tag / 生产发布。
