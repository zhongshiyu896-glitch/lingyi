# TASK-070C 权限治理审计脱敏CSV导出基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-070C
- 任务名称：权限治理审计脱敏CSV导出基线
- 模块：权限治理 / 系统管理 / 审计导出
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-070B 审计通过（审计意见书第425份）
- 设计依据：`TASK-020A_权限治理设计.md`、`TASK-020_权限治理设计.md`、`TASK-007_权限与审计统一基座设计.md`
- 当前定位：权限治理主线第三张实现任务，仅开放安全审计与操作审计查询结果的脱敏 CSV 导出能力，不开放权限配置写入、审批、回滚、诊断或其它治理动作。

## 2. 任务目标

实现权限治理审计脱敏 CSV 导出基线：

1. 注册并校验细粒度动作 `permission:export`。
2. 新增安全审计日志脱敏 CSV 导出接口。
3. 新增操作审计日志脱敏 CSV 导出接口。
4. 导出数据复用 TASK-070B 的审计查询过滤范围与脱敏边界。
5. 增加 CSV 公式注入防护、固定安全文件名、权限隔离与敏感信息负向测试。
6. 前端 `/permissions/governance` 页面增加最小导出按钮，使用既有统一下载 client，并捕获下载错误提示用户。
7. 按设计要求记录导出操作审计；该审计记录是本任务唯一允许的本地审计写入。

本任务不做：

```text
权限配置写入 / 角色创建 / 角色更新 / 角色禁用 / 用户资源权限更新 / 审批 / 回滚 / 导入 / 诊断 / 缓存刷新 / 重算 / 生成 / 同步 / 提交 / migration / models / outbox / worker / run-once / internal / ERPNext 访问 / commit / push / PR / tag / 生产发布
```

除本任务明确指定的两条脱敏 CSV 导出接口外，不得新增任何导出能力。

## 3. 允许修改范围

只允许修改或新增以下文件。未列入文件一律不得改动。

### 3.1 后端权限注册与路由映射

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端权限治理模块

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_service.py`

必须新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_export_service.py`

允许读取但不得随意改动：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

`audit_service.py` 只有在现有公共审计记录接口不满足“记录导出操作审计”时，才允许做最小兼容改动；如修改，必须在回交报告中单独说明原因、改动点和测试证据。

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_audit_export.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_audit_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端导出入口

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/permission_governance.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅允许补 `permission:export` 页面门禁，不得开放写按钮）

允许读取但禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070C_权限治理审计脱敏CSV导出基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 后端实现要求

### 4.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

```text
permission:export
```

若已有历史常量名冲突，不得重命名旧常量；请使用不冲突的新常量名，例如：

```text
PERMISSION_GOVERNANCE_EXPORT = "permission:export"
```

要求：

1. `permission:export` 必须进入 `MODULE_ACTION_REGISTRY["permission"]`。
2. `System Manager` 静态角色必须获得 `permission:export`。
3. `Viewer`、业务模块角色默认不得获得 `permission:export`。
4. 不得删除或重命名既有 `permission:read`、`permission:audit_read` 或 `permission_audit:*` 动作。
5. 不得用 `permission:read` 或 `permission:audit_read` 替代 `permission:export`。
6. 不得新增 `permission:manage_all`、`permission:*` 等宽泛动作。

### 4.2 导出接口

在 `app/routers/permission_governance.py` 中新增：

```text
GET /api/permissions/audit/security/export
GET /api/permissions/audit/operations/export
```

两条路由必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口校验 `permission:export`。
2. 路由声明必须位于 `/api/permissions/audit/security` 与 `/api/permissions/audit/operations` 的动态或相近路由之前，避免被错误匹配。
3. 返回 `StreamingResponse` 或项目既有等价文件响应。
4. `Content-Type` 必须以 `text/csv` 开头，并包含 `charset=utf-8`。
5. `Content-Disposition` 文件名必须使用固定安全前缀，不得拼入用户输入：
   - `permission_security_audit_export_YYYYMMDDHHMMSS.csv`
   - `permission_operation_audit_export_YYYYMMDDHHMMSS.csv`
6. 只读取本地审计表：`LySecurityAuditLog`、`LyOperationAuditLog`。
7. 不访问 ERPNext。
8. 不新增 `POST / PUT / PATCH / DELETE`。
9. 非 `permission:export` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 4.3 导出查询参数

两条导出接口必须复用 TASK-070B 对应查询接口的过滤条件：

```text
from_date: YYYY-MM-DD，可选
to_date: YYYY-MM-DD，可选
module: 可选
action: 可选
request_id: 可选
resource_type: 可选
resource_id: 可选
```

安全审计额外支持：

```text
event_type: 可选
user_id: 可选
```

操作审计额外支持：

