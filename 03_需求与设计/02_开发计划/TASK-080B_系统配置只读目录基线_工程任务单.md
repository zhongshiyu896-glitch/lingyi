# TASK-080B 系统配置只读目录基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-080B
- 任务名称：系统配置只读目录基线
- 模块：系统管理 / 系统配置目录
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 07:18 CST+8
- 前置依赖：TASK-080A 系统管理设计冻结审计通过（审计意见书第440份）
- 设计依据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- 当前定位：系统管理实现链路第一张任务，只建立系统配置只读目录，不开放写入、字典、诊断、导出、同步、缓存刷新、平台管理。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

## 2. 任务目标

实现系统配置只读目录基线：

1. 注册 `system:read` 与 `system:config_read`。
2. 新增 `GET /api/system/configs/catalog`。
3. 返回本地静态系统配置目录元数据，只展示 key、分组、说明、来源、是否敏感，不返回任何真实敏感值。
4. 新增最小前端只读入口 `/system/management`，展示系统配置目录。
5. 补充权限、只读边界、敏感信息保护、前端门禁测试。
6. 不新增数据库表、不新增 migration、不访问 ERPNext、不新增 outbox/worker/internal。

## 3. 允许修改范围

只允许修改或新增以下文件。未列入文件一律不得改动。

### 3.1 后端权限注册与映射

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端系统管理只读模块

允许新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/system_management.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/system_management.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_config_catalog_service.py`

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_system_config_catalog_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端最小只读入口

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅允许补 `system:read` / `system:config_read` 只读显示门禁，不得开放写按钮）

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080B_系统配置只读目录基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止新增或修改数据库 migration。
2. 禁止新增或修改 SQLAlchemy model。
3. 禁止新增或修改字典目录接口。
4. 禁止新增或修改系统健康诊断接口。
5. 禁止新增导出、导入、同步、缓存刷新、平台管理能力。
6. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
7. 禁止访问 ERPNext 或 `/api/resource`。
8. 禁止新增 ERPNext 写调用或外部写调用。
9. 禁止 outbox / worker / run-once / internal。
10. 禁止返回 token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload。
11. 禁止复用 `permission:*`、`dashboard:*`、`report:*`、`warehouse:*`、`inventory:*` 作为 `system:*` 授权通过条件。
12. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
13. 禁止 commit / push / PR / tag / 生产发布。

## 5. 后端实现要求

### 5.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

- `SYSTEM_READ = "system:read"`
- `SYSTEM_CONFIG_READ = "system:config_read"`
- `ALL_SYSTEM_ACTIONS = {SYSTEM_READ, SYSTEM_CONFIG_READ}`
- `MODULE_ACTION_REGISTRY["system"] = ALL_SYSTEM_ACTIONS`

要求：

1. `System Manager` 必须获得 `system:read` 与 `system:config_read`。
2. `Viewer` 默认不得获得 `system:read` 或 `system:config_read`。
3. 不得注册 `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 为可用动作；这些动作在本阶段只允许出现在测试或文档负向断言中。
4. 不得改变既有 `permission:*`、`report:*`、`dashboard:*`、`warehouse:*` 权限语义。

### 5.2 只读接口

新增 router：`app/routers/system_management.py`

路由：

```text
GET /api/system/configs/catalog
```

必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口校验 `system:read`。
2. 再校验 `system:config_read`，不得只校验其中一个动作。
3. 返回统一信封 `{code,message,data}`。
4. 只读取本地静态配置目录元数据。
5. 不读取业务数据库。
6. 不访问 ERPNext。
7. 不写安全审计或操作审计以外的业务事实；本任务不要求新增操作审计写入。
8. 非 `system:*` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 5.3 查询参数

允许以下只读过滤参数：

- `module`：可选，按模块过滤。
- `config_group`：可选，按配置分组过滤。
- `source`：可选，按来源过滤。
- `is_sensitive`：可选，`true/false`。

要求：

1. 非法 `is_sensitive` 必须返回 `400 / INVALID_QUERY_PARAMETER`，不得静默忽略。
2. 未知过滤值可以返回空列表，但不能返回错误敏感信息。
3. 不得支持 `value`、`raw_value`、`secret`、`token` 等参数。

### 5.4 响应字段

