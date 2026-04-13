# TASK-002F 验货扣款金额口径工程任务单

- 任务编号：TASK-002F
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.1
- 更新时间：2026-04-13 13:05 CST
- 作者：技术架构师
- 审计来源：TASK-002E1 审计意见书第 42 份通过，允许进入 TASK-002F
- 前置依赖：TASK-002A/B1/C1/D1/E1 已通过；继续遵守外发模块 V1.10 与 ADR-030~ADR-038
- 任务边界：只实现验货、本地扣款金额口径和状态流转；不得实现加工厂对账单、结算、应付、ERPNext GL/AP/Payment

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002F
模块：验货扣款金额口径
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 `/api/subcontract/{id}/inspect` 从 fail closed 升级为正式验货接口，固化 `gross_amount / deduction_amount / net_amount` 金额公式，禁止再出现“数量减金额”的旧错误公式。

【模块概述】
验货是外发回料后的质量确认环节。加工厂回料入库后，工厂对回料批次进行验货，记录验货数量、不合格数量、扣款单价和扣款金额，作为后续加工厂对账单的金额来源。本任务只写 FastAPI 本地验货事实和金额汇总，不创建 ERPNext Stock Entry，不创建 Purchase Invoice，不做付款或结算锁定。

【前置清理】
必须先处理 TASK-002E1 审计遗留风险：
1. 删除 `SubcontractStockOutboxService.get_retry_target()` 旧方法。
2. 如果因兼容原因暂不能删除，必须改为显式废弃方法，生产代码调用时直接抛出 `RuntimeError("deprecated retry target selector")`。
3. 新增防回归测试或扫描，确保 `/api/subcontract/{id}/stock-sync/retry` 不会调用“按最新 outbox”选择逻辑。
4. 任何新代码不得重新引入按订单最新 outbox 重试的逻辑。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002c_subcontract_company_and_schema.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts（仅允许补验货接口类型，不做对账/结算 UI）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_inspection | 外发验货事实和扣款金额 | `id, company, subcontract_id, inspection_no, receipt_batch_no, receipt_warehouse, item_code, inspected_qty, rejected_qty, accepted_qty, rejected_rate, subcontract_rate, gross_amount, deduction_amount_per_piece, deduction_amount, net_amount, idempotency_key, payload_hash, inspected_by, inspected_at, request_id, remark, created_at, updated_at` | `uk_ly_subcontract_inspection_no(company,inspection_no)`；`uk_ly_subcontract_inspection_idempotency(subcontract_id,idempotency_key)`；`idx_ly_subcontract_inspection_order(company,subcontract_id,created_at)`；`idx_ly_subcontract_inspection_receipt_batch(receipt_batch_no)` |
| ly_schema.ly_subcontract_order | 外发主单汇总 | `inspected_qty, rejected_qty, accepted_qty, gross_amount, deduction_amount, net_amount, status, settlement_status` | 复用 `idx_ly_subcontract_order_company_status` |
| ly_schema.ly_subcontract_receipt | 验货来源批次 | `receipt_batch_no, received_qty, sync_status, stock_entry_name, receipt_warehouse` | 复用 `idx_ly_subcontract_receipt_outbox` 和批次索引 |
| ly_schema.ly_subcontract_status_log | 状态流转日志 | `from_status, to_status, action, before_data, after_data, operator, request_id` | 复用 company/order/time 索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 外发验货 | POST | `/api/subcontract/{id}/inspect` | `receipt_batch_no, inspected_qty, rejected_qty, deduction_amount_per_piece?, idempotency_key, remark?` | `{inspection_no, inspected_qty, accepted_qty, rejected_qty, rejected_rate, gross_amount, deduction_amount, net_amount, status}` |
| 外发详情 | GET | `/api/subcontract/{id}` | `id` | 返回 inspections、金额汇总和最新状态 |
| 外发列表 | GET | `/api/subcontract/` | 原入参 | 可返回 inspected_qty、rejected_qty、net_amount 摘要 |

【请求结构】
`POST /api/subcontract/{id}/inspect` 请求体：

```json
{
  "receipt_batch_no": "REC-20260413-0001",
  "inspected_qty": "100",
  "rejected_qty": "5",
  "deduction_amount_per_piece": "2.00",
  "idempotency_key": "inspect-rec-0001",
  "remark": "5件破损扣款"
}
```

字段要求：
1. `receipt_batch_no` 必填，必须属于当前外发单。
2. `inspected_qty` 必填，必须大于 0。
3. `rejected_qty` 必填，必须大于等于 0。
4. `deduction_amount_per_piece` 可选，未传按 0 处理。
5. `idempotency_key` 必填。
6. `remark` 可选，必须脱敏，最长 200 字符。
7. 验货人从当前登录用户解析，禁止前端提交 `inspected_by/operator` 覆盖真实操作者。

