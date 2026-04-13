# TASK-001D ERPNext User Permission 查询失败 Fail Closed 整改任务单

- 任务编号：TASK-001D
- 模块：BOM 管理 / 权限服务
- 优先级：P0
- 预计工时：1 天
- 更新时间：2026-04-12 10:22 CST
- 作者：技术架构师
- 审计来源：审计意见书第 7 份，ERPNext User Permission 查询失败时 fail open

════════════════════════════════════════════════════════════════════

【任务目标】

修复 ERPNext User Permission 查询失败时返回空列表导致放行的问题，将权限来源不可用统一改为 fail closed，明确区分“ERPNext 明确无 User Permission 限制”和“ERPNext 权限查询失败”。

════════════════════════════════════════════════════════════════════

【问题背景】

当前 `get_user_permissions()` 在 ERPNext 权限查询失败时返回 `[]`。

后续资源级权限判断会把 `[]` 理解成“该用户没有 Item 限制”，最终导致：只要用户有 `bom:read` 动作权限，即使 ERPNext User Permission 查询失败，也可能访问全部 BOM。

这是权限系统的高危 fail open 问题，必须改为 fail closed。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py（如已有统一异常文件则修改已有文件）

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_service.py

════════════════════════════════════════════════════════════════════

【整改要求】

1. 新增权限来源不可用异常。

建议异常名：

- PermissionSourceUnavailable

建议错误码：

- PERMISSION_SOURCE_UNAVAILABLE

建议 HTTP 状态：

- 503 Service Unavailable

要求：

- 该异常不得被转换成空权限列表。
- 该异常返回时不得包含任何 BOM 明细、工价、用料、展开结果数据。

2. `get_user_permissions()` 禁止在异常时返回 `[]`。

必须改成以下语义：

- ERPNext 查询成功且返回 0 条 User Permission：表示“明确无 User Permission 限制”。
- ERPNext 查询成功且返回 N 条 User Permission：表示“按返回记录限制资源范围”。
- ERPNext 查询失败、超时、数据库异常、REST API 异常、返回结构异常：必须抛出 PermissionSourceUnavailable。

3. 权限结果必须使用结构化返回，禁止继续用裸 `list` 表达权限状态。

建议结构：

```python
class UserPermissionResult:
    source_available: bool
    unrestricted: bool
    allowed_items: set[str]
    allowed_companies: set[str]
```

语义要求：

- `source_available=True and unrestricted=True`：ERPNext 明确查询成功，且无 User Permission 限制。
- `source_available=True and unrestricted=False`：ERPNext 明确查询成功，且存在资源限制。
- `source_available=False`：不允许继续业务查询，必须 fail closed。

4. BOM 列表接口必须继承 fail closed。

接口：

- GET /api/bom/

要求：

- 如果 ERPNext User Permission 查询失败，直接返回 503 + PERMISSION_SOURCE_UNAVAILABLE。
- 不允许降级为返回全部 BOM。
- 不允许降级为只按角色动作权限过滤。
- 不允许返回空列表伪装成功。

5. BOM 详情接口必须继承 fail closed。

接口：

- GET /api/bom/{bom_id}

要求：

- 如果 ERPNext User Permission 查询失败，直接返回 503 + PERMISSION_SOURCE_UNAVAILABLE。
- 不允许返回 BOM 详情。
- 不允许继续执行 BOM 明细查询。

6. BOM 展开接口必须继承 fail closed。

接口：

- POST /api/bom/{bom_id}/explode

要求：

- 如果 ERPNext User Permission 查询失败，直接返回 503 + PERMISSION_SOURCE_UNAVAILABLE。
- 不允许返回 material_requirements。
- 不允许返回 operation_costs。
- 不允许返回 total_material_qty / total_operation_cost。

7. 权限动作接口也必须继承 fail closed。

接口：

- GET /api/auth/actions?module=bom

要求：

