# TASK-003 工票/车间管理工程任务单

- 任务编号：TASK-003
- 模块：工票/车间管理
- 优先级：P0
- 预计工时：4-6 天
- 更新时间：2026-04-12 12:21 CST
- 作者：技术架构师
- 前置依赖：TASK-001 BOM 管理已通过审计；权限、审计、日志安全能力沿用 BOM 模块已落地机制

════════════════════════════════════════════════════════════════════

【任务目标】

实现车间工票登记、撤销、批量导入、日薪统计和 ERPNext Job Card 关联，形成“工序执行数量 -> 员工计件工资 -> 工单进度同步”的闭环。

════════════════════════════════════════════════════════════════════

【一、模块边界】

FastAPI 自建负责：

1. 工票登记、撤销、批量导入。
2. 工票幂等控制。
3. 工价档案维护和工票单价快照。
4. 员工日薪汇总。
5. 工票与 ERPNext Job Card 的关联和进度同步状态记录。
6. 工票权限校验、安全审计、操作审计。

ERPNext 负责：

1. Employee 员工主数据。
2. Job Card 工序卡。
3. Work Order 生产工单。
4. Role / User Permission 权限事实源。
5. 标准 Workflow，如后续 Job Card 状态流转需要审批。

Vue3 前端负责：

1. 工票登记页面。
2. 工票批量导入页面。
3. 工票查询页面。
4. 员工日薪统计页面。
5. 工价档案维护页面。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端新建：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003_create_workshop_tables.py

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py（注册 workshop 路由）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py（新增 workshop 权限动作）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py（接入 workshop 权限聚合）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py（复用操作审计和安全审计）

前端新建：

- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue

前端修改：

- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts（新增车间路由）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts（接入 workshop 权限动作）

测试新增：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py

════════════════════════════════════════════════════════════════════

【三、数据库表设计】

1. 表：ly_schema.ys_workshop_ticket

用途：工票明细事实表，登记和撤销都作为独立工票记录，不物理删除。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| ticket_no | varchar(64) | 是 | 系统工票编号，全局唯一 |
| ticket_key | varchar(128) | 是 | 外部幂等键，来自扫码/PDA/MES/手工生成 |
| job_card | varchar(140) | 是 | ERPNext Job Card.name |
| work_order | varchar(140) | 否 | ERPNext Work Order.name，来自 Job Card 或入参冗余 |
| bom_id | bigint | 否 | ly_apparel_bom.id |
| item_code | varchar(140) | 是 | ERPNext Item.name，成品/款式 |
| employee | varchar(140) | 是 | ERPNext Employee.name |
| process_name | varchar(100) | 是 | 工序名称 |
| color | varchar(64) | 否 | 颜色 |
| size | varchar(64) | 否 | 尺码 |
| operation_type | varchar(16) | 是 | register / reversal |
| qty | numeric(18,6) | 是 | 本次登记或撤销数量，必须大于 0 |
| unit_wage | numeric(18,6) | 是 | 工票生成时快照计件单价 |
| wage_amount | numeric(18,6) | 是 | qty * unit_wage，撤销记录为负向影响 |
| work_date | date | 是 | 工作日期 |
| source | varchar(32) | 是 | manual / pda / mes / import |
| source_ref | varchar(140) | 否 | 外部来源单号 |
| original_ticket_id | bigint | 否 | 撤销时可关联原登记工票 |
| sync_status | varchar(32) | 是 | pending / synced / failed |
| sync_error_code | varchar(64) | 否 | ERPNext 同步失败错误码 |
| sync_error_message | varchar(255) | 否 | 脱敏后的同步失败原因 |
| created_by | varchar(140) | 是 | 创建人 |
| created_at | timestamptz | 是 | 创建时间 |
| updated_at | timestamptz | 是 | 更新时间 |

索引与约束：