【业务规则】
1. 验货接口必须先鉴权：当前用户、动作权限 `subcontract:inspect`、外发单本地 `company` 资源权限。
2. 资源权限必须校验 `company/item_code/supplier/receipt_warehouse`。
3. 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得写 inspection，不得改主单。
4. `resource_scope_status='blocked_scope'` 返回 `SUBCONTRACT_SCOPE_BLOCKED`。
5. `settlement_status='settled'` 返回 `SUBCONTRACT_SETTLEMENT_LOCKED`。
6. `cancelled/completed` 状态禁止新增验货。
7. 允许验货状态为 `waiting_inspection`；兼容 `waiting_receive` 中仍存在未验批次的历史/并发场景。
8. 验货必须绑定 `receipt_batch_no`，不得对没有回料事实的外发单直接验货。
9. 目标回料批次必须已同步 ERPNext Material Receipt 成功：receipt `sync_status='succeeded'` 且 `stock_entry_name` 不为空。
10. receipt outbox 仍为 `pending/failed/dead/processing` 时返回 `SUBCONTRACT_RECEIPT_NOT_SYNCED`，不得验货。
11. 同一 `idempotency_key` + 相同 payload 重复提交，返回第一次 inspection 结果，不新增验货事实，不重复扣款。
12. 同一 `idempotency_key` + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
13. 幂等检查必须前置到剩余可验数量校验之前。
14. 可验数量 = 当前 `receipt_batch_no` 的已回料数量 - 当前批次已验数量。
15. `inspected_qty <= 可验数量`，否则返回 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`。
16. `rejected_qty <= inspected_qty`，否则返回 `SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED`。
17. `accepted_qty = inspected_qty - rejected_qty`。
18. `rejected_rate = rejected_qty / inspected_qty`，保留 6 位小数。
19. `gross_amount = inspected_qty × subcontract_rate`。
20. `deduction_amount = rejected_qty × deduction_amount_per_piece`。
21. `net_amount = gross_amount - deduction_amount`。
22. `deduction_amount` 不得大于 `gross_amount`，否则返回 `SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS`。
23. 金额字段使用 Decimal，按财务金额保留 2 位小数，舍入规则为 ROUND_HALF_UP。
24. 禁止旧错误公式：不得出现 `net_amount = inspected_qty - deduction_amount` 或任何数量减金额逻辑。
25. 验货成功后更新主单汇总：`inspected_qty/rejected_qty/accepted_qty/gross_amount/deduction_amount/net_amount`。
26. 状态流转规则：若累计已验数量小于累计已回料数量，状态为 `waiting_inspection`。
27. 状态流转规则：若累计已验数量等于累计已回料数量且累计已回料数量小于计划数量，状态为 `waiting_receive`。
28. 状态流转规则：若累计已验数量等于累计已回料数量且累计已回料数量等于计划数量，状态为 `completed`。
29. 本任务不创建 ERPNext Stock Entry，不创建 GL，不创建 Purchase Invoice，不创建 Payment Entry。
30. 验货成功必须写操作审计；401/403/503 必须写安全审计。
31. 普通日志、操作审计、安全审计不得泄露 SQL 原文、Authorization、Cookie、token、password、secret、ERPNext 原始敏感响应。
32. 数据库读失败返回 `DATABASE_READ_FAILED`，数据库写失败返回 `DATABASE_WRITE_FAILED`。
33. 审计写失败返回 `AUDIT_WRITE_FAILED`，不得误包装为业务错误。
34. 必须使用事务和行锁或等效机制防止并发验货超量。

【错误码】
必须新增或补齐：
- `SUBCONTRACT_RECEIPT_BATCH_REQUIRED`
- `SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND`
- `SUBCONTRACT_RECEIPT_NOT_SYNCED`
- `SUBCONTRACT_INSPECTION_NOT_READY`
- `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`
- `SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED`
- `SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS`
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `SUBCONTRACT_SETTLEMENT_LOCKED`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`

