# TASK-016A 财务管理边界设计

- 任务编号：TASK-016A
- 任务名称：财务管理边界设计冻结
- 文档状态：待审计
- 更新日期：2026-04-23
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结 Payment Entry、GL、AR、AP 的系统责任边界、ERPNext 集成策略、权限审计策略、Outbox 策略与前端门禁策略，作为后续财务相关任务的唯一前置设计。

本任务只做设计冻结，不做代码实现，不做环境联调。

## 2. 财务模块总边界（5.1）

本任务仅冻结财务管理设计边界。
禁止实现 Payment Entry / GL Entry / AR / AP 代码。
禁止连接生产 ERPNext。
禁止直接写 ERPNext 财务接口。
禁止绕过 TASK-008 Fail-Closed Adapter。
禁止绕过 TASK-009 Outbox 状态机。
TASK-014C 未完成前，不允许进入任何真实平台联调或生产发布。

补充约束：

1. 本文档结论不代表财务功能可上线。
2. 本文档结论不代表 Hosted Runner / required checks / branch protection 已闭环。
3. 财务写入能力必须后续单独任务、单独审计、单独放行。

## 3. Payment Entry 边界（5.2）

### 3.1 发起与审批职责

1. 发起人：仅财务执行角色（如 `finance_operator`）可发起 Payment Entry 草稿。
2. 审批人：仅财务审批角色（如 `finance_approver`）可执行确认类动作。
3. 普通业务角色、只读角色、前端诊断角色不得发起或审批 Payment Entry。

### 3.2 生产写入边界

1. Payment Entry 生产写入默认冻结（当前阶段不允许）。
2. 即使沙箱验证通过，也不得外推到生产写入。

### 3.3 草稿/提交/取消边界

1. 草稿（draft）：允许在后续沙箱任务验证创建路径。
2. 提交（submit）：本阶段冻结，禁止执行。
3. 取消（cancel）：本阶段冻结，禁止执行。
4. 若后续开放提交/取消，必须附带独立审计任务与回归测试矩阵。

### 3.4 与 ERPNext 集成方式

1. 只读查询：必须走 TASK-008 Adapter。
2. 写入建议：必须走 TASK-009 Outbox（禁止同步直写）。
3. 生产写入：继续冻结，未放行前禁止执行。

### 3.5 幂等策略

1. `idempotency_key`：用于同请求重放检测（replay/conflict）。
2. `event_key`：用于同业务事实去重，禁止包含运行态字段。
3. 冲突策略：同 key 异 hash 必须 conflict / fail closed，不得静默覆盖。

### 3.6 状态机冻结

Payment Entry 写链路设计状态机（仅冻结，不执行）：

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

约束：

1. `succeeded`、`dead`、`cancelled` 为终态。
2. `processing` 必须绑定 lease 与重试规则。
3. 任何状态转移都要写操作审计。

### 3.7 操作审计要求

1. 草稿创建、确认、取消、重试、dead 处理均必须写操作审计。
2. 权限拒绝、资源越权、外部不可用必须写安全审计。
3. 审计日志必须脱敏，禁止出现 token/password/secret/DSN。

## 4. GL 总账边界（5.3）

1. Sprint 3 默认 GL Entry 只读。
2. 禁止直接创建 GL Entry。
3. GL 查询来源：ERPNext 只读查询，经 TASK-008 Adapter 归一。
4. GL 查询权限：必须校验 `finance:read` 与资源范围（company/account/cost_center）。
5. GL 与 Payment Entry / Purchase Invoice / Sales Invoice 的关系：
   - GL 作为会计事实只读结果；
   - Payment/Purchase/Sales 作为来源单据，不得反向由前端计算替代 GL 事实。
6. GL 数据不得由前端重算为财务事实。
7. GL 查询 fail-closed 条件：401/403/timeout/5xx/malformed/docstatus 异常（如适用）必须阻断并返回标准错误信封。

## 5. AR 应收边界（5.4）

1. 客户对账单范围：客户维度应收余额、账龄、单据明细（只读）。
2. Sales Invoice 读取范围：仅读取，禁止写入/提交/取消。
3. Payment Entry 与应收核销关系：仅做只读关联展示，不在本任务实现核销写入。
4. 应收账龄分析口径：以 ERPNext 会计事实与单据状态为准，不使用前端自算替代。
5. 客户资源权限：必须按 `company + customer` 过滤，越权 fail closed。
6. ERPNext 读取 fail-closed：401/403/404/timeout/5xx/malformed 均按标准阻断语义处理。
7. 禁止本地伪造应收余额。

## 6. AP 应付边界（5.5）

1. 供应商对账单范围：供应商维度应付余额、账龄、单据明细（只读）。
2. Purchase Invoice 读取范围：仅查询草稿/已提交状态信息，不在本任务做写入。
3. TASK-006 加工厂对账单与 AP 的关系：
   - TASK-006 是业务对账来源之一；
   - AP 为财务事实视图；
   - 两者关系通过受控映射与审计链路衔接，不可混写。
