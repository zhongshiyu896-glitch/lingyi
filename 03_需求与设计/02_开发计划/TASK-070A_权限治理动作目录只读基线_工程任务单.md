# TASK-070A 权限治理动作目录只读基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-070A
- 任务名称：权限治理动作目录只读基线
- 模块：权限治理 / 系统管理
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-060G 审计通过（审计意见书第421份）
- 设计依据：`TASK-020A_权限治理设计.md`、`TASK-020_权限治理设计.md`、`TASK-007_权限与审计统一基座设计.md`
- 当前定位：进入权限治理主线的第一张实现任务，只建立只读动作目录与静态角色矩阵查询，不开放任何权限配置写入。

## 2. 任务目标

实现权限治理只读基线：

1. 注册 `permission:read` 动作权限。
2. 新增只读后端接口：动作目录、静态角色矩阵。
3. 新增最小前端只读页面入口，用于查看动作目录和角色矩阵。
4. 补充权限、只读边界、前端门禁测试。
5. 不修改现有鉴权核心语义，不改写现有角色权限配置。

本任务不做：

```text
权限配置写入 / 审批 / 回滚 / 导入 / 导出 / 诊断 / 安全审计查询 / 操作审计查询 / migration / models / outbox / worker / internal / ERPNext 写调用 / commit / push / PR / tag / 生产发布
```

## 3. 允许修改范围

只允许修改或新增以下文件。未列入文件一律不得改动。

### 3.1 后端权限注册

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端权限治理只读模块