【验收标准】
□ 旧 `get_retry_target()` 已删除或显式废弃，生产代码不可调用。  
□ `POST /api/subcontract/{id}/inspect` 权限通过后能创建 `ly_subcontract_inspection`。  
□ 验货接口必须绑定 `receipt_batch_no`。  
□ `receipt_batch_no` 不属于当前外发单时返回 `SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND`。  
□ receipt 未同步成功时返回 `SUBCONTRACT_RECEIPT_NOT_SYNCED`，不写 inspection。  
□ 相同 idempotency key + 相同 payload 重复提交，不新增 inspection，不重复扣款。  
□ 相同 idempotency key + 不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ 幂等检查前置，已全量验货后同 key 重试不返回超量错误。  
□ `inspected_qty=100,rejected_qty=5` 时 `accepted_qty=95`。  
□ `inspected_qty=100,rejected_qty=5` 时 `rejected_rate=0.050000`。  
□ `subcontract_rate=10,inspected_qty=100` 时 `gross_amount=1000.00`。  
□ `rejected_qty=5,deduction_amount_per_piece=2` 时 `deduction_amount=10.00`。  
□ 上述场景 `net_amount=990.00`。  
□ 不允许出现 `net_amount=inspected_qty-deduction_amount`。  
□ `rejected_qty > inspected_qty` 返回 `SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED`。  
□ `deduction_amount > gross_amount` 返回 `SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS`。  
□ 验货数量超过批次剩余可验数量返回 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`。  
□ 无 `receipt_warehouse` 权限返回 `AUTH_FORBIDDEN`，不落库。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不落库。  
□ `blocked_scope` 外发单不能验货。  
□ `settlement_status=settled` 外发单不能验货。  
□ 验货成功后主单汇总字段正确累加。  
□ 部分验货后状态保持 `waiting_inspection`。  
□ 当前已回料全部验完但未全部计划回料时，状态为 `waiting_receive`。  
□ 全部计划数量回料且验完后，状态为 `completed`。  
□ 本任务不调用 ERPNext 写接口。  
□ 本任务不创建 Purchase Invoice、Payment Entry、GL Entry。  
□ 验货成功写操作审计，401/403/503 写安全审计。  
□ 数据库写失败返回 `DATABASE_WRITE_FAILED` 并 rollback。  
□ 并发验货不会超过批次可验数量。  
□ 响应、普通日志、安全审计、操作审计不泄露 SQL 原文、Authorization、Cookie、token、password、secret。  
□ 业务代码扫描不出现 `STE-REC-*`、`STE-ISS-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_inspect_creates_inspection_and_amounts`
2. `test_inspect_requires_receipt_batch_no`
3. `test_inspect_rejects_receipt_batch_from_other_order`
4. `test_inspect_rejects_unsynced_receipt_batch`
5. `test_inspect_idempotent_same_payload_returns_existing_result`
6. `test_inspect_idempotent_different_payload_returns_conflict`
7. `test_inspect_idempotent_retry_after_full_inspection_does_not_check_remaining_first`
8. `test_inspect_calculates_accepted_qty_rejected_rate_gross_deduction_net`
9. `test_inspect_rejects_rejected_qty_greater_than_inspected_qty`
10. `test_inspect_rejects_deduction_amount_greater_than_gross_amount`
11. `test_inspect_rejects_qty_exceeding_batch_remaining_qty`
12. `test_inspect_forbidden_when_receipt_warehouse_not_allowed`
13. `test_inspect_permission_source_unavailable_fails_closed`
14. `test_inspect_blocked_scope_order_rejected`
15. `test_inspect_settled_order_rejected`
16. `test_inspect_updates_order_rollups`
17. `test_inspect_partial_batch_keeps_waiting_inspection`
18. `test_inspect_all_received_but_not_all_planned_sets_waiting_receive`
19. `test_inspect_all_planned_received_and_inspected_sets_completed`
20. `test_inspect_does_not_call_erpnext_or_create_finance_docs`
21. `test_inspect_database_write_failure_rolls_back`
22. `test_inspect_concurrent_requests_do_not_overinspect`
23. `test_inspect_logs_are_sanitized`
24. `test_inspect_security_audit_on_401_403_503`
25. `test_deprecated_get_retry_target_not_used_by_retry_endpoint`
26. `test_no_latest_outbox_retry_selector_in_production_path`

【TASK-002F1 审计整改补充】
1. inspection 幂等 hash 必须包含 `receipt_batch_no`。
2. 同一 `idempotency_key` 不同 `receipt_batch_no` 必须返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
3. 不得复用 stock outbox 的易变字段排除清单作为 inspection hash 排除清单。
4. 外发详情必须返回 `inspections[]`。
5. TASK-002F 验货字段必须通过独立 TASK-002F Alembic migration 补齐，不能只依赖已存在的 TASK-002C migration。

【禁止事项】
- 禁止实现加工厂对账单。
- 禁止实现结算、应付、付款、GL。
- 禁止验货接口调用 ERPNext 写接口。
- 禁止生成 `STE-ISS-*`、`STE-REC-*` 或任何伪 `stock_entry_name`。
- 禁止使用旧公式 `net_amount = inspected_qty - deduction_amount`。
- 禁止前端传入 `operator/inspected_by` 覆盖当前登录用户。
- 禁止对未同步成功的回料批次验货。
- 禁止按订单最新 outbox 做 retry。
- 禁止使用 `detail=str(exc)` 或普通日志输出 SQL/密钥/ERPNext 敏感响应。

【前置依赖】
TASK-002E1 已通过审计意见书第 42 份；必须先完成本任务并通过审计，才允许进入 TASK-002G/TASK-002H。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════

【版本记录】
| 版本 | 更新时间 | 作者 | 说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-04-13 12:31 CST | 技术架构师 | 初版 TASK-002F 验货扣款金额口径任务单 |
| V1.1 | 2026-04-13 13:05 CST | 技术架构师 | 同步 TASK-002F1 审计整改：receipt_batch_no 必须参与验货幂等 hash，详情返回 inspections，迁移独立化 |
