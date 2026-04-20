# TASK-070D 权限治理诊断只读健康检查基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-070D
- 任务名称：权限治理诊断只读健康检查基线
- 模块：权限治理 / 系统管理 / 诊断
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-070C_FIX1 审计通过（审计意见书第429份）
- 设计依据：`TASK-020A_权限治理设计冻结_工程任务单.md`、`TASK-020_权限治理设计.md`、`TASK-070A_权限治理动作目录只读基线_工程任务单.md`、`TASK-070B_权限治理审计查询只读基线_工程任务单.md`、`TASK-070C_权限治理审计脱敏CSV导出基线_工程任务单.md`
- 当前定位：权限治理主线第四张实现任务，仅开放管理员诊断只读健康检查接口；不开放权限配置写入、审批、回滚、导入、普通前端诊断入口或任何生产发布动作。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。B 未形成真实代码改动、测试结果、变更清单和证据路径前，不得回交 C。

## 2. 任务目标

实现权限治理诊断只读健康检查基线：

1. 注册并校验细粒度动作 `permission:diagnostic`。
2. 新增只读诊断接口：`GET /api/permissions/diagnostic`。
3. 诊断接口只返回本地安全健康摘要，不返回敏感配置、环境变量值、原始请求头、原始 payload 或凭据。
4. `permission:read`、`permission:audit_read`、`permission:export`、历史 `permission_audit:diagnostic`、`dashboard:read`、`report:diagnostic`、`warehouse:diagnostic`、`inventory:read` 均不得替代 `permission:diagnostic`。
5. 诊断结果仅基于本地静态权限注册表、角色矩阵、动作分类、治理接口能力开关与 main.py 安全目标映射；不得查询业务 DB，不得访问 ERPNext，不得触发导出下载，不得写审计表。
6. 通过 `main.py` 安全目标映射纳入统一审计/安全识别链路；不得在 permission governance router/service 中显式 `session.add/commit/rollback` 写审计。

本任务不做：

```text
权限配置写入 / 角色创建 / 角色更新 / 角色禁用 / 用户资源权限更新 / 审批 / 回滚 / 导入 / 导出新增 / 审计查询新增 / 缓存刷新 / 重算 / 生成 / 同步 / 提交 / migration / models / outbox / worker / run-once / internal / ERPNext 访问 / commit / push / PR / tag / 生产发布
```

## 3. 允许修改范围

未列入的文件一律不得修改。

### 3.1 后端权限注册与路由映射

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端权限治理模块

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/permission_governance.py`

必须新增或允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_diagnostic_service.py`

允许读取但原则上不得修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_export_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

如必须修改上述“原则上不得修改”的文件，必须在回交中单独说明原因、最小改动点、验证证据。

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_diagnostic.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 工程师日志

允许追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止修改范围

1. 禁止修改任何前端文件，包括但不限于：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/permission_governance.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
2. 禁止新增普通前端诊断按钮、菜单、路由或 API 封装。
3. 禁止新增 `permission:manage_all`、`permission:*`、`permission:write` 等宽泛或写入动作。
4. 禁止删除、重命名或改变既有 `permission:read`、`permission:audit_read`、`permission:export`、`permission_audit:*` 动作语义。
5. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
6. 禁止访问 ERPNext `/api/resource`，禁止使用 `requests/httpx` 外部访问或写调用。
7. 禁止查询业务 DB；本任务诊断服务只能读取本地静态注册表和代码内静态目录。
8. 禁止新增 migration、model、outbox、worker、run-once、internal 接口。
9. 禁止显式 `session.add/delete/commit/rollback` 出现在 permission governance router/service/diagnostic service 中。
10. 禁止改动 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
11. 禁止 commit / push / PR / tag / 生产发布。

## 5. 后端实现要求

### 5.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

```text
permission:diagnostic
```

建议常量名：

```python
PERMISSION_GOVERNANCE_DIAGNOSTIC = "permission:diagnostic"
```

要求：

1. `permission:diagnostic` 必须进入 `ALL_PERMISSION_ACTIONS`。
2. `MODULE_ACTION_REGISTRY["permission"]` 必须包含 `permission:diagnostic`。
3. `System Manager` 必须包含 `permission:diagnostic`。
4. `Viewer` 与业务角色默认不得包含 `permission:diagnostic`。
5. 历史 `PERMISSION_AUDIT_DIAGNOSTIC = "permission_audit:diagnostic"` 必须保留，但不得作为本接口的通过权限。
6. 不得使用 `permission:read`、`permission:audit_read` 或 `permission:export` 作为诊断接口授权回退。

