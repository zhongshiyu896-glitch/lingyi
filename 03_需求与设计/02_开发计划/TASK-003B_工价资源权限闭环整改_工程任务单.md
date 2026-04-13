# TASK-003B 工价资源权限闭环整改任务单

- 任务编号：TASK-003B
- 模块：工票/车间管理 / 工价档案 / 资源级权限
- 优先级：P0（审计阻断）
- 预计工时：1 天
- 更新时间：2026-04-12 13:52 CST
- 作者：技术架构师
- 审计来源：审计意见书第 15 份，工价资源权限未闭环

════════════════════════════════════════════════════════════════════

【任务目标】

修复工价档案的资源级权限漏洞：`GET /api/workshop/wage-rates` 必须按 `item_code/company` 做资源过滤；工价创建和停用必须完成 `item_code -> company` 解析；只有 Company 权限但没有 Item 权限的用户，不允许读取或维护指定款式工价。

════════════════════════════════════════════════════════════════════

【一、问题背景】

审计探针已复现：

1. 仅授权 `ITEM-B` 的用户仍能读取 `ITEM-A` 工价。
2. 只有 Company 权限、没有 Item 权限的用户，也能创建指定 `ITEM-Z` 的工价。

工价属于工资/成本敏感数据，不能只按 `workshop:wage_rate_read` 或 `workshop:wage_rate_manage` 动作权限放行。

必须补齐：

1. 工价读取资源过滤。
2. 工价写入资源校验。
3. `item_code -> company` 解析。
4. Company-only 场景 fail closed。
5. 通用工价的全局权限边界。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py

数据库迁移新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003b_wage_rate_resource_scope.py

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage_permissions.py（建议新增）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py

前端修改：

- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts

════════════════════════════════════════════════════════════════════

【三、数据库整改要求】

表：`ly_schema.ly_operation_wage_rate`

必须新增或确认存在字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| company | varchar(140) | 否 | ERPNext Company.name，用于 Company 资源权限过滤 |
| is_global | boolean | 是 | 是否通用工价，item_code 为空时为 true |

字段规则：

1. `item_code` 不为空时，表示款式专属工价。
2. `item_code` 为空时，表示通用工价，`is_global=true`。
3. 款式专属工价必须能确定 `company`。
4. 如果项目暂不支持跨公司共享款式工价，则款式专属工价 `company` 必填。
5. 通用工价必须具备 `workshop:wage_rate_manage_all` 才能创建或停用。

索引要求：

- idx_ly_operation_wage_rate_company_item_process(company, item_code, process_name)
- idx_ly_operation_wage_rate_company_status(company, status)
- idx_ly_operation_wage_rate_global(is_global, status)

区间约束：

同一 `company + item_code + process_name` 的 active 生效区间不得重叠。

通用工价按：

- company + process_name + is_global=true

检查 active 生效区间不得重叠。

════════════════════════════════════════════════════════════════════

【四、资源识别规则】

1. 新增或确认统一函数：

- resolve_wage_rate_resource(item_code: str | None, company: str | None) -> WageRateResource

返回结构建议：

- item_code
- company
- is_global
- resolution_status

2. item_code 不为空时：

必须校验 ERPNext Item 存在且未禁用。

3. item_code -> company 解析顺序：

优先级 1：请求明确传入 company 时，校验 company 存在，并作为目标 company。

优先级 2：如果请求未传 company，则尝试从 ERPNext Item Default / 项目已约定的 Item 公司映射中解析 company。

优先级 3：如果系统只有一个启用 Company，可使用该 Company。

4. 无法确定 company 时：

- 返回 400
- code = WORKSHOP_WAGE_RATE_COMPANY_REQUIRED
- 禁止写入工价

5. item_code 对应多个 company 且请求未指定 company 时：

- 返回 400
- code = WORKSHOP_WAGE_RATE_COMPANY_REQUIRED
- 禁止写入工价

6. Company-only 不等于 Item 权限。

用户只有 Company 权限、没有目标 Item 权限时：

- 不允许读取该 item_code 的工价。
- 不允许创建该 item_code 的工价。
- 不允许停用该 item_code 的工价。

7. 用户必须同时满足：

- 动作权限：`workshop:wage_rate_read` 或 `workshop:wage_rate_manage`
- Item 资源权限：目标 item_code 在用户允许范围内
- Company 资源权限：目标 company 在用户允许范围内；如用户没有 Company 限制，以 ERPNext 明确返回的 unrestricted 为准

8. 权限来源不可用时：

- 返回 503
- code = PERMISSION_SOURCE_UNAVAILABLE
- 禁止 fail open

════════════════════════════════════════════════════════════════════

【五、GET /api/workshop/wage-rates 读取过滤规则】