```text
operator: 可选
result: success|failed，可选
error_code: 可选
```

导出规模控制：

```text
limit: 默认 1000，最小 1，最大 5000
```

参数要求：

1. 非法日期返回 `400 / INVALID_QUERY_PARAMETER` 或当前项目统一参数错误码。
2. `from_date > to_date` 返回 `400 / INVALID_QUERY_PARAMETER` 或当前项目统一参数错误码。
3. `limit > 5000` 必须被拒绝，不得静默截断后伪成功。
4. 导出排序与 TASK-070B 查询一致：`created_at desc, id desc`。
5. 不得用 200 + 空文件掩盖非法参数。

### 4.4 安全审计 CSV 字段

安全审计导出 CSV 表头固定为：

```text
id,event_type,module,action,resource_type,resource_id,resource_no,user_id,permission_source,deny_reason,request_method,request_path,request_id,created_at
```

不得导出：

```text
authorization / cookie / token / secret / password / dsn / DATABASE_URL / raw headers / raw payload
```

### 4.5 操作审计 CSV 字段

操作审计导出 CSV 表头固定为：

```text
id,module,action,operator,resource_type,resource_id,resource_no,result,error_code,request_id,has_before_data,has_after_data,before_keys,after_keys,created_at
```

要求：

1. 不得导出 `before_data` / `after_data` 完整内容。
2. `before_keys` / `after_keys` 只能是脱敏后的键名列表，建议用 `|` 拼接。
3. 键名列表中不得出现 `token/cookie/authorization/password/secret/dsn/DATABASE_URL` 等敏感键。
4. 不得导出原始 request headers、request payload、raw body。

### 4.6 CSV 安全要求

所有 CSV 单元格必须做公式注入防护。

当单元格原始文本或去除前导空白后的文本以以下字符开头时：

```text
= + - @
```

或原始文本以制表符、回车、换行开头时，必须前置单引号 `'` 或采用项目已有等价安全策略。

必须补测试覆盖以下样例：

```text
=cmd|'/C calc'!A0
+SUM(1,2)
-10
@HYPERLINK("http://evil")
\t=1+1
```

### 4.7 导出审计记录

本任务唯一允许的写入是：为每次成功或失败的导出动作记录一条本地操作审计记录。

要求：

1. 必须通过项目现有审计服务或等价公共审计入口记录，不得在业务逻辑中散落直接 `session.add/commit`。
2. 审计记录模块建议为 `permission`。
3. 审计记录 action 必须能体现 `permission:export` 或具体导出动作。
4. 审计记录不得写入 CSV 原始内容、敏感查询值、token、cookie、authorization、password、secret、dsn、DATABASE_URL。
5. 如果审计记录失败，应 fail-closed，不得在审计写入失败时继续返回导出文件。
6. 除上述导出审计记录外，不得新增其它业务写入。

## 5. 后端服务要求

必须新增 `permission_governance_export_service.py`，并在其中隔离 CSV 构建、脱敏和公式注入防护逻辑；现有 service 只保留查询过滤复用或轻量编排。

要求：

1. 查询逻辑复用 TASK-070B 的过滤与脱敏规则。
2. CSV 构建逻辑必须可单测。
3. 不访问 ERPNext。
4. 不访问业务表。
5. 不新增 migration / model。
6. 不新增 outbox / worker / run-once / internal 能力。
7. 不新增配置写入、角色写入、审批、回滚、诊断、缓存刷新、重算、生成、同步、提交能力。

## 6. 前端实现要求

### 6.1 API

在 `src/api/permission_governance.ts` 中新增：

```text
exportPermissionSecurityAuditCsv(...)
exportPermissionOperationAuditCsv(...)
```

要求：

1. 必须复用既有 `requestFile(...)`。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 禁止直接 `link.href = '/api/permissions/audit/.../export'`。
5. 成功响应必须使用 blob/object URL 触发下载。
6. 文件名必须使用后端 `Content-Disposition` 返回值，并保留前端 fallback 安全文件名。

### 6.2 页面

在 `src/views/system/PermissionGovernance.vue` 中为审计查询区域新增最小导出按钮。

要求：

1. 仅当用户具备 `permission:export` 时显示或启用导出按钮。
2. 无 `permission:export` 时不得发起导出请求；应提示无权限或隐藏按钮。
3. 导出按钮只导出当前查询条件对应的数据。
4. 导出函数必须 `async + await + try/catch`。
5. 下载错误必须通过 `ElMessage.error(...)` 或项目现有提示机制告知用户。
6. 不得新增普通权限配置写按钮。
7. 不得新增角色创建、角色更新、角色禁用、审批、回滚、导入、诊断入口。

## 7. 测试要求

### 7.1 后端测试

新增或补充测试，至少覆盖：

