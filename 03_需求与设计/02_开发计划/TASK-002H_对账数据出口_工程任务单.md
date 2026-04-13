# TASK-002H 对账数据出口工程任务单

- 任务编号：TASK-002H
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 14:51 CST
- 作者：技术架构师
- 审计来源：TASK-002G3 审计意见书第 50 份通过，允许进入 TASK-002H
- 前置依赖：TASK-002A/B1/C1/D1/E1/F3/G3 已通过；继续遵守外发模块 V1.18 与 ADR-030~ADR-046
- 任务边界：只做外发侧对账数据出口、结算候选、金额快照、结算锁定服务；不得实现 TASK-006 加工厂对账单主表、对账单编号规则、应付发票、付款、GL、ERPNext Purchase Invoice

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H
模块：对账数据出口
优先级：P1（外发模块封版出口）
════════════════════════════════════════════════════════════════════════════

【任务目标】
为 TASK-006 加工厂对账单提供稳定、可审计、可锁定的外发验货结算明细出口，确保对账金额来源清晰且不会重复结算。

【模块概述】
外发验货已经在 `ly_subcontract_inspection` 形成加工费、扣款和净应付金额事实。加工厂对账单需要按供应商、公司和日期范围拉取可结算明细，并在生成对账单时锁定这些明细，避免后续重复进入其他对账单。本任务只负责外发侧的数据出口和锁定边界，不创建正式对账单主表，不生成 ERPNext 应付或总账。

【架构裁决】
1. 结算明细事实源以 `ly_subcontract_inspection` 为准。
2. `ly_subcontract_order` 的 `gross_amount/deduction_amount/net_amount` 只作为订单汇总，不作为唯一结算行事实源。
3. 一个外发单允许多批回料、多次验货、分批进入不同对账单。
4. 对账候选以 inspection 行为最小粒度，避免订单级字段导致部分结算无法表达。
5. 列表同步状态只展示最新发料/最新回料 outbox 摘要；多批次同步流水继续放在详情页或后续独立同步流水页，不放入外发列表。
6. `_latest_outbox_by_order_ids()` 当前 Python 取最新的性能风险不阻塞 TASK-002H；后续如列表性能告警，再单独排期窗口函数/子查询优化。

