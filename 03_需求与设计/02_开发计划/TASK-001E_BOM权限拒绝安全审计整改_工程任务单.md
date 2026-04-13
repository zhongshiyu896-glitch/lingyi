# TASK-001E BOM 权限拒绝安全审计整改任务单

- 任务编号：TASK-001E
- 模块：BOM 管理 / 权限服务 / 安全审计
- 优先级：P0
- 预计工时：1 天
- 更新时间：2026-04-12 10:35 CST
- 作者：技术架构师
- 审计来源：审计意见书第 8 份，401/403 权限拒绝未形成安全审计闭环

════════════════════════════════════════════════════════════════════

【任务目标】

补齐 BOM 模块 401、403、权限来源不可用等权限拒绝场景的安全审计日志或持久化审计记录，确保越权尝试可追踪、可复查、可统计。

════════════════════════════════════════════════════════════════════

【问题背景】

当前 BOM 权限拒绝只返回客户端错误，未形成审计闭环。

这会导致以下问题：

1. 无法追踪谁尝试访问 BOM 敏感数据。
2. 无法统计连续越权访问、撞库式探测、异常账号行为。
3. 审计复查无法确认权限拒绝是否发生过、拒绝原因是什么。
4. 生产环境无法支撑安全告警和追责。

BOM 用料、工价、损耗率、展开结果属于敏感经营数据，所有权限拒绝必须留痕。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/auth.py

数据库迁移新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/[新增安全审计表迁移].py

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_permissions.py

依赖清单新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements.txt
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements-dev.txt

如项目实际使用 pyproject.toml，则改对应文件，不重复维护两套依赖。

════════════════════════════════════════════════════════════════════

【数据库表设计】

优先使用独立安全审计表，不建议混入业务操作审计表。

新增表：ly_schema.ly_security_audit_log

用途：记录认证失败、权限拒绝、权限来源不可用、资源级越权等安全事件。

字段要求：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| event_type | varchar(64) | 是 | AUTH_UNAUTHORIZED / AUTH_FORBIDDEN / PERMISSION_SOURCE_UNAVAILABLE |
| module | varchar(64) | 是 | bom / auth |
| action | varchar(64) | 否 | bom:read / bom:create / bom:update / bom:publish 等 |
| resource_type | varchar(64) | 否 | BOM / Item / AuthAction |
| resource_id | varchar(140) | 否 | BOM id 或业务资源 id |
| resource_no | varchar(140) | 否 | bom_no / item_code |
| user_id | varchar(140) | 否 | 已识别用户；未登录可为空 |
| user_roles | jsonb | 否 | 当前用户角色 |
| permission_source | varchar(32) | 否 | static / erpnext |
| deny_reason | varchar(255) | 是 | 拒绝原因 |
| request_method | varchar(16) | 是 | GET / POST / PUT |
| request_path | varchar(255) | 是 | 请求路径 |
| request_id | varchar(64) | 是 | 请求追踪 id |
| ip_address | varchar(64) | 否 | 客户端 IP |
| user_agent | text | 否 | User-Agent |
| created_at | timestamptz | 是 | 创建时间 |

索引要求：

- idx_ly_security_audit_log_created_at(created_at)
- idx_ly_security_audit_log_user_id(user_id)
- idx_ly_security_audit_log_event_type(event_type)
- idx_ly_security_audit_log_module_action(module, action)
- idx_ly_security_audit_log_resource(resource_type, resource_id)
- idx_ly_security_audit_log_request_id(request_id)

════════════════════════════════════════════════════════════════════

【必须记录的事件】

1. 未登录访问 BOM 接口。

事件类型：AUTH_UNAUTHORIZED

覆盖接口：

- GET /api/bom/
- GET /api/bom/{bom_id}
- POST /api/bom/{bom_id}/explode
- POST /api/bom/
- PUT /api/bom/{bom_id}
- POST /api/bom/{bom_id}/activate
- POST /api/bom/{bom_id}/deactivate
- POST /api/bom/{bom_id}/set-default

2. 已登录但缺少动作权限。

事件类型：AUTH_FORBIDDEN

覆盖权限动作：

- bom:read
- bom:create
- bom:update
- bom:publish
- bom:deactivate
- bom:set_default

3. 已登录且有动作权限，但无资源权限。

事件类型：AUTH_FORBIDDEN

覆盖资源：

- BOM item_code 权限不足
- Company 权限不足
- User Permission 不允许访问目标资源

4. ERPNext 权限来源不可用。

事件类型：PERMISSION_SOURCE_UNAVAILABLE

覆盖场景：

- ERPNext User Permission 查询失败
- ERPNext REST API 超时
- ERPNext 数据库查询异常
- ERPNext 返回结构异常

5. 权限动作接口拒绝。

覆盖接口：

- GET /api/auth/actions?module=bom

要求：

- 权限来源不可用时必须记录 PERMISSION_SOURCE_UNAVAILABLE。
- 未登录或无权限时必须记录对应安全审计事件。

════════════════════════════════════════════════════════════════════

【业务规则】

1. 权限拒绝审计不得影响权限拒绝本身。

- 如果业务判断应拒绝，则必须拒绝。
- 如果审计写入失败，必须至少写入服务端 error 日志。
- 对 401/403 场景，审计写入失败不得改成放行。

