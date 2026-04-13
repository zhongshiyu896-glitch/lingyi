# TASK-002E 回料 Stock Entry Outbox 工程任务单

- 任务编号：TASK-002E
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.1
- 更新时间：2026-04-13 12:31 CST
- 作者：技术架构师
- 审计来源：TASK-002D1 审计通过，允许进入 TASK-002E；审计官已确认回料 outbox 开发边界
- 前置依赖：TASK-002A/B1/C1/D1 已通过；继续遵守外发模块 V1.8 与 ADR-030/031/032/033/034/035/036
- 任务边界：只实现外发回料 `Material Receipt` 的本地回料事实、Stock Entry outbox、内部 worker 和重试；不得实现验货扣款金额口径、加工厂对账单、结算逻辑

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002E
模块：回料 Stock Entry Outbox
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现外发回料的本地事实写入和 ERPNext `Stock Entry / Material Receipt` outbox 异步同步，确保回料重复提交不重复入账，ERPNext 写入不发生在本地业务事务内。

【模块概述】
外发回料是加工厂完成加工后，将成品、半成品或加工结果回入本厂仓库的库存动作。FastAPI 负责记录回料业务事实和 `stock_action='receipt'` outbox，ERPNext 继续作为库存事实源，由内部 worker 在本地事务提交后创建并提交 `Stock Entry / Material Receipt`。本任务要把此前 fail closed 的 `receive` 路径升级为正式回料 outbox 路径，同时复用 TASK-002D1 已通过的幂等前置、event_key 稳定、ERPNext docstatus 校验和 worker 短事务规则。本任务不允许恢复验货成功路径，不允许引入扣款、对账、结算金额。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002c_subcontract_company_and_schema.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts（仅允许补回料 outbox 状态字段类型，不做验货/对账 UI）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_receipt | 外发回料事实，一次回料请求生成一条或多条回料事实 | `id, subcontract_id, company, receipt_batch_no, receipt_warehouse, item_code, color, size, batch_no, uom, received_qty, stock_outbox_id, sync_status, sync_error_code, idempotency_key, payload_hash, received_by, received_at` | `idx_ly_subcontract_receipt_company_order(company,subcontract_id)`；`idx_ly_subcontract_receipt_outbox(stock_outbox_id)`；`idx_ly_subcontract_receipt_idempotency(subcontract_id,idempotency_key)` |
| ly_schema.ly_subcontract_stock_outbox | ERPNext Stock Entry 回料同步任务，一次回料请求生成一条 outbox | `id, event_key, subcontract_id, company, supplier, item_code, warehouse, stock_action, idempotency_key, payload_hash, payload_json, status, attempts, max_attempts, next_retry_at, locked_by, locked_at, lease_until, stock_entry_name, last_error_code, last_error_message, request_id, created_by, created_at, updated_at` | 复用 `uk_ly_subcontract_stock_outbox_event_key`；复用 `uk_ly_subcontract_stock_outbox_idempotency(subcontract_id,stock_action,idempotency_key)`；复用 `idx_ly_subcontract_outbox_due(stock_action,status,next_retry_at,id)`；复用 `idx_ly_subcontract_outbox_scope(company,supplier,item_code,warehouse,stock_action,status,next_retry_at)` |
| ly_schema.ly_subcontract_stock_sync_log | 每次 ERPNext Stock Entry 同步尝试日志 | `id, outbox_id, subcontract_id, company, stock_action, attempt_no, erpnext_status, stock_entry_name, error_code, error_message, request_id, created_at` | `idx_ly_subcontract_sync_log_outbox(outbox_id,attempt_no)`；`idx_ly_subcontract_sync_log_company(company,created_at)` |
| ly_schema.ly_subcontract_status_log | 外发状态流转日志 | `id, subcontract_id, company, from_status, to_status, action, operator, request_id, before_data, after_data, created_at` | `idx_ly_subcontract_status_log_company_order(company,subcontract_id,created_at)` |