### 5.2 路由

在 `app/routers/permission_governance.py` 中新增：

```text
GET /api/permissions/diagnostic
```

要求：

1. 必须使用 `PermissionService.require_action(...)` 或等价公共权限入口校验 `permission:diagnostic`。
2. 响应必须使用项目统一 `{code,message,data}` envelope。
3. 路由声明不得影响既有：
   - `GET /api/permissions/actions/catalog`
   - `GET /api/permissions/roles/matrix`
   - `GET /api/permissions/audit/security`
   - `GET /api/permissions/audit/operations`
   - `GET /api/permissions/audit/security/export`
   - `GET /api/permissions/audit/operations/export`
4. 不得新增写路由。
5. 不得在 route 中直接写审计表或提交事务。

### 5.3 诊断服务

新增 `app/services/permission_governance_diagnostic_service.py`。

服务职责：

1. 汇总 `MODULE_ACTION_REGISTRY["permission"]` 动作列表。
2. 汇总历史 `permission_audit` 模块动作列表，但仅作为兼容状态展示，不作为本任务授权动作。
3. 汇总静态角色中包含 permission 模块动作的角色数量和动作覆盖情况。
4. 返回高危动作和前端隐藏动作，包括 `permission:diagnostic`。
5. 返回权限治理能力开关摘要：
   - `catalog_enabled=true`
   - `roles_matrix_enabled=true`
   - `audit_read_enabled=true`
   - `export_enabled=true`
   - `diagnostic_enabled=true`
6. 返回本地 checks 列表，至少包含：
   - `permission:read_registered`
   - `permission:audit_read_registered`
   - `permission:export_registered`
   - `permission:diagnostic_registered`
   - `permission_diagnostic_hidden`
   - `permission_diagnostic_high_risk`
   - `permission_audit_legacy_kept`
   - `no_wildcard_permission_action`
7. 返回 `generated_at` UTC ISO 字符串。

建议响应字段：

```text
module: permission
status: ok
registered_actions: string[]
legacy_permission_audit_actions: string[]
high_risk_actions: string[]
ui_hidden_actions: string[]
roles_with_permission_actions_count: number
checks: list[{name,status,message?}]
catalog_enabled: boolean
roles_matrix_enabled: boolean
audit_read_enabled: boolean
export_enabled: boolean
diagnostic_enabled: boolean
generated_at: string
```

硬性限制：

1. 不读取或返回环境变量值。
2. 不返回数据库连接串、ERPNext URL、token、cookie、Authorization、secret、password、DSN、DATABASE_URL。
3. 不返回 raw headers、raw payload、before_data、after_data 原文。
4. 不查询业务 DB。
5. 不访问 ERPNext。
6. 不触发导出下载。
7. 不写审计表；诊断访问的安全识别依赖 `main.py` 安全目标映射与项目统一基座。

### 5.4 schema

在 `app/schemas/permission_governance.py` 中新增诊断响应 schema。

要求：

1. 字段必须显式定义，避免直接透传内部 dict。
2. 不得定义敏感字段名，例如 `token`、`cookie`、`authorization`、`secret`、`password`、`dsn`、`database_url`、`headers`、`payload`。
3. `checks` 必须有稳定结构，至少包含 `name`、`status`、可选 `message`。

### 5.5 main.py 动作映射

在 `app/main.py` 的路径动作映射中补充：

```text
/api/permissions/diagnostic -> module=permission / action=permission:diagnostic / resource_type=PermissionDiagnostic
```

要求：

1. 不影响既有 permission governance 路径映射。
2. 不影响 `permission_audit:*` 历史模块映射。
3. C 审计时必须能通过测试或直接调用映射函数确认该路径识别为 `permission:diagnostic`。

## 6. 测试要求

必须新增或补充测试覆盖：

