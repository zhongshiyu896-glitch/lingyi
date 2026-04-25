# TASK-017A 采购管理边界设计

- 任务编号：TASK-017A
- 任务名称：采购管理边界设计冻结
- 文档状态：待审计
- 更新日期：2026-04-23
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

## 3. Purchase Request 边界（5.1A）

1. Purchase Request（PR）在采购主链中仅负责“采购需求事实”的受控表达与审批前置，不承担下游 ERPNext 写入执行。
2. PR 与 PO 的职责分离：
   - PR 负责需求来源、需求数量、需求日期、需求归属（company/cost_center）；
   - PO 负责对外采购承诺与供应商执行事实；
   - 未经审批通过的 PR 不得进入 PO 候选写链。
3. PR 当前冻结为设计层能力，不放行实现；普通前端不得出现未审计 PR 写入口。
4. PR 生产写入当前冻结；若后续放行，仍必须走 `TASK-008` fail-closed adapter + `TASK-009` outbox。
5. PR 与 Supplier/Item/Warehouse/Cost Center 的关系仅冻结为资源依赖约束，不放行任何主数据写入：
   - Supplier 提供采购主体候选；
   - Item/Warehouse/Account/Cost Center 提供只读约束与归属校验；
   - 未命中资源权限时默认 fail closed。

## 4. Purchase Order 边界（5.2）

### 4.1 创建范围

1. 本阶段仅冻结 PO 创建规则，不执行实现。
2. PO 创建仅允许在受控后端服务入口定义，不允许前端直写 ERPNext。
3. PO 创建必须携带 company/supplier/item_code/warehouse 等关键资源上下文。

### 4.2 审批流程

1. PO 采用“草稿 -> 审批确认”双阶段。
2. 审批动作必须与创建动作分离，禁止同角色默认全流程直通。
3. 审批拒绝必须写安全审计/操作审计记录。

### 4.3 修改/取消范围

1. draft 状态允许受控修改。
2. confirmed/succeeded 后默认不允许业务字段直接修改。
3. 取消动作需权限校验与审计落库。

### 4.4 谁可以创建、审批、取消

1. 创建：`purchase:po_draft`。
2. 审批确认：`purchase:po_confirm`。
3. 取消：`purchase:po_cancel`。
4. 普通只读角色不得触发创建/审批/取消。

### 4.5 与 ERPNext 的集成方式

1. 只读查询走 Adapter（TASK-008）。
2. 写入草稿走 Outbox（TASK-009）。
3. 生产写入继续冻结。

### 4.6 幂等策略

1. `idempotency_key`：请求级重放/冲突判定。
2. `event_key`：业务事实级去重。
3. replay/conflict：同 key 同 hash replay，同 key 异 hash conflict；不同 key 同事实命中 event_key 防重。

### 4.7 状态机（冻结）

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

### 4.8 操作审计要求

1. create/update/confirm/cancel/retry/dead 均需操作审计。
2. 权限拒绝、资源越权、ERPNext 不可用必须安全审计。
3. 审计脱敏：禁止记录 token/secret/password/DSN。

## 5. Purchase Receipt 边界（5.3）

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

## 6. Purchase Invoice 边界（5.4）

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

## 7. Supplier 主数据边界（5.5）

1. Supplier 默认只读集成。
2. Supplier 创建/修改不纳入本阶段。
3. Supplier 资源权限：必须校验 `company + supplier`，并结合动作权限。
4. fail-closed 规则：Supplier 不存在/disabled/permission denied 时必须阻断。
5. 敏感字段脱敏：供应商名称、税号、银行账号等在日志与审计输出中按最小暴露规则脱敏。
6. 禁止前端直接维护 ERPNext Supplier 主数据。

## 8. ERPNext 集成策略（5.6）

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

## 9. 权限与审计要求（5.7）

### 9.1 动作权限（冻结）

- `purchase:read`
- `purchase:export`
- `purchase:request_read`
- `purchase:request_draft`
- `purchase:request_submit`
- `purchase:po_draft`
- `purchase:po_confirm`
- `purchase:po_cancel`
- `purchase:receipt_draft`
- `purchase:invoice_draft`
- `purchase:diagnostic`

