# ERPNext 生产联调方案

- 任务编号：TASK-015A
- 任务名称：ERPNext 生产联调设计冻结
- 文档状态：待审计
- 更新日期：2026-04-17
- 适用阶段：TASK-015A（设计冻结）

## 1. 联调状态与边界

本方案是生产联调设计冻结，不代表生产联调已经执行。
TASK-014C 未完成前，不允许执行真实生产联调。
不得连接生产 ERPNext。
不得写入生产 ERPNext。
不得绕过 TASK-008 Fail-Closed Adapter。
不得绕过 TASK-009 Outbox 状态机。

补充冻结口径：

1. Hosted Runner 与 Branch Protection required checks 当前仍未平台闭环。
2. 本文档仅冻结联调要求与证据模板，不代表任何平台动作已完成。
3. 本文档不构成生产发布依据。

## 2. 账号与权限要求

### 2.1 只读联调账号权限

| 账号类型 | Doctype/能力 | 允许动作 | 禁止动作 |
|---|---|---|---|
| `erpnext_ro_integration` | Supplier/Item/Warehouse/BOM/Work Order/Sales Order/Delivery Note/SLE/Account/Cost Center/Purchase Invoice/Payment Entry/GL Entry | GET/查询 | 所有写动作（POST/PUT/PATCH/DELETE/submit/cancel） |
| `erpnext_ro_permission_source` | User Permission、Company 维度读取 | GET/查询 | 所有写动作 |

### 2.2 沙箱写入账号权限

| 账号类型 | 环境 | 允许动作 | 限制 |
|---|---|---|---|
| `erpnext_sandbox_writer` | ERPNext Sandbox | 草稿创建（Purchase Invoice/Stock Entry/Payment Entry/Work Order） | 仅草稿；不得提交生产；必须经 Adapter 与 Outbox |

### 2.3 生产写入账号冻结策略

1. 生产写入账号默认冻结，不发放到业务开发执行链路。
2. 未下发独立生产写入任务单前，所有写能力均视为禁用。
3. 即使沙箱验证通过，也不得外推为生产可写。

### 2.4 ERPNext API Key / Secret 管理方式

1. 仅通过管理员平台 Secret 管理，不写入仓库与文档。
2. 本地 `.env` 仅可放占位键名，不可放真实值。
3. 运行日志与证据文档必须脱敏（不可出现 token/secret/password/DSN）。

### 2.5 最小权限原则与账号治理

1. 按模块、按环境、按动作分离账号。
2. 禁止共享个人账号用于联调。
3. 禁止使用管理员全权限账号进行常规联调。

### 2.6 账号失效/权限不足/ERPNext 不可用时 fail-closed 规则

1. 账号失效、401/403：fail closed，返回标准错误信封并记安全审计。
2. 权限不足：fail closed，不得降级为“空数据成功”。
3. ERPNext timeout/5xx/网络不可达：fail closed，不得返回 200 + 空数据。
4. 权限源不可用：fail closed，不得放行为 unrestricted。

## 3. 主数据清单（含校验方式）