- pk_ys_workshop_ticket(id)
- uk_ys_workshop_ticket_no(ticket_no)
- uk_ys_workshop_ticket_idempotent(ticket_key, process_name, color, size, operation_type, work_date)
- idx_ys_workshop_ticket_employee_date(employee, work_date)
- idx_ys_workshop_ticket_job_card(job_card)
- idx_ys_workshop_ticket_item_process(item_code, process_name)
- idx_ys_workshop_ticket_sync_status(sync_status)
- check operation_type in ('register', 'reversal')
- check qty > 0
- check unit_wage >= 0

2. 表：ly_schema.ys_workshop_daily_wage

用途：员工日薪汇总表，可由工票写入后实时刷新，也可由重算任务刷新。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| employee | varchar(140) | 是 | ERPNext Employee.name |
| work_date | date | 是 | 工作日期 |
| process_name | varchar(100) | 是 | 工序名称 |
| item_code | varchar(140) | 否 | 款式/成品 |
| register_qty | numeric(18,6) | 是 | 登记数量合计 |
| reversal_qty | numeric(18,6) | 是 | 撤销数量合计 |
| net_qty | numeric(18,6) | 是 | register_qty - reversal_qty |
| wage_amount | numeric(18,6) | 是 | 按工票单价快照汇总后的工资 |
| last_ticket_at | timestamptz | 否 | 最后工票时间 |
| updated_at | timestamptz | 是 | 更新时间 |

索引与约束：

- pk_ys_workshop_daily_wage(id)
- uk_ys_workshop_daily_wage_emp_date_process_item(employee, work_date, process_name, item_code)
- idx_ys_workshop_daily_wage_work_date(work_date)
- idx_ys_workshop_daily_wage_employee(employee)

3. 表：ly_schema.ly_operation_wage_rate

用途：工价档案，维护本厂工序计件价。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| item_code | varchar(140) | 否 | ERPNext Item.name；为空表示通用工价 |
| process_name | varchar(100) | 是 | 工序名称 |
| wage_rate | numeric(18,6) | 是 | 计件单价 |
| effective_from | date | 是 | 生效开始日期 |
| effective_to | date | 否 | 生效结束日期，空表示长期有效 |
| status | varchar(32) | 是 | active / inactive |
| created_by | varchar(140) | 是 | 创建人 |
| created_at | timestamptz | 是 | 创建时间 |
| updated_at | timestamptz | 是 | 更新时间 |

索引与约束：

- pk_ly_operation_wage_rate(id)
- idx_ly_operation_wage_rate_item_process(item_code, process_name)
- idx_ly_operation_wage_rate_effective(effective_from, effective_to)
- check wage_rate >= 0
- 同一 item_code + process_name 的 active 生效区间不得重叠，通用工价 item_code 为空时也要检查区间重叠。

4. 表：ly_schema.ys_workshop_job_card_sync_log

用途：记录工票汇总同步 ERPNext Job Card 的结果。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| job_card | varchar(140) | 是 | ERPNext Job Card.name |
| sync_type | varchar(32) | 是 | ticket_register / ticket_reversal / manual_retry |
| local_completed_qty | numeric(18,6) | 是 | 本地工票净完成数量 |
| erpnext_status | varchar(32) | 是 | success / failed |
| erpnext_response | jsonb | 否 | 脱敏后的 ERPNext 响应摘要 |
| error_code | varchar(64) | 否 | 错误码 |
| error_message | varchar(255) | 否 | 脱敏错误信息 |
| request_id | varchar(64) | 是 | 规范化 request_id |
| created_at | timestamptz | 是 | 创建时间 |

索引：

- idx_ys_workshop_job_card_sync_log_job_card(job_card)
- idx_ys_workshop_job_card_sync_log_status(erpnext_status)
- idx_ys_workshop_job_card_sync_log_created_at(created_at)

════════════════════════════════════════════════════════════════════

【四、接口清单】

统一响应格式：

{
  "code": "0",
  "message": "success",
  "data": {}
}