接口：

- GET /api/workshop/wage-rates

必须执行：

1. 校验当前用户登录态。
2. 校验 `workshop:wage_rate_read` 动作权限。
3. 获取 ERPNext User Permission 中的 Item / Company 限制。
4. 在数据库查询层过滤工价数据。
5. 不允许先查全量再由前端过滤。
6. 不允许先返回全量再靠前端隐藏。

过滤规则：

1. 用户有明确 Item 限制时：

- 只返回 `item_code in allowed_items` 的款式专属工价。
- 如同时有 Company 限制，还必须 `company in allowed_companies`。

2. 用户没有 Item 限制，但有 Company 限制时：

- 默认不返回任何款式专属工价，除非 ERPNext 明确返回该用户对 Item 不受限。
- Company-only 不能推导出 Item 权限。

3. 用户对 Item 明确 unrestricted，且 Company 有限制时：

- 返回 `company in allowed_companies` 的款式专属工价。

4. 通用工价 `is_global=true`：

- 只有具备 `workshop:wage_rate_read_all` 或等价全局权限时可读取。
- 无全局权限不得返回通用工价。

5. 查询参数带 `item_code=ITEM-A` 时：

- 如用户无 ITEM-A 权限，返回空列表或 403 二选一。
- 本项目统一采用 403，code = AUTH_FORBIDDEN，便于审计识别越权探测。

════════════════════════════════════════════════════════════════════

【六、POST /api/workshop/wage-rates 创建校验规则】

接口：

- POST /api/workshop/wage-rates

必须执行：

1. 校验当前用户登录态。
2. 校验 `workshop:wage_rate_manage` 动作权限。
3. 解析 `item_code/company` 资源。
4. 校验 Item 资源权限。
5. 校验 Company 资源权限。
6. 校验生效区间不重叠。
7. 写操作审计。

创建指定 item_code 工价：

- 用户必须具备目标 item_code 权限。
- 用户如有 company 限制，还必须具备目标 company 权限。
- 只有 Company 权限、没有 Item 权限时，必须返回 403，code = AUTH_FORBIDDEN。

创建通用工价：

- item_code 为空。
- 必须具备 `workshop:wage_rate_manage_all`。
- 如指定 company，还必须具备该 company 权限。
- 无全局权限返回 403，code = WORKSHOP_WAGE_RATE_GLOBAL_FORBIDDEN 或 AUTH_FORBIDDEN。

════════════════════════════════════════════════════════════════════

【七、POST /api/workshop/wage-rates/{id}/deactivate 停用校验规则】

接口：

- POST /api/workshop/wage-rates/{id}/deactivate

必须执行：

1. 先读取目标工价。
2. 校验 `workshop:wage_rate_manage` 动作权限。
3. 如果目标工价 `item_code` 不为空，校验该 item_code 权限和 company 权限。
4. 如果目标工价是通用工价，校验 `workshop:wage_rate_manage_all`。
5. 无权限返回 403，code = AUTH_FORBIDDEN。
6. 停用成功写操作审计。
7. 资源级拒绝写安全审计。

════════════════════════════════════════════════════════════════════

【八、安全审计要求】

以下场景必须写入 `ly_security_audit_log`：

1. 用户无 `workshop:wage_rate_read` 读取工价。
2. 用户无目标 item_code 权限读取工价。
3. 用户无目标 company 权限读取工价。
4. 用户只有 Company 权限、没有 Item 权限，却尝试读取指定 Item 工价。
5. 用户只有 Company 权限、没有 Item 权限，却尝试创建指定 Item 工价。
6. 用户无全局权限读取或维护通用工价。
7. 权限来源不可用。

安全审计字段至少包含：

- event_type
- module = workshop
- action = workshop:wage_rate_read 或 workshop:wage_rate_manage
- resource_type = WageRate / Item / Company
- resource_id
- resource_no = item_code 或 company
- user_id
- deny_reason
- request_id
- ip_address
- user_agent
- created_at

脱敏要求沿用 BOM：

- 不记录 Token / Cookie / password / secret。
- 不记录 SQL 原文和 SQL 参数。
- request_id 必须规范化并拦截语义敏感词。

════════════════════════════════════════════════════════════════════

【九、测试必须覆盖的审计探针】

1. 仅授权 ITEM-B 的用户读取工价列表。

前置数据：

- ITEM-A 工价 1 条
- ITEM-B 工价 1 条

期望：

- GET /api/workshop/wage-rates 只返回 ITEM-B。
- 不返回 ITEM-A。

2. 仅授权 ITEM-B 的用户按 item_code=ITEM-A 查询。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 写安全审计

3. 只有 Company 权限、没有 Item 权限的用户创建 ITEM-Z 工价。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 不写 ly_operation_wage_rate
- 写安全审计