| 主数据 | 来源 | 用途 | 是否只读 | 是否允许沙箱写入 | 是否允许生产写入 | 缺失时处理策略 |
|---|---|---|---|---|---|---|
| Company | ERPNext | 公司归属与权限域 | 是 | 否 | 否 | fail closed，阻断流程 |
| Item | ERPNext | 物料归属、质量/库存关联 | 是 | 否 | 否 | fail closed，返回主数据缺失错误 |
| Supplier | ERPNext | 供应商归属、应付关联 | 是 | 否 | 否 | fail closed，阻断确认/写入 |
| Customer | ERPNext | 销售只读查询与过滤 | 是 | 否 | 否 | fail closed，阻断返回 |
| Warehouse | ERPNext | 库存归属与仓库过滤 | 是 | 否 | 否 | fail closed，阻断返回 |
| BOM | ERPNext | 生产只读依赖 | 是 | 否 | 否 | fail closed，阻断读取结果 |
| Work Order | ERPNext | 生产单据关联 | 是 | 沙箱可草稿创建验证 | 否 | 缺失/非法状态 fail closed |
| Sales Order | ERPNext | 销售订单只读与关联 | 是 | 否 | 否 | docstatus 缺失/非法 fail closed |
| Delivery Note | ERPNext | 发货单只读关联 | 是 | 否 | 否 | docstatus 缺失/非法 fail closed |
| Stock Ledger Entry | ERPNext | 库存流水只读事实 | 是 | 否 | 否 | 必填字段缺失 fail closed |
| Account | ERPNext | 财务科目校验 | 是 | 否 | 否 | fail closed，阻断草稿创建 |
| Cost Center | ERPNext | 成本中心校验 | 是 | 否 | 否 | fail closed，阻断草稿创建 |
| Purchase Invoice | ERPNext | 应付草稿与只读查询 | 是（生产） | 沙箱可草稿创建验证 | 否 | 缺失/docstatus 非法 fail closed |
| Payment Entry | ERPNext | 只读查询、沙箱草稿验证 | 是（生产） | 沙箱可草稿创建验证 | 否 | 缺失/非法 fail closed |
| GL Entry | ERPNext | 总账只读核对 | 是 | 否 | 否 | 查询异常 fail closed |

## 4. 只读 API 验证清单

说明：以下路径均通过 TASK-008 Adapter 发起，禁止前端或业务逻辑裸连 ERPNext。

| 验证项 | API 路径（ERPNext） | 预期成功条件 | 预期 fail-closed 条件 | 禁止伪成功条件 |
|---|---|---|---|---|
| Supplier 读取 | `GET /api/resource/Supplier` | 返回结构合法、字段完整 | 401/403/404/5xx/timeout/malformed | `200 + []` 或吞异常后成功 |
| Item 读取 | `GET /api/resource/Item` | 返回 Item 标识、状态可用 | 缺字段、状态非法、响应结构错误 | 用默认字段填充后继续 |
| Warehouse 读取 | `GET /api/resource/Warehouse` | company 归属可校验 | company 缺失/非法、401/403/5xx | company 缺失仍放行 |
| BOM 读取 | `GET /api/resource/BOM` | 读取 BOM 基本字段 | 404/5xx/malformed | 404 返回 success |
| Work Order 读取 | `GET /api/resource/Work Order` | docstatus 合法且字段完整 | docstatus 缺失/非法、timeout | docstatus 默认 0 放行 |
| Sales Order 读取 | `GET /api/resource/Sales Order` | docstatus 合法，数据完整 | docstatus 非法、401/403、5xx | 200 空数据当成功 |
| Delivery Note 读取 | `GET /api/resource/Delivery Note` | docstatus 合法，结构正常 | docstatus 缺失/非法、malformed | 降级为空列表成功 |
| Stock Ledger Entry 读取 | `GET /api/resource/Stock Ledger Entry` | `company/item_code/warehouse/posting_date/actual_qty/qty_after_transaction` 完整 | 任一必填字段缺失、malformed | 缺字段行仍纳入结果 |
| Account 读取 | `GET /api/resource/Account` | account 可用且归属合法 | 404/401/403/5xx | 失败时返回默认账户 |
| Cost Center 读取 | `GET /api/resource/Cost Center` | cost center 可用且归属合法 | 404/401/403/timeout | 失败时静默降级 |
| GL Entry 只读查询 | `GET /api/resource/GL Entry` | 只读查询成功，字段完整 | 401/403/5xx/malformed | 200 + 空对象伪成功 |
| Purchase Invoice 只读查询 | `GET /api/resource/Purchase Invoice` | 仅查询，不写入 | docstatus 异常、响应非法 | 查询失败伪装成功 |
| Payment Entry 只读查询 | `GET /api/resource/Payment Entry` | 仅查询，不写入 | 401/403/timeout/5xx | 空数据当成功 |

## 5. 沙箱写入验证清单（仅设计，不执行）