【涉及文件】
必须新增或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/alembic/versions/[new]_subcontract_settlement_export.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限复用测试 fixture）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/factories.py（如已有，仅限补测试工厂）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/*（TASK-006 才做）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py（TASK-006 才做）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py（TASK-006 才做）

【数据库表设计】
本任务不得新建加工厂对账单主表，只允许补外发 inspection 结算字段和必要索引。

| 表名 | 字段 | 用途 |
| --- | --- | --- |
| `ly_schema.ly_subcontract_inspection` | `settlement_status` | 结算状态：unsettled/statement_locked/settled/adjusted/cancelled |
| `ly_schema.ly_subcontract_inspection` | `statement_id` | TASK-006 对账单 ID，当前阶段 nullable、无强制 FK |
| `ly_schema.ly_subcontract_inspection` | `statement_no` | TASK-006 对账单号快照 |
| `ly_schema.ly_subcontract_inspection` | `settlement_line_key` | 结算明细唯一键，建议 `subcontract_inspection:{inspection_id}` |
| `ly_schema.ly_subcontract_inspection` | `settlement_locked_by` | 锁定人 |
| `ly_schema.ly_subcontract_inspection` | `settlement_locked_at` | 锁定时间 |
| `ly_schema.ly_subcontract_inspection` | `settled_by` | 确认结算人，TASK-006 确认时写 |
| `ly_schema.ly_subcontract_inspection` | `settled_at` | 确认结算时间，TASK-006 确认时写 |
| `ly_schema.ly_subcontract_inspection` | `settlement_request_id` | 锁定/释放请求 ID |

索引要求：
1. `idx_ly_subcontract_inspection_settlement_status(settlement_status, inspected_at, id)`。
2. `idx_ly_subcontract_inspection_statement(statement_id, settlement_status)`。
3. `uk_ly_subcontract_inspection_settlement_line_key(settlement_line_key)`。
4. 如数据库不支持表达式索引，`settlement_line_key` 由迁移和新增验货逻辑补齐。
5. 历史 inspection 迁移时默认 `settlement_status='unsettled'`，`settlement_line_key='subcontract_inspection:' || id`。

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 查询可结算明细 | GET | `/api/subcontract/settlement-candidates` | company, supplier, from_date, to_date, item_code?, process_name?, page, page_size | items, total, page, page_size, summary |
| 对账预览汇总 | POST | `/api/subcontract/settlement-preview` | inspection_ids[] 或筛选条件 | company, supplier, line_count, total_qty, gross_amount, deduction_amount, net_amount, items |
| 锁定结算明细 | POST | `/api/subcontract/settlement-locks` | statement_id, statement_no, inspection_ids[], idempotency_key, remark? | locked_count, gross_amount, deduction_amount, net_amount, locked_items |
| 释放结算锁定 | POST | `/api/subcontract/settlement-locks/release` | statement_id 或 statement_no, inspection_ids[], idempotency_key, reason | released_count, released_items |

说明：
1. `settlement-locks` 和 `settlement-locks/release` 是给 TASK-006 调用的后端接口/服务入口，不做普通前端按钮。
2. 本任务不创建 `factory_statement` 业务页面。
3. 本任务不创建 ERPNext Purchase Invoice、Payment Entry、GL Entry。
4. 本任务不调用 ERPNext 写接口。

【权限要求】
必须新增或确认以下权限动作：
1. `subcontract:settlement_read`：查询可结算明细、预览汇总。
2. `subcontract:settlement_lock`：锁定结算明细。
3. `subcontract:settlement_release`：释放未确认对账单的结算锁定。

权限规则：
1. 所有接口必须接入 `current_user`。
2. 所有接口必须校验动作权限。
3. 所有查询必须按 ERPNext User Permission 聚合后的 company/supplier/item 范围过滤。
4. 权限源不可用必须 fail closed，返回 `PERMISSION_SOURCE_UNAVAILABLE`。
5. 资源权限拒绝必须返回 403，并写安全审计。
6. service account 不得全模块全资源放行，必须遵守已有服务账号最小权限策略。

【候选明细规则】
一条 inspection 进入可结算候选必须同时满足：
1. inspection `status='inspected'`。
2. inspection `settlement_status='unsettled'`。
3. inspection `net_amount >= 0`。
4. 所属外发单 `status` 不为 `draft/cancelled`。
5. 所属外发单 `resource_scope_status='ready'`。
6. 所属外发单 `company` 非空。
7. 对应 `receipt_batch_no` 的回料已同步成功：相关 receipt `sync_status='succeeded'` 且 `stock_entry_name` 非空。
8. 所属外发单未被整体取消。
9. 当前用户对 company/supplier/item 有资源权限。
10. 日期范围默认按 `inspection.inspected_at` 过滤。

不得进入候选：
1. 未验货的回料。
2. 未同步成功的回料。
3. 已 `statement_locked/settled/adjusted/cancelled` 的 inspection。
4. `resource_scope_status='blocked_scope'` 的外发单。
5. 权限源不可用或资源无权限的明细。

【金额口径】
1. 结算行 `gross_amount` 读取 `ly_subcontract_inspection.gross_amount`。
2. 结算行 `deduction_amount` 读取 `ly_subcontract_inspection.deduction_amount`。
3. 结算行 `net_amount` 读取 `ly_subcontract_inspection.net_amount`。
4. 汇总金额 = 候选行金额 Decimal 求和，保留 2 位小数，ROUND_HALF_UP。
5. 禁止重新按 `accepted_qty × subcontract_rate` 计算加工费。
6. 禁止使用旧错误公式 `net_amount = inspected_qty - deduction_amount`。
7. 不合格率只做展示：`rejected_qty / inspected_qty`，不得参与金额重算。
8. 对账金额不得读取 receipt 历史金额字段。

【锁定规则】
1. 锁定以 inspection 行为粒度。
2. `POST /settlement-locks` 必须使用事务和行级锁，防止两个对账单同时锁同一 inspection。
3. 同一 `statement_id + inspection_ids + idempotency_key` 重复提交必须返回第一次锁定结果。
4. 同一 inspection 已被相同 statement 锁定时，重复锁定返回幂等成功。
5. 同一 inspection 已被其他 statement 锁定或结算时，返回 `SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED`。
6. 锁定成功后 inspection `settlement_status='statement_locked'`，写入 `statement_id/statement_no/settlement_locked_by/settlement_locked_at/settlement_request_id`。
7. 锁定成功必须写操作审计。
8. 锁定失败不得部分提交；必须 rollback。
9. `release` 只允许释放 `statement_locked` 状态，不允许释放 `settled`。
10. `release` 必须校验 statement_id/statement_no 匹配，不得释放其他对账单的锁。
11. `release` 成功后 inspection 回到 `unsettled`，清空 statement 关联和 locked 字段。
12. TASK-006 确认对账单时，才允许把 locked 行推进为 `settled`。

【既有写接口保护】
必须补齐或确认以下保护：
1. 已 `settled` 的 inspection 不允许被修改。
2. 已 `statement_locked` 的 inspection 不允许被重复验货、释放外的状态变更或金额重算。
3. 已存在 locked/settled inspection 的外发单不允许取消；返回 `SUBCONTRACT_SETTLEMENT_LOCKED`。
4. 新增回料/验货可以继续发生在未锁定的新批次上，但不得影响已锁定/已结算 inspection 的金额。
5. 发料/回料/验货/retry 原有幂等规则不得被本任务破坏。

【错误码】
必须新增或复用以下错误码：
1. `SUBCONTRACT_SETTLEMENT_CANDIDATE_NOT_FOUND`
2. `SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED`
3. `SUBCONTRACT_SETTLEMENT_STATUS_INVALID`
4. `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`
5. `SUBCONTRACT_SETTLEMENT_LOCKED`
6. `SUBCONTRACT_SETTLEMENT_STATEMENT_REQUIRED`
7. `DATABASE_READ_FAILED`
8. `DATABASE_WRITE_FAILED`
9. `AUTH_FORBIDDEN`
10. `PERMISSION_SOURCE_UNAVAILABLE`

【审计要求】
1. 查询候选失败的 401/403/503 必须写安全审计。
2. 锁定成功必须写操作审计，包含 statement_id、statement_no、inspection_ids、金额汇总和 request_id。
3. release 成功必须写操作审计，包含 statement_id、statement_no、inspection_ids、reason 和 request_id。
4. 锁定/释放失败的系统错误必须脱敏记录，不得写 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。
5. 查询接口不得输出 payload_json、ERPNext 原始异常、内部堆栈。

【验收标准】
□ Alembic 迁移补齐 inspection 结算字段和索引，空库升级到 head 通过。  
□ 历史 inspection 默认回填 `settlement_status='unsettled'` 和唯一 `settlement_line_key`。  
□ `GET /api/subcontract/settlement-candidates` 只返回已验货、回料同步成功、未结算、用户有权限的 inspection 明细。  
□ 未验货、未同步回料、已锁定、已结算、取消、blocked_scope、无权限的明细均不返回。  
□ `POST /api/subcontract/settlement-preview` 返回行数、数量和 gross/deduction/net 汇总。  
□ 汇总金额来自 inspection 金额事实，不重新按旧公式计算。  
□ `POST /api/subcontract/settlement-locks` 能锁定 inspection 行并写 statement_id/statement_no。  
□ 同一 statement 重复锁定同一批 inspection 返回幂等成功。  
□ 其他 statement 重复锁定同一 inspection 返回 `SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED`。  
□ 锁定过程任一行失败必须整体 rollback。  
□ `POST /api/subcontract/settlement-locks/release` 只能释放 `statement_locked` 行，不能释放 `settled` 行。  
□ 已 locked/settled inspection 的外发单不允许取消。  
□ 查询、锁定、释放均做动作权限和资源权限校验。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得放开候选数据。  
□ 操作审计和安全审计不泄露敏感信息。  
□ 不创建 factory_statement 表。  
□ 不创建 ERPNext Purchase Invoice / Payment Entry / GL Entry。  
□ 不调用 ERPNext 写接口。  
□ 发料、回料、验货、retry 既有测试全部通过。  
□ `.venv/bin/python -m pytest -q` 通过。  
□ `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。  

【测试要求】
必须新增或补齐以下测试：
1. `test_settlement_candidates_return_only_eligible_inspections`
2. `test_settlement_candidates_filter_by_company_supplier_date_and_permission`
3. `test_settlement_candidates_exclude_unsynced_receipt`
4. `test_settlement_candidates_exclude_locked_and_settled_inspections`
5. `test_settlement_preview_sums_inspection_amount_facts`
6. `test_settlement_preview_does_not_use_old_amount_formula`
7. `test_settlement_lock_marks_inspections_statement_locked`
8. `test_settlement_lock_is_idempotent_for_same_statement`
9. `test_settlement_lock_conflicts_for_other_statement`
10. `test_settlement_lock_rolls_back_all_rows_on_failure`
11. `test_settlement_release_unlocks_statement_locked_rows`
12. `test_settlement_release_rejects_settled_rows`
13. `test_cancel_rejects_order_with_locked_or_settled_inspections`
14. `test_settlement_permission_source_fail_closed`
15. `test_settlement_security_audit_on_forbidden`
16. `test_no_erpnext_write_called_by_settlement_export_or_lock`

【禁止事项】
- 禁止创建加工厂对账单主表或页面。
- 禁止生成对账单编号规则，除非只作为 TASK-006 传入的 `statement_no` 校验。
- 禁止创建 ERPNext Purchase Invoice、Payment Entry、GL Entry。
- 禁止调用 ERPNext 写接口。
- 禁止重算历史 inspection 金额。
- 禁止使用 receipt 历史金额字段作为对账事实源。
- 禁止使用旧公式 `net_amount = inspected_qty - deduction_amount`。
- 禁止在接口响应或日志中输出敏感凭证、SQL 原文、堆栈。
- 禁止修改 TASK-002G/G1/G2/G3 已通过的前端鉴权和列表 N+1 修复。

【前置依赖】
TASK-002G3 已通过审计意见书第 50 份；本任务通过审计后，TASK-002 外发加工管理可进入模块封版，随后进入 TASK-006 加工厂对账单。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════
