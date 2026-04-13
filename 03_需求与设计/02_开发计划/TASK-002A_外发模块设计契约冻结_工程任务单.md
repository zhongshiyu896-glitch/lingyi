# 工程任务单：TASK-002A 外发模块设计契约冻结

- 任务编号：TASK-002A
- 模块：外发加工管理
- 优先级：P0（开发前门禁）
- 任务类型：架构整改 / 契约冻结 / 研发前置
- 创建时间：2026-04-12 20:03 CST
- 更新时间：2026-04-12 20:08 CST
- 作者：技术架构师
- 结论来源：`TASK-002_外发加工管理_开发前基线盘点.md`
- 审计补充：TASK-002A 任务单/架构审阅意见，必须补齐写接口幂等契约、对账结算边界、内部库存同步 worker 安全契约

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002A
模块：外发加工管理
优先级：P0（未完成前禁止进入 TASK-002B 工程实现）
════════════════════════════════════════════════════════════════════════════

【任务目标】
冻结外发模块 V1.1 设计契约，明确“数据模型、状态机、API、权限、审计、ERPNext 边界、一致性策略、写接口幂等、金额口径、对账结算边界、内部库存同步 worker 安全契约”，作为 TASK-002B~TASK-002H 的唯一实现依据。

【问题背景】
当前外发模块仅为演示级骨架，存在以下阻塞：
1. 发料/回料未真实创建 ERPNext `Stock Entry`。
2. 无鉴权、资源权限、安全审计、操作审计。
3. 本地事务与 ERPNext 库存落账没有一致性策略。
4. 状态机、金额公式、BOM 工序/加工厂/仓库校验不完整。
5. 无 TASK-002 专属迁移和自动化测试基线。
6. 写接口缺少幂等契约，重复提交可能造成重复本地事实和重复 Stock Entry outbox。
7. 外发与 TASK-006 对账边界未锁定，结算后金额修改和调整/反冲规则不明确。
8. 内部库存同步 worker 缺少生产开关、服务账号最小权限、dry-run/诊断审计和越权 outbox 处理策略。

本任务不是直接写业务代码，而是“冻结契约 + 冻结验收口径 + 冻结拆分任务”。

【涉及文件】
必须修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`

必须新增/更新：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-002A_外发模块设计契约冻结_工程任务单.md`（本文件）