说明：本节仅冻结验证项。TASK-014C 未完成前不得执行。

| 验证项 | 允许环境 | 约束 | 必经链路 | 审计要求 |
|---|---|---|---|---|
| Purchase Invoice 草稿创建 | Sandbox | 仅草稿，不 submit | TASK-008 Adapter + TASK-009 Outbox | 安全审计 + 操作审计 |
| Stock Entry 草稿创建 | Sandbox | 仅草稿，不提交生产 | TASK-008 Adapter + TASK-009 Outbox | 安全审计 + 操作审计 |
| Payment Entry 草稿创建 | Sandbox | 仅草稿验证，不入生产账务 | TASK-008 Adapter + TASK-009 Outbox | 安全审计 + 操作审计 |
| Work Order 草稿创建 | Sandbox | 仅草稿，不允许生产执行 | TASK-008 Adapter + TASK-009 Outbox | 安全审计 + 操作审计 |
| Outbox `pending -> processing -> succeeded/failed` | 本地+Sandbox 模拟 | 不允许绕过状态机 | TASK-009 统一状态机 | 操作审计完整 |
| 幂等 replay/conflict | 本地+Sandbox 模拟 | `idempotency_key` 与 `event_key` 分离校验 | TASK-009 规范 | 安全审计 + 操作审计 |
| `external_docname` 回填 | Sandbox | 仅在外调成功后回填 | TASK-008 + TASK-009 | 回填行为写操作审计 |
| ERPNext `5xx/timeout/malformed` fail-closed | Sandbox | 失败必须阻断并留痕 | TASK-008 Adapter | 安全审计完整，禁止伪成功 |

强制规则：

1. 只能在沙箱执行。
2. 不允许生产执行。
3. 必须经过 TASK-008 Adapter。
4. 必须经过 TASK-009 Outbox。
5. 必须写安全审计与操作审计。

## 6. 安全约束

1. 禁止生产写入。
2. 禁止裸连 ERPNext `/api/resource`（仅允许 Adapter 封装调用）。
3. 禁止把 ERPNext secret 写入仓库。
4. 禁止 `detail=str(exc)` 泄露。
5. 禁止 `200 + 空数据` 伪成功。
6. 禁止跳过权限校验。
7. 禁止跳过审计日志。
8. 禁止跳过 outbox 直接写财务/库存/生产单据。
9. 禁止本地测试结果冒充生产联调证据。
10. 禁止在 TASK-014C 未完成前启动真实联调。

## 7. 联调证据模板（冻结）

> 使用说明：每条联调记录必须一行一证据；敏感字段必须脱敏。

| 字段 | 说明 | 必填 |
|---|---|---|
| ERPNext 环境（生产/沙箱） | 当前联调环境 | 是 |
| 执行人 | 责任人 | 是 |
| 执行时间 | 开始-结束时间 | 是 |
| commit SHA | 对应代码版本 | 是 |
| API 名称 | 适配器动作名 | 是 |
| request_id | 请求链路 ID | 是 |
| trace_id | 全链路追踪 ID | 是 |
| ERPNext response status | 上游状态码 | 是 |
| 本地错误信封 | `{code,message,data}` 摘要 | 是 |
| 安全审计日志 ID | 安全审计记录主键 | 是 |
| 操作审计日志 ID | 操作审计记录主键 | 是 |
| outbox event_key | 仅涉及 outbox 时填写 | 条件必填 |
| external_docname | 外部单据号回填值 | 条件必填 |
| 结论 | 通过/失败/阻断 | 是 |
| 敏感信息扫描结论 | 无泄露/发现泄露并阻断 | 是 |

## 8. 本任务结论边界

1. 本文档仅为设计冻结，不代表生产联调已经执行。
2. `TASK-014C` 未完成前，真实生产联调继续冻结。
3. 未经管理员提供最小平台证据包，不进入平台闭环任务。
4. 本文档不触发代码实现、不触发环境变更、不触发发布动作。
