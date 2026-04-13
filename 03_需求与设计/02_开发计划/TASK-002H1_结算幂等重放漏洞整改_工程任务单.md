# TASK-002H1 结算幂等重放漏洞整改工程任务单

- 任务编号：TASK-002H1
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 15:26 CST
- 作者：技术架构师
- 审计来源：TASK-002H 审计意见书第 51 份不通过，P1 为锁定/释放共用 `settlement_request_id` 导致“锁定 K -> 释放 R -> 旧锁定 K 重试”重新锁定的状态重放漏洞；P2 为 API 允许 128 字符幂等键但数据库字段仅 64 字符
- 架构裁决：结算幂等改为 append-only 操作表；候选/预览 `summary` 统一定义为筛选条件全量汇总，不是当前页汇总
- 前置依赖：TASK-002H 本轮不通过；继续遵守外发模块 V1.19 与 ADR-047
- 任务边界：只修结算锁定/释放幂等重放、幂等键长度契约、summary 语义；不得新增加工厂对账单主表、应付、付款、GL 或 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H1
模块：结算幂等重放漏洞整改
优先级：P1（结算安全阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复外发结算锁定/释放使用可变字段做幂等导致旧请求可重放的问题，确保 release 后旧 lock 重试不能把已释放明细重新锁回去。

【模块概述】
TASK-002H 已实现候选、预览、锁定和释放接口，但把锁定和释放的幂等键都写在 inspection 行的 `settlement_request_id` 上。释放会覆盖锁定 key，导致旧锁定请求网络重试时无法识别历史操作，会把已释放的 `unsettled` 行重新变成 `statement_locked`。结算状态属于财务前置状态，必须使用不可变、可追溯的操作记录锁定幂等历史。

【涉及文件】
必须新增或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/alembic/versions/[new]_subcontract_settlement_operation_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限复用测试 fixture）

【数据库设计】
新增 append-only 操作表：`ly_schema.ly_subcontract_settlement_operation`

| 字段 | 类型 | 要求 | 说明 |
| --- | --- | --- | --- |
| `id` | BigInteger | PK | 操作记录 ID |
| `operation_type` | String(16) | not null | `lock/release` |
| `idempotency_key` | String(128) | not null | 请求幂等键 |
| `request_hash` | String(64) | not null | 语义 payload hash |
| `statement_id` | BigInteger/null | nullable | 对账单 ID |
| `statement_no` | String(64)/null | nullable | 对账单号 |
| `inspection_ids_json` | JSON | not null | 排序后的 inspection_ids 快照 |
| `result_status` | String(32) | not null | `succeeded/conflict/failed`，成功操作写 `succeeded` |
| `affected_inspection_ids_json` | JSON | not null | 实际影响行 ID 快照 |
| `response_json` | JSON | nullable | 脱敏后的成功响应快照 |
| `operator` | String(140) | not null | 操作者 |
| `request_id` | String(140) | nullable | request id |
| `created_at` | DateTime | not null | 创建时间 |

索引与约束：
1. `uk_ly_subcontract_settlement_operation_idem(operation_type, idempotency_key)` 唯一。
2. `idx_ly_subcontract_settlement_operation_statement(statement_id, statement_no, operation_type)`。
3. `idx_ly_subcontract_settlement_operation_created(created_at)`。
4. `idempotency_key` 长度统一为 128 字符，Schema、模型、迁移必须一致。
5. 操作表 append-only，成功记录不得被后续 lock/release 覆盖或删除。

【幂等规则】
1. lock 和 release 使用不同幂等命名空间：`operation_type + idempotency_key` 唯一。
2. `request_hash = hash(operation_type + statement_id + statement_no + sorted(inspection_ids))`。
3. 同一 `operation_type + idempotency_key` 且 `request_hash` 相同：返回第一次成功响应，不再次修改 inspection 行。
4. 同一 `operation_type + idempotency_key` 但 `request_hash` 不同：返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。
5. lock K 成功后 release R 成功，再重试 lock K：必须返回第一次 lock 的响应或明确幂等历史结果，但不得重新锁定 inspection 行。
6. release R 成功后重复 release R：返回第一次 release 的响应，不再次修改 inspection 行。
7. 旧 lock K 重试时，如果目标 inspection 已经 `unsettled` 且操作表存在 K 成功记录，不得把行改回 `statement_locked`。
8. 操作表记录写入和 inspection 状态变更必须在同一事务内提交。
9. 操作表写入失败必须 rollback inspection 状态变更。
10. inspection 上的 `settlement_request_id` 不再作为幂等历史权威；可保留为最后操作 request id 的展示/追踪字段，但不得用于幂等判断。

