# TASK-070F 权限治理本地封版复审证据

- 任务编号：TASK-070F
- 执行角色：B Engineer
- 执行时间：2026-04-21 06:00-06:18 (Asia/Shanghai)
- 当前分支：`codex/sprint4-seal`
- 当前 HEAD：`f08015c`
- HEAD tag：无
- 结论：建议进入 C 本地封版审计
- 说明：本证据为本地封版复审，不等同 commit / push / PR / tag / 生产发布。

## 1. 任务链路与审计闭环

| 任务 | 审计闭环 | 复审结论 |
| --- | --- | --- |
| TASK-070A | 第422份阻塞（控制面对账）-> 第423份通过 | 动作目录与角色矩阵只读基线保留 |
| TASK-070B | 第424份阻塞（控制面对账）-> 第425份通过 | 审计查询只读基线保留 |
| TASK-070C | 第426份阻塞（控制面对账）-> 第427份需修复 | 导出写入边界问题进入 FIX1 |
| TASK-070C_FIX1 | 第428份阻塞（控制面对账）-> 第429份通过 | 导出审计写入边界收敛到 AuditService |
| TASK-070D | 第430份阻塞（控制面对账）-> 第431份通过 | 诊断只读健康检查基线保留 |
| TASK-070E | 第432份阻塞（控制面对账）-> 第433份需修复 | 收口报告时间线问题进入 FIX1 |
| TASK-070E_FIX1 | 第434份阻塞（控制面对账）-> 第435份通过 | 收口报告时间线元数据已闭环 |

## 2. 已完成能力清单

1. `permission:read` + `GET /api/permissions/actions/catalog` + `GET /api/permissions/roles/matrix` 只读能力保留。
2. `permission:audit_read` + 安全/操作审计查询只读能力保留。
3. `permission:export` + 安全/操作审计脱敏 CSV 导出能力保留。
4. CSV 公式注入防护、统一下载 client（`requestFile`）与前端错误提示闭环保留。
5. 导出审计写入边界保留为 `AuditService` 公共 helper（FIX1 闭环后状态）。
6. `permission:diagnostic` + `GET /api/permissions/diagnostic` 只读诊断能力保留。
7. `TASK-070E_FIX1` 时间线元数据修复状态保留。
8. 权限配置写入、角色创建更新禁用、用户资源权限更新、审批、回滚、导入、配置发布继续冻结。

## 3. 后端测试结果

命令：

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

结果：`50 passed, 1 warning`（与 TASK-070E 收口基线一致）。

## 4. Python 编译结果

命令：

```bash
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

结果：通过（无输出，退出码 0）。

## 5. 前端 typecheck 结果

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

结果：通过（`vue-tsc --noEmit -p tsconfig.json` 退出码 0）。

## 6. 权限动作与路由映射证据

扫描命中确认：

- 权限动作：`permission:read`、`permission:audit_read`、`permission:export`、`permission:diagnostic`
- 主映射：`/api/permissions/actions/catalog`、`/api/permissions/roles/matrix`、`/api/permissions/audit/security`、`/api/permissions/audit/operations`、`/api/permissions/audit/security/export`、`/api/permissions/audit/operations/export`、`/api/permissions/diagnostic`

关键文件：

- `app/core/permissions.py`
- `app/main.py`
- `app/routers/permission_governance.py`
- `tests/test_permissions_registry.py`
- `tests/test_permission_governance_*.py`

## 7. 后端边界扫描结果

### 7.1 写路由扫描

- `rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py`
- 结果：空（无权限治理写路由）。

### 7.2 直接 session 写入扫描

- `rg -n "session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(|AuditService\.record_(success|failure)\(" ...`
- 结果：空（`permission_governance.py` / `permission_governance_service.py` / `permission_governance_export_service.py` / `permission_governance_diagnostic_service.py` 未命中直接 session 写入）。

### 7.3 ERPNext/库存财务高危写语义扫描

- `rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|Stock Entry|Stock Reconciliation|Stock Ledger Entry|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" ...`
- 结果：空。

### 7.4 冻结动作关键词扫描

- `rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import" ...`
- 结果：有命中，但均为静态字符串/分类字典/`import` 语法，不构成新增能力入口。

### 7.5 敏感信息扫描

- `rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL|before_data|after_data|raw headers|raw payload" ...`
- 结果：命中为字段名与脱敏键名常量（如 `token/password/secret/dsn`、`has_before_data/has_after_data`），未发现原始敏感值泄露。

## 8. 前端边界与下载闭环扫描结果

### 8.1 前端边界

命令：

```bash
rg -n "fetch\(|axios\.|/api/resource|permission:diagnostic|/api/permissions/diagnostic|approval|rollback|import|cache_refresh|recalculate|generate|sync|submit" \
  src/api/permission_governance.ts src/views/system/PermissionGovernance.vue src/router/index.ts || true
```

结果：

- 未命中裸 `fetch/axios`、`/api/resource`、`permission:diagnostic`、`/api/permissions/diagnostic`。
- 命中主要为 TS `import` 语法与路由懒加载 `import(...)`，不构成越界业务动作。

### 8.2 CSV 下载闭环

命令：

```bash
rg -n "requestFile|exportSecurityAuditCsv|exportOperationAuditCsv|URL\.createObjectURL|ElMessage\.error|ElMessage\.warning|await permissionGovernanceApi\.export" \
  src/api/request.ts src/api/permission_governance.ts src/views/system/PermissionGovernance.vue || true
```

结果：

- 命中 `requestFile`、`URL.createObjectURL`、`exportPermissionSecurityAuditCsv/exportPermissionOperationAuditCsv`。
- 页面命中 `ElMessage.warning`（无导出权限）与 `ElMessage.error`（导出失败）提示闭环。

## 9. 导出审计写入边界说明

- 按第429份已通过口径，导出审计写入边界由 `AuditService` 公共 helper 负责。
- 本轮扫描未在 permission governance router/service/export service/diagnostic service 命中直接 `session.add/delete/commit/rollback`。

## 10. 禁改目录与继承脏基线

### 10.1 禁改目录 diff

命令：

```bash
git diff --name-only -- .github .ci-reports '01_需求与资料' '02_源码' '03_环境与部署' '04_测试与验收' '05_交付物'
```

结果：空。

### 10.2 业务代码区继承脏基线

命令：

```bash
git diff --name-only -- 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src
```

结果：

- `06_前端/lingyi-pc/src/router/index.ts`
- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/services/audit_service.py`
- `07_后端/lingyi_service/tests/test_permissions_registry.py`

说明：以上为继承差异，不属于 `TASK-070F` 新增改动。

### 10.3 diff check

- `git diff --check`：通过。

## 11. 剩余风险

1. 本地封版复审不等同生产发布。
2. 本地封版复审不等同 ERPNext 生产联调完成。
3. 本地封版复审不等同 GitHub hosted runner / required check 平台闭环。
4. 当前工作区存在历史未跟踪目录与继承脏基线；若需提交，必须另开白名单提交任务。
5. 权限配置写入、角色创建/更新/禁用、用户资源权限更新、审批、回滚、导入、配置发布仍冻结，未在本链路放行。

## 12. 结论

建议进入 C 本地封版审计。
