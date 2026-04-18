# TASK-022A 成本核算边界设计

- 任务编号：TASK-022A
- 任务名称：成本核算边界设计冻结
- 角色：架构师
- 优先级：P1
- 文档状态：待审计
- 更新日期：2026-04-17
- 前置依赖：TASK-021A 审计通过（审计意见书第 212 份）
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结成本核算模块边界，明确成本中心、成本分摊、标准成本、实际成本、财务联动、ERPNext 集成策略、Adapter/Outbox 策略、权限审计要求与禁止事项。

本任务只做设计冻结，不做代码实现，不做真实联调，不做生产发布。

```text
禁止写业务代码。
禁止连接生产 ERPNext。
禁止直接写 ERPNext 财务接口。
禁止直接写 GL Entry / Payment Entry。
禁止绕过 TASK-008 Fail-Closed Adapter。
禁止绕过 TASK-009 Outbox 公共状态机。
TASK-014C 仍冻结，不得解冻。
不得声明 required checks / Hosted Runner / Branch Protection 闭环。
不得声明生产发布完成。
```

## 2. 成本中心边界

### 2.1 资源维度冻结

成本核算的最小资源维度冻结为：

- `company`
- `cost_center`
- `department` / `workshop`
- `production_line`
- `work_order`
- `item_code`
- `supplier`
- `customer`

### 2.2 语义与隔离规则

1. `company` 是一级隔离键，缺失即 fail closed。
2. `cost_center` 是财务归集维度，必须与 `company` 一致，越权拒绝。
3. `department/workshop/production_line` 是生产分摊维度，不得替代财务事实维度。
4. `work_order/item_code` 用于生产归属，无法归属时不得进入可记账事实。
5. `supplier/customer` 仅用于外发和应收应付关联，不得跨主体混算。

## 3. 成本分摊边界

### 3.1 分摊对象与规则

| 分摊类别 | 推荐分摊基准 | 当前阶段结论 |
|---|---|---|
| 人工成本分摊 | 工票净工时 / 净工票数量 / 标准工时权重 | 仅冻结口径，不实现自动分摊写入 |
| 材料成本分摊 | BOM 展开用量权重 + 实际领退料净额 | 仅冻结口径，不实现写入 |
| 外发成本分摊 | 外发结算净额优先、验货 provisional 兜底 | 仅冻结口径，不实现写入 |
| 制造费用分摊 | 成本中心+期间维度，按工时/产量/工单权重 | 仅冻结口径，不纳入财务写入 |
| 质量损耗分摊 | 检验不合格数量或损耗金额归集到工单/款式 | 仅冻结口径，需显式标记损耗来源 |
| 期间费用纳入 | 默认不纳入 V1 成本主公式 | 后续单独 ADR 放行 |

### 3.2 分摊硬约束

1. 分摊规则必须版本化，禁止运行时隐式切换。
2. 分摊失败不得返回“成功+空数据”。
3. 不得以前端重算结果回写财务事实。
4. provisional（未结算）与 settled（已结算）必须可区分、可审计。

## 4. 标准成本边界

### 4.1 标准成本组成

1. BOM 标准材料成本：`sum(standard_required_qty * standard_unit_cost)`。
2. 标准损耗：依据 BOM 损耗率，纳入标准材料成本。
3. 标准工序成本：`sum(operation_standard_rate * planned_qty)`。
4. 标准外发加工成本：使用 BOM 外发单件标准成本。

### 4.2 ERPNext 参考价使用边界

| 数据源 | 角色 | 边界 |
|---|---|---|
| `Item Price` | 标准成本参考价 | 可用于标准价参考，不直接作为实际成本 |
| `valuation_rate` | 库存估值参考 | 可用于分析，不直接替代 SLE 实际成本事实 |

### 4.3 标准成本 fail-closed 规则

1. BOM 缺失 / BOM 映射缺失 -> fail closed。
2. 标准工序缺失 -> fail closed。
3. 参考价响应 malformed / timeout / 401 / 403 / 5xx -> fail closed。

## 5. 实际成本边界

### 5.1 实际成本来源冻结

| 成本来源 | 事实口径 | 边界 |
|---|---|---|
| Stock Ledger Entry | `sum(abs(stock_value_difference))`（按归属筛选） | 实际材料成本主来源 |
| 工票 / 日薪 / 工价 | `net_ticket_qty * wage_rate_snapshot` | 实际人工成本来源 |
| 外发加工扣款 | 结算净额优先，验货 provisional 兜底 | 扣款不得重复扣减 |
| 质量检验损耗 | 质量模块损耗事实（需来源标识） | 不得无归属入账 |
| 采购入库成本 | `Purchase Receipt` 仅参考与排查 | 不直接计入实际材料成本主口径 |

### 5.2 实际成本归属约束

1. 必须归属到 `company + item_code + (sales_order/work_order/production_plan)` 之一。
2. 无法归属必须标记 unresolved，不得静默计入。
3. 取消/冲销/非法状态单据不得计入。
4. 前端禁止把展示层计算结果当作财务事实提交。

## 6. 与财务模块联动边界（TASK-016A）

