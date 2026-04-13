# TASK-003D Job Card 同步 Outbox 整改任务单

- 任务编号：TASK-003D
- 模块：工票/车间管理 / ERPNext Job Card 同步 / Outbox
- 优先级：P0（审计阻断）
- 预计工时：1-2 天
- 更新时间：2026-04-12 14:38 CST
- 作者：技术架构师
- 审计来源：审计意见书第 17 份，Job Card 同步发生在本地事务提交前，存在跨系统不一致风险

════════════════════════════════════════════════════════════════════

【任务目标】

将工票写入后的 ERPNext Job Card 同步从“本地事务提交前直接调用 ERPNext”改为 outbox / after-commit / 异步重试模式，确保本地工票、日薪、操作审计先在同一事务提交成功，再由异步同步任务更新 ERPNext Job Card，避免 ERPNext 已更新但本地事务回滚的跨系统不一致。

════════════════════════════════════════════════════════════════════

【一、问题背景】

审计指出：当前 Job Card 同步仍发生在本地事务提交前。

风险场景：

1. 本地工票写入成功但事务尚未提交。
2. 代码立即调用 ERPNext 更新 Job Card 完成数量。
3. ERPNext 更新成功。
4. 随后本地数据库 commit 失败或审计写入失败导致本地事务 rollback。
5. 最终出现 ERPNext Job Card 已更新，但本地没有对应工票事实和审计记录。

这是典型跨系统一致性问题。ERPNext 调用不能放在本地事务提交前。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端新增：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003d_create_workshop_outbox.py

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py

前端修改：

- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_outbox.py（建议新增）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py

════════════════════════════════════════════════════════════════════

【三、数据库表设计】

新增表：ly_schema.ys_workshop_job_card_sync_outbox

用途：保存待同步 ERPNext Job Card 的异步任务。该表记录“最终待办状态”，不是每次尝试日志。

字段要求：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint | 是 | 主键 |
| event_key | varchar(140) | 是 | 同步事件幂等键 |
| job_card | varchar(140) | 是 | ERPNext Job Card.name |
| work_order | varchar(140) | 否 | ERPNext Work Order.name |
| item_code | varchar(140) | 是 | Job Card / Work Order 派生的 Item |
| company | varchar(140) | 是 | Job Card / Work Order 派生的 Company |
| local_completed_qty | numeric(18,6) | 是 | 当前本地工票净完成数量 |
| source_type | varchar(32) | 是 | ticket_register / ticket_reversal / ticket_batch / manual_retry |
| source_ids | jsonb | 是 | 触发本次同步的本地工票 id 列表 |
| status | varchar(32) | 是 | pending / processing / succeeded / failed / dead |
| attempts | int | 是 | 已尝试次数 |
| max_attempts | int | 是 | 最大尝试次数，默认 5 |
| next_retry_at | timestamptz | 是 | 下次允许重试时间 |
| locked_by | varchar(140) | 否 | worker 标识 |
| locked_at | timestamptz | 否 | 锁定时间 |
| last_error_code | varchar(64) | 否 | 最近一次错误码 |
| last_error_message | varchar(255) | 否 | 脱敏后的最近错误信息 |
| request_id | varchar(64) | 是 | 规范化 request_id |
| created_by | varchar(140) | 是 | 创建人 |
| created_at | timestamptz | 是 | 创建时间 |
| updated_at | timestamptz | 是 | 更新时间 |

索引与约束：

- pk_ys_workshop_job_card_sync_outbox(id)
- uk_ys_workshop_job_card_sync_outbox_event_key(event_key)
- idx_ys_workshop_job_card_sync_outbox_status_retry(status, next_retry_at)
- idx_ys_workshop_job_card_sync_outbox_job_card(job_card)
- idx_ys_workshop_job_card_sync_outbox_company_item(company, item_code)
- check status in ('pending', 'processing', 'succeeded', 'failed', 'dead')
- check attempts >= 0
- check max_attempts > 0

继续使用表：ly_schema.ys_workshop_job_card_sync_log

用途：记录每次同步尝试结果。outbox 一条任务可以对应多条 sync_log。

新增或确认字段：

- outbox_id
- attempt_no
- erpnext_status
- error_code
- error_message
- request_id
- created_at

索引：

- idx_ys_workshop_job_card_sync_log_outbox_id(outbox_id)
- idx_ys_workshop_job_card_sync_log_job_card(job_card)
- idx_ys_workshop_job_card_sync_log_created_at(created_at)

