# TASK-003A 工票写接口资源级权限整改任务单

- 任务编号：TASK-003A
- 模块：工票/车间管理 / 权限服务 / ERPNext Job Card 集成
- 优先级：P0（审计阻断）
- 预计工时：1 天
- 更新时间：2026-04-12 13:17 CST
- 作者：技术架构师
- 审计来源：审计意见书第 14 份，车间写接口缺少资源级 Item / Job Card 权限校验

════════════════════════════════════════════════════════════════════

【任务目标】

修复工票/车间写接口资源级越权问题：用户即使具备 `workshop:*` 动作权限，也必须同时具备目标 `Job Card / Work Order / Item / Company` 的资源权限，才允许登记、撤销、批量导入、Job Card 同步和维护款式专属工价。

════════════════════════════════════════════════════════════════════

【一、问题背景】

审计探针已复现：仅授权 `ITEM-B` 的用户，可以成功登记 `ITEM-A` 工票。

这是直接权限越权：

1. 前端传入的 `item_code` 不可信。
2. 工票写接口不能只校验 `workshop:ticket_register` 等动作权限。
3. 必须从 ERPNext `Job Card / Work Order` 派生真实 `item_code` 和 `company`。
4. 必须用 ERPNext `User Permission` 或权限聚合结果做资源级校验。
5. 未授权资源不得写入 `ys_workshop_ticket`、不得刷新日薪、不得同步 Job Card。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py

════════════════════════════════════════════════════════════════════

【三、整改接口范围】

必须补资源级权限校验的写接口：

| 接口 | 方法 | 路径 | 动作权限 | 资源权限 |
| --- | --- | --- | --- | --- |
| 登记工票 | POST | /api/workshop/tickets/register | workshop:ticket_register | Job Card 派生 item_code / company |
| 撤销工票 | POST | /api/workshop/tickets/reversal | workshop:ticket_reversal | 原工票 + Job Card 派生 item_code / company |
| 批量导入工票 | POST | /api/workshop/tickets/batch | workshop:ticket_batch | 每行 Job Card 派生 item_code / company |
| 手动重试 Job Card 同步 | POST | /api/workshop/job-cards/{job_card}/sync | workshop:job_card_sync | Job Card 派生 item_code / company |
| 创建工价档案 | POST | /api/workshop/wage-rates | workshop:wage_rate_manage | item_code 资源权限；通用工价需全局权限 |
| 停用工价档案 | POST | /api/workshop/wage-rates/{id}/deactivate | workshop:wage_rate_manage | wage_rate.item_code 资源权限；通用工价需全局权限 |

说明：

- 本任务优先修复写接口。
- 查询接口如当前未做资源过滤，也必须至少补测试暴露风险，后续可单独出读权限整改任务。

════════════════════════════════════════════════════════════════════

【四、资源识别规则】

1. 登记工票不得信任前端传入的 `item_code`。

正确流程：

- 读取请求中的 `job_card`。
- 调 ERPNext 读取 `Job Card`。
- 由 `Job Card.work_order` 继续读取 ERPNext `Work Order`。
- 从 `Work Order.production_item` 或项目已约定字段派生真实 `item_code`。
- 从 `Work Order.company` 或 Job Card 关联公司派生真实 `company`。
- 将派生出的 `item_code/company` 作为资源权限校验依据。

2. 如果请求体包含 `item_code`：

- 必须与 ERPNext Job Card / Work Order 派生出的 `item_code` 一致。
- 不一致返回 `WORKSHOP_ITEM_MISMATCH`。
- 不允许用请求体 `item_code` 覆盖 ERPNext 派生值。

3. 如果无法从 Job Card / Work Order 派生 item_code：

- 返回 `WORKSHOP_JOB_CARD_ITEM_NOT_FOUND`。
- 不允许继续写入工票。

4. 如果无法从 Job Card / Work Order 派生 company：

- 返回 `WORKSHOP_JOB_CARD_COMPANY_NOT_FOUND`。
- 不允许继续写入工票。

5. 撤销工票必须同时校验：

- 当前用户对原工票 `item_code/company` 有权限。
- 当前用户对请求中的 `job_card` 派生资源有权限。
- 如 original_ticket_id 存在，必须与同一 job_card / employee / process_name / color / size 维度一致。

6. 批量导入必须逐行派生资源并逐行校验。

处理规则：

- 授权行可以正常写入。
- 越权行不得写入，进入 `failed_items`。
- 越权行必须写安全审计。
- `failed_items` 必须包含 row_index、ticket_key、error_code、message。

7. Job Card 同步重试必须按 Job Card 派生资源校验。

