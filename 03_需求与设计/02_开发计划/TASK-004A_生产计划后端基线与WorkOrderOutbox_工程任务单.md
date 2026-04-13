# TASK-004A 生产计划后端基线与 Work Order Outbox 工程任务单

- 任务编号：TASK-004A
- 模块：生产计划集成
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 17:28 CST
- 作者：技术架构师
- 前置依赖：TASK-001 BOM 管理已通过；TASK-003 工票/车间管理已通过；TASK-002 不阻塞本任务；TASK-006 仍因 GitHub 平台门禁 pending 保持阻塞
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.0；`ADR-058`
- 任务边界：只做生产计划后端基线、权限审计、数据模型、迁移、Work Order outbox/worker、Job Card 本地映射；不做前端、不做生产入库、不做外发单自动创建、不做 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004A
模块：生产计划后端基线与 Work Order Outbox
优先级：P0（生产主链路核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现 `Sales Order -> BOM -> 本地生产计划 -> Work Order outbox -> ERPNext Work Order -> Job Card 本地映射` 的后端闭环基线。

【模块概述】
生产计划集成负责把 ERPNext 已审批销售订单转化为车间可执行生产任务。FastAPI 只保存本地计划、物料检查快照、ERPNext Work Order/Job Card 映射和同步状态；ERPNext 仍是 `Sales Order / Work Order / Job Card` 的权威事实源。跨系统写入必须使用 outbox/worker，禁止在本地事务内直接调用 ERPNext 创建 Work Order。Job Card 完成数量仍由 TASK-003 工票模块同步，本任务只负责创建和映射生产执行对象。

【涉及文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_004a_create_production_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py

修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py（注册 production router、session dependency、security audit fallback 目标）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py（新增 production 权限动作和角色映射）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py（如当前错误码集中维护）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/__init__.py（如项目需要导出模型）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py（除非只引用现有公开能力，不改工票逻辑）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- 任意 TASK-005/TASK-006 文件

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引/约束 |
| --- | --- | --- | --- |
| `ly_schema.ly_production_plan` | 生产计划主表 | id, plan_no, company, sales_order, sales_order_item, customer, item_code, bom_id, bom_version, planned_qty, planned_start_date, fg_warehouse, wip_warehouse, status, idempotency_key, request_hash, created_by, created_at | uk_plan_no, uk_company_idempotency, idx_sales_order_item, idx_company_item, idx_status |
| `ly_schema.ly_production_plan_material` | 物料检查快照 | id, plan_id, bom_item_id, material_item_code, uom, qty_per_piece, loss_rate, required_qty, warehouse, available_qty, shortage_qty, checked_at | idx_plan_id, idx_material_item, idx_shortage |
| `ly_schema.ly_production_work_order_link` | Work Order 映射 | id, plan_id, work_order, erpnext_docstatus, erpnext_status, sync_status, last_synced_at, created_by, created_at | uk_plan_id, uk_work_order, idx_sync_status |
| `ly_schema.ly_production_work_order_outbox` | Work Order 创建 outbox | id, event_key, plan_id, company, item_code, action, payload_json, status, attempts, max_attempts, next_retry_at, locked_by, locked_at, erpnext_work_order, last_error_code, last_error_message, request_id, created_by, created_at, updated_at | uk_event_key, idx_status_retry, idx_scope_status_retry, idx_plan_id |
| `ly_schema.ly_production_job_card_link` | Job Card 本地映射 | id, plan_id, work_order, job_card, operation, operation_sequence, item_code, company, expected_qty, completed_qty, erpnext_status, synced_at | uk_job_card, idx_plan_id, idx_work_order, idx_company_item |
| `ly_schema.ly_production_status_log` | 状态流转日志 | id, plan_id, from_status, to_status, action, operator, operated_at, remark, request_id | idx_plan_id, idx_operated_at |

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 创建生产计划 | POST | `/api/production/plans` | `sales_order, sales_order_item?, bom_id?, planned_qty, planned_start_date?, idempotency_key` | `code, message, data.plan_id, data.plan_no, data.status` |
| 查询生产计划 | GET | `/api/production/plans` | `sales_order?, item_code?, status?, page, page_size` | `items, total, page, page_size` |
| 查询生产计划详情 | GET | `/api/production/plans/{plan_id}` | `plan_id` | `plan, materials, work_order, job_cards` |
| 物料检查 | POST | `/api/production/plans/{plan_id}/material-check` | `warehouse` | `material_items, shortage_items, checked_at` |
| 创建 Work Order | POST | `/api/production/plans/{plan_id}/create-work-order` | `fg_warehouse, wip_warehouse, start_date, idempotency_key` | `outbox_id, sync_status, work_order?` |
| 同步 Job Card | POST | `/api/production/work-orders/{work_order}/sync-job-cards` | `work_order` | `job_cards, sync_status` |
| 内部 Worker | POST | `/api/production/internal/work-order-sync/run-once` | `limit, dry_run?` | `claimed, succeeded, failed, dead` |