════════════════════════════════════════════════════════════════════

【四、核心架构规则】

1. 工票本地事务中只能做本地写入。

同一事务内允许：

- 写 ys_workshop_ticket。
- 刷新 ys_workshop_daily_wage。
- 写 ly_operation_audit_log。
- 写 ys_workshop_job_card_sync_outbox，status=pending。

同一事务内禁止：

- 调用 ERPNext 更新 Job Card。
- 调用任何跨系统写接口。

2. ERPNext Job Card 同步必须发生在本地事务提交之后。

允许方式：

- after-commit hook 触发同步任务。
- 后台 worker 扫描 outbox pending 任务。
- 手动重试接口触发 outbox 任务重试。

3. 本地事务 commit 失败时：

- 不得产生 outbox 持久化记录。
- 不得调用 ERPNext。
- 返回 DATABASE_WRITE_FAILED 或对应业务错误码。

4. 操作审计失败时：

- 本地事务整体回滚。
- 不得调用 ERPNext。
- 返回 AUDIT_WRITE_FAILED。

5. outbox 写入失败时：

- 属于本地数据库写失败。
- 本地事务整体回滚。
- 不得调用 ERPNext。
- 返回 DATABASE_WRITE_FAILED。

6. ERPNext 同步失败时：

- 不回滚已提交的本地工票。
- outbox.status 标记为 failed 或 pending 并设置 next_retry_at。
- 写 ys_workshop_job_card_sync_log。
- ticket.sync_status 可标记 failed 或由汇总状态反映。

7. ERPNext 同步成功时：

- outbox.status = succeeded。
- 写 ys_workshop_job_card_sync_log。
- 对应 job_card 的本地工票 sync_status 更新为 synced。

════════════════════════════════════════════════════════════════════

【五、同步幂等规则】

1. event_key 必须稳定且唯一。

推荐：

- `job_card + local_completed_qty + source_type + sorted(source_ids)` 的 hash。

2. 重复创建同一 event_key 的 outbox：

- 不新增第二条。
- 返回已有 outbox。

3. Worker 同步 ERPNext 时必须使用最终态覆盖，而不是增量累加。

正确方式：

- 读取当前 job_card 的本地净完成数量。
- 将 ERPNext Job Card completed_qty 更新为该净数量。

禁止方式：

- 每次工票登记后向 ERPNext 增加 qty。

原因：增量同步在重试时容易重复累加。

4. Worker 必须支持重复执行同一 outbox 不造成 ERPNext 数量重复。

5. 对同一 job_card 的多个 pending outbox：

- 可以合并为最新 local_completed_qty 同步。
- 或按创建顺序处理，但最终 ERPNext completed_qty 必须等于本地净数量。

════════════════════════════════════════════════════════════════════

【六、Worker 处理规则】

1. 获取任务条件：

- status in ('pending', 'failed')
- next_retry_at <= now
- attempts < max_attempts

2. 锁定任务：

必须使用数据库行锁或原子更新，防止多 worker 重复处理同一 outbox。

建议：

- SELECT ... FOR UPDATE SKIP LOCKED
- 或 UPDATE ... WHERE status='pending' RETURNING *

3. 状态流转：

- pending -> processing
- processing -> succeeded
- processing -> failed
- failed -> processing
- failed -> dead（超过最大重试）

4. 重试策略：

建议指数退避：

- 第 1 次失败：1 分钟后重试
- 第 2 次失败：5 分钟后重试
- 第 3 次失败：15 分钟后重试
- 第 4 次失败：1 小时后重试
- 第 5 次失败：标记 dead

5. 每次尝试必须写 sync_log。

6. Worker 日志必须脱敏。

7. request_id 使用 outbox.request_id 或 worker 生成的规范化 request_id。

════════════════════════════════════════════════════════════════════

【七、接口调整要求】

1. POST /api/workshop/tickets/register

成功响应中返回：

- ticket_no
- ticket_id
- unit_wage
- wage_amount
- sync_status = pending
- sync_outbox_id

禁止在该接口本地事务提交前调用 ERPNext 更新 Job Card。

2. POST /api/workshop/tickets/reversal

成功响应中返回：

- ticket_no
- ticket_id
- net_qty
- wage_amount
- sync_status = pending
- sync_outbox_id

禁止在该接口本地事务提交前调用 ERPNext 更新 Job Card。

3. POST /api/workshop/tickets/batch

每条成功行返回：

- ticket_no
- ticket_id
- sync_status = pending
- sync_outbox_id