1. 登记工票

- 方法：POST
- 路径：/api/workshop/tickets/register
- 权限：workshop:ticket_register
- 入参：ticket_key, job_card, employee, process_name, color, size, qty, work_date, source, source_ref
- 出参：ticket_no, ticket_id, unit_wage, wage_amount, sync_status

2. 撤销工票

- 方法：POST
- 路径：/api/workshop/tickets/reversal
- 权限：workshop:ticket_reversal
- 入参：ticket_key, job_card, employee, process_name, color, size, qty, work_date, original_ticket_id, reason
- 出参：ticket_no, ticket_id, net_qty, wage_amount, sync_status

3. 批量导入工票

- 方法：POST
- 路径：/api/workshop/tickets/batch
- 权限：workshop:ticket_batch
- 入参：tickets[]
- 出参：success_count, failed_count, success_items[], failed_items[]

4. 查询工票

- 方法：GET
- 路径：/api/workshop/tickets
- 权限：workshop:read
- 入参：employee, job_card, item_code, process_name, operation_type, work_date, from_date, to_date, page, page_size
- 出参：items, total, page, page_size

5. 查询日薪

- 方法：GET
- 路径：/api/workshop/daily-wages
- 权限：workshop:wage_read
- 入参：employee, from_date, to_date, process_name, item_code, page, page_size
- 出参：items, total, total_amount, page, page_size

6. 查询 Job Card 工票汇总

- 方法：GET
- 路径：/api/workshop/job-cards/{job_card}/summary
- 权限：workshop:read
- 入参：job_card
- 出参：job_card, register_qty, reversal_qty, net_qty, sync_status

7. 手动重试 Job Card 同步

- 方法：POST
- 路径：/api/workshop/job-cards/{job_card}/sync
- 权限：workshop:job_card_sync
- 入参：job_card
- 出参：job_card, local_completed_qty, sync_status

8. 查询工价档案

- 方法：GET
- 路径：/api/workshop/wage-rates
- 权限：workshop:wage_rate_read
- 入参：item_code, process_name, status, page, page_size
- 出参：items, total, page, page_size

9. 创建工价档案

- 方法：POST
- 路径：/api/workshop/wage-rates
- 权限：workshop:wage_rate_manage
- 入参：item_code, process_name, wage_rate, effective_from, effective_to
- 出参：id, status

10. 停用工价档案

- 方法：POST
- 路径：/api/workshop/wage-rates/{id}/deactivate
- 权限：workshop:wage_rate_manage
- 入参：reason
- 出参：id, status

════════════════════════════════════════════════════════════════════

【五、业务规则】

1. 工票类型只允许：

- register：登记
- reversal：撤销

2. 工票数量必须大于 0。

3. 工票幂等键：

同一 `ticket_key + process_name + color + size + operation_type + work_date` 只允许一条记录。

4. 幂等重复提交规则：

- 如果幂等键相同且业务 payload 完全一致，返回已有工票，不新增第二条。
- 如果幂等键相同但 payload 不一致，返回 `WORKSHOP_IDEMPOTENCY_CONFLICT`。

5. 撤销数量不得超过同维度已登记未撤销数量。

计算维度：

- job_card + employee + process_name + color + size + work_date

公式：

- available_qty = sum(register.qty) - sum(reversal.qty)
- reversal.qty <= available_qty

6. 日薪计算公式：

- register_amount = sum(register.qty * register.unit_wage)
- reversal_amount = sum(reversal.qty * reversal.unit_wage)
- wage_amount = register_amount - reversal_amount
- net_qty = register_qty - reversal_qty

7. 工票单价快照规则：

- 工票创建时从 `ly_operation_wage_rate` 找到 work_date 生效的工价。
- 优先匹配 item_code + process_name。
- 如果没有款式专属工价，再匹配 item_code 为空的 process_name 通用工价。
- 工票创建后 unit_wage 不随工价档案变化而变化。