- 如果生产环境使用 ERPNext 作为权限来源，而 ERPNext 权限查询失败，必须返回 503 + PERMISSION_SOURCE_UNAVAILABLE。
- 不允许返回静态兜底权限。
- 不允许返回全部按钮权限。

8. 日志要求。

当 ERPNext 权限来源不可用时，必须记录服务端错误日志，字段至少包含：

- request_id
- user
- permission_source
- action
- resource_type
- resource_id
- exception_type
- exception_message
- created_at

日志中禁止记录完整 Token、密码、Cookie。

════════════════════════════════════════════════════════════════════

【业务规则】

1. 权限系统默认安全策略：权限来源不可用时拒绝访问，而不是放行。

2. “无 User Permission 限制”必须以 ERPNext 查询成功为前提。

3. 空列表 `[]` 只能表示 ERPNext 查询成功且明确没有限制，不能表示查询失败。

4. BOM 读权限由两层组成：

- 动作权限：用户必须具备 `bom:read`
- 资源权限：用户必须有权访问该 BOM 对应 `item_code`

5. 任何一层权限状态不可确认，都必须拒绝返回敏感数据。

════════════════════════════════════════════════════════════════════

【验收标准】

□ 模拟 ERPNext User Permission 查询抛异常时，GET /api/bom/ 返回 503，code = PERMISSION_SOURCE_UNAVAILABLE。

□ 模拟 ERPNext User Permission 查询抛异常时，GET /api/bom/{bom_id} 返回 503，code = PERMISSION_SOURCE_UNAVAILABLE。

□ 模拟 ERPNext User Permission 查询抛异常时，POST /api/bom/{bom_id}/explode 返回 503，code = PERMISSION_SOURCE_UNAVAILABLE。

□ 模拟 ERPNext User Permission 查询抛异常时，GET /api/auth/actions?module=bom 不返回静态兜底的全部 BOM 权限。

□ ERPNext 查询成功且返回 0 条 User Permission 时，有 `bom:read` 的用户可以正常访问 BOM 列表。

□ ERPNext 查询成功且返回指定 Item 限制时，BOM 列表只返回允许 item_code 对应的 BOM。

□ ERPNext 查询成功且返回指定 Item 限制时，访问未授权 item_code 的 BOM 详情返回 403，code = AUTH_FORBIDDEN。

□ ERPNext 查询成功且返回指定 Item 限制时，对未授权 item_code 执行 BOM 展开返回 403，code = AUTH_FORBIDDEN。

□ 代码中不存在 `except Exception: return []` 形式的权限查询兜底。

□ 使用 rg "return \[\]" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services 检查，不存在用于掩盖 ERPNext 权限查询失败的空列表返回。

□ 权限来源不可用时，服务端日志记录 request_id、user、permission_source、action、exception_type。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止 ERPNext 权限查询失败时返回 `[]`。

2. 禁止 ERPNext 权限查询失败时当作“无权限限制”。

3. 禁止用静态角色权限兜底生产环境 ERPNext 权限失败。

4. 禁止返回空列表伪装成功。

5. 禁止在权限异常时返回 BOM 明细、工价、损耗率、展开结果。

6. 禁止吞掉异常不打日志。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001D 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- get_user_permissions 查询失败已改为抛出 PermissionSourceUnavailable
- 已区分“ERPNext 查询成功但无限制”和“ERPNext 查询失败”
- BOM 列表、详情、展开接口已继承 fail closed
- /api/auth/actions 已继承 fail closed

自测结果：
- ERPNext 权限查询失败访问 GET /api/bom/：通过 / 不通过
- ERPNext 权限查询失败访问 GET /api/bom/{bom_id}：通过 / 不通过
- ERPNext 权限查询失败访问 POST /api/bom/{bom_id}/explode：通过 / 不通过
- ERPNext 查询成功返回 0 条限制：通过 / 不通过
- ERPNext 查询成功返回 Item 限制：通过 / 不通过
- rg 检查不存在 except 后 return []：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