如果系统级异常发生，按 TASK-003C 返回非 200 标准错误响应。

4. GET /api/workshop/job-cards/{job_card}/summary

返回：

- job_card
- local_completed_qty
- outbox_status
- last_sync_at
- last_error_code
- last_error_message

5. POST /api/workshop/job-cards/{job_card}/sync

用途：手动创建或触发重试 outbox。

要求：

- 必须校验动作权限和资源权限。
- 不得在本地事务提交前调用 ERPNext。
- 可以创建 manual_retry outbox，或将 failed/dead outbox 重新置为 pending。

6. 建议新增内部接口或命令，不暴露给普通前端：

- POST /api/workshop/internal/job-card-sync/run-once

用途：测试或运维手动触发 worker 单次处理。

权限：

- workshop:job_card_sync_worker
- 仅管理员或服务账号可用。

════════════════════════════════════════════════════════════════════

【八、服务账号权限要求】

1. ERPNext Job Card 同步必须使用受控服务账号或集成 Token。

2. 服务账号权限最小化：

- 只允许读取 Job Card / Work Order。
- 只允许更新 Job Card 完成数量或项目约定字段。
- 不允许财务权限。
- 不允许库存过账权限。
- 不允许任意 DocType 写权限。

3. 服务账号调用必须记录：

- service_account_id
- action = workshop:job_card_sync
- job_card
- request_id
- outbox_id

4. 服务账号凭证禁止写入日志和审计表。

5. 服务账号权限配置缺失时：

- Worker 任务失败。
- outbox.status = failed。
- error_code = ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN 或 ERPNEXT_SERVICE_UNAVAILABLE。
- 不影响本地工票事实。

════════════════════════════════════════════════════════════════════

【九、错误码】

新增或确认以下错误码：

| 错误码 | HTTP 状态 | 场景 |
| --- | --- | --- |
| WORKSHOP_OUTBOX_NOT_FOUND | 404 | outbox 任务不存在 |
| WORKSHOP_OUTBOX_ALREADY_SUCCEEDED | 409 | 已成功任务不允许重复重试 |
| WORKSHOP_OUTBOX_LOCKED | 409 | outbox 正在被其他 worker 处理 |
| WORKSHOP_JOB_CARD_SYNC_PENDING | 202 | 已创建同步任务，等待异步处理 |
| WORKSHOP_JOB_CARD_SYNC_FAILED | 502 | ERPNext Job Card 同步失败 |
| ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN | 403 | 服务账号无 ERPNext Job Card 更新权限 |
| ERPNEXT_SERVICE_UNAVAILABLE | 503 | ERPNext 服务不可用 |
| DATABASE_WRITE_FAILED | 500 | 本地 outbox / ticket / wage / audit 写失败 |
| WORKSHOP_INTERNAL_ERROR | 500 | 未知异常 |

说明：

- 登记/撤销接口本地成功但同步待处理时，不应返回 `WORKSHOP_JOB_CARD_SYNC_FAILED`。
- 同步失败属于 outbox 后续状态，不影响本地工票登记接口成功响应。

════════════════════════════════════════════════════════════════════

【十、测试必须覆盖的审计探针】

1. 本地事务提交前不得调用 ERPNext。

模拟：

- monkeypatch ERPNext Job Card update 方法。
- 调 POST /api/workshop/tickets/register。
- 在服务层 commit 前断言 update 方法未调用。

期望：

- 本地事务提交前 ERPNext update 调用次数 = 0。

2. 本地 commit 失败不得调用 ERPNext。

模拟：

- session.commit() 抛 DatabaseWriteFailed。

期望：

- HTTP 500
- code = DATABASE_WRITE_FAILED
- ERPNext Job Card update 调用次数 = 0
- outbox 无持久化成功记录

3. 审计写入失败不得调用 ERPNext。

模拟：

- 操作审计写入失败。

期望：

- HTTP 500
- code = AUDIT_WRITE_FAILED
- ERPNext Job Card update 调用次数 = 0
- 本地事务回滚

4. 本地成功后创建 outbox。

模拟：

- 正常登记工票。

期望：

- HTTP 200
- code = 0
- ys_workshop_ticket 有记录
- ys_workshop_job_card_sync_outbox 有 pending 记录
- 响应 sync_status = pending

5. Worker 成功同步。

模拟：

- outbox pending。
- ERPNext update 成功。

期望：

- outbox.status = succeeded
- sync_log 写 success
- ticket.sync_status = synced

