# TASK-002F1 验货幂等批次隔离与详情闭环整改工程任务单

- 任务编号：TASK-002F1
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 13:05 CST
- 作者：技术架构师
- 审计来源：TASK-002F 审计意见书第 43 份，结论不通过
- 前置依赖：TASK-002A/B1/C1/D1/E1 已通过；TASK-002F 已交付但未通过审计
- 任务边界：只修验货幂等批次隔离、外发详情验货明细、缺失测试和迁移自洽；不得进入加工厂对账、结算、应付、付款、ERPNext GL/AP

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002F1
模块：验货幂等批次隔离与详情闭环整改
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复验货幂等 hash 错误排除 `receipt_batch_no` 的高危问题，确保同一 `idempotency_key` 换不同回料批次时返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`，并补齐外发详情验货明细与 TASK-002F 缺失测试。

【模块概述】
验货是按回料批次确认质量和扣款的业务事实。`receipt_batch_no` 不是验货的易变字段，而是验货事实的核心身份字段。若同一幂等键换批次仍返回第一次结果，系统会给出 200 成功响应但实际未验第二批，后续加工厂对账会少计金额。本任务把 inspection 幂等 hash 与 stock outbox event hash 分离，避免把 outbox 的易变字段规则误用于验货业务事实。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002f_inspection_detail_and_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts（仅允许补详情字段类型，不做对账/结算 UI）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_inspection | 验货事实表 | `id, company, subcontract_id, inspection_no, receipt_batch_no, receipt_warehouse, item_code, inspected_qty, rejected_qty, accepted_qty, rejected_rate, subcontract_rate, gross_amount, deduction_amount_per_piece, deduction_amount, net_amount, idempotency_key, payload_hash, inspected_by, inspected_at, request_id, remark` | `uk_ly_subcontract_inspection_idempotency(subcontract_id,idempotency_key)`；`idx_ly_subcontract_inspection_batch(company,subcontract_id,receipt_batch_no)` |
| ly_schema.ly_subcontract_receipt | 回料批次来源 | `receipt_batch_no, received_qty, sync_status, stock_entry_name, receipt_warehouse` | `idx_ly_subcontract_receipt_batch(company,subcontract_id,receipt_batch_no)` |
| ly_schema.ly_subcontract_order | 外发主单汇总 | `inspected_qty, rejected_qty, accepted_qty, gross_amount, deduction_amount, net_amount, status` | 复用 company/status 索引 |

【迁移要求】
1. 必须新增独立 Alembic migration：`task_002f_inspection_detail_and_idempotency.py`。
2. 禁止继续把 TASK-002F 验货字段追加到已存在的 `task_002c_subcontract_company_and_schema.py` 作为唯一迁移来源。
3. 新迁移必须幂等补齐 inspection 字段和索引，适配已经执行过 TASK-002C revision 的环境。
4. 新迁移必须补齐或确认 `idx_ly_subcontract_inspection_batch(company,subcontract_id,receipt_batch_no)`。
5. 如果模型字段已存在，新迁移不得破坏已有数据。
6. Alembic 从空库升级到 head 必须通过。

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 外发验货 | POST | `/api/subcontract/{id}/inspect` | `receipt_batch_no, inspected_qty, rejected_qty, deduction_amount_per_piece?, idempotency_key, remark?` | `{inspection_no, receipt_batch_no, inspected_qty, accepted_qty, rejected_qty, rejected_rate, gross_amount, deduction_amount, net_amount, status}` |
| 外发详情 | GET | `/api/subcontract/{id}` | `id` | `order, materials?, receipts?, inspections, status_logs?, stock_sync_summary` |
| 外发列表 | GET | `/api/subcontract/` | 原入参 | 返回验货与金额摘要 |

【验货幂等规则】
1. 不得复用会排除 `receipt_batch_no` 的 stock outbox payload hash 规则作为 inspection 幂等 hash。
2. 必须新增或独立实现 `build_inspection_payload_hash()`。
3. inspection payload hash 必须包含 `receipt_batch_no`。
4. inspection payload hash 必须包含 `inspected_qty/rejected_qty/deduction_amount_per_piece/remark` 的业务语义字段。
5. inspection payload hash 必须保留 Decimal 语义归一化，`10/10.0/10.000000` 等价。
6. 同一 `subcontract_id + idempotency_key + 同一 receipt_batch_no + 同一语义 payload` 返回第一次验货结果。
7. 同一 `subcontract_id + idempotency_key + 不同 receipt_batch_no` 必须返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
8. 同一 `subcontract_id + idempotency_key + 同一 receipt_batch_no + 不同数量/扣款/备注 payload` 必须返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
9. 幂等检查必须继续前置到剩余可验数量校验之前。
10. 幂等冲突不得写 inspection，不得更新主单汇总，不得写状态流转。

【详情接口规则】
1. `GET /api/subcontract/{id}` 必须返回 `inspections[]`。
2. `inspections[]` 至少包含：`inspection_no, receipt_batch_no, inspected_qty, accepted_qty, rejected_qty, rejected_rate, subcontract_rate, gross_amount, deduction_amount_per_piece, deduction_amount, net_amount, inspected_by, inspected_at, remark`。
3. 详情金额汇总必须来自 `ly_subcontract_inspection` 或主单已汇总字段，不得读取 receipt 表旧金额字段。
4. `ly_subcontract_receipt` 上的 `inspected_qty/rejected_qty/deduction_amount/net_amount` 若仍存在，视为历史兼容字段，不作为 TASK-002F 后续金额事实源。
5. 建议同步返回 `receipts[]` 与 `status_logs[]`；如本轮不返回，至少不得影响 `inspections[]` 验收。
6. 详情接口仍必须执行资源权限校验，权限源不可用 fail closed。

【金额口径清理】
1. 外发模块设计中的旧公式 `gross_amount = accepted_qty * subcontract_rate` 必须废弃。
2. 唯一有效公式为 `gross_amount = inspected_qty × subcontract_rate`。
3. `accepted_qty` 只代表合格数量，不作为加工费总额基数。
4. TASK-006 加工厂对账必须引用 TASK-002F1 后的 inspection 金额口径。

【操作审计要求】
1. 验货成功的操作审计 `after_data` 必须包含本次 `inspection_no/receipt_batch_no/inspected_qty/rejected_qty/gross_amount/deduction_amount/net_amount` 摘要。
2. 401/403/503 必须写安全审计。
3. 幂等冲突必须写安全审计或操作审计中的拒绝记录，至少保证可追踪。
4. 日志和审计不得泄露 SQL 原文、Authorization、Cookie、token、password、secret。

【错误码】
必须新增或确认：
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_RECEIPT_BATCH_REQUIRED`
- `SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND`
- `SUBCONTRACT_RECEIPT_NOT_SYNCED`
- `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`
- `SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED`
- `SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `SUBCONTRACT_SETTLEMENT_LOCKED`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`

