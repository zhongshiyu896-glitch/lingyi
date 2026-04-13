# TASK-003C 工票批量导入系统级异常边界整改任务单

- 任务编号：TASK-003C
- 模块：工票/车间管理 / 批量导入 / 异常处理
- 优先级：P0（审计阻断）
- 预计工时：0.5-1 天
- 更新时间：2026-04-12 14:22 CST
- 作者：技术架构师
- 审计来源：审计意见书第 16 份，批量导入将系统级异常包装成 `200/code=0` 的普通失败行

════════════════════════════════════════════════════════════════════

【任务目标】

修复 `POST /api/workshop/tickets/batch` 的异常边界：行级业务失败可以进入 `failed_items`，但数据库异常、权限来源异常、审计异常、ERPNext 系统不可用、未知异常必须向上抛出标准错误响应，禁止包装成 `200/code=0` 的普通失败行。

════════════════════════════════════════════════════════════════════

【一、问题背景】

审计指出：批量导入仍会把 `DatabaseWriteFailed` 这类系统级异常包装成 `200/code=0` 的普通失败行。

这会导致：

1. 调用方误判整个批次请求成功。
2. 运维监控无法识别数据库、权限源、审计系统故障。
3. 系统级故障被隐藏在 `failed_items` 中，审计无法定位真实风险。
4. 批量导入可能出现“部分落库 + 系统异常被吞掉”的不可追踪状态。

本任务只整改批量导入异常边界，不修改工票业务公式，不修改接口路径。

════════════════════════════════════════════════════════════════════

【二、涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py（建议新增）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py

════════════════════════════════════════════════════════════════════

【三、批量导入异常分类规则】

接口：

- POST /api/workshop/tickets/batch

必须区分两类异常。

第一类：行级业务失败，可以进入 `failed_items`，批次响应可保持 `200/code=0`。

允许进入 `failed_items` 的错误码：

| 错误码 | 场景 |
| --- | --- |
| WORKSHOP_INVALID_QTY | 单行数量非法 |
| WORKSHOP_JOB_CARD_NOT_FOUND | 单行 Job Card 不存在 |
| WORKSHOP_EMPLOYEE_NOT_FOUND | 单行 Employee 不存在或无效 |
| WORKSHOP_JOB_CARD_STATUS_INVALID | 单行 Job Card 状态不允许登记 |
| WORKSHOP_PROCESS_MISMATCH | 单行工序与 Job Card 不一致 |
| WORKSHOP_ITEM_MISMATCH | 单行请求 item_code 与 Job Card 派生 item_code 不一致 |
| WORKSHOP_WAGE_RATE_NOT_FOUND | 单行未找到生效工价 |
| WORKSHOP_IDEMPOTENCY_CONFLICT | 单行幂等键冲突且 payload 不一致 |
| WORKSHOP_REVERSAL_EXCEEDS_REGISTERED | 单行撤销数量超过可撤销数量 |
| AUTH_FORBIDDEN | 单行资源级 item_code/company 越权，且权限来源可用 |

第二类：系统级失败，必须中断批次并向上抛标准错误响应，禁止进入 `failed_items`。

必须中断批次的错误码：

| 错误码 | HTTP 状态 | 场景 |
| --- | --- | --- |
| AUTH_UNAUTHORIZED | 401 | 未登录 |
| AUTH_FORBIDDEN | 403 | 缺少 `workshop:ticket_batch` 动作权限 |
| PERMISSION_SOURCE_UNAVAILABLE | 503 | ERPNext 权限来源不可用 |
| ERPNEXT_SERVICE_UNAVAILABLE | 503 | ERPNext 服务整体不可用、超时或连接失败 |
| AUDIT_WRITE_FAILED | 500 | 安全审计或操作审计写入失败 |
| DATABASE_WRITE_FAILED | 500 | 本地数据库写失败，包括 flush/commit/事务退出失败 |
| DATABASE_READ_FAILED | 500 | 本地数据库读失败 |
| WORKSHOP_INTERNAL_ERROR | 500 | 未知程序异常 |

关键规则：

1. `DatabaseWriteFailed` / `DATABASE_WRITE_FAILED` 禁止进入 `failed_items`。
2. `PermissionSourceUnavailable` / `PERMISSION_SOURCE_UNAVAILABLE` 禁止进入 `failed_items`。
3. `AuditWriteFailed` / `AUDIT_WRITE_FAILED` 禁止进入 `failed_items`。
4. `ERPNEXT_SERVICE_UNAVAILABLE` 禁止进入 `failed_items`，除非能明确证明只是某个 Job Card 不存在；连接失败、超时、认证失败属于系统级。
5. 未知异常禁止进入 `failed_items`。