- 无资源权限不得重试同步。
- 不得泄露该 Job Card 的本地工票汇总数据。

8. 工价档案资源规则：

- item_code 不为空：必须校验用户对该 item_code 的资源权限。
- item_code 为空表示通用工价：必须具备 `workshop:wage_rate_manage_all` 或系统管理员/生产经理等全局权限。
- 无全局权限时创建或停用通用工价返回 `AUTH_FORBIDDEN`。

════════════════════════════════════════════════════════════════════

【五、资源级权限实现要求】

1. 新增或复用统一函数：

- ensure_workshop_resource_permission(current_user, action, item_code, company, job_card=None)

2. 该函数必须执行两层校验：

第一层：动作权限。

- 用户必须具备对应 `workshop:*` 动作权限。

第二层：资源权限。

- 用户必须具备目标 `item_code` 权限。
- 如存在 `company` 限制，用户必须具备目标 `company` 权限。
- 权限来源不可用时必须 fail closed。

3. 权限来源：

- 生产环境必须使用 ERPNext `Role / User Permission` 或 FastAPI `/api/auth/actions` 聚合后的 ERPNext 权限结果。
- Sprint 临时静态权限可用于本地测试，但不得 fail open。
- 权限查询失败返回 `PERMISSION_SOURCE_UNAVAILABLE`。

4. 禁止只根据前端按钮权限放行。

5. 禁止只校验 `workshop:ticket_register` 而不校验 item_code / company。

════════════════════════════════════════════════════════════════════

【六、错误码】

新增或确认以下错误码：

| 错误码 | HTTP 状态 | 场景 |
| --- | --- | --- |
| AUTH_UNAUTHORIZED | 401 | 未登录 |
| AUTH_FORBIDDEN | 403 | 无动作权限或资源权限 |
| PERMISSION_SOURCE_UNAVAILABLE | 503 | ERPNext 权限来源不可用 |
| WORKSHOP_ITEM_MISMATCH | 400 | 请求 item_code 与 Job Card 派生 item_code 不一致 |
| WORKSHOP_JOB_CARD_ITEM_NOT_FOUND | 400 | 无法从 Job Card / Work Order 派生 item_code |
| WORKSHOP_JOB_CARD_COMPANY_NOT_FOUND | 400 | 无法从 Job Card / Work Order 派生 company |
| WORKSHOP_JOB_CARD_NOT_FOUND | 400 | Job Card 不存在 |
| WORKSHOP_WAGE_RATE_GLOBAL_FORBIDDEN | 403 | 无全局权限维护通用工价 |
| ERPNEXT_SERVICE_UNAVAILABLE | 503 | ERPNext 服务不可用 |

════════════════════════════════════════════════════════════════════

【七、安全审计要求】

以下资源级拒绝必须写入 `ly_security_audit_log`：

1. 用户无目标 item_code 权限。
2. 用户无目标 company 权限。
3. 请求 item_code 与 Job Card 派生 item_code 不一致。
4. 用户无权重试目标 Job Card 同步。
5. 用户无权创建或停用目标 item_code 工价。
6. 用户无权维护通用工价。
7. ERPNext 权限来源不可用。

安全审计字段至少包含：

- event_type = AUTH_FORBIDDEN 或 PERMISSION_SOURCE_UNAVAILABLE
- module = workshop
- action
- resource_type = JobCard / Item / Company / WageRate
- resource_id
- resource_no
- user_id
- deny_reason
- request_id
- ip_address
- user_agent
- created_at

脱敏要求：

- 不记录完整 Token。
- 不记录 Cookie。
- 不记录 password / secret。
- 不记录 SQL 原文和 SQL 参数。
- request_id 必须是规范化后的值。

════════════════════════════════════════════════════════════════════

【八、测试必须覆盖的审计探针】

1. 用户仅授权 ITEM-B，尝试登记 ITEM-A 工票。

输入：

- current_user.allowed_items = ["ITEM-B"]
- job_card 派生 item_code = "ITEM-A"
- POST /api/workshop/tickets/register

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- ys_workshop_ticket 无新增记录
- ys_workshop_daily_wage 无更新
- 不调用 ERPNext Job Card 同步
- ly_security_audit_log 新增资源级拒绝记录

2. 用户仅授权 ITEM-B，尝试撤销 ITEM-A 工票。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 不新增 reversal 工票
- 不更新日薪
- 写安全审计

3. 批量导入中同时包含 ITEM-A 和 ITEM-B。

输入：

- 用户仅授权 ITEM-B
- 第 1 行 Job Card 派生 ITEM-A
- 第 2 行 Job Card 派生 ITEM-B