4. 只有 Company 权限、没有 Item 权限的用户读取工价列表。

期望：

- 不返回任何款式专属工价，除非 ERPNext 明确返回 Item unrestricted。
- 不得把 Company 权限当作 Item 权限。

5. 用户有 ITEM-Z 权限但无目标 company 权限。

期望：

- 创建 ITEM-Z 工价返回 403
- code = AUTH_FORBIDDEN
- 不写 ly_operation_wage_rate

6. 无法解析 item_code 对应 company。

期望：

- 创建工价返回 400
- code = WORKSHOP_WAGE_RATE_COMPANY_REQUIRED
- 不写 ly_operation_wage_rate

7. 无全局权限读取通用工价。

期望：

- GET /api/workshop/wage-rates 不返回 is_global=true 记录
- 如显式查询通用工价，返回 403

8. 无全局权限创建通用工价。

期望：

- POST /api/workshop/wage-rates 返回 403
- code = WORKSHOP_WAGE_RATE_GLOBAL_FORBIDDEN 或 AUTH_FORBIDDEN
- 不写 ly_operation_wage_rate

════════════════════════════════════════════════════════════════════

【十、验收标准】

□ `GET /api/workshop/wage-rates` 已校验 `workshop:wage_rate_read`。

□ `GET /api/workshop/wage-rates` 在数据库查询层按 `item_code/company` 过滤。

□ 仅授权 ITEM-B 的用户读取工价列表时，不返回 ITEM-A 工价。

□ 仅授权 ITEM-B 的用户显式查询 `item_code=ITEM-A` 时返回 403，code = AUTH_FORBIDDEN。

□ 只有 Company 权限、没有 Item 权限的用户读取工价列表时，不返回款式专属工价。

□ `POST /api/workshop/wage-rates` 已完成 `item_code -> company` 解析。

□ 只有 Company 权限、没有 Item 权限的用户创建 ITEM-Z 工价时返回 403，code = AUTH_FORBIDDEN。

□ 用户有 Item 权限但无目标 Company 权限时，创建工价返回 403，code = AUTH_FORBIDDEN。

□ 无法解析 company 时，创建工价返回 400，code = WORKSHOP_WAGE_RATE_COMPANY_REQUIRED。

□ `POST /api/workshop/wage-rates/{id}/deactivate` 按目标工价 item_code/company 做资源权限校验。

□ 通用工价读取必须具备 `workshop:wage_rate_read_all` 或等价全局权限。

□ 通用工价创建/停用必须具备 `workshop:wage_rate_manage_all` 或等价全局权限。

□ 权限来源不可用时，工价读取/创建/停用返回 503，code = PERMISSION_SOURCE_UNAVAILABLE。

□ 工价资源级拒绝均写入 ly_security_audit_log。

□ 安全审计日志不包含 Token、Cookie、password、secret、SQL 原文、SQL 参数。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。

════════════════════════════════════════════════════════════════════

【十一、禁止事项】

1. 禁止 Company-only 权限创建指定 item_code 工价。

2. 禁止 Company-only 权限读取款式专属工价，除非 ERPNext 明确返回 Item unrestricted。

3. 禁止 `GET /api/workshop/wage-rates` 返回未授权 item_code 的工价。

4. 禁止先查全量工价再交给前端过滤。

5. 禁止信任前端传入 company 而不校验 ERPNext Company 和用户 Company 权限。

6. 禁止无法解析 item_code/company 时 fail open。

7. 禁止通用工价绕过全局工价权限。

8. 禁止删除 TASK-003A 已完成的工票登记资源级权限校验。

9. 禁止记录未脱敏异常、Token、Cookie、密码、Secret、SQL 原文。

════════════════════════════════════════════════════════════════════

【十二、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003B 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- 工价读取已按 item_code/company 做资源过滤
- 工价创建已完成 item_code -> company 解析
- Company-only 无 Item 权限场景已 fail closed
- 通用工价已要求全局读/写权限
- 工价资源级拒绝已写安全审计

自测结果：
- ITEM-B 用户读取列表不返回 ITEM-A 工价：通过 / 不通过
- ITEM-B 用户显式查 ITEM-A 工价返回 403：通过 / 不通过
- Company-only 用户创建 ITEM-Z 工价返回 403：通过 / 不通过
- Item 有权但 Company 无权创建工价返回 403：通过 / 不通过
- 无法解析 company 返回 WORKSHOP_WAGE_RATE_COMPANY_REQUIRED：通过 / 不通过
- 通用工价无全局权限不可读/不可写：通过 / 不通过
- 权限来源不可用 fail closed：通过 / 不通过
- 工价资源级拒绝写安全审计：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
