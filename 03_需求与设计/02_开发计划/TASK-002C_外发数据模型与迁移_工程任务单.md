# TASK-002C 外发数据模型与迁移工程任务单

- 任务编号：TASK-002C
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-12 21:51 CST
- 作者：技术架构师
- 前置依赖：TASK-002A 已封版；TASK-002B1 已通过审计；继续遵守外发模块 V1.3 与 ADR-030/ADR-031/ADR-032
- 任务边界：只做数据模型、迁移、回填、索引、约束、资源权限切换和测试；不得实现 TASK-002D/E/F 的发料 outbox、回料 outbox、验货金额口径或 ERPNext Stock Entry worker

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002C
模块：外发数据模型与迁移
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐外发单本地 `company` 事实字段、迁移、回填、索引和约束，并把外发资源权限从运行时推断升级为本地事实字段校验。

【模块概述】
外发加工后续会驱动发料、回料、验货、对账和 ERPNext Stock Entry 同步，所有动作都必须先确定单据归属公司。TASK-002B 阶段资源权限仍可依赖请求或关联数据推断，这会在多公司、多加工厂、多款式场景下产生越权风险。TASK-002C 必须把 `company` 固化为外发本地事实字段，并通过迁移和回填处理历史数据。迁移完成后，外发列表、详情、写接口和后续 outbox 查询都必须使用本地 `company` 做资源权限判断；缺失、空白、无法解析或多义的历史数据必须 fail closed。

【涉及文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002c_subcontract_company_and_schema.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_migration_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_company_migration.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_company_permission.py

修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_fail_closed.py

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_order | 外发主单，本地资源权限事实源 | `id, subcontract_no, company, supplier, item_code, bom_id, process_name, status, resource_scope_status, scope_error_code` | `uk_ly_subcontract_order_no`；`idx_ly_subcontract_company_status(company,status)`；`idx_ly_subcontract_company_supplier_status(company,supplier,status)`；`idx_ly_subcontract_company_item_status(company,item_code,status)`；迁移完成后 `company` 不允许 NULL/空白 |
| ly_schema.ly_subcontract_material | 外发发料计划/事实字段承载，不实现发料成功路径 | `id, subcontract_id, company, issue_warehouse, material_item_code, required_qty, issued_qty, stock_entry_name, stock_outbox_id, sync_status, idempotency_key` | `idx_ly_subcontract_material_company_order(company,subcontract_id)`；`idx_ly_subcontract_material_company_item(company,material_item_code)` |
| ly_schema.ly_subcontract_receipt | 外发回料事实字段承载，不恢复回料成功路径 | `id, subcontract_id, company, receipt_warehouse, item_code, received_qty, stock_entry_name, stock_outbox_id, sync_status, idempotency_key` | `idx_ly_subcontract_receipt_company_order(company,subcontract_id)`；`idx_ly_subcontract_receipt_company_item(company,item_code)` |
| ly_schema.ly_subcontract_inspection | 外发验货事实字段承载，不实现验货金额口径 | `id, subcontract_id, company, inspected_qty, accepted_qty, rejected_qty, gross_amount, deduction_amount, net_amount, idempotency_key` | `idx_ly_subcontract_inspection_company_order(company,subcontract_id)` |
| ly_schema.ly_subcontract_status_log | 状态流转日志 | `id, subcontract_id, company, from_status, to_status, action, operator, request_id, created_at` | `idx_ly_subcontract_status_log_company_order(company,subcontract_id,created_at)` |
| ly_schema.ly_subcontract_stock_outbox | ERPNext Stock Entry 同步任务表结构准备，不实现 worker 处理 | `id, event_key, subcontract_id, company, supplier, item_code, warehouse, stock_action, status, attempts, next_retry_at, stock_entry_name` | `uk_ly_subcontract_stock_outbox_event_key`；`idx_ly_subcontract_outbox_company_status(company,status,next_retry_at)`；`idx_ly_subcontract_outbox_scope(company,supplier,item_code,warehouse,status)` |
| ly_schema.ly_subcontract_stock_sync_log | Stock Entry 同步尝试日志表结构准备 | `id, outbox_id, subcontract_id, company, stock_action, attempt_no, erpnext_status, stock_entry_name, error_code, created_at` | `idx_ly_subcontract_sync_log_company_outbox(company,outbox_id,created_at)` |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 外发列表 | GET | `/api/subcontract/` | `company, supplier, item_code, status, page, page_size` | `{items,total,page,page_size}`，每条必须返回 `company/resource_scope_status` |
| 外发详情 | GET | `/api/subcontract/{id}` | `id` | 外发主单详情，必须返回本地 `company` |
| 创建外发单 | POST | `/api/subcontract/` | `supplier,item_code,bom_id,process_name,planned_qty,idempotency_key`，`company` 不得以前端为唯一事实源 | `{name, company, resource_scope_status}` |
| 回料门禁 | POST | `/api/subcontract/{id}/receive` | `id, receipt_warehouse, received_qty, idempotency_key` | TASK-002C 仍 fail closed，不新增回料事实 |
| 验货门禁 | POST | `/api/subcontract/{id}/inspect` | `id, inspected_qty, rejected_qty, idempotency_key` | TASK-002C 仍 fail closed，不新增验货事实 |
| 迁移预检 | 内部服务函数，不开放前端路由 | `build_subcontract_company_backfill_plan(dry_run=True)` | 返回不可持久化预检报告 |
| 迁移执行 | 内部服务函数，不开放前端路由 | `backfill_subcontract_company_scope(dry_run=False)` | 返回执行报告；失败必须 rollback |