1. 成本模块可以读取 `Account`、`Cost Center` 财务维度，不得写财务主数据。
2. `GL Entry` 当前仅允许只读查询，禁止创建/改写。
3. `Payment/AP/AR` 仅允许只读关联分析，禁止直接驱动财务写入。
4. 财务事实（总账、收付款、应收应付）不得由成本模块直接写入。
5. 成本核算结果可作为“候选分录/候选调整”输出，但必须经后续独立任务与审计放行。

### 6.1 与 TASK-005 款式利润边界

1. `TASK-005` 负责利润结果与快照（利润指标、快照结果、展示与导出口径）。
2. `TASK-022A` 负责成本事实治理（成本中心、分摊规则、标准/实际成本边界与归属约束）。
3. `TASK-022A` 不重复定义利润快照主公式，不重建 `TASK-005` 已冻结的利润结果职责。
4. 两者通过统一成本事实、`source_map` 与成本来源语义衔接，确保来源可追溯、口径一致、审计可复核。

## 7. ERPNext 集成策略

### 7.1 能力矩阵

| 成本能力 | ERPNext DocType | 只读/写入 | Adapter | Outbox | 当前是否允许生产 |
|---|---|---|---|---|---|
| 成本科目读取 | Account | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 成本中心读取 | Cost Center | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 实际材料成本读取 | Stock Ledger Entry | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 采购成本参考 | Purchase Receipt / Purchase Invoice | 只读参考 | 必须 TASK-008 | 不适用 | 是（只读） |
| 外发结算参考 | Purchase Invoice / Supplier | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 成本调整候选写入 | Journal Entry / GL Entry（候选） | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否（冻结） |
| 付款联动候选 | Payment Entry（候选） | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否（冻结） |

### 7.2 fail-closed 条件

必须统一遵守：

- timeout -> fail closed
- 401/403 -> fail closed
- 404 -> not found（不得伪成功）
- 5xx -> fail closed
- malformed response -> fail closed
- docstatus 缺失/非法（适用对象） -> fail closed
- 禁止 `200 + 空数据` 伪成功

## 8. Adapter / Outbox 策略

### 8.1 Adapter 策略（TASK-008）

1. 所有 ERPNext 访问统一经 Adapter，禁止业务层裸请求。
2. Adapter 仅返回标准化结果或结构化异常。
3. 禁止 `detail=str(exc)` 向客户端泄露内部异常。

### 8.2 Outbox 策略（TASK-009）

1. 成本相关写入候选必须走 Outbox，禁止同步直写。
2. `idempotency_key` 与 `event_key` 职责分离。
3. `event_key` 禁止运行态字段（`attempts/status/locked_by/request_id/operator` 等）。
4. claim/lease/retry/dead 必须遵守公共状态机语义。
5. worker 外调前必须重校验资源权限与业务归属。

## 9. 权限与审计要求

### 9.1 动作权限冻结

- `cost:read`
- `cost:export`
- `cost:calculate`
- `cost:adjustment_draft`
- `cost:dry_run`
- `cost:diagnostic`
- `cost:worker`

### 9.2 资源权限字段

- `company`
- `cost_center`
- `department`
- `workshop`
- `production_line`
- `item_code`
- `work_order`
- `supplier`
- `customer`
- `account`

说明：`department / workshop / production_line` 既是统计与分摊维度，也是资源权限上下文字段；缺失或越权必须 fail closed。

### 9.3 安全审计事件

- 401 未认证
- 403 禁止
- 资源越权
- 权限源不可用
- ERPNext 不可用
- internal API 非授权访问
- request_id rejected

### 9.4 操作审计事件

- read
- export
- calculate
- adjustment_draft
- dry-run
- diagnostic

### 9.5 脱敏要求

审计和错误日志不得记录：

- Authorization
- Cookie
- Token
- Secret
- password
- 明文 DSN

## 10. 前端门禁要求

1. 禁止 ERPNext 直连（含 `/api/resource`）。
2. 禁止裸 `fetch/axios` 绕过统一 API client。
3. 普通前端不得暴露 `cost:diagnostic`。
4. 普通前端不得暴露 `cost:worker`。
5. 导出必须具备 CSV/Excel 公式注入防护。
6. 必须接入 TASK-010 前端写入口门禁公共框架。
7. 只读展示不得演变为财务写入事实。

## 11. 禁止事项清单

1. 禁止写业务代码。
2. 禁止连接生产 ERPNext。
3. 禁止直接写 ERPNext 财务接口。
4. 禁止直接写 GL Entry / Payment Entry。
5. 禁止绕过 TASK-008。
6. 禁止绕过 TASK-009。
7. 禁止解冻 TASK-014C。
8. 禁止声明 required checks 闭环。
9. 禁止声明 Hosted Runner 闭环。
10. 禁止声明 Branch Protection 闭环。
11. 禁止声明生产发布完成。

## 12. 生产发布前置条件（冻结）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环（由管理员证据包证明）。
3. Branch Protection 已配置（由管理员证据包证明）。
4. 成本核算实现任务完成并审计通过。
5. 财务写入能力单独任务、单独审计、单独放行。

## 13. 结论边界

1. 本文档仅冻结成本核算边界，不代表功能实现完成。
2. 本文档不代表 ERPNext 联调完成。
3. 本文档不代表 TASK-014C 解冻。
4. 本文档不代表生产发布完成。