【权限动作】
必须新增：
- `production:read`
- `production:plan_create`
- `production:material_check`
- `production:work_order_create`
- `production:job_card_sync`
- `production:work_order_worker`

建议临时角色映射：
- `Production Manager`：除内部 worker 外全部 production 动作
- `Production Planner`：`production:read, production:plan_create, production:material_check, production:work_order_create, production:job_card_sync`
- `Production Viewer`：`production:read`
- `LY Integration Service`：追加 `production:work_order_worker`

【业务规则】
1. `Sales Order.docstatus` 必须等于 1，且 status 不得为 `Cancelled/Closed`；否则返回 `PRODUCTION_SO_NOT_APPROVED` 或 `PRODUCTION_SO_CLOSED_OR_CANCELLED`。
2. 同一个 SO 存在多行相同 `item_code` 时，必须传 `sales_order_item`；否则返回 `PRODUCTION_SO_ITEM_AMBIGUOUS`。
3. `bom_id` 缺省时只能取该 `item_code` 当前生效默认 BOM；无默认 BOM 返回 `PRODUCTION_BOM_NOT_FOUND`。
4. BOM 必须已生效，且 `bom.item_code == sales_order_item.item_code`；不一致返回 `PRODUCTION_BOM_ITEM_MISMATCH`。
5. `planned_qty > 0`，且不得超过该 SO 行剩余未计划数量；超过返回 `PRODUCTION_PLANNED_QTY_EXCEEDED`。
6. 创建计划幂等：同一 `company + idempotency_key` 相同 payload 返回首次结果，不同 payload 返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
7. 物料检查只生成快照，不锁库存，不修改 ERPNext 库存。
8. `create-work-order` 只写 `ly_production_work_order_outbox`；本地 commit 前不得调用 ERPNext。
9. Work Order outbox `event_key` 必须稳定，建议 `pwo:<sha256(company|plan_id|bom_id|planned_qty|sales_order_item)>`；不得包含 `outbox_id/request_id/created_at/operator`。
10. Worker 必须先短事务 claim outbox 并提交，再调用 ERPNext；结果回写使用单独短事务。
11. ERPNext 查重必须优先按 `custom_ly_plan_id/custom_ly_plan_no` 或项目约定自定义字段，不得仅按 item/qty 模糊匹配。
12. ERPNext 返回 draft/cancelled/异常状态时不得误判为成功；状态语义必须在测试中覆盖。
13. Job Card 同步只读取 ERPNext `Job Card` 并写 `ly_production_job_card_link`，不得直接更新 Job Card 完成数量。
14. BOM 外发工序仅标记 `is_subcontract=true`，TASK-004A 不自动创建外发单。
15. 所有读写接口必须先做当前用户解析、动作权限、资源权限；资源权限按 ERPNext SO/BOM 派生的 `company/item_code` 校验，前端传入 company 不可信。
16. 权限来源不可用必须 fail closed，返回 `PERMISSION_SOURCE_UNAVAILABLE`。
17. 401/403/503 必须写安全审计，创建计划、物料检查、创建 outbox、Job Card 同步、worker run-once 必须写操作审计。
18. 数据库写失败必须返回 `DATABASE_WRITE_FAILED`，不得落入 `PRODUCTION_INTERNAL_ERROR`。
19. 日志不得输出完整 ERPNext Token、Cookie、Authorization、完整 DSN 或 SQLAlchemy 原始 SQL 参数。

