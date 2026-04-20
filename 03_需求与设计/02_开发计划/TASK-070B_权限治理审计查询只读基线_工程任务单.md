# TASK-070B 权限治理审计查询只读基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-070B
- 任务名称：权限治理审计查询只读基线
- 模块：权限治理 / 系统管理 / 审计查询
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-070A 审计通过（审计意见书第423份）
- 设计依据：`TASK-020A_权限治理设计.md`、`TASK-020_权限治理设计.md`、`TASK-007_权限与审计统一基座设计.md`
- 当前定位：权限治理主线第二张实现任务，只建立安全审计与操作审计的只读查询能力，不开放导出、诊断、审批、回滚、配置写入或权限变更。

## 2. 任务目标

实现权限治理审计查询只读基线：

1. 注册细粒度动作 `permission:audit_read`。
2. 新增安全审计日志只读查询接口。
3. 新增操作审计日志只读查询接口。
4. 前端 `/permissions/governance` 页面增加最小“审计查询”只读区域。
5. 补充权限、筛选、脱敏、只读边界、前端门禁测试。

本任务不做：

```text
权限配置写入 / 角色创建 / 角色更新 / 角色禁用 / 用户资源权限更新 / 审批 / 回滚 / 导入 / 导出 / 诊断 / 缓存刷新 / 重算 / 生成 / 同步 / 提交 / migration / models / outbox / worker / run-once / internal / ERPNext 访问 / commit / push / PR / tag / 生产发布
```

## 3. 允许修改范围

只允许修改或新增以下文件。未列入文件一律不得改动。

### 3.1 后端权限注册与路由映射

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端权限治理只读模块

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_service.py`

允许读取但不修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_audit_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端只读入口

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/permission_governance.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅允许补 `permission:audit_read` 只读显示门禁，不得开放写按钮）

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`（TASK-070A 已完成路由入口，本任务不得继续改路由）

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070B_权限治理审计查询只读基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 后端实现要求

### 4.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

```text
PERMISSION_AUDIT_READ = "permission:audit_read"
```

若已有历史常量名 `PERMISSION_AUDIT_READ` 被 `permission_audit:read` 占用，不得重命名旧常量；请使用不冲突的新常量名，例如：

```text
PERMISSION_GOVERNANCE_AUDIT_READ = "permission:audit_read"
```

要求：

1. `permission:audit_read` 必须进入 `MODULE_ACTION_REGISTRY["permission"]`。
2. `System Manager` 静态角色必须获得 `permission:audit_read`。
3. `Viewer`、业务模块角色默认不得获得 `permission:audit_read`。
4. 不得删除或重命名既有 `permission_audit:*` 动作。
5. 不得用 `permission:read` 替代 `permission:audit_read`。
6. 不得新增 `permission:manage_all`、`permission:*` 等宽泛动作。

### 4.2 只读接口

在 `app/routers/permission_governance.py` 中新增：

```text
GET /api/permissions/audit/security
GET /api/permissions/audit/operations
```

两条路由必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口校验 `permission:audit_read`。
2. 返回统一信封 `{code,message,data}`。
3. 只读取本地审计表：`LySecurityAuditLog`、`LyOperationAuditLog`。
4. 不访问 ERPNext。
5. 不写业务数据库。
6. 不新增任何审计写入语义。
7. 不新增 `POST / PUT / PATCH / DELETE`。
8. 非 `permission:audit_read` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 4.3 查询参数

两条接口至少支持：