允许新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_service.py`

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端最小只读入口

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/permission_governance.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅允许补 `permission:read` 只读显示门禁，不得开放写按钮）

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070A_权限治理动作目录只读基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 后端实现要求

### 4.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

- `PERMISSION_READ = "permission:read"`
- `ALL_PERMISSION_ACTIONS = {PERMISSION_READ}`
- `MODULE_ACTION_REGISTRY["permission"] = {PERMISSION_READ}`

要求：

1. `System Manager` 静态角色必须获得 `permission:read`。
2. `Viewer`、业务模块角色默认不得获得 `permission:read`。
3. 不得删除或重命名既有 `permission_audit:*` 动作。
4. 不得把 `permission:read` 作为任何写能力的前置。

### 4.2 只读接口

新增 router：`app/routers/permission_governance.py`

建议路由：

```text
GET /api/permissions/actions/catalog
GET /api/permissions/roles/matrix
```

两条路由必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口校验 `permission:read`。
2. 返回统一信封 `{code,message,data}`。
3. 只读取 `MODULE_ACTION_REGISTRY`、`DEFAULT_STATIC_ROLE_ACTIONS` 等本地静态注册表。
4. 不读取业务数据库。
5. 不访问 ERPNext。
6. 不写安全审计或操作审计以外的业务事实；本任务不要求新增操作审计写入。
7. 非 `permission:read` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 4.3 动作目录响应字段

`GET /api/permissions/actions/catalog` 至少返回：

```text
modules[]
modules[].module
modules[].actions[]
modules[].actions[].action
modules[].actions[].category
modules[].actions[].is_high_risk
modules[].actions[].ui_exposed
modules[].actions[].description
```

分类规则：

- `*:read` -> `read`
- `*:export` -> `export`
- `*:diagnostic` -> `diagnostic`，`is_high_risk=true`
- 包含 `worker` 或 `internal` -> `internal`，`is_high_risk=true`，`ui_exposed=false`
- `*:create/update/confirm/cancel/submit/manage/rollback/approval` -> `write_or_manage`，`is_high_risk=true`
- 其他未知动作不得静默丢弃，应归类为 `unknown` 且 `is_high_risk=true`

### 4.4 角色矩阵响应字段

`GET /api/permissions/roles/matrix` 至少返回：

```text
roles[]
roles[].role
roles[].actions[]
roles[].modules[]
roles[].high_risk_actions[]
roles[].ui_hidden_actions[]
```

要求：

1. 来源为 `DEFAULT_STATIC_ROLE_ACTIONS`。
2. 返回前按 action 字典序排序，保证测试稳定。
3. 不允许修改 `DEFAULT_STATIC_ROLE_ACTIONS` 中既有业务角色授权，除非只是给 `System Manager` 增加 `permission:read`。
4. `worker/internal/diagnostic` 类动作必须进入 `ui_hidden_actions` 或等价字段。

## 5. 前端实现要求

### 5.1 API

新增：`src/api/permission_governance.ts`

要求：

1. 必须复用统一 `request` client。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 只实现 GET：动作目录与角色矩阵。
5. 不实现导出、诊断、刷新、重算、同步、提交。

### 5.2 页面

新增：`src/views/system/PermissionGovernance.vue`

要求：

1. 最小只读页面即可，不做复杂设计。
2. 页面仅展示动作目录和角色矩阵。
3. 无 `permission:read` 时不得请求接口，应显示无权限提示。
4. 不展示或启用任何创建、编辑、删除、审批、回滚、导入、导出、诊断按钮。
5. 对 `diagnostic/internal/worker` 动作必须明显标注“高危/非普通前端动作”。

### 5.3 路由

在 `src/router/index.ts` 中新增最小路由：

```text
/permissions/governance
meta.module = permission
```

要求：

1. 不改现有 route name/path。
2. 不删除已有报表、仓库、质量、销售库存路由。
3. 不引入动态远程菜单。

## 6. 禁止范围

1. 禁止新增或修改数据库 migration。
2. 禁止新增或修改 SQLAlchemy model。
3. 禁止修改 `permission_service.py` 的核心鉴权逻辑，除非只是为了复用公开 helper 且不改变行为。
4. 禁止修改 `erpnext_permission_adapter.py`。
5. 禁止新增 `POST / PUT / PATCH / DELETE`。
6. 禁止新增权限配置写入、审批、回滚、导入、导出、诊断、审计查询接口。
7. 禁止访问 ERPNext。
8. 禁止 outbox / worker / run-once / internal。
9. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
10. 禁止 commit / push / PR / tag / 生产发布。

## 7. 必须测试

### 7.1 后端测试

新增或补充测试必须覆盖：

1. `permission:read` 已注册到 `MODULE_ACTION_REGISTRY["permission"]`。
2. `System Manager` 具备 `permission:read`。
3. `Viewer` 不具备 `permission:read`。
4. `GET /api/permissions/actions/catalog` 需要 `permission:read`。
5. `GET /api/permissions/roles/matrix` 需要 `permission:read`。
6. 只有 `dashboard:read`、`report:read`、`warehouse:read`、`quality:read` 的用户访问返回 `403`。
7. 动作目录覆盖至少 `dashboard`、`report`、`warehouse`、`quality`、`permission` 模块。
8. `diagnostic/worker/internal` 动作被标记为高危或前端隐藏。
9. 路由文件中不存在 `@router.post/put/patch/delete`。
10. 不访问 ERPNext、不创建 DB 业务查询依赖。

建议测试文件：

```text
07_后端/lingyi_service/tests/test_permission_governance_readonly.py
07_后端/lingyi_service/tests/test_permissions_registry.py
```

### 7.2 前端测试/类型检查

至少执行 `npm run typecheck`，并通过静态扫描确认：

1. `permission_governance.ts` 使用统一 `request`。
2. 无裸 `fetch/axios`。
3. 无 `/api/resource`。
4. `PermissionGovernance.vue` 无创建、编辑、删除、审批、回滚、导入、导出、诊断按钮文案或动作。

## 8. 必须执行验证命令

### 8.1 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
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
rg -n "permission:read|PERMISSION_READ|MODULE_ACTION_REGISTRY.*permission|/api/permissions/actions/catalog|/api/permissions/roles/matrix" app/core/permissions.py app/main.py app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py tests/test_permission_governance_readonly.py tests/test_permissions_registry.py
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py
rg -n "requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|ERPNext|outbox|worker|run-once|internal|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import|export|diagnostic" app/routers/permission_governance.py app/schemas/permission_governance.py app/services/permission_governance_service.py
```

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "fetch\(|axios|/api/resource|cache_refresh|recalculate|generate|sync|submit|approval|rollback|import|export|diagnostic|创建|编辑|删除|审批|回滚|导入|导出|诊断" src/api/permission_governance.ts src/views/system/PermissionGovernance.vue
```

允许命中说明：

- 页面纯文本标注“高危/非普通前端动作”可以出现。
- 若扫描命中禁用词，必须在回交中逐条解释为何不是业务能力入口；否则视为 `NEEDS_FIX`。

### 8.4 禁改目录

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
git diff --check
```

要求：禁改目录 diff 为空；`git diff --check` 通过。

## 9. 回交模板

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070A
ROLE: B Engineer

CHANGED_FILES:
- <真实改动文件>

EVIDENCE:
- permission:read 注册与权限矩阵证据
- /api/permissions/actions/catalog 实现证据
- /api/permissions/roles/matrix 实现证据
- 前端 /permissions/governance 页面证据
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

1. `permission:read` 已注册并仅授予合适角色。
2. 两个只读接口可用且受 `permission:read` 控制。
3. 前端只读页面可用且无写入口。
4. 测试与 typecheck 通过。
5. 后端无写路由、无 ERPNext 访问、无冻结能力越界。
6. 前端无裸 `fetch/axios`、无 `/api/resource`、无写按钮或危险动作入口。
7. 禁改目录无 diff。
8. 未 commit / 未 push / 未 PR / 未 tag / 未生产发布。
9. 回交包含真实改动清单、验证命令输出摘要和证据路径。