【outbox 字段要求】
1. `stock_action` 本任务启用 `receipt`；发料继续使用 `issue`。
2. `event_key` 必须使用稳定 hash，不得截断 digest；推荐格式：`sio:<64位sha256>`。
3. `event_key` 输入必须以幂等事件为单位，至少包含：`stock_action, subcontract_id, idempotency_key, stable_payload_hash`。
4. `event_key` 不得包含易变字段 `receipt_batch_no/request_id/outbox_id/created_at/operator`。
5. `receipt_batch_no` 是本地回料批次号，只用于业务展示和 receipt 分组，不参与 `event_key`。
6. `payload_json` 必须保存创建 ERPNext `Stock Entry / Material Receipt` 所需的脱敏业务 payload，包括 company、target warehouse、items、custom fields。
7. `payload_hash` 用于幂等冲突判断；相同 idempotency key 但 payload hash 不同，返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
8. `stock_entry_name` 只允许写 ERPNext 返回的真实 Stock Entry name，禁止生成 `STE-REC-*` 或任何伪号。
9. `last_error_message` 必须脱敏，禁止 SQL、Authorization、Cookie、token、password、secret、ERPNext 响应原文敏感字段。

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 回料创建 outbox | POST | `/api/subcontract/{id}/receive` | `receipt_warehouse, received_qty, idempotency_key, color?, size?, batch_no?, uom?` | `{receipt_batch_no,outbox_id,sync_status,stock_entry_name:null}` |
| 外发详情 | GET | `/api/subcontract/{id}` | `id` | 返回回料明细、receipt outbox 状态、真实 `stock_entry_name` |
| 内部库存同步 Worker | POST | `/api/subcontract/internal/stock-sync/run-once` | `limit,dry_run,include_forbidden_diagnostics,stock_action?` | 可处理 `issue/receipt`；必须按 action 分派 |
| 回料同步重试 | POST | `/api/subcontract/{id}/stock-sync/retry` | `outbox_id,idempotency_key` | `{outbox_id,status,next_retry_at}`；允许 receipt outbox |
| 验货 | POST | `/api/subcontract/{id}/inspect` | 原入参 | 继续 fail closed，不实现 TASK-002F |

【回料业务规则】
1. `POST /api/subcontract/{id}/receive` 必须校验当前用户、动作权限 `subcontract:receive`、本地 `order.company` 资源权限、`item_code/supplier/receipt_warehouse` 资源权限。
2. 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得落回料事实，不得写 outbox。
3. 外发单 `resource_scope_status='blocked_scope'` 时返回 `SUBCONTRACT_SCOPE_BLOCKED`。
4. 外发单 `settlement_status=settled` 时返回 `SUBCONTRACT_SETTLEMENT_LOCKED`。
5. `draft` 状态禁止回料；允许回料状态为 `issued/processing/waiting_receive/waiting_inspection`。`waiting_inspection` 允许继续分批回料，但不得触发验货成功路径。
6. `completed/cancelled` 禁止回料。
7. 回料 item 默认为 `order.item_code`，禁止前端提交任意 item 成为事实。
8. `received_qty > 0`。
9. 默认禁止超收：`received_qty <= planned_qty - received_qty_already_recorded`。
10. 若后续业务需要允许超收，必须另出 ADR，不得在本任务私自放开。
11. 一次回料请求生成一个 `receipt_batch_no`、一条 `stock_action='receipt'` outbox、一组 `ly_subcontract_receipt` 回料事实。
12. 本地事务内写回料事实、主单 `received_qty` 汇总、状态日志、操作审计、outbox；本地事务内禁止调用 ERPNext。
13. 本地回料事实和 receipt outbox 必须同事务提交；commit 失败不得调用 ERPNext。
14. 回料入列成功后，外发单状态可推进到 `waiting_inspection`；`waiting_inspection` 状态下仍可继续登记后续分批回料；但验货接口在 TASK-002E 阶段仍必须 fail closed。
15. 相同 `idempotency_key` + 相同 payload 重复提交，返回第一次结果，不新增 receipt，不新增 outbox，不调用 ERPNext。
16. 相同 `idempotency_key` + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
17. 幂等检查必须前置到剩余可回数量校验之前。
18. `event_key` 必须稳定命中同一幂等事件，不得包含 `receipt_batch_no`。

