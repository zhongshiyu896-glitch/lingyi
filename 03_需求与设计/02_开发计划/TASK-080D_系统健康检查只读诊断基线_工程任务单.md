# TASK-080D 系统健康检查只读诊断基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-080D
- 任务名称：系统健康检查只读诊断基线
- 模块：系统管理 / 健康检查
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 08:14 CST+8
- 前置依赖：TASK-080C 数据字典只读目录基线审计通过（审计意见书第444份）
- 设计依据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- 当前定位：系统管理实现链路第三张任务，只建立系统健康检查只读诊断能力，不开放写入、导出、同步、缓存刷新、平台管理。

> 本任务单是 A -> B 执行指令，不是 B -> C 审计输入。未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

## 2. 任务目标

实现系统健康检查只读诊断基线：

1. 注册 `system:diagnostic`。
2. 新增 `GET /api/system/health/summary`。
3. 返回本地安全健康摘要，只允许 `module / status / check_name / check_result / generated_at`。
4. 复用现有 `/system/management` 页面，追加诊断摘要区域；不得新增新路由。
5. 诊断区域默认隐藏，无 `system:diagnostic` 时不得发请求。
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
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_health_summary_service.py`

说明：`TASK-080B`、`TASK-080C` 已通过的配置目录与数据字典目录契约不得回退；如需复用，只能并行扩展，不得改变既有接口语义。

### 3.3 后端测试

允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_system_health_summary_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 3.4 前端最小只读入口

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`

说明：必须复用现有 `/system/management` 页面；本任务禁止修改 `src/router/index.ts` 与 `src/stores/permission.ts`。

### 3.5 文档与日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-080D_系统健康检查只读诊断基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止新增或修改数据库 migration。
2. 禁止新增或修改 SQLAlchemy model。
3. 禁止新增或修改系统配置目录、数据字典目录既有契约。
4. 禁止新增导出、导入、同步、缓存刷新、平台管理能力。
5. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
6. 禁止访问 ERPNext 或 `/api/resource`。
7. 禁止新增 ERPNext 写调用或外部写调用。
8. 禁止新增 direct `Session/query/select/execute` 数据库访问。
9. 禁止 outbox / worker / run-once / internal。
10. 禁止返回 token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload。
11. 禁止复用 `permission:*`、`dashboard:*`、`report:*`、`warehouse:*`、`inventory:*` 作为 `system:*` 授权通过条件。
12. 禁止修改 `src/router/index.ts`。
13. 禁止修改 `src/stores/permission.ts`。
14. 禁止修改 `.github`、`.ci-reports`、`01_需求与资料`、`02_源码`、`03_环境与部署`、`04_测试与验收`、`05_交付物`。
15. 禁止 commit / push / PR / tag / 生产发布。

## 5. 后端实现要求

### 5.1 权限动作注册

在 `app/core/permissions.py` 中新增并注册：

- `SYSTEM_DIAGNOSTIC = "system:diagnostic"`
- `ALL_SYSTEM_ACTIONS` 补充 `SYSTEM_DIAGNOSTIC`
- `MODULE_ACTION_REGISTRY["system"]` 补充 `SYSTEM_DIAGNOSTIC`

要求：

1. `System Manager` 必须获得 `system:diagnostic`。
2. `Viewer` 默认不得获得 `system:diagnostic`。
3. `system:diagnostic` 必须视为高危诊断动作；后续前端默认隐藏。
4. 不得注册 `system:config_write`、`system:dictionary_write`、`system:platform_manage`、`system:cache_refresh`、`system:sync`、`system:import`、`system:export` 为本任务开放能力。
5. 不得改变既有 `system:read`、`system:config_read`、`system:dictionary_read` 与 080B/080C 契约语义。

### 5.2 只读接口

在 `app/routers/system_management.py` 中新增路由：

```text
GET /api/system/health/summary
```

必须：

1. 使用 `PermissionService.require_action(...)` 或等价公共权限入口先校验 `system:read`。
2. 再校验 `system:diagnostic`，不得只校验其中一个动作。
3. 返回统一信封 `{code,message,data}`。
4. 只读取本地安全健康摘要，不得访问业务数据库。
5. 不访问 ERPNext。
6. 不写安全审计或操作审计以外的业务事实；本任务不要求新增操作审计写入。
7. 非 `system:*` 用户返回 `403 / AUTH_FORBIDDEN` 或当前项目统一禁止错误码。

### 5.3 响应字段