期望：

- ITEM-A 行失败，error_code = AUTH_FORBIDDEN
- ITEM-B 行成功
- success_count = 1
- failed_count = 1
- failed_items 包含第 1 行 row_index
- ITEM-A 不入库
- ITEM-A 失败写安全审计

4. 用户仅授权 ITEM-B，尝试重试 ITEM-A Job Card 同步。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 不调用 ERPNext 同步
- 写安全审计

5. 用户仅授权 ITEM-B，尝试创建 ITEM-A 工价。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 不写 ly_operation_wage_rate
- 写安全审计

6. 用户无全局权限，尝试创建 item_code 为空的通用工价。

期望：

- HTTP 403
- code = WORKSHOP_WAGE_RATE_GLOBAL_FORBIDDEN 或 AUTH_FORBIDDEN
- 不写 ly_operation_wage_rate
- 写安全审计

════════════════════════════════════════════════════════════════════

【九、验收标准】

□ `POST /api/workshop/tickets/register` 已校验动作权限 + Job Card 派生 item_code/company 资源权限。

□ `POST /api/workshop/tickets/reversal` 已校验动作权限 + 原工票/Job Card 派生资源权限。

□ `POST /api/workshop/tickets/batch` 已逐行校验 Job Card 派生 item_code/company 资源权限。

□ `POST /api/workshop/job-cards/{job_card}/sync` 已校验动作权限 + Job Card 派生资源权限。

□ `POST /api/workshop/wage-rates` 对 item_code 工价校验 item_code 资源权限。

□ `POST /api/workshop/wage-rates` 对通用工价校验全局工价维护权限。

□ `POST /api/workshop/wage-rates/{id}/deactivate` 校验目标工价资源权限。

□ 仅授权 ITEM-B 的用户登记 ITEM-A 工票返回 403，code = AUTH_FORBIDDEN。

□ 仅授权 ITEM-B 的用户登记 ITEM-A 工票时，不新增 ys_workshop_ticket。

□ 仅授权 ITEM-B 的用户登记 ITEM-A 工票时，不更新 ys_workshop_daily_wage。

□ 仅授权 ITEM-B 的用户登记 ITEM-A 工票时，不调用 ERPNext Job Card 同步。

□ 请求体 item_code 与 Job Card 派生 item_code 不一致时，返回 400，code = WORKSHOP_ITEM_MISMATCH。

□ ERPNext 权限来源不可用时，写接口返回 503，code = PERMISSION_SOURCE_UNAVAILABLE，不写业务表。

□ 所有资源级 403 均写入 ly_security_audit_log。

□ 安全审计日志包含 action、resource_type、resource_no、deny_reason、user_id、request_id。

□ 安全审计日志不包含 Token、Cookie、password、secret、SQL 原文、SQL 参数。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。

════════════════════════════════════════════════════════════════════

【十、禁止事项】

1. 禁止信任前端传入的 item_code 作为工票资源权限依据。

2. 禁止只校验 workshop 动作权限，不校验 item_code/company 资源权限。

3. 禁止 Job Card 派生资源失败时继续写工票。

4. 禁止用户仅授权 ITEM-B 时写入 ITEM-A 工票。

5. 禁止资源越权行在批量导入中静默成功。

6. 禁止资源越权后同步 ERPNext Job Card。

7. 禁止资源越权后更新日薪汇总。

8. 禁止权限来源不可用时 fail open。

9. 禁止删除 BOM 已通过审计的权限、审计、日志脱敏能力。

════════════════════════════════════════════════════════════════════

【十一、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003A 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- 工票登记已按 Job Card 派生 item_code/company 做资源级权限校验
- 工票撤销已按原工票和 Job Card 派生资源做资源级权限校验
- 批量导入已逐行做资源级权限校验
- Job Card 同步重试已做资源级权限校验
- 工价维护已做 item_code / 通用工价权限校验
- 越权场景已写安全审计

自测结果：
- ITEM-B 用户登记 ITEM-A 工票被拒绝：通过 / 不通过
- ITEM-B 用户撤销 ITEM-A 工票被拒绝：通过 / 不通过
- 批量导入 ITEM-A 失败 ITEM-B 成功：通过 / 不通过
- ITEM-B 用户重试 ITEM-A Job Card 同步被拒绝：通过 / 不通过
- ITEM-B 用户创建 ITEM-A 工价被拒绝：通过 / 不通过
- 无全局权限创建通用工价被拒绝：通过 / 不通过
- 权限来源不可用 fail closed：通过 / 不通过
- 资源级拒绝写安全审计：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