【Worker 业务规则】
1. Worker 必须明确区分 `stock_action='issue'` 与 `stock_action='receipt'`，不得用 issue handler 处理 receipt。
2. Worker 可通过 `stock_action` 入参限制处理范围；未传时可处理 due 的 issue 和 receipt，但必须按 action 分派。
3. Worker 处理 receipt 时创建并提交 ERPNext `Stock Entry / Material Receipt`。
4. Worker 主查询必须先按服务账号资源 scope 过滤，再 limit。
5. Worker 未开启、dry-run 未开启、权限源不可用、服务账号越权必须 fail closed。
6. Worker claim/ERPNext/result 回写继续沿用 TASK-002D1 短事务规则。
7. ERPNext 网络调用期间不得持有数据库事务或行锁。
8. Worker 创建 ERPNext Stock Entry 时必须写入 `custom_ly_subcontract_no/custom_ly_subcontract_outbox_id/custom_ly_outbox_event_key/custom_ly_stock_action='receipt'`。
9. ERPNext Stock Entry 必须创建并提交，提交成功后才能标记 outbox `succeeded`。
10. 重试前必须按 `custom_ly_outbox_event_key` 查询 ERPNext 是否已有 Stock Entry。
11. 找到 `docstatus=1`：可补本地 succeeded。
12. 找到 `docstatus=0`：必须 submit 原 draft 单，submit 成功后才能本地 succeeded。
13. 找到 `docstatus=2` 或未知 docstatus：不得本地成功。
14. 相同 event_key 查到多张 ERPNext Stock Entry 时必须 fail closed。
15. ERPNext 创建成功但本地回写失败时，下一次 worker 必须通过 event_key 找回原单，避免重复入账。
16. 每次尝试必须写 `ly_subcontract_stock_sync_log`。
17. Worker 成功、失败、dry-run 成功必须写操作审计；401/403/503 必须写安全审计。
18. Worker 响应不得包含 ERPNext token、Cookie、Authorization、完整异常堆栈或 SQL 原文。

【ERPNext Stock Entry Payload】
必须使用 ERPNext REST API 创建并提交：

```json
{
  "doctype": "Stock Entry",
  "stock_entry_type": "Material Receipt",
  "company": "<order.company>",
  "custom_ly_subcontract_no": "<subcontract_no>",
  "custom_ly_subcontract_outbox_id": "<outbox_id>",
  "custom_ly_outbox_event_key": "<event_key>",
  "custom_ly_stock_action": "receipt",
  "items": [
    {
      "item_code": "<order.item_code>",
      "qty": "<received_qty>",
      "uom": "<uom>",
      "t_warehouse": "<receipt_warehouse>",
      "batch_no": "<batch_no optional>"
    }
  ]
}
```