成功响应只允许包含以下字段语义：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "items": [
      {
        "module": "system",
        "status": "ok",
        "check_name": "permission_source",
        "check_result": "static_or_erpnext_ready",
        "generated_at": "2026-04-21T00:00:00Z"
      }
    ],
    "total": 1,
    "generated_at": "2026-04-21T00:00:00Z"
  }
}
```

要求：

1. `check_result` 必须是安全摘要文本，不得包含凭据、连接串、原始命令输出或错误堆栈。
2. `status` 建议限定 `ok / warn / blocked`。
3. 至少提供 4 项本地安全检查。
4. 不得返回任何原始环境变量值。

### 5.4 本地安全检查最低覆盖

`system_health_summary_service.py` 至少覆盖：

1. `permission_source`：权限源配置是否处于允许状态。
2. `system_router_mapping`：`/api/system/configs/catalog`、`/api/system/dictionaries/catalog`、`/api/system/health/summary` 是否已纳入 main 映射。
3. `ui_route_present`：`/system/management` 前端入口是否存在。
4. `readonly_contract`：system management router 是否仅存在 GET 路由。

说明：只能输出安全摘要，例如 `mapped`、`present`、`readonly_get_only`、`source_ready`；不得输出原始配置值、绝对密钥内容、环境变量全文、shell 输出全文。

## 6. 前端实现要求

### 6.1 API

在 `src/api/system_management.ts` 中新增：

- `fetchSystemHealthSummary()`
- 对应 TypeScript 类型

要求：

1. 必须复用统一 `request` client。
2. 禁止裸 `fetch` / `axios`。
3. 禁止直连 `/api/resource`。
4. 只实现 GET `/api/system/health/summary`。
5. 不实现诊断写入、导出、同步、缓存刷新、平台管理。

### 6.2 页面

修改 `src/views/system/SystemManagement.vue`：

1. 复用现有 `/system/management` 页面。
2. 追加“系统健康诊断（只读）”区域。
3. 无 `system:read` 或无 `system:diagnostic` 时不得请求诊断接口。
4. 无 `system:diagnostic` 时，该区域默认隐藏或显示无权限提示，但不得触发请求。
5. 诊断区域只展示 `module / status / check_name / check_result / generated_at`。
6. 不展示任何写按钮、导出按钮、同步按钮、缓存刷新按钮、平台管理按钮。
7. 不得影响 `TASK-080B`、`TASK-080C` 已通过的配置目录与数据字典目录功能。

## 7. 测试要求

新增或补充测试必须覆盖：

1. `system:diagnostic` 已注册到 `MODULE_ACTION_REGISTRY["system"]`。
2. `System Manager` 具备 `system:diagnostic`。
3. `Viewer` 不具备 `system:diagnostic`。
4. `GET /api/system/health/summary` 需要 `system:read`。
5. `GET /api/system/health/summary` 需要 `system:diagnostic`。
6. 只有 `permission:read`、`dashboard:read`、`report:diagnostic`、`warehouse:diagnostic`、`inventory:read` 的用户访问返回 403。
7. 响应仅包含允许字段，不包含 token/Authorization/Cookie/password/secret/DSN/DATABASE_URL/raw headers/raw payload。
8. `status` 仅出现 `ok / warn / blocked`。
9. 路由文件中不存在 `@router.post/put/patch/delete`。
10. system management 文件中不存在 direct DB query/execute、ERPNext 访问、outbox/worker/run-once/internal。
11. 前端 API 只使用统一 `request`，无裸 `fetch/axios`。
12. 前端 typecheck 通过。
13. `TASK-080B`、`TASK-080C` 既有功能不回退。

## 8. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_system_config_catalog_readonly.py tests/test_system_dictionary_catalog_readonly.py tests/test_system_health_summary_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/system_management.py app/services/system_health_summary_service.py app/schemas/system_management.py
rg -n "@router\.(post|put|patch|delete)" app/routers/system_management.py || true
rg -n "Session\(|\.query\(|select\(|execute\(|session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(" app/routers/system_management.py app/services/system_health_summary_service.py app/schemas/system_management.py || true
rg -n "requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/system_management.py app/services/system_health_summary_service.py app/schemas/system_management.py || true
rg -n "outbox|worker|run-once|internal|cache_refresh|sync|import|export|platform_manage" app/routers/system_management.py app/services/system_health_summary_service.py app/schemas/system_management.py || true
rg -n "token|Authorization|authorization|Cookie|cookie|password|secret|DSN|dsn|DATABASE_URL|database_url|raw headers|raw payload" app/routers/system_management.py app/services/system_health_summary_service.py app/schemas/system_management.py tests/test_system_health_summary_readonly.py || true
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
```

说明：敏感字段扫描若命中测试负向断言、禁止清单或安全摘要字符串，需要在回交中解释；实现响应不得返回这些字段值。

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource|cache_refresh|sync|import|export|platform_manage|submit" src/api/system_management.ts src/views/system/SystemManagement.vue || true
```

在 `/Users/hh/Desktop/领意服装管理系统` 执行：

```bash
git diff --check -- \
  07_后端/lingyi_service/app/core/permissions.py \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/app/routers/system_management.py \
  07_后端/lingyi_service/app/schemas/system_management.py \
  07_后端/lingyi_service/app/services/system_health_summary_service.py \
  07_后端/lingyi_service/tests/test_system_health_summary_readonly.py \
  07_后端/lingyi_service/tests/test_permissions_registry.py \
  06_前端/lingyi-pc/src/api/system_management.ts \
  06_前端/lingyi-pc/src/views/system/SystemManagement.vue \
  03_需求与设计/02_开发计划/TASK-080D_系统健康检查只读诊断基线_工程任务单.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

## 9. 回交格式

B 完成后按以下格式回交：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080D
ROLE: B Engineer

CHANGED_FILES:
- 列出真实改动文件绝对路径

EVIDENCE:
- 说明 system:diagnostic 注册与权限矩阵结果
- 说明 GET /api/system/health/summary 只读实现与字段白名单
- 说明前端 /system/management 复用页面追加诊断摘要区域，且无权限不发请求
- 说明未开放写入、导出、同步、缓存刷新、平台管理、写路由
- 说明 TASK-080B、TASK-080C 既有功能未回退

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

1. `system:diagnostic` 注册完成且测试覆盖。
2. `/api/system/health/summary` 只读接口可用，权限 fail closed。
3. 响应不包含任何敏感字段或敏感值。
4. `/system/management` 页面已追加诊断摘要区域，且无权限时不发请求。
5. `TASK-080B`、`TASK-080C` 既有功能不回退。
6. 必跑验证全部执行并记录结果。
7. 禁改目录无 diff。
8. 未执行 commit / push / PR / tag / 生产发布。