4. Payment Entry 与应付核销关系：仅定义只读关联，不实现写入核销。
5. 应付账龄分析口径：以 ERPNext 财务事实为准。
6. Supplier 资源权限：必须按 `company + supplier` 过滤，越权 fail closed。
7. ERPNext 读取 fail-closed：权限失败、超时、响应非法、外部不可用时统一阻断。
8. 禁止重复生成应付草稿（后续写链路需 `idempotency_key + event_key` 双重防重）。

## 7. ERPNext 集成策略（5.6）

| 财务能力 | ERPNext DocType | 只读/写入 | Adapter | Outbox | 是否允许生产 |
|---|---|---|---|---|---|
| 收款/付款单 | Payment Entry | 生产只读；写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 总账分录 | GL Entry | 只读 | 必须（TASK-008） | 不适用（当前只读） | 否（写入冻结） |
| 销售发票 | Sales Invoice | 只读 | 必须（TASK-008） | 写入链路暂不开放 | 否（写入冻结） |
| 采购发票 | Purchase Invoice | 只读；草稿写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 科目 | Account | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 成本中心 | Cost Center | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 客户 | Customer | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 供应商 | Supplier | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 日记账 | Journal Entry | 只读（当前阶段） | 必须（TASK-008） | 若未来写入必须接入（TASK-009） | 否（当前冻结） |

集成总原则：

1. 所有 ERPNext 访问统一经 Adapter，不允许业务层裸请求。
2. 所有写链路统一经 Outbox，不允许同步直写。
3. 未明确放行的能力默认 fail closed。

## 8. 权限与审计要求（5.7）

### 8.1 动作权限命名（冻结）

- `finance:read`
- `finance:export`
- `finance:payment_draft`
- `finance:payment_confirm`
- `finance:diagnostic`

### 8.2 资源权限字段（冻结）

- `company`
- `customer`
- `supplier`
- `account`
- `cost_center`
- `sales_order`
- `purchase_invoice`

规则：

1. 列表接口必须先动作权限，再资源过滤。
2. 详情接口必须先动作权限，再资源校验。
3. 缺关键资源字段默认拒绝（fail closed）。

### 8.3 安全审计事件（冻结）

- 401
- 403
- 资源越权
- ERPNext 不可用
- internal API 访问

### 8.4 操作审计事件（冻结）

- create
- confirm
- cancel
- export
- dry-run
- diagnostic

### 8.5 财务安全硬约束（冻结）

1. 禁止 secret 入库（包括 API Key/Secret、账号口令、DSN）。
2. 禁止 `detail=str(exc)` 直接回传到客户端。
3. 禁止 `200 + 空数据` 伪成功。
4. 禁止跳过权限校验。
5. 禁止跳过审计日志。

## 9. 前端写入口门禁要求（5.8）

1. 财务模块所有写入口默认禁止。
2. `finance:diagnostic` 不得暴露给普通前端菜单。
3. 前端禁止直连 ERPNext `/api/resource`。
4. 前端禁止裸 `fetch/axios` 绕过 API client。
5. 前端金额展示不得重算为财务事实。
6. CSV / Excel 导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。

## 10. 生产发布前置条件（5.9）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 生产联调只读验证通过。
5. 沙箱写入验证通过。
6. 财务写入功能必须单独设计、单独审计、单独放行。
7. 生产写入必须由总调度书面批准。

## 11. 三层能力冻结统一矩阵

统一口径定义（本章为唯一口径）：

1. 只读能力：允许查询/展示/导出，不允许写入。
2. 候选写能力：仅允许后续任务继续做设计与沙箱论证，不等于允许实现。
3. 生产写能力：仅在后续“单独任务 + 单独审计 + 单独放行”后才可能开放；当前全部未放行。

| 对象 | 只读能力 | 候选写能力 | 生产写能力 | 当前冻结结论 |
|---|---|---|---|---|
| Payment Entry | 允许（经 TASK-008 Adapter） | 仅草稿路径可进入后续设计/沙箱论证 | 未放行 | 当前冻结 |
| GL Entry | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Sales Invoice | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Purchase Invoice | 允许（经 TASK-008 Adapter） | 仅草稿写入可进入后续设计/沙箱论证 | 未放行 | 当前冻结 |
| Account | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Cost Center | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Customer | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Supplier | 允许（经 TASK-008 Adapter） | 不开放 | 未放行 | 当前冻结 |
| Journal Entry | 允许（经 TASK-008 Adapter） | 不开放（如未来开放，必须先定义 TASK-009 Outbox 写链） | 未放行 | 当前冻结 |

补充约束：

1. “候选写能力”只代表后续可继续设计，不代表当前允许代码实现。
2. 未进入单独放行任务前，任何写能力均不得进入联调、提测、上线或生产写入。
3. 所有写链路仍必须遵循 TASK-008 fail-closed adapter + TASK-009 outbox。

## 12. 结论边界

1. 本文档仅冻结财务管理边界，不包含财务功能实现。
2. 本文档不代表平台闭环完成。
3. 本文档不代表生产 ERPNext 联调完成。
4. 本文档不代表生产发布完成。
5. `TASK-016A` 通过后，仅允许继续 `TASK-016B` 设计。
6. 不允许直接进入任何实现任务。
7. 不允许直接进入联调、提测、上线、生产写入。
