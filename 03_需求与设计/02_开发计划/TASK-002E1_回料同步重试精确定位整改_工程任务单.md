# TASK-002E1 回料同步重试精确定位整改工程任务单

- 任务编号：TASK-002E1
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 12:06 CST
- 作者：技术架构师
- 审计来源：TASK-002E 审计意见书第 41 份，结论不通过
- 前置依赖：TASK-002A/B1/C1/D1 已通过；TASK-002E 主回料 outbox 路径基本成立但未通过审计
- 任务边界：只修库存同步重试精确定位、回料 receipt 专属测试、payload hash 数量归一化和 submit 后 docstatus 确认；不得进入验货、扣款、对账、结算

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002E1
模块：回料同步重试精确定位整改
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复 `/api/subcontract/{id}/stock-sync/retry` 按订单取最新 outbox 的高危问题，改为按 `outbox_id + idempotency_key + stock_action` 精确重试目标 outbox，防止已成功回料或发料 outbox 被误重置。

【模块概述】
TASK-002E 已将回料主链路升级为本地 receipt 事实 + `stock_action='receipt'` outbox，但审计发现库存同步重试接口仍按订单选择最新 outbox。真实场景中同一外发单可能同时存在失败的 issue outbox 和成功的 receipt outbox，如果 retry 选错目标，会把已经成功的回料重新入队，造成重复库存同步风险。本任务只整改 retry 定位契约和回料专属测试，不扩大到验货、扣款、对账或结算。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 精确重试库存同步 | POST | `/api/subcontract/{id}/stock-sync/retry` | `outbox_id, stock_action, idempotency_key, reason?` | `{outbox_id, stock_action, status, next_retry_at}` |
| 内部库存同步 Worker | POST | `/api/subcontract/internal/stock-sync/run-once` | `limit,dry_run,include_forbidden_diagnostics,stock_action?` | action 分派后的处理结果 |
| 回料创建 outbox | POST | `/api/subcontract/{id}/receive` | 原 TASK-002E 入参 | 保持 TASK-002E 契约，不扩展验货/对账 |
| 验货 | POST | `/api/subcontract/{id}/inspect` | 原入参 | 继续 fail closed |

【请求结构】
`POST /api/subcontract/{id}/stock-sync/retry` 必须改为接收请求体：

```json
{
  "outbox_id": 123,
  "stock_action": "issue",
  "idempotency_key": "original-request-key",
  "reason": "manual retry after ERPNext timeout"
}
```

字段要求：
1. `outbox_id` 必填，必须是目标 `ly_subcontract_stock_outbox.id`。
2. `stock_action` 必填，只允许 `issue` 或 `receipt`。
3. `idempotency_key` 必填，必须等于目标 outbox 原始 `idempotency_key`。
4. `reason` 可选，写入操作审计，必须脱敏，最长 200 字符。

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_stock_outbox | 精确重试目标表 | `id, subcontract_id, stock_action, idempotency_key, status, attempts, next_retry_at, locked_by, locked_at, lease_until, stock_entry_name, last_error_code, last_error_message` | 复用 `uk_ly_subcontract_stock_outbox_idempotency(subcontract_id,stock_action,idempotency_key)`；按主键 `id` 精确读取 |
| ly_schema.ly_subcontract_stock_sync_log | 同步尝试日志 | `outbox_id, stock_action, attempt_no, erpnext_status, error_code, error_message` | 必须补齐或确认 `idx_ly_subcontract_sync_log_outbox(outbox_id,attempt_no)` |
| ly_schema.ly_subcontract_receipt | 回料事实 | `stock_outbox_id, sync_status, sync_error_code, stock_entry_name` | 复用 `idx_ly_subcontract_receipt_outbox(stock_outbox_id)` |
| ly_schema.ly_subcontract_material | 发料事实 | `stock_outbox_id, sync_status, sync_error_code, stock_entry_name` | 复用 outbox 关联索引 |