```text
from_date: YYYY-MM-DD，可选
to_date: YYYY-MM-DD，可选
module: 可选
action: 可选
request_id: 可选
resource_type: 可选
resource_id: 可选
page: 默认 1，最小 1
page_size: 默认 20，最小 1，最大 100
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

参数要求：

1. 非法日期返回 `400 / INVALID_QUERY_PARAMETER` 或当前项目统一参数错误码。
2. `from_date > to_date` 返回 `400 / INVALID_QUERY_PARAMETER` 或当前项目统一参数错误码。
3. `page_size > 100` 必须被拒绝。
4. 查询结果按 `created_at desc, id desc` 排序。
5. 不得用 200 + 空数据掩盖非法参数。

### 4.4 安全审计响应字段

`GET /api/permissions/audit/security` 至少返回：

```text
items[]
items[].id
items[].event_type
items[].module
items[].action
items[].resource_type
items[].resource_id
items[].resource_no
items[].user_id
items[].permission_source
items[].deny_reason
items[].request_method
items[].request_path
items[].request_id
items[].created_at
total
page
page_size
```

不得返回：

```text
authorization / cookie / token / secret / password / dsn / DATABASE_URL / raw headers / raw payload
```

### 4.5 操作审计响应字段

`GET /api/permissions/audit/operations` 至少返回：

```text
items[]
items[].id
items[].module
items[].action
items[].operator
items[].resource_type
items[].resource_id
items[].resource_no
items[].result
items[].error_code
items[].request_id
items[].created_at
total
page
page_size
```

默认不得返回 `before_data` / `after_data` 完整内容。

如确需返回变更摘要，只允许返回脱敏后的摘要字段，例如：

```text
has_before_data
has_after_data
before_keys[]
after_keys[]
```

不得返回 token、cookie、authorization、password、secret、dsn、DATABASE_URL 等敏感字段。

### 4.6 服务层要求

在 `permission_governance_service.py` 中增加只读查询逻辑。

要求：

1. 只使用 SQLAlchemy 只读 query/select。
2. 不调用 `AuditService.record_*`。
3. 不新增 session.add / session.delete / session.commit / bulk_update / execute(update/delete/insert)。
4. 查询异常按项目现有错误信封返回，不得吞异常后伪成功。
5. 对字符串筛选使用精确匹配；本任务不做模糊搜索。

## 5. 前端实现要求

### 5.1 API

在 `src/api/permission_governance.ts` 中新增：

```text
fetchPermissionSecurityAudit(...)
fetchPermissionOperationAudit(...)
```

要求：

1. 必须复用统一 `request` client。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 只实现 GET。
5. 不实现导出、诊断、刷新、重算、同步、提交、审批、回滚、导入。

### 5.2 页面

在 `src/views/system/PermissionGovernance.vue` 中新增最小“审计查询”只读区域。

要求：

1. 无 `permission:audit_read` 时不得请求审计查询接口，应显示无权限提示。
2. 有 `permission:audit_read` 时可查询安全审计与操作审计列表。
3. 页面仅展示摘要字段，不展示敏感字段。
4. 不展示或启用任何导出、诊断、创建、编辑、删除、审批、回滚、导入按钮。
5. 不修改路由文件。

## 6. 禁止范围

1. 禁止新增或修改数据库 migration。
2. 禁止新增或修改 SQLAlchemy model。
3. 禁止修改 `audit_service.py`。
4. 禁止修改 `erpnext_permission_adapter.py`。
5. 禁止修改 `permission_service.py` 核心鉴权逻辑。
6. 禁止新增 `POST / PUT / PATCH / DELETE`。
7. 禁止新增权限配置写入、审批、回滚、导入、导出、诊断接口。
8. 禁止访问 ERPNext。
9. 禁止 outbox / worker / run-once / internal。
10. 禁止修改 `src/router/index.ts`。
11. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
12. 禁止 commit / push / PR / tag / 生产发布。

## 7. 必须测试

### 7.1 后端测试

新增或补充测试必须覆盖：

1. `permission:audit_read` 已注册到 `MODULE_ACTION_REGISTRY["permission"]`。
2. `System Manager` 具备 `permission:audit_read`。
3. `Viewer` 不具备 `permission:audit_read`。
4. 只有 `permission:read` 不能访问审计查询接口。
5. 只有其他模块 read 权限不能访问审计查询接口。
6. `GET /api/permissions/audit/security` 需要 `permission:audit_read`。
7. `GET /api/permissions/audit/operations` 需要 `permission:audit_read`。
8. 安全审计查询支持 event_type、module、action、user_id、request_id、日期、分页筛选。
9. 操作审计查询支持 module、action、operator、result、error_code、request_id、日期、分页筛选。
10. 非法日期、from_date > to_date、page_size > 100 均 fail-closed。
11. 响应不包含 token/cookie/authorization/password/secret/dsn/DATABASE_URL/raw headers/raw payload。
12. 路由文件中不存在 `@router.post/put/patch/delete`。
13. 服务层不调用 `AuditService.record_*`，不执行写入语义。

建议测试文件：

```text
07_后端/lingyi_service/tests/test_permission_governance_audit_readonly.py
07_后端/lingyi_service/tests/test_permissions_registry.py
```

### 7.2 前端测试/类型检查

至少执行 `npm run typecheck`，并通过静态扫描确认：

1. `permission_governance.ts` 使用统一 `request`。
2. 无裸 `fetch/axios`。
3. 无 `/api/resource`。
4. `PermissionGovernance.vue` 无导出、诊断、创建、编辑、删除、审批、回滚、导入按钮或动作入口。
5. 无 `permission:audit_read` 分支不请求审计接口。

## 8. 必须执行验证命令

### 8.1 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_permission_governance_audit_readonly.py \
  tests/test_permission_governance_readonly.py \
  tests/test_permissions_registry.py \
  -v --tb=short
```

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile \
  app/routers/permission_governance.py \
  app/schemas/permission_governance.py \
  app/services/permission_governance_service.py \
  app/core/permissions.py \
  app/main.py
