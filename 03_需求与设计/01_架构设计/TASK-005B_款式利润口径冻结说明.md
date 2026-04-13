# TASK-005B 款式利润口径冻结说明

- 任务编号：TASK-005B
- 模块：款式利润报表
- 版本：V1.0
- 更新时间：2026-04-14 00:11 CST
- 作者：技术架构师
- 审计来源：审计意见书第 83 份，TASK-004C14 已通过；TASK-005B 只允许进入利润口径设计冻结
- 适用范围：TASK-005C 后续数据模型、迁移、API、计算服务、前端报表的唯一口径依据
- 禁止范围：本文档不代表允许创建模型、迁移、API 或前端实现；TASK-005C 必须另行下发任务单

## 1. 冻结结论摘要

1. 收入采用双口径：预计收入来自 ERPNext `Sales Order`，实际收入来自 ERPNext `Sales Invoice`。
2. 实际材料成本采用 ERPNext `Stock Ledger Entry`，不直接采用 `Purchase Receipt`。
3. 外发成本采用结算优先、验货兜底，扣款不得重复扣减。
4. 工票成本采用工票净数量乘以登记时工价快照。
5. V1 不纳入制造费用/管理费用分摊，费用分摊字段保留但状态为 `not_enabled`。
6. 利润快照不可变，重算必须生成新快照。
7. 生成快照必须幂等，幂等键为 `company + idempotency_key`。
8. 权限必须按 `company + item_code + sales_order` 做资源级控制。

## 2. 收入口径

| 字段 | 来源 | 用途 | 规则 |
| --- | --- | --- | --- |
| `estimated_revenue_amount` | ERPNext `Sales Order` 已提交订单行 | 生产前、未开票场景 | 只读取 `docstatus=1` 的 Sales Order |
| `actual_revenue_amount` | ERPNext `Sales Invoice` 已提交发票行 | 财务确认利润 | 只读取 `docstatus=1` 的 Sales Invoice |
| `revenue_status` | 计算状态 | 标识收入可信度 | `actual / estimated / unresolved` |

冻结规则：

1. V1 默认优先使用 `actual_revenue_amount`。
2. 若没有已提交 Sales Invoice，则使用 `estimated_revenue_amount`，并标记 `revenue_status=estimated`。
3. draft/cancelled Sales Invoice 不得计入实际收入。
4. Sales Order 和 Sales Invoice 不得重复计入收入。
5. 销售退货、折让、贷项通知暂不进入 V1，必须在快照中标记 `revenue_adjustment_status=not_supported_v1`。

## 3. 标准材料成本口径

公式：

```text
standard_material_cost = sum(bom_exploded_required_qty * standard_unit_cost)
```

字段说明：

| 字段 | 口径 |
| --- | --- |
| `bom_exploded_required_qty` | BOM 展开后含损耗用量 |
| `standard_unit_cost` | 标准单位成本 |

`standard_unit_cost` 来源优先级：

1. ERPNext Item Price 中有效采购价。
2. ERPNext Item `valuation_rate`。
3. 以上均缺失时标记 `standard_cost_unresolved`。

冻结规则：

1. 不允许标准成本缺失时静默按 0 计算。
2. 标准材料明细必须保留物料编码、BOM 用量、损耗率、展开数量、单价来源和 unresolved 状态。
3. 标准成本用于对比，不等同于实际利润成本。

## 4. 标准工序成本口径

公式：

```text
standard_operation_cost = sum(bom_operation_rate * planned_qty)
```

规则：

1. 本厂工序使用 BOM 工序计件工价。
2. 外发工序使用 BOM `subcontract_cost_per_piece`。
3. BOM 工序无工价时标记 `standard_operation_cost_unresolved`。
4. 标准工序成本进入 `standard_total_cost`，不进入 `actual_total_cost`。

## 5. 实际材料成本口径

冻结为 ERPNext `Stock Ledger Entry` 口径。

公式：

```text
actual_material_cost = sum(abs(stock_value_difference))
```

纳入范围：

1. 与目标 Sales Order / Production Plan / Work Order 关联的生产材料消耗。
2. 由 submitted Stock Entry 产生的 `Stock Ledger Entry`。
3. 与成品入库、材料发料、WIP 消耗相关的库存价值变动。

排除范围：

1. draft/cancelled 库存单据。
2. 无法关联到目标订单或工单的库存台账。
3. `Purchase Receipt` 本身不直接作为实际材料成本。

冻结规则：

1. `Purchase Receipt` 仅作为采购成本参考和异常排查来源。
2. 无法关联 SLE 时标记 `actual_material_cost_unresolved`。
3. 实际材料成本为正数展示，底层负向库存价值差异取绝对值。

## 6. 实际工票成本口径

公式：

```text
net_ticket_qty = register_qty - reversal_qty
actual_workshop_cost = sum(net_ticket_qty * wage_rate_snapshot)
```

冻结规则：

1. 只统计可归属到目标 Sales Order / Production Plan / Work Order / Job Card 的工票。
2. 工价必须使用登记时工价快照或可追溯工价版本。
3. 不允许使用当前最新工价覆盖历史工票。
4. 撤销工票必须参与净数量抵扣。
5. 无法归属的工票不进入利润快照，标记 `workshop_cost_unresolved`。

## 7. 实际外发成本与扣款口径

冻结为结算优先、验货兜底。

公式：

```text
subcontract_gross_amount = accepted_qty * subcontract_unit_price
subcontract_deduction_amount = rejected_qty * deduction_amount_per_piece
subcontract_net_amount = subcontract_gross_amount - subcontract_deduction_amount
actual_subcontract_cost = sum(settlement_locked_net_amount or provisional_inspection_net_amount)
```