1. 持有 `permission:diagnostic` 可访问 `GET /api/permissions/diagnostic`。
2. 仅持有 `permission:read` 访问诊断接口返回 403。
3. 仅持有 `permission:audit_read` 访问诊断接口返回 403。
4. 仅持有 `permission:export` 访问诊断接口返回 403。
5. 仅持有历史 `permission_audit:diagnostic` 访问诊断接口返回 403。
6. 仅持有 `dashboard:read`、`report:diagnostic`、`warehouse:diagnostic` 或 `inventory:read` 访问诊断接口返回 403。
7. 响应字段包含：
   - `module`
   - `status`
   - `registered_actions`
   - `legacy_permission_audit_actions`
   - `high_risk_actions`
   - `ui_hidden_actions`
   - `roles_with_permission_actions_count`
   - `checks`
   - `catalog_enabled`
   - `roles_matrix_enabled`
   - `audit_read_enabled`
   - `export_enabled`
   - `diagnostic_enabled`
   - `generated_at`
8. 响应中 `registered_actions` 包含 `permission:read`、`permission:audit_read`、`permission:export`、`permission:diagnostic`。
9. `high_risk_actions` 与 `ui_hidden_actions` 包含 `permission:diagnostic`。
10. 响应不包含敏感字段名和值：`token/cookie/authorization/secret/password/DSN/dsn/DATABASE_URL/headers/payload`。
11. `MODULE_ACTION_REGISTRY["permission"]` 注册 `permission:diagnostic`。
12. `System Manager` 包含 `permission:diagnostic`，`Viewer` 不包含。
13. `main.py` 动作映射识别 `/api/permissions/diagnostic` 为 `permission:diagnostic`。
14. 既有 `TASK-070A/070B/070C` 测试不回退。

## 7. 验证命令

### 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_permission_governance_diagnostic.py tests/test_permission_governance_readonly.py tests/test_permission_governance_audit_readonly.py tests/test_permission_governance_audit_export.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/services/permission_governance_diagnostic_service.py app/schemas/permission_governance.py app/core/permissions.py app/main.py
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py || true
rg -n "session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/services/permission_governance_diagnostic_service.py || true
rg -n "requests\.|httpx\.|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice|Sales Invoice" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/services/permission_governance_diagnostic_service.py app/schemas/permission_governance.py || true
rg -n "outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/services/permission_governance_diagnostic_service.py app/schemas/permission_governance.py || true
rg -n "Authorization|Cookie|token|secret|password|DSN|dsn|DATABASE_URL|headers|payload|before_data|after_data" app/routers/permission_governance.py app/services/permission_governance_diagnostic_service.py app/schemas/permission_governance.py || true
```

### 前端边界

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
rg -n "permission:diagnostic|/api/permissions/diagnostic|diagnostic|fetch\(|axios\.|/api/resource|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import" src/api/permission_governance.ts src/views/system/PermissionGovernance.vue src/stores/permission.ts src/router/index.ts || true
```

### 禁改目录

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
git diff --check
```

## 8. 回交格式

B 完成后回交 C，必须使用以下格式：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070D
ROLE: B Engineer

CHANGED_FILES:
- <真实改动文件绝对路径>

EVIDENCE:
- permission:diagnostic 权限注册证据
- GET /api/permissions/diagnostic 路由证据
- 诊断响应字段与敏感信息排除证据
- permission:read / permission:audit_read / permission:export / permission_audit:diagnostic 不能替代诊断权限的测试证据
- main.py 动作映射证据
- 未新增前端诊断入口证据
- 未新增写路由、ERPNext访问、业务DB查询、outbox/worker/internal/cache_refresh/recalculate/generate/sync/submit证据

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 负向扫描结果
- 禁改目录 diff 结果

BLOCKERS:
- 无；如有，说明阻塞原因和已停止位置

NEXT_ROLE:
- C Auditor
```

## 9. 完成定义

1. `GET /api/permissions/diagnostic` 可用。
2. `permission:diagnostic` 是唯一入口动作权限。
3. `permission:read / permission:audit_read / permission:export / permission_audit:diagnostic / dashboard:read / report:diagnostic / warehouse:diagnostic / inventory:read` 不能替代诊断权限。
4. 响应只包含安全健康摘要，不泄露敏感字段和值。
5. `permission:diagnostic` 被动作目录分类为 `diagnostic`、`is_high_risk=true`、`ui_exposed=false`。
6. 未新增普通前端入口。
7. 未新增写路由、ERPNext访问、业务DB查询、outbox、worker、run-once、internal、cache_refresh、recalculate、generate、sync、submit。
8. TASK-070A/070B/070C 已审计能力不回退。
9. 禁改目录 diff 为空。