### 9.2 资源权限字段（冻结）

- `company`
- `supplier`
- `item_code`
- `warehouse`
- `purchase_request`
- `purchase_order`
- `purchase_receipt`
- `purchase_invoice`
- `account`
- `cost_center`

规则：

1. 列表先动作权限，再资源过滤。
2. 详情与写动作先动作权限，再资源校验。
3. 关键资源缺失默认拒绝（fail closed）。

### 9.3 审计事件（冻结）

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

## 10. 前端门禁要求（5.8）

1. 所有写入口默认禁止。
2. `purchase:diagnostic` 不得暴露给普通前端菜单。
3. 前端禁止直连 ERPNext `/api/resource`。
4. 前端禁止裸 `fetch/axios` 绕过 API client。
5. 前端禁止自行计算采购财务事实。
6. CSV / Excel 导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。

## 11. 生产发布前置条件（5.9）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 生产联调只读验证通过。
5. 沙箱写入验证通过。
6. Purchase Order / Receipt / Invoice 写入必须单独设计、单独审计、单独放行。
7. 生产写入必须由总调度书面批准。

## 12. 结论边界

1. 本文档仅冻结采购管理边界，不包含采购功能实现。
2. 本文档不代表采购写入能力可用。
3. 本文档不代表 ERPNext 生产联调完成。
4. 本文档不代表生产发布完成。
5. `TASK-017A` 通过后，仅允许进入 `TASK-017B` 设计。
6. 不允许直接进入任何采购实现任务。
7. 不允许直接进入联调、提测、上线或生产写入。

## 13. 三层能力冻结统一矩阵（新增）

统一口径说明：

1. 只读能力：允许查询与展示，不允许触发写入动作。
2. 候选写能力：仅冻结设计边界与门禁合同，不等于允许实现。
3. 生产写能力：仅在后续“单独任务 + 单独审计 + 单独放行”后才可能开放，当前全部冻结。

| 对象/动作 | 只读能力 | 候选写能力 | 生产写能力 | 当前冻结结论 |
|---|---|---|---|---|
| Supplier | 允许（主数据只读引用） | 不开放 | 冻结 | 维持只读依赖，不允许主数据写入 |
| Purchase Request | 允许（需求查询/详情） | 可冻结 `request_draft/request_submit` 设计入口 | 冻结 | 仅设计，不允许实现 |
| Purchase Order draft/create | 允许读取候选结果 | 可冻结草稿创建入口与资源校验 | 冻结 | 不允许进入实现 |
| Purchase Order confirm/cancel | 允许读取状态 | 可冻结动作拆分、权限与审计合同 | 冻结 | 不允许进入实现 |
| Purchase Receipt | 允许（入库事实只读） | 可冻结入库候选写门禁与校验项 | 冻结 | 不允许进入实现 |
| Purchase Invoice（采购侧） | 允许（只读引用财务事实） | 仅可冻结“采购侧引用边界”，不得扩写财务动作 | 冻结 | 禁止偷渡财务写入 |
| Item / Warehouse / Account / Cost Center | 允许（资源依赖只读） | 不开放 | 冻结 | 仅作为资源约束字段，不放行写入 |

## 14. 下一步门禁（新增）

1. Sprint 3 当前采购主链只冻结到设计层：PR/PO/Receipt/Supplier/PI 关系边界、权限动作、资源字段、DocType 映射、Adapter/Outbox/fail-closed 约束、审计要求与前端门禁。
2. 本轮未产出实现级证据（无代码、无测试、无联调），因此不能直接进入采购实现任务。
3. 采购写链未来若要落地，必须同时满足：
   - 先走 `TASK-008` fail-closed adapter；
   - 再走 `TASK-009` outbox；
   - 具备动作权限 + 资源字段校验 + 审计闭环；
   - 通过后续单独任务与单独审计。
4. 前端当前绝对禁止：
   - 直连 ERPNext `/api/resource`；
   - 暴露未审计采购写入口；
   - 绕过 API client、权限 guard 与 fail-closed 门禁。
5. `TASK-017A` 通过后，下一个且唯一允许进入的任务是 `TASK-017B` 设计；在 `TASK-017B` 通过前，不允许直接进入任何采购实现。
