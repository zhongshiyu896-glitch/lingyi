# TASK-070F 权限治理本地封版复审 工程任务单

## 1. 基本信息

- 任务编号：TASK-070F
- 任务名称：权限治理本地封版复审
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：权限治理 / permission governance
- 优先级：P1
- 派发时间：2026-04-21 06:12 CST+8
- 前置依赖：TASK-070E_FIX1 审计通过（审计意见书第435份）
- 当前定位：对权限治理 `TASK-070A~070E_FIX1` 任务链做本地封版复审证据汇总和核验。本任务只输出证据，不新增功能、不修改业务代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实复审证据、测试结果、扫描结果和证据路径前，不得回交 C。

## 2. 任务目标

输出一份可交给 C Auditor 审计的权限治理本地封版复审证据，证明以下链路均已闭环：

1. `TASK-070A`：权限动作目录只读接口、静态角色矩阵、`permission:read` 独立权限与前端只读页面。
2. `TASK-070B`：安全审计 / 操作审计只读查询、`permission:audit_read` 独立权限、敏感数据脱敏。
3. `TASK-070C + TASK-070C_FIX1`：安全审计 / 操作审计脱敏 CSV 导出、`permission:export` 独立权限、CSV 公式注入防护、前端统一下载与错误提示、导出操作审计写入边界收敛到 `AuditService` 公共 helper。
4. `TASK-070D`：权限治理诊断只读健康检查、`permission:diagnostic` 独立权限、普通前端不暴露诊断入口。
5. `TASK-070E + TASK-070E_FIX1`：权限治理本地收口验证与收口报告时间线元数据修复。
6. `权限配置写入 / 角色创建更新禁用 / 用户资源权限更新 / 审批 / 回滚 / 导入 / 配置发布` 继续冻结。

本任务结论只能写：

```text
建议进入 C 本地封版审计
暂不建议进入 C 本地封版审计
```

不得自行宣布：

```text
权限治理已正式封版
生产发布通过
ERPNext 生产联调通过
GitHub required check 闭环
远端 push / PR / tag 完成
```

## 3. 允许范围

只允许新增或追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需临时命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终证据文档只摘录关键结论，不得灌入大段原始日志。

## 4. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/**` 后端业务代码、schema、router、service、main.py、adapter、model、migration。
2. 禁止修改 `07_后端/lingyi_service/tests/**` 后端测试代码。
3. 禁止修改 `06_前端/lingyi-pc/src/**` 前端源码。
4. 禁止修改 `.github/**`、`.ci-reports/**`、`01_需求与资料/**`、`02_源码/**`、`03_环境与部署/**`、`04_测试与验收/**`、`05_交付物/**`。
5. 禁止修改审计日志、架构日志、控制面文件。
6. 禁止新增或修改 API 行为。
7. 禁止新增权限配置写入、角色创建/更新/禁用、用户资源权限更新、审批、回滚、导入、配置发布能力。
8. 禁止新增 ERPNext 访问、业务 DB 写入、outbox、worker、run-once、internal。
9. 禁止 commit、push、PR、tag、生产发布。
10. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核对的审计编号

证据文档必须逐项列出并核对以下审计编号：

| 任务 | 审计结论 |
| --- | --- |
| TASK-070A | 审计意见书第422份 阻塞；第423份 通过 |
| TASK-070B | 审计意见书第424份 阻塞；第425份 通过 |
| TASK-070C | 审计意见书第426份 阻塞；第427份 需修复 |
| TASK-070C_FIX1 | 审计意见书第428份 阻塞；第429份 通过 |
| TASK-070D | 审计意见书第430份 阻塞；第431份 通过 |
| TASK-070E | 审计意见书第432份 阻塞；第433份 需修复 |
| TASK-070E_FIX1 | 审计意见书第434份 阻塞；第435份 通过 |

要求：

1. 对 `阻塞/需修复` 项必须说明已由后续控制面对账或 fix pass 闭环。
2. 对最终通过项必须写清核心验证结果。
3. 不得遗漏第435份。

## 6. 必须执行验证命令

### 6.1 当前状态核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
git rev-parse --short HEAD
git tag --points-at HEAD
```

要求：当前分支应为 `codex/sprint4-seal`；当前 HEAD 应为 `f08015c` 或其后继本地提交；本任务不得已有 tag。

### 6.2 权限治理核心后端测试

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_permission_governance_readonly.py \
  tests/test_permission_governance_audit_readonly.py \
  tests/test_permission_governance_audit_export.py \
  tests/test_permission_governance_diagnostic.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

期望：全通过。若数量不是 `50 passed, 1 warning`，必须说明差异原因。

### 6.3 Python 编译核验

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile \
  app/core/permissions.py \
  app/main.py \
  app/routers/permission_governance.py \
  app/schemas/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py \
  app/services/audit_service.py
```