8. 工价生效规则：

- effective_from <= work_date。
- effective_to 为空或 effective_to >= work_date。
- active 工价才可用于工票。
- 同一 item_code + process_name 不允许 active 生效区间重叠。

9. ERPNext Job Card 校验规则：

- job_card 必须存在。
- job_card 状态为 Cancelled / Closed 时禁止登记新工票。
- Job Card 的 operation 应与 process_name 一致；不一致返回 `WORKSHOP_PROCESS_MISMATCH`。

10. ERPNext Employee 校验规则：

- employee 必须存在。
- Employee 状态为 inactive / left / disabled 时禁止登记工票。

11. Job Card 同步规则：

- 本地工票是工资结算事实源。
- ERPNext Job Card 完成数量是生产执行同步结果。
- 工票写入成功后，计算该 job_card 的本地净完成数量并同步到 ERPNext Job Card。
- ERPNext 同步失败时，本地工票不回滚，ticket.sync_status 标记为 failed，并写入 ys_workshop_job_card_sync_log。
- 必须提供手动重试同步接口。

12. 删除规则：

- 工票禁止物理删除。
- 错误登记通过 reversal 抵消。

════════════════════════════════════════════════════════════════════

【六、权限与审计要求】

1. 所有接口必须接入当前用户：

- current_user = Depends(get_current_user)

2. 权限动作：

| 动作 | 权限码 |
| --- | --- |
| 工票读取 | workshop:read |
| 工票登记 | workshop:ticket_register |
| 工票撤销 | workshop:ticket_reversal |
| 工票批量导入 | workshop:ticket_batch |
| 日薪查看 | workshop:wage_read |
| 工价查看 | workshop:wage_rate_read |
| 工价维护 | workshop:wage_rate_manage |
| Job Card 同步重试 | workshop:job_card_sync |

3. 未登录返回：

- HTTP 401
- code = AUTH_UNAUTHORIZED

4. 无权限返回：

- HTTP 403
- code = AUTH_FORBIDDEN

5. ERPNext 权限来源不可用返回：

- HTTP 503
- code = PERMISSION_SOURCE_UNAVAILABLE

6. 以下操作必须写入操作审计：

- 工票登记
- 工票撤销
- 批量导入
- 工价新增
- 工价停用
- Job Card 手动同步

7. 以下场景必须写入安全审计：

- 401 未登录
- 403 无动作权限
- 403 无资源权限
- 503 权限来源不可用

8. 日志和审计必须沿用 BOM 模块已落地的脱敏规则。

要求：

- 不记录完整 Token。
- 不记录 Cookie。
- 不记录 password / secret。
- 不记录 SQL 原文和 SQL 参数。
- request_id 必须使用规范化后的值。

════════════════════════════════════════════════════════════════════

【七、ERPNext 集成要求】

1. 读取 Job Card：

- REST API：GET /api/resource/Job Card/{name}
- 用途：校验工序卡存在、读取 operation、work_order、status。

2. 读取 Employee：

- REST API：GET /api/resource/Employee/{name}
- 用途：校验员工存在且有效。

3. 更新 Job Card 完成数量：

- REST API 或 ERPNext method API。
- 更新值来自本地工票净数量。
- 不直接写 ERPNext 数据库表。

4. ERPNext 不可用处理：

- 登记前校验 Job Card / Employee 时 ERPNext 不可用，返回 `ERPNEXT_SERVICE_UNAVAILABLE`。
- 登记后同步 Job Card 失败，本地工票保留，sync_status = failed，可手动重试。

════════════════════════════════════════════════════════════════════

【八、错误码】

