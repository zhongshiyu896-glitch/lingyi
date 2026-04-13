# TASK-002D 发料 Stock Entry Outbox 工程任务单

- 任务编号：TASK-002D
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.1
- 更新时间：2026-04-13 10:58 CST
- 作者：技术架构师
- 审计来源：TASK-002C1 审计通过，允许进入 TASK-002D；风险项要求补齐 outbox 最终字段、幂等键、事件键、Stock Entry worker 查询索引；TASK-002D1 复审通过后同步修订 `event_key` 契约
- 前置依赖：TASK-002A 已封版；TASK-002B1 已通过；TASK-002C1 已通过；继续遵守外发模块 V1.5 与 ADR-030/031/032/033/034
- 任务边界：只实现外发发料 `Material Issue` 的本地发料事实、Stock Entry outbox、内部 worker 和重试；不得实现回料 `Material Receipt`、验货扣款金额口径、加工厂对账单

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002D
模块：发料 Stock Entry Outbox
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现外发发料的本地事实写入和 ERPNext `Stock Entry / Material Issue` outbox 异步同步，确保发料重复提交不重复落账，ERPNext 写入不发生在本地业务事务内。

【模块概述】
外发发料是把本厂仓库的面辅料发给加工厂，是外发链路第一个会影响库存台账的动作。FastAPI 只沉淀外发发料事实和 outbox；ERPNext 仍是库存事实源，必须由内部 worker 在本地事务提交后创建并提交 `Stock Entry`。本任务要把 TASK-002C 的 outbox scope 骨架升级为可用于发料同步的最终结构，包括 `event_key`、`idempotency_key`、`payload_hash`、重试状态、锁定字段、ERPNext 单据回写和查询索引。本任务不做回料、验货、对账。

【涉及文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_issue_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py

修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002c_subcontract_company_and_schema.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts（仅允许补发料 outbox 状态字段类型，不做回料/验货 UI）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_material | 外发发料事实，一次发料请求可生成多行物料事实 | `id, subcontract_id, company, issue_batch_no, issue_warehouse, material_item_code, color, size, batch_no, uom, required_qty, issued_qty, remaining_qty, stock_outbox_id, sync_status, sync_error_code, idempotency_key, payload_hash, created_by, created_at` | `idx_ly_subcontract_material_company_order(company,subcontract_id)`；`idx_ly_subcontract_material_outbox(stock_outbox_id)`；`idx_ly_subcontract_material_idempotency(subcontract_id,idempotency_key)` |
| ly_schema.ly_subcontract_stock_outbox | ERPNext Stock Entry 发料同步任务，一次发料请求生成一条 outbox | `id, event_key, subcontract_id, company, supplier, item_code, warehouse, stock_action, idempotency_key, payload_hash, payload_json, status, attempts, max_attempts, next_retry_at, locked_by, locked_at, lease_until, stock_entry_name, last_error_code, last_error_message, request_id, created_by, created_at, updated_at` | `uk_ly_subcontract_stock_outbox_event_key(event_key)`；`uk_ly_subcontract_stock_outbox_idempotency(subcontract_id,stock_action,idempotency_key)`；`idx_ly_subcontract_outbox_due(stock_action,status,next_retry_at,id)`；`idx_ly_subcontract_outbox_scope(company,supplier,item_code,warehouse,stock_action,status,next_retry_at)`；`idx_ly_subcontract_outbox_stock_entry(stock_entry_name)` |
| ly_schema.ly_subcontract_stock_sync_log | 每次 ERPNext Stock Entry 同步尝试日志 | `id, outbox_id, subcontract_id, company, stock_action, attempt_no, erpnext_status, stock_entry_name, error_code, error_message, request_id, created_at` | `idx_ly_subcontract_sync_log_outbox(outbox_id,attempt_no)`；`idx_ly_subcontract_sync_log_company(company,created_at)` |
| ly_schema.ly_subcontract_status_log | 外发状态流转日志 | `id, subcontract_id, company, from_status, to_status, action, operator, request_id, before_data, after_data, created_at` | `idx_ly_subcontract_status_log_company_order(company,subcontract_id,created_at)` |

