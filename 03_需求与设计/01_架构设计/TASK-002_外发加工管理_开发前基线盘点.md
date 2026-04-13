# TASK-002 外发加工管理开发前基线盘点 / 架构审计意见

- 模块名：外发加工管理
- 任务编号：TASK-002
- 版本：V1.0
- 更新时间：2026-04-12 19:57 CST
- 作者：技术架构师
- 文档类型：开发前基线盘点 / 架构审计意见

## 1. 审计结论

结论：不建议直接进入工程实现，必须先冻结 TASK-002 外发模块契约，再拆分整改任务单开发。

当前外发模块已有后端模型、路由、服务和前端页面骨架，但整体仍是演示级实现，尚未满足衣算云外发加工链路「发料 -> 回料 -> 验货 -> 扣款 -> 对账」的生产级闭环要求。

最关键阻塞：

1. 发料/回料没有真实创建 ERPNext `Stock Entry`，只是生成伪 `stock_entry_name`。
2. 后端没有鉴权、资源级权限、安全审计和操作审计。
3. 本地事务与 ERPNext 库存落账没有一致性策略，缺少 outbox / 重试 / 对账机制。
4. 状态机、金额公式、BOM 工序校验、加工厂主数据校验均不完整。
5. 没有 TASK-002 专属迁移和测试用例。

开发前门禁：TASK-002 必须先补模块设计 V1.1 和 TASK-002A 基线整改任务单，再允许工程师实现。

## 2. 读取范围

### 2.1 设计与计划

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/00_总体架构概览.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`

### 2.2 现有后端代码

1. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
3. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
6. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
7. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/`
8. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/`

### 2.3 现有前端代码

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`

### 2.4 衣算云资料

1. `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/衣算云文档/06_跨模块关联逻辑.md`
2. `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/衣算云文档/08_校验拦截规则.md`
3. `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/衣算云文档/11_数据表映射关系.md`
4. `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/衣算云文档/72_衣算云_功能与子功能详细说明_完整版_20260405.md`
5. `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/衣算云文档/73_衣算云_全流程细节闭环说明_完整版_20260405.md`

## 3. 现有资产盘点

| 层级 | 已有资产 | 当前状态 | 结论 |
| --- | --- | --- | --- |
| 架构设计 | `02_模块设计_外发加工管理.md` | V1.0，覆盖基础表、状态机、5 个接口 | 过粗，缺权限、审计、Stock Entry 一致性、金额口径、对账边界 |
| Sprint 计划 | `当前 sprint 任务清单.md` TASK-002 | 定义目标、表、接口、ERPNext 能力 | 可作为初始任务卡，不足以直接开发 |
| 后端模型 | `models/subcontract.py` | 4 张表：order/material/receipt/status_log | 字段不足，缺 company、warehouse、stock outbox、对账状态、审计字段 |
| 后端 Schema | `schemas/subcontract.py` | create/list/issue/receive/inspect 基础 payload | 缺 detail、cancel、状态动作、幂等、错误码、权限上下文 |
| 后端 Service | `subcontract_service.py` | 可本地建单、发料、回料、验货 | 演示逻辑，未接 ERPNext，未接权限/审计/异常分类 |
| 后端 Router | `routers/subcontract.py` | 已注册 `/api/subcontract` | 无当前用户依赖，无动作权限，无资源权限，无安全审计 |
| ERPNext 集成 | 无真实 adapter | 发料生成 `STE-ISS-*` 假编号 | P0 阻塞 |
| 数据迁移 | 未发现 TASK-002 专属 migration | 仅有 BOM/Workshop 迁移 | P0 阻塞 |
| 自动测试 | 未发现 subcontract 专属测试 | 仅 BOM/Workshop 测试覆盖 | P0 阻塞 |
| 前端 API | `src/api/subcontract.ts` | fetch 基础接口 | 无统一 request 封装、无权限动作、无错误信封解析 |
| 前端页面 | 列表 + 详情处理页 | 能录入基础字段 | 缺详情加载、状态按钮控制、物料明细表、验货/扣款/对账展示 |

## 4. 衣算云外发链路要点

从资料侧提取的外发相关闭环如下：

1. 加工厂是硬前置主数据，映射到 ERPNext `Supplier` 的加工厂类型或自定义标识。
2. 仓库、加工厂、物料、款式是交易链路必填条件。
3. 物料加工、物料加工入仓、加工厂应退料报表、加工厂对账/应付/评估属于外发闭环关联页面。
4. 库存类动作必须落到 ERPNext `Stock Entry` / `Stock Ledger Entry`，FastAPI 不直接写库存台账。
5. 财务对账类接口要求主体 ID，空主体必须拦截。
6. 对账余额类算法已有滚动余额口径，外发后续进入 TASK-006 时必须复用加工厂维度数据。