| 错误码 | HTTP 状态 | 场景 |
| --- | --- | --- |
| WORKSHOP_TICKET_NOT_FOUND | 404 | 工票不存在 |
| WORKSHOP_JOB_CARD_NOT_FOUND | 400 | ERPNext Job Card 不存在 |
| WORKSHOP_EMPLOYEE_NOT_FOUND | 400 | ERPNext Employee 不存在 |
| WORKSHOP_JOB_CARD_STATUS_INVALID | 409 | Job Card 状态不允许登记 |
| WORKSHOP_PROCESS_MISMATCH | 400 | 工票工序与 Job Card 工序不一致 |
| WORKSHOP_INVALID_QTY | 400 | 数量小于等于 0 |
| WORKSHOP_IDEMPOTENCY_CONFLICT | 409 | 幂等键相同但 payload 不一致 |
| WORKSHOP_REVERSAL_EXCEEDS_REGISTERED | 409 | 撤销数量超过可撤销数量 |
| WORKSHOP_WAGE_RATE_NOT_FOUND | 400 | 未找到生效工价 |
| WORKSHOP_WAGE_RATE_OVERLAP | 409 | 工价生效区间重叠 |
| WORKSHOP_JOB_CARD_SYNC_FAILED | 502 | Job Card 同步失败 |
| ERPNEXT_SERVICE_UNAVAILABLE | 503 | ERPNext 服务不可用 |
| DATABASE_WRITE_FAILED | 500 | 本地数据库写失败 |
| DATABASE_READ_FAILED | 500 | 本地数据库读失败 |
| WORKSHOP_INTERNAL_ERROR | 500 | 未知异常 |

════════════════════════════════════════════════════════════════════

【九、前端页面要求】

1. 工票登记页：

- 支持输入/扫码 ticket_key。
- 支持选择 job_card、employee、process_name、color、size、qty、work_date。
- 提交成功展示 ticket_no、unit_wage、wage_amount、sync_status。

2. 工票批量导入页：

- 支持粘贴或上传工票列表。
- 展示 success_count、failed_count、failed_items。
- failed_items 必须展示失败行号和错误码。

3. 工票查询页：

- 支持 employee、job_card、item_code、process_name、work_date、operation_type 筛选。
- 展示 register/reversal、qty、unit_wage、wage_amount、sync_status。

4. 日薪统计页：

- 支持 employee、from_date、to_date、process_name、item_code 筛选。
- 展示 register_qty、reversal_qty、net_qty、wage_amount、total_amount。

5. 工价档案页：

- 支持查询、新增、停用工价。
- 不允许编辑已生效历史工价；如需调整，新建新生效区间。

6. 权限控制：

- 页面按钮从 GET /api/auth/actions?module=workshop 读取。
- 前端按钮隐藏不能替代后端鉴权。

════════════════════════════════════════════════════════════════════

【十、验收标准】

□ POST /api/workshop/tickets/register 能创建登记工票，并返回 ticket_no、unit_wage、wage_amount、sync_status。

□ 相同 ticket_key + process_name + color + size + operation_type + work_date 且 payload 完全一致时，重复提交返回同一条工票，不新增第二条。

□ 相同幂等键但 payload 不一致时，返回 409，code = WORKSHOP_IDEMPOTENCY_CONFLICT。

□ qty <= 0 时，登记接口返回 400，code = WORKSHOP_INVALID_QTY。

□ job_card 不存在时，登记接口返回 400，code = WORKSHOP_JOB_CARD_NOT_FOUND。

□ employee 不存在或无效时，登记接口返回 400，code = WORKSHOP_EMPLOYEE_NOT_FOUND。

□ Job Card 状态为 Cancelled / Closed 时，登记接口返回 409，code = WORKSHOP_JOB_CARD_STATUS_INVALID。

□ Job Card operation 与 process_name 不一致时，返回 400，code = WORKSHOP_PROCESS_MISMATCH。

□ 未找到生效工价时，登记接口返回 400，code = WORKSHOP_WAGE_RATE_NOT_FOUND。

□ 登记 100 件、计件单价 0.5 时，wage_amount = 50。

□ 登记 100 件、撤销 10 件、计件单价 0.5 时，GET /api/workshop/daily-wages 返回 net_qty = 90，wage_amount = 45。

