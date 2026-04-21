# TASK-080C 数据字典只读目录基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-080C
- 任务名称：数据字典只读目录基线
- 模块：系统管理 / 数据字典目录
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 07:48 CST+8
- 前置依赖：TASK-080B 系统配置只读目录基线审计通过（审计意见书第442份）
- 设计依据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- 当前定位：系统管理实现链路第二张任务，只建立数据字典只读目录，不开放写入、诊断、导出、同步、缓存刷新、平台管理。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

## 2. 任务目标

实现数据字典只读目录基线：

1. 注册 `system:dictionary_read`。
2. 新增 `GET /api/system/dictionaries/catalog`。
3. 返回本地静态数据字典目录元数据，只展示 `dict_type / dict_code / dict_name / status / source / updated_at`。
4. 复用现有 `/system/management` 页面，追加数据字典只读区域；不得新增新路由。
5. 补充权限、只读边界、静态过滤、前端门禁测试。
6. 不新增数据库表、不新增 migration、不访问 ERPNext、不新增 outbox/worker/internal。

## 3. 允许修改范围

只允许修改或新增以下文件。未列入文件一律不得改动。

### 3.1 后端权限注册与映射

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

### 3.2 后端系统管理只读模块

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/system_management.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/system_management.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_dictionary_catalog_service.py`

说明：`system_config_catalog_service.py` 属于已通过的 `TASK-080B` 基线，本任务禁止修改其既有语义；如需复用，只能在 router 或新 service 中并行接入，不得回退 080B 契约。

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_system_dictionary_catalog_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端最小只读入口

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`

说明：必须复用现有 `/system/management` 页面；本任务禁止修改 `src/router/index.ts`。

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080C_数据字典只读目录基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止新增或修改数据库 migration。
2. 禁止新增或修改 SQLAlchemy model。
3. 禁止新增或修改系统配置目录接口既有契约。
4. 禁止新增或修改系统健康诊断接口。
5. 禁止新增导出、导入、同步、缓存刷新、平台管理能力。
6. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
7. 禁止访问 ERPNext 或 `/api/resource`。
8. 禁止新增 ERPNext 写调用或外部写调用。
9. 禁止新增 direct `Session/query/select/execute` 数据库访问。
10. 禁止 outbox / worker / run-once / internal。
11. 禁止返回 token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload。
12. 禁止复用 `permission:*`、`dashboard:*`、`report:*`、`warehouse:*`、`inventory:*` 作为 `system:*` 授权通过条件。
13. 禁止修改 `src/router/index.ts`。
14. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
15. 禁止 commit / push / PR / tag / 生产发布。

## 5. 后端实现要求

### 5.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

- `SYSTEM_DICTIONARY_READ = "system:dictionary_read"`
- `ALL_SYSTEM_ACTIONS` 补充 `SYSTEM_DICTIONARY_READ`
- `MODULE_ACTION_REGISTRY["system"]` 补充 `SYSTEM_DICTIONARY_READ`

要求：

1. `System Manager` 必须获得 `system:dictionary_read`。
2. `Viewer` 默认不得获得 `system:dictionary_read`。
3. 不得注册 `system:dictionary_write`、`system:diagnostic`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 为本任务开放能力；这些动作在本阶段只允许出现在测试或文档负向断言中。
4. 不得改变既有 `system:read`、`system:config_read` 与 080B 契约语义。

### 5.2 只读接口

在 `app/routers/system_management.py` 中新增路由：

```text
GET /api/system/dictionaries/catalog
```

必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口先校验 `system:read`。
2. 再校验 `system:dictionary_read`，不得只校验其中一个动作。
3. 返回统一信封 `{code,message,data}`。
4. 只读取本地静态数据字典目录元数据。
5. 不读取业务数据库。
6. 不访问 ERPNext。
7. 不写安全审计或操作审计以外的业务事实；本任务不要求新增操作审计写入。
8. 非 `system:*` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 5.3 查询参数

允许以下只读过滤参数：

- `dict_type`：可选，按字典类型过滤。
- `status`：可选，按状态过滤。
- `source`：可选，按来源过滤。

要求：

1. `status` 若不在白名单内（建议 `active / inactive / deprecated`）必须返回 `400 / INVALID_QUERY_PARAMETER`，不得静默忽略。
2. 未知 `dict_type/source` 可以返回空列表，但不能返回错误敏感信息。
3. 不得支持 `raw_value`、`value`、`secret`、`token` 等参数。

### 5.4 响应字段