## 5. P0 阻塞问题

### P0-001 ERPNext Stock Entry 未真实接入

现状：`issue_material()` 仅生成 `STE-ISS-{timestamp}`，没有创建 ERPNext `Stock Entry`。`receive()` 也没有创建回料 `Stock Entry`。

影响：库存台账不变，发料/回料只存在本地业务记录，无法满足 ERPNext 库存边界。

整改要求：必须实现 ERPNext `Stock Entry` adapter 和本地 outbox / 同步日志。发料为 `Material Issue`，回料为 `Material Receipt` 或按 ERPNext 实际类型映射。

### P0-002 本地事务与 ERPNext 库存落账缺少一致性策略

现状：本地 commit 与 ERPNext 写接口没有事务边界设计。

影响：如果直接在本地事务内调用 ERPNext，可能出现 ERPNext 已落账、本地回滚；如果本地先提交再调用 ERPNext，可能出现本地成功、库存未落账。

整改要求：采用 `ly_subcontract_stock_outbox` + `ly_subcontract_stock_sync_log`，本地事务写业务事实和 outbox，after-commit/worker 调用 ERPNext，失败可重试、可人工补偿。

### P0-003 权限和审计缺失

现状：`routers/subcontract.py` 未接入 `get_current_user()`，`core/permissions.py` 没有 `subcontract:*` 权限动作，写接口无安全审计和操作审计。

影响：任何可访问接口的人都可创建、发料、回料、验货，绕过 ERPNext `Role / User Permission`。

整改要求：新增动作权限：`subcontract:read`、`subcontract:create`、`subcontract:issue_material`、`subcontract:receive`、`subcontract:inspect`、`subcontract:cancel`、`subcontract:stock_sync_worker`。资源权限必须按 `company/item_code/supplier/warehouse` 校验。

### P0-004 加工厂、BOM、工序、仓库主数据未校验

现状：创建外发单只校验 BOM id 存在，不校验 supplier 是否为 ERPNext 加工厂，不校验 item_code 与 BOM 是否一致，不校验 process_name 是否为 BOM 外发工序，不校验 warehouse。

影响：外发单可引用错误加工厂、错误款式、非外发工序和不存在仓库。

整改要求：创建外发单必须校验：

1. `supplier` 存在于 ERPNext `Supplier`，且为加工厂类型。
2. `item_code` 存在于 ERPNext `Item`。
3. `bom_id` 对应 `ly_apparel_bom`，且 `bom.item_code == payload.item_code`。
4. `process_name` 存在于 `ly_bom_operation`，且 `is_subcontract=true`。
5. 发料仓、回料仓存在于 ERPNext `Warehouse`，且当前用户有权限。

### P0-005 状态机不一致

现状：设计写 `draft -> processing -> waiting_receive -> waiting_inspection -> completed`，代码发料后直接 `draft -> waiting_receive`，没有 `processing`；`receive()` 允许 `draft` 状态直接回料。

影响：状态流转无法反映真实业务，不利于权限、审计、看板和后续对账。

整改要求：冻结状态机：`draft -> issued -> processing -> waiting_receive -> waiting_inspection -> completed/cancelled`，或保留设计状态但必须确保动作与状态一致。禁止 `draft` 直接回料。

### P0-006 金额公式单位错误

现状：`inspect()` 中 `net_amount = inspected_qty - deduction_amount`，数量减金额，量纲错误。

影响：加工费、扣款、实付金额全部不可信，后续款式利润和加工厂对账会错。

整改要求：必须引入外发单价：`subcontract_rate` 或引用 BOM 外发工序 `subcontract_cost_per_piece`。

公式冻结：

1. `accepted_qty = inspected_qty - rejected_qty`。
2. `rejected_rate = rejected_qty / inspected_qty`。
3. `gross_amount = inspected_qty * subcontract_rate` 或按衣算云确认为 `accepted_qty * subcontract_rate`。
4. `deduction_amount = rejected_qty * deduction_rate`。
5. `net_amount = gross_amount - deduction_amount`。

### P0-007 发料数量完全由前端传入

现状：`IssueMaterialRequest` 允许前端传 `required_qty/issued_qty`，后端不按 BOM 展开核算。

影响：可超发、错发、漏发，无法追溯物料需求来源。

整改要求：发料应从 BOM 展开结果或外发单物料计划生成，前端只能提交本次实发数量；系统校验 `issued_qty <= remaining_required_qty`，并按物料、批次、仓库累计。

### P0-008 迁移缺失

