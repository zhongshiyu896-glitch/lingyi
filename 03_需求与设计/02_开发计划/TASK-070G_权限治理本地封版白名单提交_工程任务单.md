# TASK-070G 权限治理本地封版白名单提交 工程任务单

## 1. 基本信息

- 任务编号：TASK-070G
- 任务名称：权限治理本地封版白名单提交
- 模块：权限治理 / 本地封版
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 06:38 CST+8
- 前置依赖：TASK-070F 审计通过（审计意见书第437份）
- 当前定位：把 TASK-070A~TASK-070F 已通过审计的权限治理链路纳入本地 git 基线，形成可审计的本地封版 commit。

> 本任务只允许本地 commit，不允许 push / PR / tag / 生产发布 / ERPNext 生产联调声明 / GitHub required check 闭环声明。

## 2. 任务目标

完成一次严格白名单本地提交：

1. 复核当前分支、HEAD、脏工作树。
2. 复跑权限治理核心测试、Python 编译、前端 typecheck 与边界扫描。
3. 生成 `TASK-070G_权限治理本地封版提交证据.md`。
4. 只按白名单显式 `git add`。
5. 创建本地 commit。
6. 提交后把控制面切到 `READY_FOR_AUDIT / C Auditor / TASK-070G`。
7. 回交 commit hash、parent hash、staged 清单、验证结果和证据路径给 C Auditor。

## 3. 允许新增或修改的证据文件

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 允许纳入本地 commit 的白名单

只能暂存以下文件。未列入的文件一律不得暂存。

### 4.1 后端代码

- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/routers/permission_governance.py`
- `07_后端/lingyi_service/app/schemas/permission_governance.py`
- `07_后端/lingyi_service/app/services/audit_service.py`
- `07_后端/lingyi_service/app/services/permission_governance_service.py`
- `07_后端/lingyi_service/app/services/permission_governance_export_service.py`
- `07_后端/lingyi_service/app/services/permission_governance_diagnostic_service.py`

### 4.2 后端测试

- `07_后端/lingyi_service/tests/test_permissions_registry.py`
- `07_后端/lingyi_service/tests/test_permission_governance_readonly.py`
- `07_后端/lingyi_service/tests/test_permission_governance_audit_readonly.py`
- `07_后端/lingyi_service/tests/test_permission_governance_audit_export.py`
- `07_后端/lingyi_service/tests/test_permission_governance_diagnostic.py`

### 4.3 前端代码

- `06_前端/lingyi-pc/src/api/permission_governance.ts`
- `06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
- `06_前端/lingyi-pc/src/router/index.ts`

### 4.4 任务与证据文档

- `03_需求与设计/02_开发计划/TASK-070A_权限治理动作目录只读基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070B_权限治理审计查询只读基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070C_权限治理审计脱敏CSV导出基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070C_FIX1_权限治理审计导出写入边界修复_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070D_权限治理诊断只读健康检查基线_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md`
- `03_需求与设计/02_开发计划/TASK-070E_FIX1_权限治理收口报告时间线修复_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md`
- `03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版白名单提交_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版提交证据.md`
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
10. 禁止暂存 `TASK-021* / TASK-022* / TASK-023* / TASK-024*` 等非权限治理任务单。
11. 禁止暂存 `07_后端/lingyi_service/tests/test_permission_audit_baseline.py`，该文件属于历史继承背景，不属于本次封版白名单。
12. 禁止暂存 `__pycache__`、`.pyc`、临时报告、截图、缓存目录。
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

要求：当前分支应为 `codex/sprint4-seal`；当前 HEAD 应为 `f08015c` 或其后继本地提交；提交前不得已有本任务 tag。

### 6.2 权限治理后端测试

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

期望：`50 passed, 1 warning` 或等价全通过结果。

### 6.3 Python 编译

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

要求：四类权限动作和七类权限治理接口均有证据。

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

要求：无权限治理写路由；permission governance router/service/export/diagnostic 中无直接 `session.add/delete/commit/rollback`；无 ERPNext/API resource/库存财务高危写语义；冻结动作仅可命中静态字符串或语法；无敏感值泄露。

### 6.7 前端边界与下载闭环扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios\.|/api/resource|permission:diagnostic|/api/permissions/diagnostic|approval|rollback|import|cache_refresh|recalculate|generate|sync|submit" \
  src/api/permission_governance.ts src/views/system/PermissionGovernance.vue src/router/index.ts || true
rg -n "requestFile|exportSecurityAuditCsv|exportOperationAuditCsv|URL\.createObjectURL|ElMessage\.error|ElMessage\.warning|await permissionGovernanceApi\.export" \
  src/api/request.ts src/api/permission_governance.ts src/views/system/PermissionGovernance.vue || true
```

要求：无裸 `fetch/axios`、无 `/api/resource`、无普通前端诊断入口、无审批/回滚/导入/配置发布能力；CSV 导出链路仍命中统一下载 helper、blob 下载和错误提示。

### 6.8 禁改目录检查

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
git diff --check
```