════════════════════════════════════════════════════════════════════

【四、批量导入处理流程】

推荐流程：

1. 请求进入后先校验登录态。

失败：返回 401，不进入行处理。

2. 校验 `workshop:ticket_batch` 动作权限。

失败：返回 403，不进入行处理。

3. 获取 ERPNext User Permission / 权限聚合结果。

失败：返回 503，code = PERMISSION_SOURCE_UNAVAILABLE，不进入行处理。

4. 校验批次基础格式。

- tickets 不能为空。
- tickets 数量不得超过系统上限。
- 每行必须有 ticket_key、job_card、employee、process_name、qty、work_date。

5. 逐行处理业务校验。

行级业务错误进入 `failed_items`。

6. 逐行资源权限校验。

- 资源级 `AUTH_FORBIDDEN` 可进入该行 `failed_items`。
- 必须写安全审计。
- 不得写该行工票。

7. 写入授权且业务校验通过的行。

8. 如果任何数据库写失败、审计写失败、权限源失败、ERPNext 系统失败、未知异常发生：

- 中断批次。
- 回滚本次批量导入中尚未提交的业务写入。
- 返回对应标准错误响应。
- 不返回 `200/code=0`。

9. 如果只有行级业务失败，没有系统级失败：

返回：

{
  "code": "0",
  "message": "success",
  "data": {
    "success_count": 1,
    "failed_count": 1,
    "success_items": [],
    "failed_items": []
  }
}

10. `failed_items` 必须包含：

- row_index
- ticket_key
- error_code
- message

禁止包含：

- Python traceback
- SQL 原文
- SQL 参数
- Token / Cookie / password / secret

════════════════════════════════════════════════════════════════════

【五、事务要求】

1. 系统级异常发生时，本次批量导入必须整体失败。

2. 如已开始数据库事务，系统级异常必须 rollback。

3. rollback 失败不得覆盖原始错误码。

4. 行级业务失败不得写入该行工票。

5. 行级业务失败不得影响其他合法行继续处理。

6. 资源级越权行不得写入工票、不得更新日薪、不得同步 Job Card。

7. 系统级异常不得伪装为行级失败。

8. 批量导入结果必须能回答：

- 这是业务数据有问题，还是系统不可用？
- 哪些行成功，哪些行失败？
- 是否存在数据库或权限源故障？

════════════════════════════════════════════════════════════════════

【六、审计要求】

1. 批量导入开始不要求单独审计。

2. 每条成功写入的工票必须写操作审计，或批量写一条操作审计并包含成功行摘要。

3. 每条资源级越权行必须写安全审计。

4. 动作权限不足必须写安全审计，并返回 403。

5. 权限来源不可用必须写安全审计，并返回 503。

6. 审计写入失败属于系统级异常：

- 返回 500
- code = AUDIT_WRITE_FAILED
- 禁止进入 failed_items

7. 审计日志和普通日志必须脱敏。

8. request_id 必须使用规范化后的值，且拦截语义敏感词。

════════════════════════════════════════════════════════════════════

【七、测试必须覆盖的审计探针】

1. 数据库写失败不能进 failed_items。

模拟：

- batch 第 1 行业务合法。
- 写入时抛 DatabaseWriteFailed。

期望：

- HTTP 500
- code = DATABASE_WRITE_FAILED
- 响应不是 `code=0`
- failed_items 不存在或为空
- 本批次业务写入回滚

2. 权限来源不可用不能进 failed_items。

模拟：

- 获取 ERPNext User Permission 抛 PermissionSourceUnavailable。

期望：

- HTTP 503
- code = PERMISSION_SOURCE_UNAVAILABLE
- 不进入逐行处理
- 不返回 `code=0`

3. 审计写入失败不能进 failed_items。

模拟：

- 工票业务写入成功后操作审计写入失败。

期望：

- HTTP 500
- code = AUDIT_WRITE_FAILED
- 本批次业务写入回滚
- 不返回 `code=0`

4. 未知异常不能进 failed_items。

模拟：

- 行处理过程中抛 RuntimeError。

期望：

- HTTP 500
- code = WORKSHOP_INTERNAL_ERROR
- 不返回 `code=0`

5. 行级业务错误可以进 failed_items。

模拟：

- 第 1 行 qty <= 0。
- 第 2 行合法。

期望：