建议参考：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-002_外发加工管理_开发前基线盘点.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/04_模块设计_工票车间管理.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/01_模块设计_BOM管理.md`

【冻结范围】

## 一、数据模型契约（V1.1）
必须冻结以下表及关键字段、索引、约束：

1. `ly_schema.ly_subcontract_order`
- 关键字段：
  - `id, subcontract_no, company, supplier, item_code, bom_id, process_name, subcontract_rate`
  - `planned_qty, issued_qty, received_qty, inspected_qty, rejected_qty, accepted_qty`
  - `gross_amount, deduction_amount, net_amount`
  - `settlement_status, statement_id, settlement_no, settled_by, settled_at`
  - `status, created_by, created_at, updated_by, updated_at`
- 关键约束：
  - `planned_qty > 0`
  - `subcontract_rate >= 0`
  - 金额字段 `Decimal/Numeric`，禁止 `float`

2. `ly_schema.ly_subcontract_material`
- 关键字段：
  - `subcontract_id, company, issue_warehouse, material_item_code, color, size, batch_no, uom`
  - `required_qty, issued_qty, remaining_qty`
  - `stock_entry_name, stock_outbox_id, sync_status, sync_error_code`
  - `idempotency_key, created_by, created_at`
- 关键约束：
  - `required_qty >= 0, issued_qty >= 0, remaining_qty >= 0`
  - 同一 `subcontract_id + stock_action='issue' + idempotency_key` 不得重复生成事实和 outbox

3. `ly_schema.ly_subcontract_receipt`
- 关键字段：
  - `subcontract_id, company, receipt_warehouse, item_code, received_qty`
  - `stock_entry_name, stock_outbox_id, sync_status, sync_error_code`
  - `idempotency_key, received_by, received_at`
- 关键约束：
  - `received_qty > 0`
  - 同一 `subcontract_id + stock_action='receipt' + idempotency_key` 不得重复生成事实和 outbox

4. `ly_schema.ly_subcontract_inspection`
- 关键字段：
  - `subcontract_id, inspected_qty, accepted_qty, rejected_qty, rejected_rate`
  - `deduction_rate, deduction_amount, gross_amount, net_amount`
  - `idempotency_key, inspected_by, inspected_at`
- 关键约束：
  - `inspected_qty > 0`
  - `0 <= rejected_qty <= inspected_qty`
  - `accepted_qty = inspected_qty - rejected_qty`
  - 同一 `subcontract_id + action='inspect' + idempotency_key` 不得重复累计金额

5. `ly_schema.ly_subcontract_status_log`
- 关键字段：
  - `subcontract_id, from_status, to_status, action, operator, request_id, remark`
  - `before_data(JSONB), after_data(JSONB), created_at`

6. `ly_schema.ly_subcontract_stock_outbox`
- 用途：本地库存同步待办
- 关键字段：
  - `event_key, subcontract_id, stock_action(issue/receipt), company, supplier, warehouse`
  - `item_code/material_item_code, qty, uom`
  - `status(pending/processing/succeeded/failed/dead/blocked_scope), attempts, max_attempts, next_retry_at`
  - `locked_by, locked_at, stock_entry_name, last_error_code, last_error_message, request_id, created_by, created_at, updated_at`

7. `ly_schema.ly_subcontract_stock_sync_log`
- 用途：每次同步尝试留痕
- 关键字段：
  - `outbox_id, subcontract_id, stock_action, attempt_no, erpnext_status(success/failed)`
  - `erpnext_docname(stock_entry_name), error_code, error_message, request_id, created_at`

## 二、状态机契约
外发主单状态冻结为：
- `draft`
- `issued`
- `processing`
- `waiting_receive`
- `waiting_inspection`
- `completed`
- `cancelled`

动作与状态约束：
1. 创建：`draft`
2. 发料成功（本地事实 + outbox 入列）：`draft -> issued`
3. 加工确认（如有）：`issued -> processing`
4. 回料登记：`issued/processing/waiting_receive -> waiting_inspection`
5. 验货完成：`waiting_inspection -> completed`
6. 取消：仅 `draft/issued` 可取消
7. 禁止 `draft` 直接 `receive/inspect`
8. `completed/cancelled/settled` 后禁止继续发料、回料、验货

## 三、API 契约冻结
统一前缀：`/api/subcontract/`
统一响应：`{ "code": "0", "message": "success", "data": {} }`

必需接口：
1. `POST /api/subcontract/` 创建外发单
2. `GET /api/subcontract/` 外发单分页查询
3. `GET /api/subcontract/{id}` 外发单详情
4. `POST /api/subcontract/{id}/issue-material` 发料
5. `POST /api/subcontract/{id}/receive` 回料
6. `POST /api/subcontract/{id}/inspect` 验货
7. `POST /api/subcontract/{id}/cancel` 取消
8. `POST /api/subcontract/{id}/stock-sync/retry` 手动重试库存同步
9. `POST /api/subcontract/internal/stock-sync/run-once` 内部 worker 单次执行

## 四、写接口幂等契约
必须冻结 `idempotency_key` / 业务唯一键规则：

1. 幂等键来源：优先请求头 `Idempotency-Key`，兼容请求体 `idempotency_key`。
2. 外部系统推送可使用 `external_event_key`，但必须规范化和脱敏。
3. 幂等键必须参与唯一约束或幂等记录表。
4. 幂等键相同且 payload 摘要一致：返回第一次成功结果，不新增本地事实、不新增 outbox、不新增 ERPNext Stock Entry。
5. 幂等键相同但 payload 摘要不一致：返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
6. 首次请求事务回滚：允许同 key 重试。
7. 首次请求已写 outbox 但未同步：重复提交返回原 outbox 状态。
8. 首次请求已同步成功：重复提交返回原 `stock_entry_name`。

必须覆盖接口：
- `POST /api/subcontract/`
- `POST /api/subcontract/{id}/issue-material`
- `POST /api/subcontract/{id}/receive`
- `POST /api/subcontract/{id}/inspect`
- `POST /api/subcontract/{id}/cancel`
- `POST /api/subcontract/{id}/stock-sync/retry`

## 五、权限动作与资源权限冻结
动作权限：
- `subcontract:read`
- `subcontract:create`
- `subcontract:issue_material`
- `subcontract:receive`
- `subcontract:inspect`
- `subcontract:cancel`
- `subcontract:stock_sync_retry`
- `subcontract:stock_sync_worker`（仅服务账号/系统账号）

资源权限维度：
- `company`
- `item_code`
- `supplier`
- `warehouse`

规则：
1. 动作权限 + 资源权限必须同时通过。
2. 权限源不可用必须 `fail closed`。
3. 普通前端按钮隐藏不能替代后端鉴权。

## 六、审计与日志冻结
1. 写操作必须写操作审计：创建、发料、回料、验货、取消、手动重试、worker 执行、授权 dry-run。
2. 401/403/503/权限源不可用必须写安全审计。
3. 审计和普通日志必须脱敏：禁止记录 `Authorization/Cookie/token/password/secret`，禁止记录 SQL 原文/参数。
4. request_id 使用规范化值。

## 七、ERPNext 边界冻结
1. ERPNext 是主数据与库存事实源：`Supplier, Item, Warehouse, Stock Entry, Stock Ledger Entry`。
2. FastAPI 不直写 ERPNext 数据库表。
3. 发料/回料库存动作必须通过 outbox + worker 异步创建 ERPNext `Stock Entry`。
4. 本地事务内仅写本地事实与 outbox，不在事务内直接调用 ERPNext 写接口。

## 八、一致性策略冻结
1. 本地事务内：写 `order/material/receipt/inspection/status_log/audit/stock_outbox(pending)`。
2. 提交后：worker 拉取 outbox 调 ERPNext。
3. 成功：`outbox=succeeded` + `sync_log=success` + 回写 `stock_entry_name`。
4. 失败：`outbox=failed/dead` + `sync_log=failed` + 可重试。
5. ERPNext 同步失败不回滚已提交本地业务事实。
6. 本地事务失败或审计失败，不得调用 ERPNext。

## 九、金额公式冻结
1. `accepted_qty = inspected_qty - rejected_qty`
2. `rejected_rate = rejected_qty / inspected_qty`
3. `gross_amount = accepted_qty * subcontract_rate`
4. `deduction_amount = rejected_qty * deduction_rate`
5. `net_amount = gross_amount - deduction_amount`

全部金额/单价/数量使用 `Decimal/Numeric`。

## 十、对账结算边界冻结
必须冻结 TASK-006 可用字段和锁定规则：

1. `settlement_status`：`unsettled/partially_settled/settled/adjusted/cancelled`。
2. `statement_id`：加工厂对账单主键。
3. `settlement_no`：加工厂对账单号快照。
4. `settled_by`：结算确认人。
5. `settled_at`：结算确认时间。
6. `settlement_status=settled` 后，禁止修改金额、发料、回料、验货、取消。
7. 已结算外发单需要调整时，只能通过 TASK-006 生成调整单或反冲单，不得直接改原始金额。
8. 对账单取消后，外发单退回 `unsettled` 或进入 `adjusted` 必须写状态日志和操作审计。
9. TASK-006 只读取 `status=completed` 且 `settlement_status in ('unsettled','partially_settled')` 的外发单。
10. 同一外发验货明细不得重复进入未取消对账单。

## 十一、内部库存同步 worker 安全契约冻结
必须冻结：生产开关、服务账号最小资源权限、dry-run/诊断审计、越权 outbox 处理策略。

1. 生产环境默认关闭 HTTP 内部 worker，除非 `ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API=true`。
2. 未开启时返回 `INTERNAL_API_DISABLED`，写安全审计。
3. 生产环境默认禁用 `dry_run=true`，除非 `SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN=true`。
4. dry-run 被禁用时返回 `SUBCONTRACT_DRY_RUN_DISABLED`，写安全审计，不查询 outbox。
5. 调用主体必须具备 `subcontract:stock_sync_worker`。
6. 调用主体必须是服务账号、系统级集成账号或 `System Manager`。
7. 服务账号必须按 ERPNext `User Permission` 限定 `company/item_code/supplier/warehouse`。
8. 服务账号无明确资源 scope 时 fail closed。
9. ERPNext 权限源不可用时返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得处理 outbox。
10. 主处理查询必须先按服务账号资源 scope 过滤，再 `order by/limit`。
11. 越权 outbox 不得进入主处理窗口，不得被锁定、增加 attempts、更新 retry 或标记成功。
12. 缺少资源 scope 的 outbox 必须进入 `blocked_scope/dead`，并写安全审计。
13. 越权诊断必须显式启用，默认不扫描越权 outbox。
14. 越权诊断必须有扫描上限、冷却期、去重机制。
15. dry-run 不得锁定 outbox、不得增加 attempts、不得更新状态、不得调用 ERPNext。
16. 授权 dry-run 成功必须写操作审计。

## 十二、校验规则冻结
创建外发单必须校验：
1. `supplier` 存在且是加工厂。
2. `item_code` 存在且未禁用。
3. `bom_id` 存在且 `bom.item_code == payload.item_code`。
4. `process_name` 属于 `ly_bom_operation` 且 `is_subcontract=true`。
5. 发料仓/收料仓存在且当前用户有资源权限。

发料规则：
1. 不允许前端直接决定 `required_qty` 作为事实；必须来源于外发物料计划/BOM 展开。
2. `issued_qty <= remaining_required_qty`。
3. 相同幂等键不得重复生成发料事实和 Stock Entry outbox。

回料规则：
1. `received_qty > 0`。
2. 单据状态必须允许回料。
3. 相同幂等键不得重复生成回料事实和 Stock Entry outbox。

验货规则：
1. `0 <= rejected_qty <= inspected_qty`。
2. 单据状态必须为 `waiting_inspection`。
3. 相同幂等键不得重复生成验货事实或重复累计金额。
4. 已结算单据禁止验货。

## 十三、错误码冻结
至少冻结以下错误码：
- `SUBCONTRACT_NOT_FOUND`
- `SUBCONTRACT_STATUS_INVALID`
- `SUBCONTRACT_SUPPLIER_INVALID`
- `SUBCONTRACT_ITEM_NOT_FOUND`
- `SUBCONTRACT_PROCESS_NOT_SUBCONTRACT`
- `SUBCONTRACT_BOM_ITEM_MISMATCH`
- `SUBCONTRACT_WAREHOUSE_INVALID`
- `SUBCONTRACT_INVALID_QTY`
- `SUBCONTRACT_RATE_REQUIRED`
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_SETTLEMENT_LOCKED`
- `SUBCONTRACT_STOCK_SYNC_FAILED`
- `SUBCONTRACT_DRY_RUN_DISABLED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `INTERNAL_API_DISABLED`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `SUBCONTRACT_INTERNAL_ERROR`

【输出物要求】
1. `02_模块设计_外发加工管理.md` 升级为 V1.1（替换 V1.0 粗粒度内容）。
2. `当前 sprint 任务清单.md` 增加 TASK-002A~TASK-002H 的依赖顺序与门禁。
3. 本任务单（TASK-002A）作为后续工程实现准入依据。

【验收标准】
□ `02_模块设计_外发加工管理.md` 明确标记版本 V1.1。
□ 数据模型包含 outbox/sync_log，不再是仅演示 4 张表。
□ API 契约包含详情、取消、重试、internal worker。
□ 写接口幂等契约覆盖创建、发料、回料、验货、取消、库存同步重试。
□ 相同幂等键相同 payload 不重复生成本地事实和 outbox。
□ 相同幂等键不同 payload 返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
□ 权限矩阵包含 `subcontract:*` 动作和 `company/item_code/supplier/warehouse` 资源维度。
□ 审计要求明确覆盖 401/403/503 与写操作。
□ ERPNext 边界明确“不能直写 ERPNext 表”。
□ 一致性策略明确“本地事实 + outbox -> after-commit/worker”。
□ 金额公式修正，不再存在“数量减金额”口径。
□ 对账字段包含 `statement_id/settlement_no/settled_by/settled_at`。
□ 结算后锁定规则明确，调整/反冲必须走 TASK-006。
□ 内部库存同步 worker 契约包含生产开关、服务账号最小权限、dry-run/诊断审计、越权 outbox 处理。
□ 校验规则覆盖 Supplier/Item/BOM/工序/Warehouse。
□ 错误码清单可直接供 TASK-002B~H 复用。
□ `当前 sprint 任务清单.md` 增加 TASK-002A 门禁。

【后续拆分任务（冻结）】
1. `TASK-002B` 外发权限与审计基线
2. `TASK-002C` 外发数据模型与迁移
3. `TASK-002D` 发料 Stock Entry Outbox
4. `TASK-002E` 回料 Stock Entry Outbox
5. `TASK-002F` 验货扣款金额口径
6. `TASK-002G` 前端状态与权限联动
7. `TASK-002H` 对账数据出口

【禁止事项】
1. 禁止在 TASK-002A 未冻结前直接扩展演示 service 进入业务实现。
2. 禁止发料/回料继续使用伪 `stock_entry_name` 充当库存落账。
3. 禁止只做前端权限隐藏，不做后端动作/资源校验。
4. 禁止在本地事务提交前直接调用 ERPNext 写库存。
5. 禁止继续沿用错误金额公式（数量减金额）。
6. 禁止外发写接口无幂等键直接落事实或 outbox。
7. 禁止已结算外发单直接修改金额。
8. 禁止普通业务账号调用内部库存同步 worker。

【完成后回报格式】
请按以下格式回报：

TASK-002A 外发模块设计契约冻结已完成

修改文件：
- ...

冻结结果：
- 数据模型契约：完成 / 未完成
- 状态机契约：完成 / 未完成
- API 契约：完成 / 未完成
- 写接口幂等契约：完成 / 未完成
- 权限与审计契约：完成 / 未完成
- ERPNext 边界与一致性策略：完成 / 未完成
- 金额公式与校验规则：完成 / 未完成
- 对账结算边界：完成 / 未完成
- 内部库存同步 worker 安全契约：完成 / 未完成
- 错误码冻结：完成 / 未完成

遗留问题：
- 无 / ...
