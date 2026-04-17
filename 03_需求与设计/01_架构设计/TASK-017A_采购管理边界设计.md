# TASK-017A 采购管理边界设计

- 任务编号：TASK-017A
- 任务名称：采购管理边界设计冻结
- 文档状态：待审计
- 更新日期：2026-04-17
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结 Purchase Order、Purchase Receipt、Purchase Invoice、Supplier 主数据的系统责任、权限边界、审批边界、ERPNext 集成策略、Outbox 使用边界与审计要求，作为后续采购模块实现任务的唯一前置设计。

本任务只做设计冻结，不做代码实现，不做环境联调，不做任何 ERPNext 写操作。

## 2. 采购模块总边界（5.1）

本任务仅冻结采购管理设计边界。
禁止实现 Purchase Order / Purchase Receipt / Purchase Invoice / Supplier 写入代码。
禁止连接生产 ERPNext。
禁止直接写 ERPNext 采购接口。
禁止绕过 TASK-008 Fail-Closed Adapter。
禁止绕过 TASK-009 Outbox 状态机。
TASK-014C 未完成前，不允许进入任何真实平台联调或生产发布。

补充冻结口径：

1. 本文档不代表采购功能可上线。
2. 本文档不代表 Hosted Runner required checks 与 Branch Protection 已闭环。
3. 采购写入能力必须后续单独任务、单独审计、单独放行。

## 3. Purchase Order 边界（5.2）

### 3.1 创建范围

1. 本阶段仅冻结 PO 创建规则，不执行实现。
2. PO 创建仅允许在受控后端服务入口定义，不允许前端直写 ERPNext。
3. PO 创建必须携带 company/supplier/item_code/warehouse 等关键资源上下文。

### 3.2 审批流程

1. PO 采用“草稿 -> 审批确认”双阶段。
2. 审批动作必须与创建动作分离，禁止同角色默认全流程直通。
3. 审批拒绝必须写安全审计/操作审计记录。

### 3.3 修改/取消范围

1. draft 状态允许受控修改。
2. confirmed/succeeded 后默认不允许业务字段直接修改。
3. 取消动作需权限校验与审计落库。

### 3.4 谁可以创建、审批、取消

1. 创建：`purchase:po_draft`。
2. 审批确认：`purchase:po_confirm`。
3. 取消：`purchase:po_cancel`。
4. 普通只读角色不得触发创建/审批/取消。

### 3.5 与 ERPNext 的集成方式

1. 只读查询走 Adapter（TASK-008）。
2. 写入草稿走 Outbox（TASK-009）。
3. 生产写入继续冻结。

### 3.6 幂等策略

1. `idempotency_key`：请求级重放/冲突判定。
2. `event_key`：业务事实级去重。
3. replay/conflict：同 key 同 hash replay，同 key 异 hash conflict；不同 key 同事实命中 event_key 防重。

### 3.7 状态机（冻结）

```text
draft -> pending_outbox -> processing -> succeeded
                               |             |
                               |             -> failed -> pending_outbox (retry)
                               |                           |
                               |                           -> dead
                               -> cancelled
```

状态集合：

- `draft`
- `pending_outbox`
- `processing`
- `succeeded`
- `failed`
- `dead`
- `cancelled`

### 3.8 操作审计要求

1. create/update/confirm/cancel/retry/dead 均需操作审计。
2. 权限拒绝、资源越权、ERPNext 不可用必须安全审计。
3. 审计脱敏：禁止记录 token/secret/password/DSN。

## 4. Purchase Receipt 边界（5.3）

1. Purchase Receipt 入库边界：仅冻结业务责任与校验项，不实现入库写逻辑。
2. 与 Stock Ledger / Stock Entry 关系：
   - Receipt 是入库业务事实来源之一；
   - Stock Ledger/Stock Entry 为库存结果事实；
   - 三者关联必须由后端受控链路与审计串联，不允许前端拼装事实。
3. 是否允许生产写入：当前阶段不允许。
4. 只读查询与写入草稿边界：
   - 查询可走 Adapter；
   - 草稿写入仅后续任务在沙箱验证；
   - 生产写入冻结。
5. 入库数量、批次、仓库、Item 资源校验：必须校验 `company/supplier/item_code/warehouse/purchase_receipt`。
6. ERPNext 不可用/malformed/timeout：必须 fail closed，禁止 200 + 空数据。
7. 与 TASK-018 依赖关系：采购入库与仓库增强需在 TASK-018 中定义库存侧最终影响路径与 outbox 协同规则。