冻结规则：

1. 已结算或已锁定结算的外发明细，使用结算锁定净额。
2. 未结算但已验货的外发明细，可进入预估利润，使用验货净额，并标记 `subcontract_status=provisional`。
3. 未回料或未验货的外发单不得计入实际外发成本，只作为未决风险展示。
4. 扣款金额只作为明细展示；如果已使用 `net_amount`，不得再次扣减。
5. 外发结算状态与 TASK-006 对账单仍需单独架构放行，不因本文档自动启动 TASK-006。

## 8. 费用分摊口径

V1 默认不纳入制造费用/管理费用分摊。

```text
allocated_overhead_amount = 0
allocation_status = not_enabled
```

冻结规则：

1. V1 可预留 `ly_cost_allocation_rule` 草案，但 TASK-005C 不强制实现费用分摊规则。
2. 若后续启用费用分摊，必须另行 ADR 冻结分摊基准。
3. 报表必须展示 `allocation_status=not_enabled`，避免用户误以为已含制造费用。

## 9. 利润公式

```text
revenue_amount = actual_revenue_amount if revenue_status=actual else estimated_revenue_amount
actual_total_cost = actual_material_cost + actual_workshop_cost + actual_subcontract_cost + allocated_overhead_amount
standard_total_cost = standard_material_cost + standard_operation_cost
profit_amount = revenue_amount - actual_total_cost
profit_rate = profit_amount / revenue_amount
```

边界：

1. `revenue_amount = 0` 时，`profit_rate = null`。
2. 任一 P1 成本项 unresolved 时，快照允许生成但必须标记 `snapshot_status=incomplete`。
3. 金额统一 Decimal，计算过程保留 6 位小数，展示四舍五入到 2 位。
4. 负利润允许展示，不得截断为 0。

## 10. 快照不可变与重算规则

1. 利润快照创建后不可修改。
2. 重算必须生成新 `snapshot_no`。
3. 快照明细必须保存公式版本、数据来源、来源单据号、金额和 unresolved 状态。
4. 快照生成必须写操作审计。
5. 快照删除 V1 不开放。
6. 快照状态：`complete / incomplete / failed`。

## 11. 幂等规则

`POST /api/reports/style-profit/snapshot` 必须要求 `idempotency_key`。

唯一键：

```text
company + idempotency_key
```

`request_hash` 必须包含：

1. company
2. item_code
3. sales_order
4. from_date
5. to_date
6. revenue_mode
7. include_provisional_subcontract
8. formula_version

规则：

1. 同 key + 同 hash：返回首次快照。
2. 同 key + 不同 hash：返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
3. `created_at / operator / request_id / snapshot_no` 不得进入 request_hash。

## 12. 权限与审计规则

权限动作：

| 动作 | 用途 |
| --- | --- |
| `style_profit:read` | 查询列表、详情、对比 |
| `style_profit:snapshot_create` | 创建利润快照 |
| `style_profit:export` | 导出利润报表 |

资源权限：

1. company
2. item_code
3. sales_order

规则：

1. 权限来源沿用 ERPNext Role / User Permission 聚合。
2. 权限源不可用必须 fail closed，返回 `PERMISSION_SOURCE_UNAVAILABLE`。
3. 401、403、503 必须写安全审计。
4. 快照生成、幂等 replay、幂等冲突、unresolved 快照必须写操作审计。
5. 日志不得写 Authorization、Cookie、token、password、secret 或原始 SQL 明文。

## 13. unresolved 状态清单

| 状态 | 含义 | 是否允许生成快照 |
| --- | --- | --- |
| `standard_cost_unresolved` | 标准材料价格缺失 | 允许，snapshot_status=incomplete |
| `standard_operation_cost_unresolved` | BOM 工序工价缺失 | 允许，snapshot_status=incomplete |
| `actual_material_cost_unresolved` | SLE 无法关联订单/工单 | 允许，snapshot_status=incomplete |
| `workshop_cost_unresolved` | 工票无法归属 | 允许，snapshot_status=incomplete |
| `subcontract_cost_unresolved` | 外发未回料/未验货 | 允许，snapshot_status=incomplete |
| `revenue_unresolved` | SO/SI 均无法确认收入 | 不允许生成 complete 快照 |

## 14. TASK-005C 输入清单

TASK-005C 若后续获批，只能基于本文档进入数据模型与迁移设计。输入包括：

1. `ly_style_profit_snapshot` 字段和索引设计。
2. `ly_style_profit_detail` 字段和索引设计。
3. `ly_cost_allocation_rule` 是否 V1 仅预留。
4. 幂等表或幂等字段设计。
5. unresolved 状态字段设计。
6. 权限动作和资源字段设计。
7. 操作审计事件设计。
8. 错误码清单。

## 15. 禁止实现范围

1. 本文档不允许创建数据库表。
2. 本文档不允许创建迁移。
3. 本文档不允许注册 API 路由。
4. 本文档不允许创建前端页面。
5. 本文档不允许进入 TASK-006。

## 16. 验收标准

1. 收入口径已明确区分预计收入和实际收入。
2. 实际材料成本已冻结为 Stock Ledger Entry 口径。
3. 外发成本已明确结算优先、验货兜底，扣款不重复扣减。
4. 费用分摊 V1 明确默认不纳入正式利润。
5. 快照不可变和重算新快照已冻结。
6. 幂等键和 request_hash 字段已冻结。
7. 权限动作、资源权限、安全审计和操作审计已冻结。
8. TASK-005C 输入清单已明确。
9. 未进入后端、前端、迁移或 TASK-006 实现。