### 6.4 前端 typecheck

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.5 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "permission:read|permission:audit_read|permission:export|permission:diagnostic|PERMISSION_GOVERNANCE_READ|PERMISSION_GOVERNANCE_AUDIT_READ|PERMISSION_GOVERNANCE_EXPORT|PERMISSION_GOVERNANCE_DIAGNOSTIC|/api/permissions/actions/catalog|/api/permissions/roles/matrix|/api/permissions/audit/security|/api/permissions/audit/operations|/api/permissions/audit/security/export|/api/permissions/audit/operations/export|/api/permissions/diagnostic" \
  app/core/permissions.py app/main.py app/routers/permission_governance.py \
  tests/test_permissions_registry.py tests/test_permission_governance_readonly.py tests/test_permission_governance_audit_readonly.py tests/test_permission_governance_audit_export.py tests/test_permission_governance_diagnostic.py
```

要求：四类权限动作和七类权限治理路由/映射均有证据。

### 6.6 后端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py || true
rg -n "session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(|AuditService\.record_(success|failure)\(" \
  app/routers/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py || true
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|Stock Entry|Stock Reconciliation|Stock Ledger Entry|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" \
  app/routers/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py \
  app/schemas/permission_governance.py || true
rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import" \
  app/routers/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py \
  app/schemas/permission_governance.py || true
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL|before_data|after_data|raw headers|raw payload" \
  app/routers/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py \
  app/schemas/permission_governance.py || true
```

要求：

1. 不得出现权限治理写路由。
2. `permission_governance.py`、`permission_governance_service.py`、`permission_governance_export_service.py`、`permission_governance_diagnostic_service.py` 不得直接 `session.add/delete/commit/rollback`。
3. 导出审计写入必须通过 `AuditService` 公共 helper，`audit_service.py` 中的提交 helper 为第429份已审计通过边界。
4. 不得出现 ERPNext 同步访问或库存财务高危写语义。
5. 不得出现 outbox/worker/internal、审批、回滚、导入、配置发布能力。
6. 敏感信息扫描不得命中响应泄露项；如命中字段名或测试脱敏键名，必须说明非敏感值泄露。

### 6.7 前端边界与下载闭环扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|permission:diagnostic|/api/permissions/diagnostic|approval|rollback|import|cache_refresh|recalculate|generate|sync|submit" \
  src/api/permission_governance.ts src/views/system/PermissionGovernance.vue src/router/index.ts || true
rg -n "requestFile|exportSecurityAuditCsv|exportOperationAuditCsv|URL\.createObjectURL|ElMessage\.error|ElMessage\.warning|await permissionGovernanceApi\.export" \
  src/api/request.ts src/api/permission_governance.ts src/views/system/PermissionGovernance.vue || true
```

要求：

1. 不得出现裸 `fetch/axios` 或 `/api/resource`。
2. 不得出现普通前端诊断入口。
3. 不得出现审批、回滚、导入、配置发布、`sync/submit/cache_refresh/recalculate/generate` 业务动作。
4. 必须能证明 CSV 导出仍走统一下载 client、blob 下载和错误提示闭环。

### 6.8 禁改目录与继承脏基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
git diff --check
```

要求：

1. 禁改目录 diff 必须为空。
2. 若业务代码区存在继承脏差异，必须按文件列明并说明“不属于 TASK-070F 新增改动”。
3. diff check 必须通过。

## 7. 证据文档要求

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md`

必须包含：

1. 基本信息：任务编号、执行时间、当前分支、当前 HEAD、结论。
2. 任务链路与审计闭环表。
3. 已完成能力清单：动作目录、角色矩阵、审计查询、审计导出、诊断、收口验证、FIX 闭环。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射结果。
8. 后端边界扫描结果。
9. 前端边界扫描结果。
10. CSV 导出统一下载、错误提示与审计写入边界证据。
11. 敏感信息扫描结果。
12. 禁改目录与继承脏基线结果。
13. 剩余风险。
14. 是否建议进入 C 本地封版审计。

## 8. 剩余风险必须至少披露

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录和继承脏基线；后续如需提交，必须另开白名单提交任务。
5. 权限配置写入、角色创建/更新/禁用、用户资源权限更新、审批、回滚、导入、配置发布仍冻结，未在本链路放行。

## 9. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070F
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 已核对 TASK-070A~070E_FIX1 审计闭环编号 422~435
- 已生成本地封版复审证据
- 已记录当前分支、HEAD、测试结果、扫描结果、禁改目录结果
- 已披露继承脏基线与剩余风险

VERIFICATION:
- pytest：...
- py_compile：...
- npm run typecheck：...
- 权限/路由映射扫描：...
- 后端边界扫描：...
- 前端边界扫描：...
- 禁改目录 diff：...
- git diff --check：...

BLOCKERS:
- 无 / 或列明失败原因

NEXT_ROLE:
- A Technical Architect
```

## 10. 完成定义

1. `TASK-070F_权限治理本地封版复审证据.md` 已生成。
2. `TASK-070A~070E_FIX1` 审计链路完整、编号准确、阻塞/需修复项均有闭环说明。
3. 权限治理核心测试、编译、前端 typecheck 与边界扫描完成并记录。
4. 禁改目录 diff 为空。
5. 未修改后端业务代码、测试代码、前端源码。
6. 未修改控制面、审计日志、架构日志。
7. 未执行 commit / push / PR / tag / 生产发布。