现状：未发现 `task_002_*subcontract*.py` 迁移。

影响：模型无法可靠落库，审计无法复验 schema、索引、约束。

整改要求：新增 Alembic 迁移，包含主表、明细、收货、验货、状态日志、Stock Entry outbox、同步日志、必要唯一索引和检查约束。

### P0-009 自动测试缺失

现状：未发现 subcontract 专属测试。

影响：状态机、金额、ERPNext 同步、权限、审计无法回归。

整改要求：新增 `tests/test_subcontract_*.py`，覆盖 create/list/issue/receive/inspect/cancel/stock_sync/auth/audit/exception/idempotency。

## 6. P1 重要缺口

### P1-001 API 错误信封不统一

现状：成功响应带 `trace_id`，错误响应依赖 `HTTPException(detail=str)` 后由 main 变成 `HTTP_ERROR`。与 BOM/Workshop 的标准错误码、request_id、安全审计口径不一致。

整改要求：使用统一 `{code, message, data}` 成功信封和 `{code, message, detail}` 错误信封；`trace_id` 改为规范化 `request_id`。

### P1-002 缺少详情接口

现状：前端详情页只从 URL 取 `id`，不加载外发单、物料、回料、验货、状态日志。

整改要求：新增 `GET /api/subcontract/{id}`，返回 `order/materials/receipts/inspections/status_logs/stock_sync_status`。

### P1-003 缺少取消、重试、补偿动作

现状：无取消接口，无 ERPNext Stock Entry 同步重试接口，无失败补偿入口。

整改要求：新增 `POST /api/subcontract/{id}/cancel`、`POST /api/subcontract/{id}/stock-sync/retry`、内部 worker `POST /api/subcontract/internal/stock-sync/run-once`。

### P1-004 缺少幂等键

现状：发料、回料、验货多次提交会重复落本地记录。

整改要求：写接口必须支持 `idempotency_key` 或业务唯一键，重复提交 payload 一致返回原结果，payload 不一致返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。

### P1-005 对账数据边界不清

现状：TASK-006 依赖外发数据，但 TASK-002 未定义对账可用字段和锁定规则。

整改要求：TASK-002 必须输出可结算字段：`gross_amount/deduction_amount/net_amount/settlement_status/statement_id`，对账确认后外发明细不得直接改金额，只能调整或反冲。

### P1-006 前端无按钮权限和状态控制

现状：列表和详情页按钮始终展示，详情页不读取当前状态，直接允许发料、回料、验货操作。

整改要求：前端按钮必须由 `/api/auth/actions?module=subcontract` 和单据状态共同控制；后端仍必须强制校验。

### P1-007 仓库/批次/颜色/尺码维度不足

现状：发料明细只有 `material_item_code/required_qty/issued_qty/stock_entry_name`。

整改要求：补齐服装物料维度：`warehouse/batch/color/size/uom/conversion_factor`，至少为后续物料进销存和加工厂应退料报表预留字段。

## 7. P2 优化项

1. 前端页面使用 `window.location.href` 跳转，建议统一使用 Vue Router。
2. 外发单号目前基于时间戳，建议接入统一编码规则或数据库序列，避免并发碰撞。
3. `from_date/to_date` 当前用字符串比较，建议改为日期类型解析和时区边界。
4. 模型缺少 `created_by/updated_by/approved_by` 等操作者字段。
5. 状态日志只有 operator 字符串，缺少 request_id、remark、source、before/after 快照。

## 8. 建议冻结的数据模型

### 8.1 必保留表

| 表名 | 用途 | 必须补齐字段 |
| --- | --- | --- |
| `ly_schema.ly_subcontract_order` | 外发加工主单 | `company, supplier, item_code, bom_id, process_name, subcontract_rate, planned_qty, issued_qty, received_qty, inspected_qty, rejected_qty, gross_amount, deduction_amount, net_amount, settlement_status, status, created_by, updated_by` |
| `ly_schema.ly_subcontract_material` | 发料计划和发料事实 | `warehouse, material_item_code, color, size, batch_no, required_qty, issued_qty, remaining_qty, stock_entry_name, sync_status` |
| `ly_schema.ly_subcontract_receipt` | 回料事实 | `receipt_warehouse, received_qty, stock_entry_name, sync_status, received_at, received_by` |
| `ly_schema.ly_subcontract_inspection` | 验货事实 | `inspected_qty, accepted_qty, rejected_qty, rejected_rate, deduction_rate, deduction_amount, net_amount, inspected_by, inspected_at` |
| `ly_schema.ly_subcontract_status_log` | 状态流转 | `from_status, to_status, action, operator, request_id, remark, before_data, after_data` |