【验收标准】
□ `build_inspection_payload_hash()` 独立于 stock outbox hash。  
□ inspection payload hash 必须包含 `receipt_batch_no`。  
□ 同一 idempotency_key、同数量、不同 receipt_batch_no 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ 上述冲突场景不新增 inspection，不更新主单汇总。  
□ 同一 idempotency_key、同 receipt_batch_no、同语义 payload 返回第一次验货结果。  
□ 同一 idempotency_key、同 receipt_batch_no、数量格式 `10/10.0/10.000000` 视为同一 payload。  
□ 同一 idempotency_key、同 receipt_batch_no、不同 rejected_qty 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ 同一 idempotency_key、同 receipt_batch_no、不同 deduction_amount_per_piece 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ `GET /api/subcontract/{id}` 返回 `inspections[]`。  
□ `inspections[]` 返回验货批次、数量、扣款和金额快照字段。  
□ 详情接口不得从 receipt 旧金额字段读取验货金额。  
□ 外发设计和代码中不得再保留有效口径 `gross_amount = accepted_qty * subcontract_rate`。  
□ 新增独立 TASK-002F Alembic migration。  
□ Alembic 从空库升级到 head 通过。  
□ 已执行 TASK-002C revision 的库执行 TASK-002F migration 可补齐验货字段和索引。  
□ receipt warehouse 越权返回 `AUTH_FORBIDDEN`，不落库。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不落库。  
□ 401/403/503 写安全审计。  
□ 并发验货不会超过批次可验数量。  
□ 旧 retry 最新 outbox 选择器无生产路径调用。  
□ 验货成功操作审计包含本次 inspection 摘要。  
□ 业务代码扫描不出现 `STE-ISS-*`、`STE-REC-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 业务代码扫描不出现有效公式 `gross_amount = accepted_qty * subcontract_rate`。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_inspect_same_key_different_receipt_batch_returns_conflict`
2. `test_inspect_same_key_different_receipt_batch_does_not_create_second_success_response`
3. `test_inspect_same_key_same_batch_decimal_equivalent_returns_existing_result`
4. `test_inspect_same_key_same_batch_different_rejected_qty_returns_conflict`
5. `test_inspect_same_key_same_batch_different_deduction_rate_returns_conflict`
6. `test_inspection_payload_hash_includes_receipt_batch_no`
7. `test_inspection_payload_hash_does_not_use_stock_outbox_volatile_exclusions`
8. `test_subcontract_detail_returns_inspections`
9. `test_subcontract_detail_inspection_amounts_use_inspection_table_not_receipt_legacy_fields`
10. `test_inspect_forbidden_when_receipt_warehouse_not_allowed`
11. `test_inspect_permission_source_unavailable_fails_closed`
12. `test_inspect_security_audit_on_401_403_503`
13. `test_inspect_concurrent_requests_do_not_overinspect`
14. `test_deprecated_get_retry_target_not_used_by_retry_endpoint`
15. `test_no_latest_outbox_retry_selector_in_production_path`
16. `test_task_002f_migration_adds_inspection_columns_to_existing_task_002c_database`
17. `test_alembic_upgrade_head_from_empty_database_includes_inspection_columns`
18. `test_inspection_operation_audit_contains_current_inspection_summary`
19. `test_no_gross_amount_accepted_qty_formula_in_business_code`
20. `test_no_net_amount_quantity_minus_amount_formula_in_business_code`

【禁止事项】
- 禁止把 `receipt_batch_no` 从 inspection payload hash 中排除。
- 禁止复用 stock outbox 的 `_VOLATILE_PAYLOAD_KEYS` 作为 inspection hash 排除清单。
- 禁止同一 idempotency_key 不同回料批次返回第一次验货成功结果。
- 禁止从 receipt 旧金额字段作为验货金额事实源。
- 禁止继续把 TASK-002F 字段只追加进 TASK-002C 旧 migration。
- 禁止实现加工厂对账单、结算、应付、付款、GL。
- 禁止验货接口调用 ERPNext 写接口。
- 禁止生成 `STE-ISS-*`、`STE-REC-*` 或任何伪 `stock_entry_name`。
- 禁止使用旧公式 `net_amount = inspected_qty - deduction_amount`。
- 禁止使用有效口径 `gross_amount = accepted_qty * subcontract_rate`。
- 禁止使用 `detail=str(exc)` 或普通日志输出 SQL/密钥/ERPNext 敏感响应。

【前置依赖】
TASK-002F 已交付但审计意见书第 43 份不通过；必须先完成本任务并通过复审，才允许进入 TASK-002G/TASK-002H。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