## 5. Purchase Invoice 边界（5.4）

1. Purchase Invoice 与 AP 联动：PI 为应付事实来源之一，AP 口径需与 TASK-016A 一致。
2. 与 TASK-016A 一致性：
   - PI 生产侧默认只读；
   - 写入能力冻结；
   - 财务审批链路不可绕过。
3. Purchase Invoice 只读查询范围：状态、金额、供应商、公司归属等只读字段。
4. Purchase Invoice 草稿创建是否允许：本阶段仅设计冻结，后续仅可在沙箱受控验证。
5. 与 TASK-006 payable draft 边界关系：
   - TASK-006 负责加工厂应付草稿业务链路；
   - 采购 PI 与加工厂 payable draft 必须通过统一幂等与审计口径收口；
   - 禁止重复建草稿。
6. 禁止重复生成 PI 草稿：必须使用 `idempotency_key + event_key` 防重。
7. 禁止绕过财务审批直接提交 PI。
8. 禁止生产写入，除非后续单独任务审计放行。

## 6. Supplier 主数据边界（5.5）

1. Supplier 默认只读集成。
2. Supplier 创建/修改不纳入本阶段。
3. Supplier 资源权限：必须校验 `company + supplier`，并结合动作权限。
4. fail-closed 规则：Supplier 不存在/disabled/permission denied 时必须阻断。
5. 敏感字段脱敏：供应商名称、税号、银行账号等在日志与审计输出中按最小暴露规则脱敏。
6. 禁止前端直接维护 ERPNext Supplier 主数据。

## 7. ERPNext 集成策略（5.6）

| 采购能力 | ERPNext DocType | 只读/写入 | Adapter | Outbox | 是否允许生产 |
|---|---|---|---|---|---|
| 采购订单 | Purchase Order | 生产只读；写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 采购收货 | Purchase Receipt | 生产只读；写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 采购发票 | Purchase Invoice | 生产只读；草稿写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 供应商 | Supplier | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 物料 | Item | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 仓库 | Warehouse | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 科目 | Account | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 成本中心 | Cost Center | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 库存流水 | Stock Ledger Entry | 只读 | 必须（TASK-008） | 不适用（当前只读） | 否 |
| 库存分录 | Stock Entry | 只读（当前采购模块） | 必须（TASK-008） | 若未来写入必须接入（TASK-009） | 否（当前冻结） |

集成总原则：

1. ERPNext 访问统一经 Adapter。
2. 写链路统一经 Outbox。
3. 未明确放行即默认 fail closed。

## 8. 权限与审计要求（5.7）

### 8.1 动作权限（冻结）

- `purchase:read`
- `purchase:export`
- `purchase:po_draft`
- `purchase:po_confirm`
- `purchase:po_cancel`
- `purchase:receipt_draft`
- `purchase:invoice_draft`
- `purchase:diagnostic`

### 8.2 资源权限字段（冻结）

- `company`
- `supplier`
- `item_code`
- `warehouse`
- `purchase_order`
- `purchase_receipt`
- `purchase_invoice`
- `account`
- `cost_center`

规则：

1. 列表先动作权限，再资源过滤。
2. 详情与写动作先动作权限，再资源校验。
3. 关键资源缺失默认拒绝（fail closed）。

### 8.3 审计事件（冻结）

操作审计事件：

- create
- update
- confirm
- cancel
- export
- dry-run
- diagnostic

安全审计事件：

- ERPNext unavailable
- resource access denied
- 401/403/internal API 访问拒绝

## 9. 前端门禁要求（5.8）

1. 所有写入口默认禁止。
2. `purchase:diagnostic` 不得暴露给普通前端菜单。
3. 前端禁止直连 ERPNext `/api/resource`。
4. 前端禁止裸 `fetch/axios` 绕过 API client。
5. 前端禁止自行计算采购财务事实。
6. CSV / Excel 导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。

## 10. 生产发布前置条件（5.9）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 生产联调只读验证通过。
5. 沙箱写入验证通过。
6. Purchase Order / Receipt / Invoice 写入必须单独设计、单独审计、单独放行。
7. 生产写入必须由总调度书面批准。

## 11. 结论边界

1. 本文档仅冻结采购管理边界，不包含采购功能实现。
2. 本文档不代表采购写入能力可用。
3. 本文档不代表 ERPNext 生产联调完成。
4. 本文档不代表生产发布完成。