成功响应至少包含：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "items": [
      {
        "module": "system",
        "config_key": "ui.locale.default",
        "config_group": "ui",
        "description": "默认界面语言",
        "source": "static_registry",
        "is_sensitive": false,
        "updated_at": "2026-04-21T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

禁止返回：

- `value`
- `raw_value`
- `secret_value`
- `password`
- `token`
- `authorization`
- `cookie`
- `dsn`
- `database_url`
- 任何真实连接串或凭据

### 5.5 静态目录最低数据要求

`system_config_catalog_service.py` 中至少提供 6 条本地静态配置目录元数据，覆盖：

1. `ui` 分组。
2. `security` 分组。
3. `audit` 分组。
4. `integration` 分组。
5. 至少 1 条 `is_sensitive=true`，但不得含真实值。
6. 至少 2 个不同 `source`。

## 6. 前端实现要求

### 6.1 API

新增：`src/api/system_management.ts`

要求：

1. 必须复用统一 `request` client。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 只实现 GET `/api/system/configs/catalog`。
5. 不实现字典、诊断、导出、导入、同步、缓存刷新、平台管理。

### 6.2 页面

新增：`src/views/system/SystemManagement.vue`

要求：

1. 最小只读页面即可。
2. 展示系统配置目录列表。
3. 无 `system:read` 或无 `system:config_read` 时不得请求接口，应显示无权限提示。
4. 对 `is_sensitive=true` 只展示“敏感配置”标记，不展示任何值。
5. 不展示或启用任何创建、编辑、删除、审批、回滚、导入、导出、诊断、同步、缓存刷新、平台管理按钮。

### 6.3 路由

在 `src/router/index.ts` 中新增最小路由：

```text
/system/management
meta.module = system
```

要求：

1. 不改现有 route name/path。
2. 不删除已有权限治理、报表、dashboard、仓库、质量、销售库存路由。
3. 不引入动态远程菜单。
4. 修改前记录 `src/router/index.ts` 的 SHA-256，回交中说明本任务新增 `/system/management` 路由。

## 7. 测试要求

新增或补充测试必须覆盖：

1. `system:read` 与 `system:config_read` 已注册到 `MODULE_ACTION_REGISTRY["system"]`。
2. `System Manager` 具备 `system:read` 与 `system:config_read`。
3. `Viewer` 不具备 `system:read` 与 `system:config_read`。
4. `GET /api/system/configs/catalog` 需要 `system:read`。
5. `GET /api/system/configs/catalog` 需要 `system:config_read`。
6. 只有 `permission:read`、`dashboard:read`、`report:read`、`warehouse:read`、`inventory:read` 的用户访问返回 403。
7. 响应字段不包含 `value/raw_value/password/token/authorization/cookie/dsn/database_url`。
8. `is_sensitive=true` 只返回标记，不返回真实敏感值。
9. `module/config_group/source/is_sensitive` 过滤有效；非法 `is_sensitive` 返回 400。
10. 路由文件中不存在 `@router.post/put/patch/delete`。
11. system management 文件中不存在 ERPNext 访问、业务 DB 查询、outbox/worker/run-once/internal。
12. 前端 API 只使用统一 `request`，无裸 `fetch/axios`。
13. 前端 typecheck 通过。

## 8. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_system_config_catalog_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/system_management.py app/services/system_config_catalog_service.py app/schemas/system_management.py
rg -n "@router\.(post|put|patch|delete)" app/routers/system_management.py || true
rg -n "Session\(|\.query\(|select\(|execute\(|session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(" app/routers/system_management.py app/services/system_config_catalog_service.py app/schemas/system_management.py || true
rg -n "requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/system_management.py app/services/system_config_catalog_service.py app/schemas/system_management.py || true
rg -n "outbox|worker|run-once|internal|diagnostic|cache_refresh|sync|import|export|platform_manage" app/routers/system_management.py app/services/system_config_catalog_service.py app/schemas/system_management.py || true
rg -n "value|raw_value|secret_value|password|token|Authorization|authorization|Cookie|cookie|DSN|dsn|DATABASE_URL|database_url" app/routers/system_management.py app/services/system_config_catalog_service.py app/schemas/system_management.py tests/test_system_config_catalog_readonly.py || true
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
```

说明：敏感字段扫描若命中测试中的负向断言或字段禁止清单，必须在回交中解释；实现响应不得返回这些字段。

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource|diagnostic|cache_refresh|sync|import|export|platform_manage|submit" src/api/system_management.ts src/views/system/SystemManagement.vue || true
shasum -a 256 src/router/index.ts
```

在 `/Users/hh/Desktop/领意服装管理系统` 执行：

```bash
git diff --check -- \
  07_后端/lingyi_service/app/core/permissions.py \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/app/routers/system_management.py \
  07_后端/lingyi_service/app/schemas/system_management.py \
  07_后端/lingyi_service/app/services/system_config_catalog_service.py \
  07_后端/lingyi_service/tests/test_system_config_catalog_readonly.py \
  07_后端/lingyi_service/tests/test_permissions_registry.py \
  06_前端/lingyi-pc/src/api/system_management.ts \
  06_前端/lingyi-pc/src/views/system/SystemManagement.vue \
  06_前端/lingyi-pc/src/router/index.ts \
  06_前端/lingyi-pc/src/stores/permission.ts \
  03_需求与设计/02_开发计划/TASK-080B_系统配置只读目录基线_工程任务单.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

## 9. 回交格式

B 完成后按以下格式回交：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080B
ROLE: B Engineer

CHANGED_FILES:
- 列出真实改动文件绝对路径

EVIDENCE:
- 说明 system:read / system:config_read 注册与权限矩阵结果
- 说明 GET /api/system/configs/catalog 只读实现与字段白名单
- 说明前端 /system/management 只读入口
- 说明未开放字典、诊断、导出、导入、同步、缓存刷新、平台管理、写路由

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 后端只读/敏感字段/越界扫描结果
- 前端 forbidden 扫描结果
- 禁改目录 diff 结果
- git diff --check 结果
- router/index.ts 修改前后 SHA-256 与改动说明

BLOCKERS:
- 无 / 或列明阻塞

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

满足以下条件才算完成：

1. `system:read` 与 `system:config_read` 注册完成且测试覆盖。
2. `/api/system/configs/catalog` 只读接口可用，权限 fail closed。
3. 响应不包含任何真实敏感值或敏感字段。
4. 前端 `/system/management` 只读入口可 typecheck 通过。
5. 必跑验证全部执行并记录结果。
6. 禁改目录无 diff。
7. 未执行 commit / push / PR / tag / 生产发布。