6. Worker 同步失败可重试。

模拟：

- ERPNext update 超时或返回失败。

期望：

- outbox.status = failed 或 pending with next_retry_at
- attempts + 1
- sync_log 写 failed
- 本地工票仍保留

7. Worker 重试不重复累加。

模拟：

- 同一 outbox 执行两次。

期望：

- ERPNext 最终 completed_qty = 本地净完成数量
- 不发生重复加数量

8. 手动重试接口权限。

模拟：

- 无 workshop:job_card_sync 权限调用重试接口。

期望：

- HTTP 403
- code = AUTH_FORBIDDEN
- 不触发 ERPNext
- 写安全审计

════════════════════════════════════════════════════════════════════

【十一、验收标准】

□ 工票登记接口本地事务提交前不调用 ERPNext Job Card 更新。

□ 工票撤销接口本地事务提交前不调用 ERPNext Job Card 更新。

□ 批量导入接口本地事务提交前不调用 ERPNext Job Card 更新。

□ 本地 commit 失败时返回 DATABASE_WRITE_FAILED，且 ERPNext Job Card update 调用次数为 0。

□ 操作审计写入失败时返回 AUDIT_WRITE_FAILED，且 ERPNext Job Card update 调用次数为 0。

□ 工票登记成功后写入 ys_workshop_job_card_sync_outbox，status = pending。

□ 工票撤销成功后写入 ys_workshop_job_card_sync_outbox，status = pending。

□ 批量导入成功行写入 outbox，失败行业务错误仍进入 failed_items。

□ Worker 处理 pending outbox 成功后，outbox.status = succeeded，sync_log 写 success。

□ Worker 处理失败后，outbox attempts 增加，status = failed 或 pending，next_retry_at 按策略更新。

□ 超过 max_attempts 后，outbox.status = dead。

□ 同一 outbox 重复执行不会导致 ERPNext Job Card 完成数量重复累加。

□ GET /api/workshop/job-cards/{job_card}/summary 能返回 outbox_status、last_sync_at、last_error_code。

□ POST /api/workshop/job-cards/{job_card}/sync 能在权限通过后创建或重置重试 outbox。

□ 服务账号权限缺失时，outbox 标记 failed，error_code = ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN，不影响本地工票事实。

□ 服务账号凭证不进入普通日志、操作审计、安全审计、sync_log。

□ 普通日志和审计日志不包含 Token、Cookie、password、secret、SQL 原文、SQL 参数。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。

════════════════════════════════════════════════════════════════════

【十二、禁止事项】

1. 禁止在本地数据库事务提交前调用 ERPNext Job Card 更新。

2. 禁止本地 commit 失败后仍调用 ERPNext。

3. 禁止审计写入失败后仍调用 ERPNext。

4. 禁止用增量累加方式同步 Job Card 完成数量。

5. 禁止 outbox 重试导致 ERPNext 完成数量重复增加。

6. 禁止 outbox 写入失败时继续提交本地工票。

7. 禁止 Worker 处理失败时删除 outbox。

8. 禁止服务账号使用管理员全权限 Token。

9. 禁止服务账号凭证进入日志或审计表。

10. 禁止删除 TASK-003A/TASK-003B/TASK-003C 已完成的权限和异常边界。

════════════════════════════════════════════════════════════════════

【十三、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003D 已完成。

已修改文件：
- [列出实际修改文件]

数据库变更：
- 已新增 ys_workshop_job_card_sync_outbox：是 / 否
- 已更新 ys_workshop_job_card_sync_log：是 / 否
- 已新增索引：[列出索引]

核心整改：
- Job Card 同步已从事务内直连改为 outbox/after-commit/异步重试
- 本地 commit 前不再调用 ERPNext
- commit 失败不会调用 ERPNext
- 审计失败不会调用 ERPNext
- Worker 使用最终态覆盖方式同步 completed_qty
- outbox 支持失败重试和 dead 状态
- 服务账号权限按最小权限约束

自测结果：
- commit 前 ERPNext update 调用次数为 0：通过 / 不通过
- commit 失败不调用 ERPNext：通过 / 不通过
- 审计失败不调用 ERPNext：通过 / 不通过
- 登记成功生成 pending outbox：通过 / 不通过
- Worker 成功后 outbox=succeeded：通过 / 不通过
- Worker 失败后 attempts 增加并可重试：通过 / 不通过
- 重试不重复累加 completed_qty：通过 / 不通过
- 服务账号权限缺失记录 failed 且不影响本地工票：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