```

### 8.2 前端

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
```

### 8.3 边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "permission:audit_read|/api/permissions/audit/security|/api/permissions/audit/operations|LySecurityAuditLog|LyOperationAuditLog" app/core/permissions.py app/main.py app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py tests/test_permission_governance_audit_readonly.py tests/test_permissions_registry.py
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py
rg -n "AuditService\.|record_success|record_failure|record_security_audit|session\.add|session\.delete|session\.commit|insert\(|update\(|delete\(|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|ERPNext|outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import|export|diagnostic" app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py
rg -n "authorization|cookie|token|secret|password|dsn|DATABASE_URL|raw headers|raw payload" app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py tests/test_permission_governance_audit_readonly.py
```

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios|/api/resource|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import|export|diagnostic|创建|编辑|删除|审批|回滚|导入|导出|诊断" src/api/permission_governance.ts src/views/system/PermissionGovernance.vue
```

允许命中说明：

- TypeScript `import/export` 语法可以命中，但必须在回交中说明不是业务导入/导出能力。
- 页面提示文字可以出现“无权限查看审计查询”，但不得出现导出、诊断、创建、编辑、删除、审批、回滚按钮或调用。
- 若后端扫描命中 `diagnostic/export/import` 等禁用词，仅允许来自字符串分类说明或测试说明；不得是业务能力入口。

### 8.4 禁改目录

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
git diff --name-only -- 06_前端/lingyi-pc/src/router/index.ts
git diff --check
```

要求：禁改目录 diff 为空；`src/router/index.ts` 不得出现本任务新增 diff；`git diff --check` 通过。

## 9. 回交模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070B
ROLE: B Engineer

CHANGED_FILES:
- <真实改动文件>

EVIDENCE:
- permission:audit_read 注册与权限矩阵证据
- /api/permissions/audit/security 实现证据
- /api/permissions/audit/operations 实现证据
- 前端审计查询只读区域证据
- 脱敏与敏感字段负向扫描结果
- 只读边界扫描结果
- 禁改目录 diff 结果

VERIFICATION:
- pytest：<结果>
- py_compile：<结果>
- npm run typecheck：<结果>
- 后端边界扫描：<结果>
- 前端边界扫描：<结果>
- 禁改目录 diff：<结果>

BLOCKERS:
- 无 / 或列明阻塞

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

同时满足才算完成：

1. `permission:audit_read` 已注册并仅授予合适角色。
2. 两个审计查询接口可用且受 `permission:audit_read` 控制。
3. `permission:read` 与其他模块 read 权限不能替代审计查询权限。
4. 查询参数非法时 fail-closed，不返回 200 伪成功。
5. 响应不泄露 token/cookie/authorization/password/secret/dsn/DATABASE_URL/raw headers/raw payload。
6. 默认不返回 `before_data` / `after_data` 完整内容。
7. 前端审计查询区域可用且无写入口、无导出、无诊断。
8. 测试与 typecheck 通过。
9. 后端无写路由、无 ERPNext 访问、无冻结能力越界。
10. 前端无裸 `fetch/axios`、无 `/api/resource`、无危险动作入口。
11. 禁改目录无 diff，`src/router/index.ts` 无本任务新增 diff。
12. 未 commit / 未 push / 未 PR / 未 tag / 未生产发布。
13. 回交包含真实改动清单、验证命令输出摘要和证据路径。