□ 撤销数量超过可撤销数量时，返回 409，code = WORKSHOP_REVERSAL_EXCEEDS_REGISTERED。

□ 工票创建后修改工价档案，历史工票 unit_wage 和 wage_amount 不变化。

□ 创建重叠生效区间工价时，返回 409，code = WORKSHOP_WAGE_RATE_OVERLAP。

□ 工票写入成功但 ERPNext Job Card 同步失败时，本地工票保留，sync_status = failed，并写入 ys_workshop_job_card_sync_log。

□ POST /api/workshop/job-cards/{job_card}/sync 可重试同步 failed 的 Job Card。

□ 未登录访问任一 workshop 接口返回 401，code = AUTH_UNAUTHORIZED，并写入安全审计。

□ 无对应权限访问任一 workshop 接口返回 403，code = AUTH_FORBIDDEN，并写入安全审计。

□ 工票登记、撤销、批量导入、工价新增、工价停用、Job Card 手动同步均写入操作审计。

□ 普通日志和审计日志不包含 Token、Cookie、password、secret、SQL 原文、SQL 参数。

□ request_id 使用规范化后的值，不接受语义敏感 request_id 原文。

□ .venv/bin/python -m pytest -q 通过。

□ .venv/bin/python -m unittest discover 通过。

□ .venv/bin/python -m py_compile 检查通过。

════════════════════════════════════════════════════════════════════

【十一、禁止事项】

1. 禁止把工票作为 ERPNext Job Card 的替代品；工票是本地执行事实，Job Card 是 ERPNext 工序卡。

2. 禁止直接写 ERPNext 数据库表更新 Job Card。

3. 禁止物理删除工票。

4. 禁止撤销数量超过已登记未撤销数量。

5. 禁止工票工资按当前工价动态反算历史记录，必须使用工票上的 unit_wage 快照。

6. 禁止同一幂等键 payload 不一致时静默覆盖。

7. 禁止只做前端权限控制，不做后端权限校验。

8. 禁止记录未脱敏异常、Token、Cookie、密码、Secret、SQL 原文。

9. 禁止修改 BOM 已冻结契约。

════════════════════════════════════════════════════════════════════

【十二、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003 已完成。

已修改文件：
- [列出实际修改文件]

数据库变更：
- 已新增 ys_workshop_ticket：是 / 否
- 已新增 ys_workshop_daily_wage：是 / 否
- 已新增 ly_operation_wage_rate：是 / 否
- 已新增 ys_workshop_job_card_sync_log：是 / 否
- 已新增索引：[列出索引]

接口完成：
- POST /api/workshop/tickets/register：完成 / 未完成
- POST /api/workshop/tickets/reversal：完成 / 未完成
- POST /api/workshop/tickets/batch：完成 / 未完成
- GET /api/workshop/tickets：完成 / 未完成
- GET /api/workshop/daily-wages：完成 / 未完成
- GET /api/workshop/job-cards/{job_card}/summary：完成 / 未完成
- POST /api/workshop/job-cards/{job_card}/sync：完成 / 未完成
- GET /api/workshop/wage-rates：完成 / 未完成
- POST /api/workshop/wage-rates：完成 / 未完成
- POST /api/workshop/wage-rates/{id}/deactivate：完成 / 未完成

自测结果：
- 工票登记：通过 / 不通过
- 幂等重复提交：通过 / 不通过
- 幂等冲突：通过 / 不通过
- 工票撤销：通过 / 不通过
- 撤销超量拦截：通过 / 不通过
- 日薪计算：通过 / 不通过
- 工价快照：通过 / 不通过
- 工价区间重叠拦截：通过 / 不通过
- Job Card 校验：通过 / 不通过
- Employee 校验：通过 / 不通过
- Job Card 同步失败留痕：通过 / 不通过
- 权限鉴权和安全审计：通过 / 不通过
- 操作审计：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