### 8.2 建议新增表

| 表名 | 用途 | 说明 |
| --- | --- | --- |
| `ly_schema.ly_subcontract_stock_outbox` | ERPNext Stock Entry 异步同步任务 | 发料/回料均通过 outbox 触发 ERPNext 写入 |
| `ly_schema.ly_subcontract_stock_sync_log` | Stock Entry 同步日志 | 记录每次尝试、错误码、ERPNext 返回 name |
| `ly_schema.ly_subcontract_operation_audit` | 外发操作审计，如复用全局审计表可不建 | 推荐复用 `ly_operation_audit_log` |

## 9. 建议冻结 API 契约

| 接口 | 方法 | 路径 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| 创建外发单 | POST | `/api/subcontract/` | 从 BOM 外发工序创建外发单 | P0 |
| 查询外发单 | GET | `/api/subcontract/` | 分页筛选 | P0 |
| 外发详情 | GET | `/api/subcontract/{id}` | 返回主单、物料、回料、验货、状态日志 | P0 |
| 发料 | POST | `/api/subcontract/{id}/issue-material` | 写本地发料事实和 Stock Entry outbox | P0 |
| 回料 | POST | `/api/subcontract/{id}/receive` | 写本地回料事实和 Stock Entry outbox | P0 |
| 验货 | POST | `/api/subcontract/{id}/inspect` | 计算合格、不合格、扣款、应付金额 | P0 |
| 取消 | POST | `/api/subcontract/{id}/cancel` | 草稿/未结算单据取消 | P1 |
| 手动重试库存同步 | POST | `/api/subcontract/{id}/stock-sync/retry` | 重试指定单据库存同步 | P1 |
| 内部 Stock Sync Worker | POST | `/api/subcontract/internal/stock-sync/run-once` | 服务账号处理 outbox | P1 |

## 10. ERPNext 边界冻结

| 能力 | ERPNext 负责 | FastAPI 负责 |
| --- | --- | --- |
| 加工厂主数据 | `Supplier` + 加工厂标识 | 校验和引用 `supplier` |
| 款式主数据 | `Item` | 引用 `item_code`，不复制主数据 |
| 仓库主数据 | `Warehouse` | 校验发料仓/收料仓权限 |
| 库存落账 | `Stock Entry` / `Stock Ledger Entry` | 生成业务 outbox、调用 ERPNext、保存 `stock_entry_name` |
| 财务应付 | `Purchase Invoice` / AP | TASK-006 对账确认后生成应付草稿 |
| 权限事实源 | `Role / User Permission` | 聚合动作权限和资源权限，fail closed |

## 11. 推荐后续任务拆分

| 任务编号 | 任务名称 | 目标 | 优先级 |
| --- | --- | --- | --- |
| TASK-002A | 外发模块设计契约冻结 | 更新模块设计 V1.1，冻结表、状态机、API、ERPNext 边界 | P0 |
| TASK-002B | 外发权限与审计基线 | 接入当前用户、动作权限、资源权限、安全审计、操作审计 | P0 |
| TASK-002C | 外发数据模型与迁移 | 新增迁移、补齐字段、索引、约束、outbox/log 表 | P0 |
| TASK-002D | 发料 Stock Entry Outbox | 发料按 BOM 物料计划写 outbox，Worker 创建 ERPNext `Material Issue` | P0 |
| TASK-002E | 回料 Stock Entry Outbox | 回料写 outbox，Worker 创建 ERPNext `Material Receipt` | P0 |
| TASK-002F | 验货扣款金额口径 | 修复验货公式，固化 `gross/deduction/net` | P0 |
| TASK-002G | 前端状态与权限联动 | 详情页加载真实数据，按钮按权限和状态显示 | P1 |
| TASK-002H | 对账数据出口 | 为 TASK-006 输出可结算明细和锁定规则 | P1 |

## 12. 开发前门禁

在 TASK-002A 开始前，工程师不得直接扩展当前 `subcontract_service.py` 的演示逻辑。

必须先完成：

1. 外发模块设计 V1.1。
2. 外发状态机冻结。
3. Stock Entry 同步策略冻结。
4. 权限动作矩阵冻结。
5. 数据模型迁移范围冻结。
6. 金额公式冻结。
7. TASK-002A 工程任务单输出。

## 13. 总体判断

TASK-002 当前代码可作为接口命名和页面骨架参考，不可作为生产实现基线。外发模块牵动 BOM、库存、加工厂、财务对账和款式利润，必须按“先契约、再权限、再库存同步、再金额与对账”的顺序推进。

建议下一步：输出 TASK-002A《外发模块设计契约冻结整改任务单》。