【outbox 字段要求】
1. `event_key` 必须使用稳定 hash，不得截断 digest；推荐格式：`sio:<64位sha256>`。
2. `event_key` 输入必须以幂等事件为单位，至少包含：`stock_action, subcontract_id, idempotency_key, stable_payload_hash`。
3. `event_key` 不得包含易变字段 `issue_batch_no/request_id/outbox_id/created_at/operator`。
4. `issue_batch_no` 是本地发料批次号，只用于业务展示和 material 分组，不参与 `event_key`。
5. `stock_action` 本任务只允许 `issue`；`receipt` 由 TASK-002E 实现。
6. `payload_json` 必须保存创建 ERPNext `Stock Entry` 所需的脱敏业务 payload，包括 company、source warehouse、items、custom fields。
7. `payload_hash` 用于幂等冲突判断；相同 idempotency key 但 payload hash 不同，返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
8. `last_error_message` 必须脱敏，禁止 SQL、Authorization、Cookie、token、password、secret、ERPNext 响应原文敏感字段。
9. `stock_entry_name` 只允许写 ERPNext 返回的真实 Stock Entry name，禁止生成 `STE-ISS-*` 或任何伪号。

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 发料创建 outbox | POST | `/api/subcontract/{id}/issue-material` | `issue_warehouse, items[], idempotency_key`；items 可为空，空表示按 BOM 剩余需求全量发料 | `{issue_batch_no,outbox_id,sync_status,stock_entry_name:null}` |
| 外发详情 | GET | `/api/subcontract/{id}` | `id` | 返回发料明细、outbox 状态、真实 `stock_entry_name` |
| 内部库存同步 Worker | POST | `/api/subcontract/internal/stock-sync/run-once` | `limit,dry_run,include_forbidden_diagnostics` | `{processed_count,succeeded_count,failed_count,dead_count,blocked_scope_count}` |
| 发料同步重试 | POST | `/api/subcontract/{id}/stock-sync/retry` | `outbox_id,idempotency_key` | `{outbox_id,status,next_retry_at}`；仅允许 issue outbox |
| 回料 | POST | `/api/subcontract/{id}/receive` | 原入参 | 继续 fail closed，不实现 TASK-002E |
| 验货 | POST | `/api/subcontract/{id}/inspect` | 原入参 | 继续 fail closed，不实现 TASK-002F |

【发料业务规则】
1. `POST /api/subcontract/{id}/issue-material` 必须校验当前用户、动作权限 `subcontract:issue_material`、本地 `order.company` 资源权限、`item_code/supplier/issue_warehouse` 资源权限。
2. 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得落发料事实，不得写 outbox。
3. 外发单 `resource_scope_status='blocked_scope'` 时返回 `SUBCONTRACT_SCOPE_BLOCKED`，不得发料。
4. 外发单 `settlement_status=settled` 时返回 `SUBCONTRACT_SETTLEMENT_LOCKED`。
5. 外发单状态只允许 `draft/issued/processing/waiting_receive` 发料；`completed/cancelled` 禁止发料。
6. 发料物料必须来自 BOM 展开或外发物料计划，禁止前端提交任意 `material_item_code` 成为事实。
7. `issued_qty > 0`，且不得超过该物料剩余可发数量。
8. 默认发料策略：如果请求 `items` 为空，后端按 BOM 展开剩余需求生成发料明细。
9. 部分发料允许多次执行，但每次必须使用独立 `idempotency_key`。
10. 一次发料请求生成一个 `issue_batch_no`、一条 `ly_subcontract_stock_outbox`、多条 `ly_subcontract_material`。
11. 本地事务内写发料事实、主单 `issued_qty` 汇总、状态日志、操作审计、outbox；本地事务内禁止调用 ERPNext。
12. 本地 commit 成功后，才允许 worker 异步调用 ERPNext。
13. 发料成功入列后，外发单状态可从 `draft` 推进到 `issued`；后续同步失败不回滚本地发料事实，但必须展示 `sync_status`。
14. 相同 `idempotency_key` + 相同 payload 重复提交，返回第一次结果，不新增 material，不新增 outbox，不调用 ERPNext。
15. 相同 `idempotency_key` + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。