【业务规则】
1. retry 接口必须先鉴权：当前用户、动作权限 `subcontract:stock_sync_retry`、外发单本地 `company` 资源权限。
2. retry 接口必须精确加载 `outbox_id`，不得再按外发单取“最新 outbox”。
3. `outbox.subcontract_id` 必须等于路径 `{id}`，否则返回 `SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH`。
4. `outbox.stock_action` 必须等于请求 `stock_action`，否则返回 `SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH`。
5. `outbox.idempotency_key` 必须等于请求 `idempotency_key`，否则返回 `SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH`。
6. retry 资源权限必须使用目标 outbox 的 `company/item_code/supplier/warehouse/stock_action` 校验，不能只用订单推断。
7. 权限源不可用必须返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得修改 outbox。
8. 只允许重试 `failed/dead` 状态。
9. `succeeded/processing/pending/blocked_scope` 状态禁止重置，返回 `SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE`。
10. retry 接口只允许重置本地 outbox 状态，不得调用 ERPNext。
11. `failed` 重试：保留 attempts，清空锁字段，设置 `status='pending'`，设置 `next_retry_at=now`。
12. `dead` 人工重试：重置 attempts 为 0，清空锁字段，设置 `status='pending'`，设置 `next_retry_at=now`，并写操作审计。
13. retry 成功必须写操作审计，记录 `outbox_id/stock_action/old_status/new_status/reason/request_id/operator`。
14. retry 失败的 401/403/503 必须写安全审计。
15. 普通日志、操作审计、安全审计不得泄露 SQL 原文、Authorization、Cookie、token、password、secret、ERPNext 原始敏感响应。
16. `stable_payload_hash` 必须对数量字段做语义归一化，`10`、`10.0`、`10.000000` 必须视为同一 payload。
17. 数量归一化同时适用于发料和回料 payload，至少覆盖 `issued_qty/required_qty/received_qty/qty`。
18. Worker submit ERPNext draft 后必须确认最终 `docstatus=1`，否则不得标记本地 `succeeded`。
19. 正式确认 `waiting_inspection` 状态允许继续分批回料，但只允许继续写 receipt/outbox，不允许执行 inspect 成功路径。
20. `completed/cancelled/settled` 状态仍禁止回料。
21. `inspect` 在本任务完成后仍必须 fail closed，不新增验货事实、不写金额、不推进 completed。

【错误码】
必须新增或补齐：
- `SUBCONTRACT_STOCK_OUTBOX_REQUIRED`
- `SUBCONTRACT_STOCK_OUTBOX_NOT_FOUND`
- `SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH`
- `SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH`
- `SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH`
- `SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE`
- `SUBCONTRACT_STOCK_OUTBOX_SCOPE_FORBIDDEN`
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED`
- `ERPNEXT_STOCK_ENTRY_STATUS_INVALID`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`