【业务规则】
1. `ly_subcontract_order.company` 是外发资源权限的本地权威字段；TASK-002C 完成后，读取、详情、写操作、后续 outbox 查询不得再以请求参数或运行时推断作为权限事实源。
2. `company` 缺失口径统一为 `NULL/空字符串/空白字符串`，三者必须同等视为缺失。
3. 新建外发单必须在本地写入非空 `company`；如果无法从 BOM、Item、Supplier 或明确授权上下文唯一解析公司，必须返回 `SUBCONTRACT_COMPANY_REQUIRED` 或 `SUBCONTRACT_COMPANY_UNRESOLVED`，不得创建“无公司”外发单。
4. 历史外发单回填必须只接受唯一确定的公司候选；候选多于 1 个返回 `SUBCONTRACT_COMPANY_AMBIGUOUS`，候选为 0 返回 `SUBCONTRACT_COMPANY_UNRESOLVED`。
5. ERPNext 主数据或权限源查询失败属于外部事实源不可用，必须 fail closed，返回 `ERPNEXT_SERVICE_UNAVAILABLE` 或 `PERMISSION_SOURCE_UNAVAILABLE`，不得降级为“无候选”。
6. 数据库读取失败返回 `DATABASE_READ_FAILED`；数据库写入、flush、commit 失败返回 `DATABASE_WRITE_FAILED`。
7. dry-run 预检必须真正只读：不得把 ORM 对象挂入 session，不得新增迁移日志，不得改外发单，不得写操作审计。
8. `ly_subcontract_material.company`、`ly_subcontract_receipt.company`、`ly_subcontract_inspection.company`、`ly_subcontract_status_log.company`、`ly_subcontract_stock_outbox.company` 必须从 `ly_subcontract_order.company` 派生，禁止以前端传入值覆盖。
9. 历史数据无法回填时，必须把主单标记为 `resource_scope_status='blocked_scope'` 或等价状态；列表、详情和写接口仍可被有权限管理员查看诊断，但普通业务动作必须禁止。
10. 列表查询必须在数据库层按当前用户可访问 `company` 过滤，不能先查全量再在 Python 过滤。
11. 详情和写接口必须先读取主单本地 `company`，再执行 `company/item_code/supplier/warehouse` 资源级校验。
12. TASK-002C 不得恢复回料和验货成功路径；`receive/inspect` 在鉴权与资源权限通过后仍按 TASK-002B1 门禁 fail closed。