2. 权限来源不可用场景必须 fail closed。

- 返回 503 + PERMISSION_SOURCE_UNAVAILABLE。
- 同时写入 ly_security_audit_log。

3. 401 未登录场景允许 user_id 为空，但必须记录 request_id、ip_address、user_agent、request_path。

4. 403 已登录但无权限场景必须记录 user_id、action、deny_reason。

5. 资源级 403 必须记录 resource_type、resource_id、resource_no。

6. 日志禁止记录敏感凭证。

禁止写入：

- Authorization 完整 Token
- Cookie 完整内容
- 密码
- ERPNext API Secret

7. 审计服务必须封装成统一函数。

建议函数：

- record_security_audit(event_type, module, action, resource_type, resource_id, resource_no, user, deny_reason, request)

8. 权限校验函数必须在抛出 AUTH_UNAUTHORIZED / AUTH_FORBIDDEN / PERMISSION_SOURCE_UNAVAILABLE 前调用审计服务。

════════════════════════════════════════════════════════════════════

【接口影响】

接口响应格式保持不变。

401 示例：

{
  "code": "AUTH_UNAUTHORIZED",
  "message": "未登录或登录已过期",
  "data": {}
}

403 示例：

{
  "code": "AUTH_FORBIDDEN",
  "message": "无权限访问该资源",
  "data": {}
}

503 示例：

{
  "code": "PERMISSION_SOURCE_UNAVAILABLE",
  "message": "权限来源暂时不可用",
  "data": {}
}

禁止为了审计改接口路径、改成功响应结构。

════════════════════════════════════════════════════════════════════

【测试与依赖要求】

1. 必须补齐后端依赖清单，使审计官可以复现测试。

如使用 requirements：

- requirements.txt 包含运行依赖 fastapi、sqlalchemy、pydantic 等。
- requirements-dev.txt 包含 pytest、pytest-asyncio、httpx 等测试依赖。

如使用 pyproject.toml：

- 必须包含运行依赖和测试依赖分组。

2. 必须提供可执行测试入口。

至少支持以下命令之一：

- python -m pytest
- python -m unittest

3. 测试必须覆盖 401、403、503 三类安全审计事件。

════════════════════════════════════════════════════════════════════

【验收标准】

□ 未登录访问 GET /api/bom/ 返回 401，并新增 1 条 ly_security_audit_log，event_type = AUTH_UNAUTHORIZED。

□ 无 bom:read 权限访问 GET /api/bom/ 返回 403，并新增 1 条 ly_security_audit_log，event_type = AUTH_FORBIDDEN，action = bom:read。

□ 无 item_code 资源权限访问 GET /api/bom/{bom_id} 返回 403，并新增 1 条 ly_security_audit_log，resource_no = 对应 item_code。

□ 无 item_code 资源权限调用 POST /api/bom/{bom_id}/explode 返回 403，并新增 1 条 ly_security_audit_log，resource_type = BOM。

□ ERPNext User Permission 查询失败时，GET /api/bom/ 返回 503，并新增 1 条 ly_security_audit_log，event_type = PERMISSION_SOURCE_UNAVAILABLE。

□ ERPNext User Permission 查询失败时，GET /api/auth/actions?module=bom 返回 503，并新增 1 条 ly_security_audit_log。

□ 审计记录包含 request_id、request_method、request_path、ip_address、user_agent、created_at。

□ 403 审计记录包含 user_id、action、deny_reason。

□ 资源级 403 审计记录包含 resource_type、resource_id 或 resource_no。

□ 审计日志中不包含完整 Authorization Token、Cookie、密码、ERPNext API Secret。

□ python -m py_compile 检查通过。

□ python -m pytest 或 python -m unittest 至少一个测试入口可执行。

□ 审计官可根据依赖清单安装依赖并复现权限审计测试。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止只打印 console，不落库或不进入统一服务端日志。

2. 禁止吞掉 401/403，不记录审计事件。

3. 禁止审计写入失败后放行请求。

4. 禁止在审计日志中记录完整 Token、Cookie、密码。

5. 禁止为了审计修改 BOM 接口路径。

6. 禁止把 401/403 统一改成 500。

7. 禁止只覆盖写接口，不覆盖 BOM 读接口和展开接口。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001E 已完成。

已修改文件：
- [列出实际修改文件]

数据库变更：
- 已新增 / 未新增 ly_schema.ly_security_audit_log
- 已新增索引：[列出索引]

核心整改：
- 401 未登录已记录安全审计
- 403 动作权限拒绝已记录安全审计
- 403 资源级权限拒绝已记录安全审计
- 503 权限来源不可用已记录安全审计
- 权限审计日志不记录敏感凭证

自测结果：
- 未登录访问 GET /api/bom/ 产生 AUTH_UNAUTHORIZED 审计：通过 / 不通过
- 无 bom:read 访问 GET /api/bom/ 产生 AUTH_FORBIDDEN 审计：通过 / 不通过
- 无资源权限访问 GET /api/bom/{bom_id} 产生资源级 403 审计：通过 / 不通过
- ERPNext 权限源失败产生 PERMISSION_SOURCE_UNAVAILABLE 审计：通过 / 不通过
- python -m pytest 或 python -m unittest 可执行：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
