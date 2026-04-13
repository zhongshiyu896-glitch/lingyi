# TASK-001A BOM 鉴权、权限动作与敏感操作审计整改任务单

- 任务编号：TASK-001A
- 关联任务：TASK-001 BOM 管理
- 优先级：P0
- 预计工时：2-3 天
- 输出人：技术架构师
- 更新时间：2026-04-12 00:00 CST
- 项目根目录：`/Users/hh/Desktop/领意服装管理系统/`
- 当前状态：待工程师整改

## 一、任务目标

修复 BOM 写接口无鉴权、无权限动作校验、无真实操作者、无敏感操作审计的问题。

整改完成后，BOM 写接口必须：

1. 能解析真实当前用户。
2. 能按动作校验权限。
3. 不再使用 `operator="system"` 代表业务用户。
4. 发布、停用、设默认、创建、更新都写敏感操作审计日志。
5. 未登录返回 401，无权限返回 403。

## 二、涉及文件

新建：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_001a_create_operation_audit_log.py`

修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`

## 三、数据库表

新增表：`ly_schema.ly_operation_audit_log`

用途：记录敏感操作审计日志。

关键字段：

- `id`
- `module`
- `action`
- `operator`
- `operator_roles`
- `resource_type`
- `resource_id`
- `resource_no`
- `before_data`
- `after_data`
- `result`
- `error_code`
- `request_id`
- `ip_address`
- `user_agent`
- `created_at`

索引：

- `pk_ly_operation_audit_log`
- `idx_ly_operation_audit_module_action`
- `idx_ly_operation_audit_operator_time`
- `idx_ly_operation_audit_resource`
- `idx_ly_operation_audit_request_id`

字段要求：

1. `before_data` 和 `after_data` 使用 PostgreSQL `JSONB`。
2. `operator_roles` 使用 PostgreSQL `JSONB` 或文本 JSON。
3. `result` 枚举：`success`、`failed`。
4. 审计日志不得由前端直接写入。

## 四、当前用户解析

新增 `app/core/auth.py`。

必须提供：

1. `CurrentUser` 数据结构。

字段：

- `username`
- `roles`
- `is_service_account`
- `source`

2. `get_current_user()` FastAPI Depends。

解析规则：

1. 优先解析 ERPNext 登录态或 Token。
2. 必须通过 ERPNext API 校验用户真实性，不允许只信任前端传入的用户名。
3. 本地开发可支持 `X-LY-Dev-User`，但必须受环境变量 `LINGYI_ALLOW_DEV_AUTH=true` 控制。
4. 生产环境未登录或 Token 无效时，返回 HTTP 401，错误码 `AUTH_UNAUTHORIZED`。

禁止：

1. 禁止业务写接口默认使用 `system`。
2. 禁止从普通请求头直接信任 `username`。
3. 禁止前端传 `operator` 字段决定操作者。

## 五、权限动作定义

新增 `app/core/permissions.py`。

BOM 权限动作：

| 动作 | 权限码 | 适用接口 |
| --- | --- | --- |
| 创建 BOM | `bom:create` | `POST /api/bom/` |
| 更新 BOM | `bom:update` | `PUT /api/bom/{bom_id}` |
| 发布 BOM | `bom:publish` | `POST /api/bom/{bom_id}/activate` |
| 停用 BOM | `bom:deactivate` | `POST /api/bom/{bom_id}/deactivate` |
| 设置默认 BOM | `bom:set_default` | `POST /api/bom/{bom_id}/set-default` |

权限校验要求：

1. 每个写接口必须调用权限 guard。
2. 权限 guard 输入：`CurrentUser`、`action`、`resource`。
3. 权限 guard 输出：允许继续或抛出 HTTP 403。
4. 无权限返回：

```json
{
  "code": "AUTH_FORBIDDEN",
  "message": "无权执行该操作",
  "data": {}
}
```

5. 允许角色先用配置方式实现，后续再接 ERPNext `Role / User Permission`。
6. 后端权限校验必须强制执行，不能只靠前端按钮隐藏。

## 六、BOM Router 整改

修改 `/07_后端/lingyi_service/app/routers/bom.py`。

必须整改：

1. 所有写接口增加 `current_user: CurrentUser = Depends(get_current_user)`。
2. 所有写接口执行权限校验。
3. 所有写接口把 `operator=current_user.username` 传入 Service。
4. 删除所有业务路径中的 `operator="system"`。

接口整改明细：

1. `POST /api/bom/`

要求：

- Depends `get_current_user`
- 校验 `bom:create`
- `service.create_bom(..., operator=current_user.username)`
- 写审计日志 action=`bom:create`

2. `PUT /api/bom/{bom_id}`

要求：

- Depends `get_current_user`
- 校验 `bom:update`
- `service.update_bom_draft(..., operator=current_user.username)`
- 写审计日志 action=`bom:update`

3. `POST /api/bom/{bom_id}/activate`

要求：

- Depends `get_current_user`
- 校验 `bom:publish`
- `service.activate(..., operator=current_user.username)`
- 写审计日志 action=`bom:publish`

4. `POST /api/bom/{bom_id}/deactivate`

要求：

- Depends `get_current_user`
- 校验 `bom:deactivate`
- `service.deactivate(..., operator=current_user.username)`
- 写审计日志 action=`bom:deactivate`

5. `POST /api/bom/{bom_id}/set-default`

要求：