1. 仅持有 `permission:export` 可访问两条导出接口。
2. 仅持有 `permission:read` 不可导出。
3. 仅持有 `permission:audit_read` 不可导出。
4. `dashboard:read`、`report:read`、`warehouse:read`、`inventory:read` 不可替代导出权限。
5. 非法日期、`from_date > to_date`、`limit > 5000` fail-closed。
6. 安全审计 CSV 表头固定且字段脱敏。
7. 操作审计 CSV 表头固定且不包含 `before_data/after_data` 原文。
8. CSV 公式注入防护样例全部通过。
9. 成功导出会记录导出操作审计。
10. 审计记录失败时导出 fail-closed。
11. 后端无新增写路由。
12. 后端无 ERPNext 访问和业务写调用。

### 7.2 前端测试或类型检查

至少确保：

1. `permission_governance.ts` 复用 `requestFile(...)`。
2. `PermissionGovernance.vue` 对导出调用使用 `await` 与 `try/catch`。
3. 无权限时不发起导出请求。
4. `npm run typecheck` 通过。

## 8. 必跑验证命令

### 8.1 后端 pytest

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_permission_governance_audit_export.py tests/test_permission_governance_audit_readonly.py tests/test_permission_governance_readonly.py tests/test_permissions_registry.py -v --tb=short
```

### 8.2 Python 编译检查

```bash
.venv/bin/python -m py_compile app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/core/permissions.py app/main.py
```

### 8.3 前端类型检查

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
```

### 8.4 后端边界扫描

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行并记录输出：

```bash
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py
rg -n "requests\.|httpx\.|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/schemas/permission_governance.py || true
rg -n "session\.(add|delete|commit)|insert\(|update\(|delete\(|bulk_update|execute\(" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py || true
rg -n "AuditService\.record_|record_success|record_failure" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py || true
rg -n "authorization|cookie|token|secret|password|dsn|DATABASE_URL|raw headers|raw payload|before_data|after_data" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/schemas/permission_governance.py tests/test_permission_governance_audit_export.py || true
rg -n "permission:export|/api/permissions/audit/(security|operations)/export|StreamingResponse|Content-Disposition|text/csv" app tests
```

说明：

- `AuditService.record_*` 或 `record_success/record_failure` 只允许出现在导出审计记录链路和对应测试中。
- `session.add/commit` 不应出现在权限治理 router/service/export service 中；若由既有 `audit_service.py` 内部完成，需在回交中明确说明。

### 8.5 前端边界扫描

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行并记录输出：

```bash
rg -n "requestFile|exportPermission(Security|Operation)AuditCsv|URL\.createObjectURL|ElMessage\.(error|warning)" src/api/permission_governance.ts src/views/system/PermissionGovernance.vue
rg -n "fetch\(|axios\.|/api/resource|window\.location|location\.href|diagnostic|cache_refresh|recalculate|generate|sync|submit|approve|rollback|import" src/api/permission_governance.ts src/views/system/PermissionGovernance.vue || true
```

### 8.6 禁改目录检查

在 `/Users/hh/Desktop/领意服装管理系统` 执行：

```bash
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
```

必须为空。

### 8.7 格式检查

```bash
git diff --check
```

必须通过。

## 9. 回交格式

B 完成后，必须按以下格式回交 C，不得只回状态：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070C
ROLE: B Engineer

CHANGED_FILES:
- 逐项列出真实改动文件绝对路径

IMPLEMENTATION:
- permission:export 注册与角色归属说明
- 两条导出接口说明
- CSV 字段、脱敏、公式注入防护说明
- 导出审计记录说明
- 前端 requestFile 下载与错误提示说明

VERIFICATION:
- pytest 命令与结果
- py_compile 命令与结果
- npm run typecheck 结果
- 后端边界扫描结果
- 前端边界扫描结果
- 禁改目录 diff 结果
- git diff --check 结果

RISKS:
- 如存在继承脏基线，说明路径、哈希或原因
- 不得把继承脏基线包装成本轮新增改动

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

本任务只有同时满足以下条件才算完成：

1. `permission:export` 已注册到 `permission` 模块，且权限隔离测试通过。
2. 两条脱敏 CSV 导出接口可用并强制 `permission:export`。
3. CSV 字段固定、敏感字段不泄露、公式注入防护生效。
4. 成功和失败导出均按设计记录导出操作审计；审计记录失败时 fail-closed。
5. 前端通过 `requestFile(...)` 下载，且下载错误可被页面捕获并提示。
6. 后端 pytest、py_compile、前端 typecheck 全部通过。
7. 后端/前端负向扫描无越界命中，或命中均为本任务明确允许项并已说明。
8. 禁改目录 diff 为空。
9. 未执行 commit / push / PR / tag / 生产发布。
10. 已追加工程师会话日志，并以真实证据回交 C。
