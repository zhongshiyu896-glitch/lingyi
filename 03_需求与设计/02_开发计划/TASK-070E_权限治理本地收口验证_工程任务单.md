# TASK-070E 权限治理本地收口验证 工程任务单

## 1. 基本信息

- 任务编号：TASK-070E
- 任务名称：权限治理本地收口验证
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 模块：权限治理 / system permission governance
- 前置依据：`TASK-020_权限治理设计.md`、`TASK-020A_权限治理设计冻结_工程任务单.md`、`TASK-070A` 审计意见书第423份通过、`TASK-070B` 第425份通过、`TASK-070C` 第427份有问题、`TASK-070C_FIX1` 第429份通过、`TASK-070D` 第431份通过
- 当前定位：对 `TASK-070A~070D` 权限治理本地实现链路做收口验证与证据汇总。不新增功能、不修代码、不提交、不 push、不 PR、不 tag、不生产发布。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实验证报告、测试结果、扫描结果和证据路径前，不得回交 C。

## 2. 目标

输出一份可交给 C Auditor 审计的权限治理本地收口验证报告，证明以下链路均已闭环：

1. `TASK-070A`：权限动作目录只读接口、静态角色矩阵、`permission:read` 独立权限与前端只读页面。
2. `TASK-070B`：安全审计 / 操作审计只读查询、`permission:audit_read` 独立权限、敏感数据脱敏。
3. `TASK-070C` + `TASK-070C_FIX1`：安全审计 / 操作审计脱敏 CSV 导出、`permission:export` 独立权限、CSV 公式注入防护、前端统一下载与错误提示、导出审计写入边界收敛到 `AuditService` 公共 helper。
4. `TASK-070D`：权限治理诊断只读健康检查、`permission:diagnostic` 独立权限、普通前端不暴露诊断入口。
5. 权限配置写入、角色创建/更新/禁用、用户资源权限更新、审批、回滚、导入、配置发布继续冻结。
6. 未新增 ERPNext 访问、业务 DB 写入、outbox、worker、run-once、internal、生产发布链路。

## 3. 允许修改范围

仅允许新增或更新以下证据文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如需要临时保存命令输出，只能写入 `.ci-reports/` 或系统临时目录；最终报告必须摘录关键结论，不得把大段原始日志灌入文档。

## 4. 禁止修改范围

1. 禁止修改任何后端业务代码：`07_后端/lingyi_service/app/**`。
2. 禁止修改任何后端测试代码：`07_后端/lingyi_service/tests/**`。
3. 禁止修改任何前端代码：`06_前端/lingyi-pc/src/**`。
4. 禁止修改 `03_需求与设计/01_架构设计/**`、`03_需求与设计/05_审计记录/**`。
5. 禁止修改 `LOOP_STATE.md`、`HANDOVER_STATUS.md`。
6. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
7. 禁止新增或启用权限配置写入、角色创建/更新/禁用、用户资源权限更新、审批、回滚、导入、配置发布。
8. 禁止新增 write route、migration、model、outbox、worker、run-once、internal、ERPNext 写调用。
9. 禁止 commit / push / PR / tag / 生产发布。
10. 如验证失败，不得在本任务内修复代码或测试，必须回报失败证据。

## 5. 必须核验的任务闭环

验证报告必须逐项列出：

| 任务 | 审计意见书 | 必须核验证据 |
|---|---:|---|
| TASK-070A | 第423份 | `permission:read`、动作目录、角色矩阵、前端只读页、无写入口 |
| TASK-070B | 第425份 | `permission:audit_read`、安全/操作审计只读查询、脱敏、无写入 |
| TASK-070C | 第427份 | 原导出能力已实现但存在写入边界 P1 |
| TASK-070C_FIX1 | 第429份 | P1 已闭环，导出审计写入收敛到 `AuditService` 公共 helper |
| TASK-070D | 第431份 | `permission:diagnostic`、只读诊断接口、前端无诊断入口 |

要求：

1. 对第427份 `有问题` 项必须说明已由第429份 `TASK-070C_FIX1` 闭环。
2. 对最终通过项必须写清核心验证结果。
3. 不得遗漏第431份。

## 6. 必跑验证命令

### 6.1 后端核心测试

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

### 6.2 Python 编译核验

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

### 6.3 前端类型检查

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 6.4 权限动作与路由映射扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "permission:read|permission:audit_read|permission:export|permission:diagnostic|PERMISSION_READ|PERMISSION_GOVERNANCE_AUDIT_READ|PERMISSION_GOVERNANCE_EXPORT|PERMISSION_GOVERNANCE_DIAGNOSTIC|/api/permissions/actions/catalog|/api/permissions/roles/matrix|/api/permissions/audit/security|/api/permissions/audit/operations|/api/permissions/audit/security/export|/api/permissions/audit/operations/export|/api/permissions/diagnostic" \
  app/core/permissions.py app/main.py app/routers/permission_governance.py app/schemas/permission_governance.py \
  tests/test_permission_governance_readonly.py tests/test_permission_governance_audit_readonly.py tests/test_permission_governance_audit_export.py tests/test_permission_governance_diagnostic.py tests/test_permissions_registry.py