【错误码】
必须新增或补齐：
- `SUBCONTRACT_COMPANY_REQUIRED`
- `SUBCONTRACT_COMPANY_UNRESOLVED`
- `SUBCONTRACT_COMPANY_AMBIGUOUS`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `SUBCONTRACT_MIGRATION_DRY_RUN_ONLY`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`

【验收标准】
□ Alembic 迁移能为 `ly_subcontract_order` 增加 `company/resource_scope_status/scope_error_code`，且迁移可重复执行不报错。  
□ Alembic 迁移能为外发 material、receipt、inspection、status_log、stock_outbox、stock_sync_log 增加或补齐 `company` 字段。  
□ `ly_subcontract_order.company` 对新数据不允许 NULL、空字符串、空白字符串。  
□ 历史 `company=NULL` 的外发单能按唯一候选回填为正确公司。  
□ 历史 `company=''` 和 `company='   '` 的外发单与 NULL 使用同一缺失判断。  
□ ERPNext Item/Supplier/BOM 候选查询不可用时，回填返回 `ERPNEXT_SERVICE_UNAVAILABLE`，不改数据。  
□ 数据库读取候选失败时，回填返回 `DATABASE_READ_FAILED`，不改数据。  
□ 候选多义时，回填不随意选择公司，并标记或返回 `SUBCONTRACT_COMPANY_AMBIGUOUS`。  
□ 候选为空时，回填不写默认公司，并标记或返回 `SUBCONTRACT_COMPANY_UNRESOLVED`。  
□ dry-run 后 `session.new/session.dirty/session.deleted` 均为 0。  
□ dry-run 后即使调用方执行 `session.commit()`，也不会产生外发单变更、迁移日志或审计副作用。  
□ execute 模式成功时，主单及其 material/receipt/inspection/status_log/outbox/sync_log 的 `company` 与主单一致。  
□ execute 模式发生写入失败时返回 `DATABASE_WRITE_FAILED` 并 rollback。  
□ `GET /api/subcontract/` 在数据库查询层按本地 `company` 过滤，授权 `Company B` 的用户看不到 `Company A` 外发单。  
□ `GET /api/subcontract/{id}` 对本地 `company` 无权限时返回 `AUTH_FORBIDDEN` 并写安全审计。  
□ `POST /api/subcontract/{id}/receive` 对本地 `company` 无权限时返回 `AUTH_FORBIDDEN`，且不进入 payload 业务校验。  
□ `POST /api/subcontract/{id}/inspect` 对本地 `company` 无权限时返回 `AUTH_FORBIDDEN`，且不进入 payload 业务校验。  
□ `resource_scope_status='blocked_scope'` 的外发单不得执行发料、回料、验货、取消、库存同步重试。  
□ 新建外发单返回体包含 `company`，并且该值来自后端解析/校验后的本地事实。  
□ 响应、普通日志、安全审计、操作审计不得泄露 SQL 原文、Authorization、Cookie、token、password、secret。  
□ 全量测试通过。  
□ `rg "STE-ISS|STE-REC|net_amount = .*inspected_qty" app/routers app/services app/models tests` 不命中外发正向实现。  
□ `receive/inspect` 在 TASK-002C 完成后仍保持 TASK-002B1 fail closed，不新增回料/验货事实。  

【测试要求】
必须新增或补齐以下测试：
1. `test_subcontract_migration_adds_company_to_order_and_children`
2. `test_new_subcontract_order_requires_non_blank_company`
3. `test_company_missing_null_empty_blank_use_same_scope_rule`
4. `test_backfill_company_from_unique_candidate_success`
5. `test_backfill_company_ambiguous_fails_closed`
6. `test_backfill_company_unresolved_fails_closed`
7. `test_backfill_erpnext_item_unavailable_fails_closed`
8. `test_backfill_database_read_failed_returns_database_read_failed`
9. `test_backfill_database_write_failed_rolls_back`
10. `test_backfill_dry_run_is_read_only_even_if_caller_commits`
11. `test_child_rows_company_derived_from_order_company`
12. `test_subcontract_list_filters_by_local_company_in_database_query`
13. `test_subcontract_detail_forbidden_when_local_company_not_allowed`
14. `test_receive_forbidden_when_local_company_not_allowed_before_payload_validation`
15. `test_inspect_forbidden_when_local_company_not_allowed_before_payload_validation`
16. `test_blocked_scope_order_cannot_receive_or_inspect`
17. `test_create_order_returns_backend_resolved_company`
18. `test_subcontract_company_errors_are_sanitized`
19. `test_task_002c_does_not_restore_receive_success_path`
20. `test_task_002c_does_not_restore_inspect_success_path`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|STE-REC|net_amount = .*inspected_qty|detail=str\(exc\)|Authorization|Cookie" app/routers app/services app/models tests
```

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Item` | REST API 或共享 PostgreSQL 只读 | 解析款式/物料候选 company；不可用必须 fail closed |
| `Supplier` | REST API 或共享 PostgreSQL 只读 | 校验加工厂和可能的 company 归属；不可用必须 fail closed |
| `User Permission` | ERPNext 权限聚合 | 当前用户 company/item/supplier/warehouse 资源权限；不可用必须 fail closed |
| `Stock Entry` | 不调用 | TASK-002C 禁止创建 ERPNext Stock Entry |
| `Stock Ledger Entry` | 不调用 | TASK-002C 不做库存落账验证 |

【前置依赖】
- TASK-002A：外发模块设计契约冻结已封版。
- TASK-002B1：权限、审计、回料/验货 fail closed 阻断项已通过。
- ADR-030：外发模块 V1.1 生产级契约冻结。
- ADR-031：TASK-002B 阶段回料与验货旧演示成功路径必须 fail closed。
- ADR-032：外发资源权限必须以本地 company 事实字段为准。

【交付物】
1. TASK-002C 数据库迁移文件。
2. 外发模型、schema、服务层的 `company/resource_scope_status` 字段补齐。
3. 历史外发数据 company 回填 dry-run 与 execute 服务。
4. 外发资源权限从推断切换为本地 `company` 字段校验。
5. 外发列表、详情、receive、inspect 的本地 company 权限测试。
6. dry-run 只读、fail closed、异常分类和日志脱敏测试。
7. 全量测试结果。

【禁止事项】
1. 禁止在 TASK-002C 中实现发料 Stock Entry outbox 业务成功路径。
2. 禁止在 TASK-002C 中实现回料 Stock Entry outbox 业务成功路径。
3. 禁止在 TASK-002C 中实现验货扣款金额正式口径。
4. 禁止创建 ERPNext `Stock Entry`。
5. 禁止恢复 `receive/inspect` 成功写本地事实路径。
6. 禁止生成或返回伪 `STE-ISS-*`、`STE-REC-*`、伪 `stock_entry_name`。
7. 禁止把 `company` 以前端传参作为唯一事实源。
8. 禁止在 company 无法解析时默认写入任意公司或放开全资源权限。
9. 禁止把 ERPNext 查询失败降级为“无候选”。
10. 禁止日志、审计、响应中泄露 SQL 原文或敏感凭证。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════