【summary 语义裁决】
1. `GET /api/subcontract/settlement-candidates` 返回的 `summary` 必须是当前筛选条件下全量候选汇总，不是当前页汇总。
2. `POST /api/subcontract/settlement-preview` 返回的 `summary` 必须是请求指定明细或筛选条件的全量汇总。
3. 如果实现暂时只能返回分页汇总，字段名必须改成 `page_summary`，并新增 `filter_summary` 作为全量汇总；不得用 `summary` 表示当前页导致财务误读。
4. 推荐本轮直接实现全量数据库聚合，输出 `summary`。
5. `summary` 聚合必须在同一资源权限过滤条件下执行。

【错误码】
必须新增或确认：
1. `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`
2. `SUBCONTRACT_SETTLEMENT_OPERATION_NOT_FOUND`（可选）
3. `DATABASE_READ_FAILED`
4. `DATABASE_WRITE_FAILED`

【验收标准】
□ 新增 `ly_subcontract_settlement_operation` append-only 操作表。  
□ `operation_type + idempotency_key` 唯一约束生效。  
□ `idempotency_key` Schema、模型、迁移长度统一为 128。  
□ lock 成功会写一条 operation 记录，且 response_json 脱敏。  
□ release 成功会写一条 operation 记录，且 response_json 脱敏。  
□ lock K 成功 -> release R 成功 -> 重试 lock K，不得重新锁定 inspection。  
□ release R 成功 -> 重试 release R，不得再次修改 inspection。  
□ 同 key 不同 payload 返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。  
□ operation 写入失败时 inspection 锁定/释放必须 rollback。  
□ inspection.settlement_request_id 不再作为幂等历史判断依据。  
□ `GET /api/subcontract/settlement-candidates` 的 `summary` 是筛选条件全量汇总，或明确拆成 `page_summary/filter_summary`。  
□ summary 聚合与候选列表使用同一权限过滤条件。  
□ 不创建 factory_statement 表。  
□ 不调用 ERPNext 写接口。  
□ 不修改发料、回料、验货、retry 既有业务逻辑。  
□ `.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py` 通过。  
□ `.venv/bin/python -m pytest -q` 通过。  
□ `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。  

【必须新增或补齐的测试】
1. `test_settlement_lock_release_then_old_lock_retry_does_not_relock`
2. `test_settlement_release_retry_returns_first_result_without_mutation`
3. `test_settlement_same_idempotency_key_different_payload_conflicts`
4. `test_settlement_operation_record_is_append_only`
5. `test_settlement_operation_write_failure_rolls_back_lock`
6. `test_settlement_operation_write_failure_rolls_back_release`
7. `test_settlement_idempotency_key_accepts_128_chars`
8. `test_settlement_idempotency_key_rejects_over_128_chars`
9. `test_settlement_summary_is_filter_total_not_page_total`
10. `test_settlement_summary_uses_same_resource_filter_as_candidates`

【禁止事项】
- 禁止继续把 inspection.settlement_request_id 作为唯一幂等凭据。
- 禁止 release 覆盖 lock 幂等历史。
- 禁止旧 lock 请求在 release 后重新修改 inspection 状态。
- 禁止创建加工厂对账单主表。
- 禁止创建 ERPNext Purchase Invoice、Payment Entry、GL Entry。
- 禁止调用 ERPNext 写接口。
- 禁止重算历史 inspection 金额。
- 禁止在 operation.response_json 中保存 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。

【前置依赖】
TASK-002H 审计意见书第 51 份不通过；必须完成本任务并通过审计后，才允许继续 TASK-002H 封版。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