要求：禁改目录 diff 为空；`git diff --check` 通过。

## 7. 生成封版提交证据

新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版提交证据.md`

必须包含：

1. 当前分支、提交前 HEAD。
2. 前置审计：第437份 `TASK-070F PASS`。
3. 权限治理审计闭环摘要：第422~437份关键结论。
4. 后端测试结果。
5. Python 编译结果。
6. 前端 typecheck 结果。
7. 权限动作与路由映射扫描结果。
8. 后端边界扫描结果。
9. 前端边界与 CSV 下载闭环扫描结果。
10. 禁改目录与 diff check 结果。
11. 预提交 staged 白名单清单。
12. 残余风险。
13. 提交后记录策略：不得在 commit 后为了回填 hash 修改已提交证据；提交后 hash 与 parent 只在回交正文和必要的 post-commit 工程师日志中提供。

## 8. 显式暂存要求

必须逐个或按明确路径列表暂存白名单文件。示例：

```bash
git add -- \
  '07_后端/lingyi_service/app/core/permissions.py' \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/routers/permission_governance.py' \
  '07_后端/lingyi_service/app/schemas/permission_governance.py' \
  '07_后端/lingyi_service/app/services/audit_service.py' \
  '07_后端/lingyi_service/app/services/permission_governance_service.py' \
  '07_后端/lingyi_service/app/services/permission_governance_export_service.py' \
  '07_后端/lingyi_service/app/services/permission_governance_diagnostic_service.py' \
  '07_后端/lingyi_service/tests/test_permissions_registry.py' \
  '07_后端/lingyi_service/tests/test_permission_governance_readonly.py' \
  '07_后端/lingyi_service/tests/test_permission_governance_audit_readonly.py' \
  '07_后端/lingyi_service/tests/test_permission_governance_audit_export.py' \
  '07_后端/lingyi_service/tests/test_permission_governance_diagnostic.py' \
  '06_前端/lingyi-pc/src/api/permission_governance.ts' \
  '06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '03_需求与设计/02_开发计划/TASK-070A_权限治理动作目录只读基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070B_权限治理审计查询只读基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070C_权限治理审计脱敏CSV导出基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070C_FIX1_权限治理审计导出写入边界修复_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070D_权限治理诊断只读健康检查基线_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070E_权限治理本地收口验证报告.md' \
  '03_需求与设计/02_开发计划/TASK-070E_FIX1_权限治理收口报告时间线修复_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070F_权限治理本地封版复审证据.md' \
  '03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版白名单提交_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版提交证据.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md' \
  '00_交接与日志/HANDOVER_STATUS.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

暂存后必须执行：

```bash
git diff --cached --name-only
```

并逐项核对：

- staged 文件必须全部属于白名单。
- staged 文件不得包含 `test_permission_audit_baseline.py`。
- staged 文件不得包含 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
- staged 文件不得包含 `__pycache__` 或 `.pyc`。

## 9. 本地 commit

暂存清单核验通过后执行：

```bash
git commit -m "chore: seal permission governance baseline"
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
- parent 应为 `f08015c` 或其后继本地提交。
- `git diff --cached --name-only` 为空。
- `git tag --points-at HEAD` 为空。
- 不执行 push / PR / tag / 生产发布。

## 10. 提交后控制面写回

commit 成功后，B 需要写回：

- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`：`READY_FOR_AUDIT / C Auditor / TASK-070G`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`：`TASK-070G / 状态=待审计`

注意：这两个写回发生在 commit 之后，因此可作为 post-commit 工作区差异存在；C 审计时需明确区分 commit 内容与 post-commit 控制面差异。

## 11. 完成回报格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070G
ROLE: B Engineer

CHANGED_FILES:
- 列出本地 commit 文件清单摘要
- 列出 post-commit 控制面差异文件

EVIDENCE:
- commit=<short_hash>
- parent=<short_hash>
- message=chore: seal permission governance baseline
- staged 文件全部在 TASK-070G 白名单内
- 未暂存/提交禁改目录、test_permission_audit_baseline.py、__pycache__、.pyc
- 未 push / PR / tag / 生产发布

VERIFICATION:
- pytest：...
- py_compile：...
- npm run typecheck：...
- 权限/路由映射扫描：...
- 后端边界扫描：...
- 前端边界扫描：...
- 禁改目录 diff：...
- git diff --check：...
- git diff --cached --name-only：空
- git tag --points-at HEAD：空

NEXT_ROLE:
- C Auditor
```

## 12. 完成定义

1. `TASK-070G_权限治理本地封版提交证据.md` 已生成。
2. 所有验证命令通过或有明确可审计失败说明。
3. staged 清单完全等于白名单子集，不含禁改路径和历史噪声。
4. 已创建本地 commit：`chore: seal permission governance baseline`。
5. 提交后控制面已切到 `READY_FOR_AUDIT / C Auditor / TASK-070G`。
6. 未执行 push / PR / tag / 生产发布。