【错误码】
必须覆盖：
- `PRODUCTION_SO_NOT_FOUND`
- `PRODUCTION_SO_NOT_APPROVED`
- `PRODUCTION_SO_CLOSED_OR_CANCELLED`
- `PRODUCTION_SO_ITEM_NOT_FOUND`
- `PRODUCTION_SO_ITEM_AMBIGUOUS`
- `PRODUCTION_BOM_NOT_FOUND`
- `PRODUCTION_BOM_NOT_ACTIVE`
- `PRODUCTION_BOM_ITEM_MISMATCH`
- `PRODUCTION_PLANNED_QTY_EXCEEDED`
- `PRODUCTION_IDEMPOTENCY_CONFLICT`
- `PRODUCTION_WAREHOUSE_REQUIRED`
- `PRODUCTION_WORK_ORDER_ALREADY_EXISTS`
- `PRODUCTION_WORK_ORDER_SYNC_FAILED`
- `PRODUCTION_JOB_CARD_SYNC_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `PERMISSION_SOURCE_UNAVAILABLE`

【测试要求】
必须新增并通过：
1. 创建计划成功：SO 已提交、BOM 生效、qty 合法，返回 `plan_id/plan_no/status`。
2. SO 未提交或未审批，返回 `PRODUCTION_SO_NOT_APPROVED`，不落库。
3. SO 已取消/关闭，返回 `PRODUCTION_SO_CLOSED_OR_CANCELLED`。
4. 同 SO 多行同 item 未传 `sales_order_item`，返回 `PRODUCTION_SO_ITEM_AMBIGUOUS`。
5. BOM 与 SO 行 item 不一致，返回 `PRODUCTION_BOM_ITEM_MISMATCH`。
6. 计划数量超过剩余未计划数量，返回 `PRODUCTION_PLANNED_QTY_EXCEEDED`。
7. 同一 idempotency_key 相同 payload 重试返回首次计划。
8. 同一 idempotency_key 不同 payload 返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
9. 物料检查按 BOM 展开写入材料快照，短缺数量计算正确。
10. `create-work-order` 本地事务 commit 前不调用 ERPNext。
11. `create-work-order` commit 失败时 ERPNext 调用次数为 0。
12. Worker claim 后再调用 ERPNext，不持有本地事务跨网络调用。
13. Worker 成功后写 `ly_production_work_order_link`。
14. Worker 遇到 ERPNext draft/cancelled/异常状态不误判成功。
15. 重复 create-work-order 返回已有 outbox 或已有 work_order，不创建第二条。
16. Job Card 同步能写入 `ly_production_job_card_link`。
17. 仅授权 ITEM-B 的用户访问 ITEM-A 生产计划返回 403，且写安全审计。
18. 权限源不可用返回 503，且不落库、不调用 ERPNext。
19. 数据库写失败返回 `DATABASE_WRITE_FAILED`。
20. 操作审计写失败返回 `AUDIT_WRITE_FAILED`。

【验收标准】
□ 新增生产计划模型和迁移，空库迁移可创建全部生产计划相关表。  
□ `POST /api/production/plans` 已实现 SO/BOM/qty/idempotency 校验。  
□ `GET /api/production/plans` 在数据库层按 `company/item_code` 做资源过滤。  
□ `GET /api/production/plans/{plan_id}` 无资源权限返回 403，不泄露详情。  
□ `POST /api/production/plans/{plan_id}/material-check` 能写入物料检查快照。  
□ `POST /api/production/plans/{plan_id}/create-work-order` 只创建 outbox，不在请求事务中调用 ERPNext。  
□ 内部 worker 能创建 ERPNext Work Order 并回写映射。  
□ `POST /api/production/work-orders/{work_order}/sync-job-cards` 能读取 ERPNext Job Card 并写本地映射。  
□ 401/403/503 均有安全审计。  
□ 创建计划、物料检查、创建 Work Order outbox、Job Card 同步、worker run-once 均有操作审计。  
□ 全量 `.venv/bin/python -m pytest -q` 通过。  
□ 全量 `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)` 通过。  
□ 未修改外发结算业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】
- 禁止在本地数据库事务提交前调用 ERPNext 创建 Work Order。
- 禁止直接写 ERPNext public schema 表。
- 禁止用前端传入 company 作为权限判断依据。
- 禁止权限源不可用时 fail open。
- 禁止 Work Order outbox `event_key` 包含 `outbox_id/request_id/created_at/operator`。
- 禁止只按 item/qty 模糊查重 ERPNext Work Order。
- 禁止 TASK-004A 自动创建外发单。
- 禁止 TASK-004A 修改工票 Job Card 完成数量同步逻辑。
- 禁止进入 TASK-005 款式利润报表。
- 禁止进入 TASK-006 加工厂对账单。
- 禁止在日志或审计中记录 Authorization/Cookie/Token/Secret/完整 DSN。

【前置依赖】
TASK-001 BOM 管理已通过；TASK-003 工票/车间管理已通过。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════