成功响应至少包含：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "items": [
      {
        "dict_type": "system_region",
        "dict_code": "CN-ZJ-HZ",
        "dict_name": "杭州",
        "status": "active",
        "source": "static_registry",
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

`system_dictionary_catalog_service.py` 中至少提供 6 条本地静态数据字典元数据，覆盖：

1. 至少 3 个不同 `dict_type`。
2. 至少 2 个不同 `source`。
3. `status` 至少覆盖 `active` 与 `inactive`。
4. 每条记录必须包含 `dict_type / dict_code / dict_name / status / source / updated_at`。
5. 不得包含字典真实业务 payload、凭据、敏感值。

## 6. 前端实现要求

### 6.1 API

在 `src/api/system_management.ts` 中新增：

- `fetchSystemDictionaryCatalog(...)`
- 对应 query/data/item TypeScript 类型

要求：

1. 必须复用统一 `request` client。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 只实现 GET `/api/system/dictionaries/catalog`。
5. 不实现字典写入、诊断、导出、导入、同步、缓存刷新、平台管理。

### 6.2 页面

修改 `src/views/system/SystemManagement.vue`：

1. 复用现有 `/system/management` 页面。
2. 在现有“系统配置目录（只读）”之外，追加“数据字典目录（只读）”区域或 tabs。
3. 无 `system:read` 或无 `system:dictionary_read` 时不得请求字典接口，应显示无权限提示。
4. 字典区域只展示 `dict_type / dict_code / dict_name / status / source / updated_at`。
5. 不展示或启用任何创建、编辑、删除、审批、回滚、导入、导出、诊断、同步、缓存刷新、平台管理按钮。
6. 不得影响 `TASK-080B` 已通过的系统配置目录查询行为。

## 7. 测试要求

新增或补充测试必须覆盖：

1. `system:dictionary_read` 已注册到 `MODULE_ACTION_REGISTRY["system"]`。
2. `System Manager` 具备 `system:dictionary_read`。
3. `Viewer` 不具备 `system:dictionary_read`。
4. `GET /api/system/dictionaries/catalog` 需要 `system:read`。
5. `GET /api/system/dictionaries/catalog` 需要 `system:dictionary_read`。
6. 只有 `permission:read`、`dashboard:read`、`report:read`、`warehouse:read`、`inventory:read` 的用户访问返回 403。
7. `dict_type/status/source` 过滤有效；非法 `status` 返回 400。
8. 响应字段不包含 `value/raw_value/password/token/authorization/cookie/dsn/database_url`。
9. 路由文件中不存在 `@router.post/put/patch/delete`。
10. system management 文件中不存在 direct DB query/execute、ERPNext 访问、outbox/worker/run-once/internal。
11. 前端 API 只使用统一 `request`，无裸 `fetch/axios`。
12. 前端 typecheck 通过。
13. `TASK-080B` 既有配置目录接口与页面功能不回退。

## 8. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_system_config_catalog_readonly.py tests/test_system_dictionary_catalog_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/system_management.py app/services/system_dictionary_catalog_service.py app/schemas/system_management.py
rg -n "@router\.(post|put|patch|delete)" app/routers/system_management.py || true
rg -n "Session\(|\.query\(|select\(|execute\(|session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(" app/routers/system_management.py app/services/system_dictionary_catalog_service.py app/schemas/system_management.py || true
rg -n "requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/system_management.py app/services/system_dictionary_catalog_service.py app/schemas/system_management.py || true
rg -n "outbox|worker|run-once|internal|diagnostic|cache_refresh|sync|import|export|platform_manage" app/routers/system_management.py app/services/system_dictionary_catalog_service.py app/schemas/system_management.py || true
rg -n "value|raw_value|secret_value|password|token|Authorization|authorization|Cookie|cookie|DSN|dsn|DATABASE_URL|database_url" app/routers/system_management.py app/services/system_dictionary_catalog_service.py app/schemas/system_management.py tests/test_system_dictionary_catalog_readonly.py || true
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
```

说明：敏感字段扫描若命中测试中的负向断言或字段禁止清单，必须在回交中解释；实现响应不得返回这些字段。

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource|diagnostic|cache_refresh|sync|import|export|platform_manage|submit" src/api/system_management.ts src/views/system/SystemManagement.vue || true
```

在 `/Users/hh/Desktop/领意服装管理系统` 执行：

```bash
git diff --check -- \
  07_后端/lingyi_service/app/core/permissions.py \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/app/routers/system_management.py \
  07_后端/lingyi_service/app/schemas/system_management.py \
  07_后端/lingyi_service/app/services/system_dictionary_catalog_service.py \
  07_后端/lingyi_service/tests/test_system_dictionary_catalog_readonly.py \
  07_后端/lingyi_service/tests/test_permissions_registry.py \
  06_前端/lingyi-pc/src/api/system_management.ts \
  06_前端/lingyi-pc/src/views/system/SystemManagement.vue \
  03_需求与设计/02_开发计划/TASK-080C_数据字典只读目录基线_工程任务单.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

## 9. 回交格式

B 完成后按以下格式回交：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080C
ROLE: B Engineer

CHANGED_FILES:
- 列出真实改动文件绝对路径

EVIDENCE:
- 说明 system:dictionary_read 注册与权限矩阵结果
- 说明 GET /api/system/dictionaries/catalog 只读实现与字段白名单
- 说明前端 /system/management 复用页面追加字典目录区域
- 说明未开放字典写入、诊断、导出、导入、同步、缓存刷新、平台管理、写路由
- 说明 TASK-080B 既有系统配置目录功能未回退

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 后端只读/敏感字段/越界扫描结果
- 前端 forbidden 扫描结果
- 禁改目录 diff 结果
- git diff --check 结果

BLOCKERS:
- 无 / 或列明阻塞

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

满足以下条件才算完成：

1. `system:dictionary_read` 注册完成且测试覆盖。
2. `/api/system/dictionaries/catalog` 只读接口可用，权限 fail closed。
3. 响应不包含任何真实敏感值或敏感字段。
4. `/system/management` 页面已追加数据字典只读区域，且不新增路由。
5. `TASK-080B` 既有系统配置目录功能不回退。
6. 必跑验证全部执行并记录结果。
7. 禁改目录无 diff。
8. 未执行 commit / push / PR / tag / 生产发布。