【Worker 业务规则】
1. 内部 worker 接口生产默认关闭，必须通过 `ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API=true` 开启。
2. `dry_run=true` 生产默认禁用，除非 `SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN=true`。
3. dry-run 禁用判断必须早于 outbox 查询。
4. 调用主体必须已认证，具备 `subcontract:stock_sync_worker`，且是服务账号或明确允许的内部主体。
5. 服务账号必须按 ERPNext User Permission 限定 `company/item_code/supplier/warehouse`；权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`。
6. Worker 主查询必须先按服务账号资源 scope 过滤，再 `order by id asc limit`，越权 outbox 不得进入主处理窗口。
7. 查询条件必须限制 `stock_action='issue'`，不得处理 `receipt`。
8. Worker claim outbox 时必须使用行级锁或租约字段，避免并发重复处理。
9. Worker 不得在持有数据库长事务时调用 ERPNext；推荐 claim 提交后调用 ERPNext，再写回结果。
10. ERPNext Stock Entry 必须创建并提交，提交成功后才可标记 outbox `succeeded`。
11. ERPNext Stock Entry payload 必须包含追踪字段：`custom_ly_subcontract_no`、`custom_ly_subcontract_outbox_id`、`custom_ly_outbox_event_key`、`custom_ly_stock_action='issue'`。
12. 如果 ERPNext 自定义字段不存在或拒绝追踪字段，返回 `ERPNEXT_CUSTOM_FIELD_MISSING` 或等价错误，不得创建不可追踪库存单。
13. 重试时必须先按 `custom_ly_outbox_event_key` 查询 ERPNext 是否已存在 Stock Entry；存在则不得重复创建，直接补本地成功回写。
14. ERPNext 创建成功但本地回写失败时，下次 worker 必须通过 event_key 找回真实 Stock Entry，避免重复落账。
15. ERPNext 超时、连接失败、5xx 返回 `ERPNEXT_SERVICE_UNAVAILABLE`，outbox 标记 `failed` 并按退避重试。
16. ERPNext 业务校验失败，如库存不足、物料无效、仓库无效，必须记录脱敏错误，超过策略后进入 `dead` 或业务失败状态。
17. `attempts >= max_attempts` 后进入 `dead`，不得无限重试。
18. 每次尝试必须写 `ly_subcontract_stock_sync_log`。
19. Worker 成功、失败、dry-run 成功必须写操作审计；401/403/503 必须写安全审计。
20. Worker 响应不得包含 ERPNext token、Cookie、Authorization、完整异常堆栈或 SQL 原文。

【ERPNext Stock Entry Payload】
必须使用 ERPNext REST API 创建并提交：

```json
{
  "doctype": "Stock Entry",
  "stock_entry_type": "Material Issue",
  "company": "<order.company>",
  "custom_ly_subcontract_no": "<subcontract_no>",
  "custom_ly_subcontract_outbox_id": "<outbox_id>",
  "custom_ly_outbox_event_key": "<event_key>",
  "custom_ly_stock_action": "issue",
  "items": [
    {
      "item_code": "<material_item_code>",
      "qty": "<issued_qty>",
      "uom": "<uom>",
      "s_warehouse": "<issue_warehouse>",
      "batch_no": "<batch_no optional>"
    }
  ]
}
```

【错误码】
必须新增或补齐：
- `SUBCONTRACT_STOCK_OUTBOX_REQUIRED`
- `SUBCONTRACT_STOCK_OUTBOX_NOT_FOUND`
- `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_INVALID_QTY`
- `SUBCONTRACT_MATERIAL_NOT_IN_BOM`
- `SUBCONTRACT_MATERIAL_QTY_EXCEEDED`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `SUBCONTRACT_SETTLEMENT_LOCKED`
- `SUBCONTRACT_WORKER_DISABLED`
- `SUBCONTRACT_DRY_RUN_DISABLED`
- `ERPNEXT_CUSTOM_FIELD_MISSING`
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
□ `POST /api/subcontract/{id}/issue-material` 权限通过后能创建 `ly_subcontract_material` 发料事实。  
□ `POST /api/subcontract/{id}/issue-material` 能创建一条 `stock_action='issue'` 的 `ly_subcontract_stock_outbox`。  
□ 发料接口本地事务内不调用 ERPNext。  
□ 发料接口返回 `outbox_id`、`issue_batch_no`、`sync_status='pending'`，`stock_entry_name` 为 null。  
□ 相同 idempotency key + 相同 payload 重复提交，不新增 material，不新增 outbox。  
□ 相同 idempotency key + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ `event_key` 使用完整 hash，长输入不会截断 digest 或碰撞。  
□ `event_key` 不包含 `issue_batch_no`，同一幂等事件重试必须稳定命中同一 outbox。  
□ 前端提交非 BOM 物料返回 `SUBCONTRACT_MATERIAL_NOT_IN_BOM`。  
□ 发料数量超过剩余可发数量返回 `SUBCONTRACT_MATERIAL_QTY_EXCEEDED`。  
□ 无 issue warehouse 权限返回 `AUTH_FORBIDDEN`，不落库。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不落库。  
□ `blocked_scope` 外发单不能发料。  
□ `settlement_status=settled` 外发单不能发料。  
□ Worker 未开启时返回 `SUBCONTRACT_WORKER_DISABLED`，不查询 outbox。  
□ 生产 dry-run 未开启时返回 `SUBCONTRACT_DRY_RUN_DISABLED`，不查询 outbox。  
□ Worker 主查询只处理 `stock_action='issue'`。  
□ Worker 主查询先按服务账号资源 scope 过滤，再 limit。  
□ 普通外发角色不能调用内部 worker。  
□ Worker dry-run 不锁定 outbox、不增加 attempts、不调用 ERPNext、写操作审计。  
□ Worker 正式执行能创建并提交 ERPNext `Stock Entry / Material Issue`。  
□ ERPNext 成功后 outbox 标记 `succeeded`，回写真实 `stock_entry_name`。  
□ ERPNext 成功后 material `sync_status` 更新为 `succeeded`。  
□ ERPNext 成功后写 `ly_subcontract_stock_sync_log` 成功记录。  
□ ERPNext 超时或 5xx 时 outbox 标记 `failed`，设置 `next_retry_at`，不写伪 Stock Entry。  
□ ERPNext 业务校验失败超过最大次数后 outbox 进入 `dead`。  
□ ERPNext 已创建但本地回写失败后，下一次 worker 能按 `event_key` 找回原 Stock Entry，不重复创建。  
□ Worker 并发执行不会重复处理同一 outbox。  
□ `receive/inspect` 仍保持 fail closed，不新增回料/验货事实。  
□ 业务代码扫描不出现 `STE-ISS-*`、`STE-REC-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 响应、普通日志、安全审计、操作审计不泄露 SQL 原文、Authorization、Cookie、token、password、secret。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_issue_material_creates_material_rows_and_pending_outbox`
2. `test_issue_material_does_not_call_erpnext_before_commit`
3. `test_issue_material_returns_outbox_without_fake_stock_entry_name`
4. `test_issue_material_idempotent_same_payload_returns_existing_result`
5. `test_issue_material_idempotency_key_different_payload_returns_conflict`
6. `test_issue_material_event_key_uses_full_hash_without_truncation_collision`
7. `test_issue_material_rejects_material_not_in_bom`
8. `test_issue_material_rejects_qty_exceeding_remaining_required_qty`
9. `test_issue_material_forbidden_when_issue_warehouse_not_allowed`
10. `test_issue_material_permission_source_unavailable_fails_closed`
11. `test_issue_material_blocked_scope_order_rejected`
12. `test_issue_material_settled_order_rejected`
13. `test_stock_worker_disabled_returns_before_outbox_query`
14. `test_stock_worker_dry_run_disabled_returns_before_outbox_query`
15. `test_stock_worker_requires_service_account_action`
16. `test_stock_worker_filters_due_outbox_by_service_account_scope_before_limit`
17. `test_stock_worker_ignores_receipt_outbox_in_task_002d`
18. `test_stock_worker_dry_run_does_not_lock_or_call_erpnext_and_writes_audit`
19. `test_stock_worker_creates_and_submits_erpnext_material_issue`
20. `test_stock_worker_writes_custom_ly_trace_fields`
21. `test_stock_worker_existing_erpnext_entry_by_event_key_prevents_duplicate_create`
22. `test_stock_worker_success_updates_outbox_material_and_sync_log`
23. `test_stock_worker_erpnext_timeout_marks_failed_with_retry`
24. `test_stock_worker_business_validation_dead_after_max_attempts`
25. `test_stock_worker_local_write_failure_after_erpnext_success_recovered_by_event_key`
26. `test_stock_worker_concurrent_run_does_not_double_process_outbox`
27. `test_task_002d_does_not_restore_receive_or_inspect_success_path`
28. `test_subcontract_stock_logs_are_sanitized`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q tests/test_subcontract_issue_outbox.py tests/test_subcontract_stock_worker.py tests/test_subcontract_stock_outbox_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|STE-REC|net_amount = .*inspected_qty|detail=str\(exc\)|Authorization|Cookie|password|secret" app migrations tests
```

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Warehouse` | REST API 或共享 PostgreSQL 只读 | 校验发料仓存在、未禁用、用户有权限 |
| `Item` | REST API 或共享 PostgreSQL 只读 | 校验物料存在、未禁用、BOM 物料合法 |
| `Stock Entry` | REST API 创建 + submit | 创建并提交 `Material Issue`，回写真实 `stock_entry_name` |
| `User Permission` | ERPNext 权限聚合 | 服务账号按 company/item/supplier/warehouse 过滤 outbox |
| `Stock Ledger Entry` | 不写，可后续只读核验 | 本任务不直接写库存台账 |

【前置依赖】
- TASK-002A：外发模块设计契约冻结已封版。
- TASK-002B1：权限、审计、回料/验货 fail closed 已通过。
- TASK-002C1：迁移自洽、BOM 一致性、company 错误信封、回填 rollback 已通过。
- ADR-034：外发发料必须通过 outbox 异步创建 ERPNext Material Issue。

【交付物】
1. 发料 outbox 最终字段、索引、约束迁移。
2. `issue-material` 本地发料事实 + outbox 入列实现。
3. 幂等键、payload_hash、event_key 实现。
4. 内部 stock worker 的 issue-only 查询、claim、ERPNext create/submit、回写、重试。
5. ERPNext event_key 查重防重复落账。
6. 安全审计、操作审计、日志脱敏。
7. 定向测试与全量测试结果。

【禁止事项】
1. 禁止在 TASK-002D 中实现回料 `Material Receipt`。
2. 禁止在 TASK-002D 中实现验货扣款金额口径。
3. 禁止在发料接口本地事务内调用 ERPNext。
4. 禁止生成或返回伪 `STE-ISS-*`、`STE-REC-*`、伪 `stock_entry_name`。
5. 禁止 worker 处理 `stock_action='receipt'`。
6. 禁止普通业务角色调用内部 worker。
7. 禁止把权限源不可用当成无资源限制。
8. 禁止 ERPNext 创建成功后因本地失败而重复创建第二张 Stock Entry。
9. 禁止日志、审计、响应中泄露 SQL 原文或敏感凭证。

【预计工时】
3-4 天

════════════════════════════════════════════════════════════════════════════