```

### 6.5 后端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py || true
rg -n "session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(" \
  app/routers/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py || true
rg -n "record_success_and_commit|record_failure_and_commit|AuditWriteFailed|session\.(commit|rollback)" app/services/audit_service.py || true
rg -n "requests\.|httpx\.|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" \
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
```

要求：

1. `permission_governance.py`、`permission_governance_service.py`、`permission_governance_export_service.py`、`permission_governance_diagnostic_service.py` 不得出现直接 `session.add/delete/commit/rollback`。
2. `audit_service.py` 可以命中第429份已审计通过的公共 helper：`record_success_and_commit` / `record_failure_and_commit` / `session.commit` / `session.rollback`，报告中必须说明这是导出审计唯一允许写入边界的公共入口，不是 permission governance 模块内直接提交。
3. `internal/import/export/diagnostic` 若由 Python `import` 语法、TypeScript `export` 语法、动作分类描述或已审计 `permission:export/permission:diagnostic` 命中，必须在报告中解释。

### 6.6 前端边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|/api/permissions/diagnostic|permission:diagnostic|创建|编辑|删除|审批|回滚|导入|配置|发布|submit|sync|cache_refresh|recalculate|generate" \
  src/api/permission_governance.ts \
  src/views/system/PermissionGovernance.vue \
  src/stores/permission.ts \
  src/router/index.ts || true
```

要求：

1. 不得出现普通前端诊断入口、诊断按钮或 `/api/permissions/diagnostic` API 封装。
2. 不得出现创建、编辑、删除、审批、回滚、导入、配置发布等前端能力入口。
3. 允许命中已审计 `permission:export` 下载入口，但必须说明其对应第429份闭环。
4. `import/export` 如仅为 TypeScript 语法，必须说明不是业务导入/导出入口。

### 6.7 敏感信息扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL|headers|payload|before_data|after_data" \
  app/routers/permission_governance.py \
  app/schemas/permission_governance.py \
  app/services/permission_governance_service.py \
  app/services/permission_governance_export_service.py \
  app/services/permission_governance_diagnostic_service.py || true
```

要求：

- 若命中测试/过滤常量/脱敏键名，必须说明为防泄漏逻辑，不是响应泄露。
- 不得出现原始敏感值输出。

### 6.8 禁改目录与源码 diff

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
git diff --check -- \
  03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

要求：

1. 禁改目录 diff 必须为空。
2. 本任务不得新增业务代码、测试代码或前端源码 diff。
3. 如 `07_后端/lingyi_service/app`、`07_后端/lingyi_service/tests`、`06_前端/lingyi-pc/src` 存在前序继承脏差异，报告必须按文件列明并说明“不属于 TASK-070E 新增改动”。

## 7. 报告必须包含章节

在 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md` 中至少包含：

1. 结论：建议进入 C 收口审计 / 暂不建议。
2. 任务链路：`TASK-070A~070D` 与审计意见书编号。
3. 第427份问题与第429份 FIX1 闭环说明。
4. 测试结果：pytest、py_compile、npm typecheck。
5. 权限闭环：`permission:read`、`permission:audit_read`、`permission:export`、`permission:diagnostic`。
6. 路由闭环：动作目录、角色矩阵、审计查询、审计导出、诊断健康检查。
7. 前端闭环：权限治理页面只读、审计查询区域、导出下载、无诊断入口、无写入口。
8. 导出审计写入边界：permission governance 模块无直接 commit/rollback，公共审计 helper 承担唯一允许写入。
9. 禁止能力扫描：写路由、ERPNext、业务 DB 写入、outbox/worker/internal、配置写入、审批、回滚、导入、发布。
10. 敏感信息扫描：Authorization/Cookie/token/secret/password/DSN/DATABASE_URL/headers/payload/before_data/after_data。
11. 禁改目录检查。
12. 工作树残余风险：如存在继承脏差异或未跟踪目录，必须说明不属于本任务新增业务改动。
13. 明确声明：本地收口验证不等同 commit / push / PR / tag / 生产发布。

## 8. 回交格式

B 完成后回交 C，必须使用以下格式：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070E
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- TASK-070A~070D 审计闭环编号
- 第427份 -> 第429份修复闭环说明
- pytest / py_compile / npm typecheck 结果
- 权限动作与路由映射扫描结果
- 后端边界扫描结果
- 前端边界扫描结果
- 敏感信息扫描结果
- 禁改目录 diff 结果
- 未修改业务代码、测试代码、前端源码证据

VERIFICATION:
- 逐条列出命令和结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 9. 完成定义

1. 收口验证报告已生成。
2. `TASK-070A~070D` 审计编号与能力闭环完整。
3. 第427份问题已明确由第429份闭环。
4. 后端核心测试、Python 编译、前端 typecheck 均通过。
5. 权限与路由映射扫描证明四类动作闭环。
6. 负向扫描未发现新增写路由、ERPNext 访问、业务 DB 写入、outbox/worker/run-once/internal、配置写入、审批、回滚、导入、发布。
7. 前端未暴露普通诊断入口，未暴露权限写入入口，未直连 ERPNext，未裸 `fetch/axios`。
8. 敏感信息扫描无泄露。
9. 禁改目录 diff 为空。
10. 本任务未修改业务代码、测试代码或前端源码。