- Depends `get_current_user`
- 校验 `bom:set_default`
- `service.set_default(..., operator=current_user.username)`
- 写审计日志 action=`bom:set_default`

GET 接口要求：

1. `GET /api/bom/` 可以先不强制鉴权，但建议接入只读权限 `bom:read`。
2. `GET /api/bom/{bom_id}` 可以先不强制鉴权，但建议接入只读权限 `bom:read`。

## 七、BOM Service 整改

修改 `/07_后端/lingyi_service/app/services/bom_service.py`。

必须整改：

1. `set_default(self, bom_id: int)` 改为 `set_default(self, bom_id: int, operator: str)`。
2. `activate(self, bom_id: int)` 改为 `activate(self, bom_id: int, operator: str)`。
3. `deactivate(self, bom_id: int, reason: str)` 改为 `deactivate(self, bom_id: int, reason: str, operator: str)`。
4. 发布、停用、设默认时必须写 `updated_by=operator`。
5. 创建和更新继续使用真实 `operator`。
6. Service 不允许自行使用 `"system"` 作为业务用户。

## 八、审计日志要求

新增 `/07_后端/lingyi_service/app/services/audit_service.py`。

必须提供：

1. `record_success(...)`
2. `record_failure(...)`
3. `snapshot_resource(...)`

审计动作范围：

| 动作 | 是否必须审计 |
| --- | --- |
| BOM 创建 | 是 |
| BOM 更新 | 是 |
| BOM 发布 | 是 |
| BOM 停用 | 是 |
| BOM 设置默认 | 是 |
| BOM 查询 | 否 |
| BOM 展开 | 否 |

审计内容：

1. 操作者 username。
2. 操作者 roles。
3. 操作动作 action。
4. 操作对象 resource_type=`bom`。
5. 操作对象 id/no。
6. 操作前 before_data。
7. 操作后 after_data。
8. 操作结果 success/failed。
9. 失败错误码。
10. request_id。
11. ip_address。
12. user_agent。

事务要求：

1. 业务写入成功但审计日志写入失败时，整个操作必须回滚。
2. 业务写入失败时，也要尽量记录失败审计；如果失败发生在数据库不可用场景，可只返回错误。

## 九、前端要求

修改 `/06_前端/lingyi-pc/src/api/bom.ts`。

要求：

1. 所有 BOM 写接口带上登录态或 token。
2. 前端不传 `operator`。
3. 遇到 401 跳转登录或提示登录失效。
4. 遇到 403 显示“无权执行该操作”。
5. 不通过隐藏按钮替代后端鉴权。

## 十、统一错误码

必须新增或使用以下错误码：

| 错误码 | HTTP 状态 | 含义 |
| --- | --- | --- |
| `AUTH_UNAUTHORIZED` | 401 | 未登录或 Token 无效 |
| `AUTH_FORBIDDEN` | 403 | 无权执行该动作 |
| `AUDIT_WRITE_FAILED` | 500 | 审计日志写入失败 |
| `BOM_NOT_FOUND` | 404 | BOM 不存在 |
| `BOM_STATUS_INVALID` | 409 | 当前状态不允许操作 |

## 十一、验收标准

必须全部满足：

□ `POST /api/bom/` 不带登录态时返回 401，错误码 `AUTH_UNAUTHORIZED`。

□ 无 `bom:create` 权限的用户调用 `POST /api/bom/` 返回 403，错误码 `AUTH_FORBIDDEN`。

□ 有 `bom:create` 权限的用户调用 `POST /api/bom/` 成功后，`ly_apparel_bom.created_by` 等于真实用户名。

□ `PUT /api/bom/{bom_id}` 成功后，`ly_apparel_bom.updated_by` 等于真实用户名。

□ `POST /api/bom/{bom_id}/activate` 成功后，审计日志新增 `action=bom:publish` 记录。

□ `POST /api/bom/{bom_id}/deactivate` 成功后，审计日志新增 `action=bom:deactivate` 记录。

□ `POST /api/bom/{bom_id}/set-default` 成功后，审计日志新增 `action=bom:set_default` 记录。

□ BOM router 中不再出现 `operator="system"`。

□ BOM service 中不再硬编码业务操作者为 `system`。

□ 前端调用 BOM 写接口时不传 `operator`。

□ 审计日志包含 operator、action、resource_type、resource_id、result、created_at。

□ 审计日志写入失败时，业务写操作回滚。

## 十二、自测命令建议

工程师完成后执行：

```bash
rg 'operator="system"|operator=.system.|operator = "system"' /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app
```

预期：BOM 业务路径无结果。

```bash
rg 'bom:create|bom:update|bom:publish|bom:deactivate|bom:set_default' /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app
```

预期：能看到权限动作定义和 router 校验。

## 十三、工程师完成后回报格式

```text
TASK-001A BOM 鉴权权限审计整改完成

后端文件：
- ...

前端文件：
- ...

迁移文件：
- ...

自测结果：
- 无登录态 POST /api/bom/ 返回 401：通过 / 失败
- 无权限 POST /api/bom/ 返回 403：通过 / 失败
- 有权限 POST /api/bom/ 写入 created_by 真实用户：通过 / 失败
- activate 写入 bom:publish 审计日志：通过 / 失败
- deactivate 写入 bom:deactivate 审计日志：通过 / 失败
- set-default 写入 bom:set_default 审计日志：通过 / 失败
- rg operator="system"：通过 / 失败

遗留问题：
- 无 / ...
```