【验收标准】
□ `POST /api/subcontract/{id}/stock-sync/retry` 必须要求 `outbox_id + stock_action + idempotency_key`。  
□ retry 接口不再按订单选择最新 outbox。  
□ 同一订单下 issue outbox 为 failed、receipt outbox 为 succeeded 时，重试 issue 只重置 issue outbox。  
□ 上述场景中 succeeded receipt outbox 保持 `succeeded`，不得变成 `pending`。  
□ receipt outbox 为 failed 时，按精确 `outbox_id + stock_action='receipt' + idempotency_key` 可重置为 `pending`。  
□ `succeeded` outbox 调用 retry 返回 `SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE`，不修改状态。  
□ `processing` outbox 调用 retry 返回 `SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE`，不修改锁字段。  
□ `pending` outbox 调用 retry 返回 `SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE`，不重复写审计放大。  
□ outbox 属于其他订单时返回 `SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH`。  
□ `stock_action` 不匹配时返回 `SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH`。  
□ `idempotency_key` 不匹配时返回 `SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH`。  
□ 无目标 outbox 资源权限时返回 `AUTH_FORBIDDEN`，不修改状态。  
□ 权限源不可用时返回 `PERMISSION_SOURCE_UNAVAILABLE`，不修改状态。  
□ retry 接口成功和失败均不调用 ERPNext。  
□ retry 成功写操作审计，401/403/503 写安全审计。  
□ 回料仓库无权限时 `POST /api/subcontract/{id}/receive` 返回 `AUTH_FORBIDDEN`，不落 receipt，不落 outbox。  
□ 回料权限源不可用时返回 `PERMISSION_SOURCE_UNAVAILABLE`，不落 receipt，不落 outbox。  
□ receipt duplicate event_key 必须 fail closed，不得本地 succeeded。  
□ receipt 本地结果回写失败后，下一轮 worker 能按 event_key 找回 ERPNext 单据并恢复本地状态。  
□ receipt worker 并发执行不会重复处理同一 outbox。  
□ receipt ERPNext timeout 标记 failed 并设置 retry 时间。  
□ receipt ERPNext 业务校验失败达到最大次数后进入 dead。  
□ submit draft 后必须确认 `docstatus=1`，否则返回 `ERPNEXT_STOCK_ENTRY_STATUS_INVALID` 或 `ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED`，不得本地 succeeded。  
□ `received_qty=10`、`10.0`、`10.000000` 生成相同 `payload_hash`。  
□ `issued_qty=10`、`10.0`、`10.000000` 生成相同 `payload_hash`。  
□ `waiting_inspection` 状态允许继续分批回料，但 `inspect` 仍 fail closed。  
□ 业务代码扫描不出现 `STE-REC-*`、`STE-ISS-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 响应、普通日志、安全审计、操作审计不泄露 SQL 原文、Authorization、Cookie、token、password、secret。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_stock_sync_retry_requires_outbox_id_stock_action_and_idempotency_key`
2. `test_stock_sync_retry_targets_failed_issue_when_receipt_succeeded_latest`
3. `test_stock_sync_retry_does_not_reset_succeeded_receipt_outbox`
4. `test_stock_sync_retry_targets_failed_receipt_by_exact_outbox_id`
5. `test_stock_sync_retry_rejects_succeeded_outbox`
6. `test_stock_sync_retry_rejects_processing_outbox`
7. `test_stock_sync_retry_rejects_pending_outbox`
8. `test_stock_sync_retry_rejects_wrong_stock_action`
9. `test_stock_sync_retry_rejects_wrong_idempotency_key`
10. `test_stock_sync_retry_rejects_outbox_from_other_order`
11. `test_stock_sync_retry_checks_receipt_outbox_resource_permission`
12. `test_stock_sync_retry_permission_source_unavailable_fails_closed`
13. `test_stock_sync_retry_does_not_call_erpnext`
14. `test_receive_forbidden_when_receipt_warehouse_not_allowed`
15. `test_receive_permission_source_unavailable_fails_closed`
16. `test_stock_worker_receipt_duplicate_event_key_fails_closed`
17. `test_stock_worker_receipt_result_write_failure_recovered_by_event_key_next_run`
18. `test_stock_worker_receipt_concurrent_run_does_not_double_process_outbox`
19. `test_stock_worker_receipt_erpnext_timeout_marks_failed_with_retry`
20. `test_stock_worker_receipt_business_validation_dead_after_max_attempts`
21. `test_stock_worker_receipt_submit_draft_requires_final_docstatus_1`
22. `test_receive_payload_hash_normalizes_decimal_qty_equivalents`
23. `test_issue_payload_hash_normalizes_decimal_qty_equivalents`
24. `test_receive_waiting_inspection_allows_additional_batch_receipt`
25. `test_inspect_still_fail_closed_after_task_002e1`
26. `test_retry_logs_are_sanitized`

【禁止事项】
- 禁止 retry 接口继续按外发单取最新 outbox。
- 禁止 retry 接口重置 `succeeded/processing/pending` outbox。
- 禁止 retry 接口调用 ERPNext。
- 禁止生成 `STE-ISS-*`、`STE-REC-*` 或任何伪 `stock_entry_name`。
- 禁止恢复 `inspect` 成功路径。
- 禁止引入验货金额、扣款、对账、结算逻辑。
- 禁止使用 `detail=str(exc)` 或普通日志输出 SQL/密钥/ERPNext 敏感响应。

【前置依赖】
TASK-002E 已交付但审计不通过；必须先完成本任务并通过复审，才允许进入 TASK-002F。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