- HTTP 200
- code = 0
- success_count = 1
- failed_count = 1
- failed_items[0].error_code = WORKSHOP_INVALID_QTY

6. 行级资源越权可以进 failed_items，但必须写安全审计。

模拟：

- 用户仅授权 ITEM-B。
- 第 1 行 Job Card 派生 ITEM-A。
- 第 2 行 Job Card 派生 ITEM-B。

期望：

- HTTP 200
- code = 0
- ITEM-A 行 failed_items.error_code = AUTH_FORBIDDEN
- ITEM-B 行成功
- ITEM-A 行写安全审计

════════════════════════════════════════════════════════════════════

【八、验收标准】

□ `POST /api/workshop/tickets/batch` 缺登录态时返回 401，code = AUTH_UNAUTHORIZED，不进入行处理。

□ `POST /api/workshop/tickets/batch` 缺 `workshop:ticket_batch` 动作权限时返回 403，code = AUTH_FORBIDDEN，不进入行处理。

□ 权限来源不可用时返回 503，code = PERMISSION_SOURCE_UNAVAILABLE，不进入 failed_items。

□ 数据库写失败时返回 500，code = DATABASE_WRITE_FAILED，不进入 failed_items。

□ 数据库读失败时返回 500，code = DATABASE_READ_FAILED，不进入 failed_items。

□ 审计写入失败时返回 500，code = AUDIT_WRITE_FAILED，不进入 failed_items。

□ ERPNext 服务整体不可用时返回 503，code = ERPNEXT_SERVICE_UNAVAILABLE，不进入 failed_items。

□ 未知异常时返回 500，code = WORKSHOP_INTERNAL_ERROR，不进入 failed_items。

□ qty <= 0 的行级业务错误进入 failed_items，批次可继续处理其他合法行。

□ Job Card 不存在的行级业务错误进入 failed_items，批次可继续处理其他合法行。

□ Employee 不存在的行级业务错误进入 failed_items，批次可继续处理其他合法行。

□ 幂等冲突的行级业务错误进入 failed_items，批次可继续处理其他合法行。

□ 资源级越权行进入 failed_items，且写入 ly_security_audit_log。

□ 系统级异常响应不包含 success_count / failed_count，避免调用方误判为业务行失败。

□ failed_items 不包含 traceback、SQL 原文、SQL 参数、Token、Cookie、password、secret。

□ 普通日志和审计日志不包含 Token、Cookie、password、secret、SQL 原文、SQL 参数。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。

════════════════════════════════════════════════════════════════════

【九、禁止事项】

1. 禁止把 `DatabaseWriteFailed` 包装成 `failed_items`。

2. 禁止把 `PermissionSourceUnavailable` 包装成 `failed_items`。

3. 禁止把 `AuditWriteFailed` 包装成 `failed_items`。

4. 禁止把未知异常包装成 `failed_items`。

5. 禁止系统级异常返回 `200/code=0`。

6. 禁止系统级异常响应包含 `success_count/failed_count`。

7. 禁止系统级异常发生后继续处理后续行。

8. 禁止系统级异常发生后提交部分业务写入。

9. 禁止吞掉异常只写日志不返回标准错误码。

10. 禁止删除 TASK-003A/TASK-003B 已完成的资源级权限校验。

════════════════════════════════════════════════════════════════════

【十、完成后回复格式】

请工程师完成后按以下格式回复：

TASK-003C 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- 批量导入已区分行级业务失败和系统级失败
- DATABASE_WRITE_FAILED 不再进入 failed_items
- PERMISSION_SOURCE_UNAVAILABLE 不再进入 failed_items
- AUDIT_WRITE_FAILED 不再进入 failed_items
- WORKSHOP_INTERNAL_ERROR 不再进入 failed_items
- 系统级异常不再返回 200/code=0
- 行级业务失败仍支持 partial success

自测结果：
- 数据库写失败返回 DATABASE_WRITE_FAILED：通过 / 不通过
- 权限来源不可用返回 PERMISSION_SOURCE_UNAVAILABLE：通过 / 不通过
- 审计写入失败返回 AUDIT_WRITE_FAILED：通过 / 不通过
- 未知异常返回 WORKSHOP_INTERNAL_ERROR：通过 / 不通过
- qty 非法进入 failed_items 且合法行成功：通过 / 不通过
- 资源越权行进入 failed_items 且写安全审计：通过 / 不通过
- 系统级异常不返回 success_count/failed_count：通过 / 不通过
- pytest/unittest/py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