【错误码】
必须新增或补齐：
- `SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED`
- `SUBCONTRACT_RECEIPT_QTY_EXCEEDED`
- `SUBCONTRACT_RECEIPT_ITEM_INVALID`
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_INVALID_QTY`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `SUBCONTRACT_SETTLEMENT_LOCKED`
- `SUBCONTRACT_WORKER_DISABLED`
- `SUBCONTRACT_DRY_RUN_DISABLED`
- `ERPNEXT_CUSTOM_FIELD_MISSING`
- `ERPNEXT_STOCK_ENTRY_CANCELLED`
- `ERPNEXT_STOCK_ENTRY_STATUS_INVALID`
- `ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY`
- `ERPNEXT_STOCK_ENTRY_CREATE_FAILED`
- `ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`
- `PERMISSION_SOURCE_UNAVAILABLE`

【验收标准】
□ `POST /api/subcontract/{id}/receive` 权限通过后能创建 `ly_subcontract_receipt` 回料事实。  
□ `POST /api/subcontract/{id}/receive` 能创建一条 `stock_action='receipt'` 的 `ly_subcontract_stock_outbox`。  
□ 回料接口本地事务内不调用 ERPNext。  
□ 回料事实和 receipt outbox 同事务提交；commit 失败不得调用 ERPNext。  
□ 回料接口返回 `outbox_id`、`receipt_batch_no`、`sync_status='pending'`，`stock_entry_name` 为 null。  
□ 相同 idempotency key + 相同 payload 重复提交，不新增 receipt，不新增 outbox。  
□ 相同 idempotency key + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ 幂等检查前置，已全量回料后同 key 重试不返回超收错误。  
□ `event_key` 不包含 `receipt_batch_no`，同一幂等事件重试稳定命中同一 outbox。  
□ `draft` 状态调用回料返回 `SUBCONTRACT_STATUS_INVALID`。  
□ 回料数量超过剩余可回数量返回 `SUBCONTRACT_RECEIPT_QTY_EXCEEDED`。  
□ 无 receipt warehouse 权限返回 `AUTH_FORBIDDEN`，不落库。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不落库。  
□ `blocked_scope` 外发单不能回料。  
□ `settlement_status=settled` 外发单不能回料。  
□ Worker 可处理 `stock_action='receipt'`，并使用 Material Receipt payload。  
□ Worker 不用 issue handler 处理 receipt outbox。  
□ Worker 主查询先按服务账号资源 scope 过滤，再 limit。  
□ 普通外发角色不能调用内部 worker。  
□ Worker dry-run 不锁定 outbox、不增加 attempts、不调用 ERPNext、写操作审计。  
□ Worker 正式执行能创建并提交 ERPNext `Stock Entry / Material Receipt`。  
□ ERPNext 成功后 outbox 标记 `succeeded`，回写真实 `stock_entry_name`。  
□ ERPNext 成功后 receipt `sync_status` 更新为 `succeeded`。  
□ ERPNext 成功后写 `ly_subcontract_stock_sync_log` 成功记录。  
□ `find_by_event_key()` 返回 `docstatus=0` 时，worker submit existing draft，submit 成功后本地 succeeded。  
□ `find_by_event_key()` 返回 `docstatus=2` 或未知状态时，不得本地 succeeded。  
□ 相同 event_key 查到多个 ERPNext 单据时 fail closed。  
□ ERPNext 超时或 5xx 时 outbox 标记 `failed`，设置 `next_retry_at`，不写伪 Stock Entry。  
□ ERPNext 业务校验失败超过最大次数后 outbox 进入 `dead`。  
□ ERPNext 已创建但本地回写失败后，下一次 worker 能按 `event_key` 找回原 Stock Entry，不重复创建。  
□ Worker 并发执行不会重复处理同一 receipt outbox。  
□ `inspect` 仍保持 fail closed，不新增验货事实、不写金额、不推进 completed。  
□ 业务代码扫描不出现 `STE-REC-*`、`STE-ISS-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 响应、普通日志、安全审计、操作审计不泄露 SQL 原文、Authorization、Cookie、token、password、secret。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_receive_creates_receipt_rows_and_pending_outbox`
2. `test_receive_does_not_call_erpnext_before_commit`
3. `test_receive_returns_outbox_without_fake_stock_entry_name`
4. `test_receive_idempotent_same_payload_returns_existing_result`
5. `test_receive_idempotency_key_different_payload_returns_conflict`
6. `test_receive_event_key_excludes_receipt_batch_no`
7. `test_receive_idempotent_retry_after_full_receipt_does_not_check_remaining_qty_first`
8. `test_receive_rejects_draft_order`
9. `test_receive_rejects_qty_exceeding_remaining_receivable_qty`
10. `test_receive_forbidden_when_receipt_warehouse_not_allowed`
11. `test_receive_permission_source_unavailable_fails_closed`
12. `test_receive_blocked_scope_order_rejected`
13. `test_receive_settled_order_rejected`
14. `test_stock_worker_processes_receipt_outbox_as_material_receipt`
15. `test_stock_worker_does_not_process_receipt_with_issue_handler`
16. `test_stock_worker_receipt_writes_custom_ly_trace_fields`
17. `test_stock_worker_receipt_find_existing_docstatus_1_marks_succeeded_without_create`
18. `test_stock_worker_receipt_find_existing_docstatus_0_submits_draft_then_succeeds`
19. `test_stock_worker_receipt_find_existing_docstatus_2_does_not_succeed`
20. `test_stock_worker_receipt_duplicate_event_key_fails_closed`
21. `test_stock_worker_receipt_result_write_failure_recovered_by_event_key_next_run`
22. `test_stock_worker_receipt_concurrent_run_does_not_double_process_outbox`
23. `test_stock_worker_receipt_erpnext_timeout_marks_failed_with_retry`
24. `test_stock_worker_receipt_business_validation_dead_after_max_attempts`
25. `test_task_002e_does_not_restore_inspect_success_path`
26. `test_subcontract_receipt_stock_logs_are_sanitized`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q tests/test_subcontract_receive_outbox.py tests/test_subcontract_stock_worker.py tests/test_subcontract_stock_outbox_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|STE-REC|net_amount = .*inspected_qty|detail=str\(exc\)|Authorization|Cookie|password|secret" app migrations tests
```

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Warehouse` | REST API 或共享 PostgreSQL 只读 | 校验回料仓存在、未禁用、用户有权限 |
| `Item` | REST API 或共享 PostgreSQL 只读 | 校验回料 item 为外发单 item，未禁用 |
| `Stock Entry` | REST API 创建 + submit | 创建并提交 `Material Receipt`，回写真实 `stock_entry_name` |
| `Stock Entry` 查找 | REST API GET | 按 `custom_ly_outbox_event_key` 查询 name/docstatus，防重复入账 |
| `User Permission` | ERPNext 权限聚合 | 服务账号按 company/item/supplier/warehouse 过滤 outbox |

【前置依赖】
- TASK-002D1：发料 outbox、幂等、docstatus、短事务已通过审计。
- ADR-036：外发回料必须通过 outbox 异步创建 ERPNext Material Receipt。

【交付物】
1. 回料 outbox 字段、索引、约束补齐。
2. `receive` 本地回料事实 + receipt outbox 入列实现。
3. 回料幂等键、payload_hash、event_key 实现。
4. Worker receipt handler：ERPNext create/submit、docstatus 查重、回写、重试。
5. 回料安全审计、操作审计、日志脱敏。
6. 定向测试与全量测试结果。

【禁止事项】
1. 禁止在 TASK-002E 中实现验货扣款金额口径。
2. 禁止在 TASK-002E 中实现加工厂对账单或结算逻辑。
3. 禁止在回料接口本地事务内调用 ERPNext。
4. 禁止生成或返回伪 `STE-REC-*`、伪 `stock_entry_name`。
5. 禁止把 ERPNext draft/cancelled Stock Entry 当成同步成功。
6. 禁止同幂等键重试先做剩余可回数量校验。
7. 禁止 issue/receipt outbox handler 混用。
8. 禁止恢复 `inspect` 成功路径。
9. 禁止日志、审计、响应中泄露 SQL 原文或敏感凭证。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════

【版本记录】
| 版本 | 更新时间 | 作者 | 说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-04-13 11:01 CST | 技术架构师 | 初版 TASK-002E 回料 Stock Entry Outbox 任务单 |
| V1.1 | 2026-04-13 12:31 CST | 技术架构师 | 同步 TASK-002E1 审计确认：waiting_inspection 状态允许继续分批回料 |
