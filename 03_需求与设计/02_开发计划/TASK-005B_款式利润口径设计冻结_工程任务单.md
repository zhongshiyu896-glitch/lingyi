# TASK-005B 款式利润口径设计冻结工程任务单

- 任务编号：TASK-005B
- 模块：款式利润报表 / 利润口径设计冻结
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 00:11 CST
- 作者：技术架构师
- 审计来源：审计意见书第 83 份，TASK-004C14 通过；TASK-005B 可从“等待 GitHub URL”阻塞中释放，但只能进入利润口径设计冻结，不得直接进入模型、迁移、API 或前端实现
- 前置依赖：TASK-005A/A1/A2 文档问题已闭环；TASK-004C14 本地仓库门禁已通过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.3；`ADR-079`
- 任务边界：只输出利润口径冻结设计文档和 ADR 证据；不写后端代码，不写前端代码，不建迁移，不注册接口，不进入 TASK-005C/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005B
模块：款式利润口径设计冻结
优先级：P0（实现前口径冻结）
════════════════════════════════════════════════════════════════════════════

【任务目标】
冻结款式利润报表 V1 的收入、标准材料、实际材料、工票、外发、扣款、费用分摊、快照、幂等、权限和审计口径，形成后续 TASK-005C 数据模型与迁移的唯一依据。

【当前允许范围】
1. 允许读取 TASK-005A 基线盘点报告。
2. 允许读取 BOM、外发、工票、生产计划模块设计与现有代码。
3. 允许输出利润口径冻结文档。
4. 允许更新模块设计、ADR、Sprint 状态和日志。
5. 禁止创建或修改后端 `style_profit` 代码。
6. 禁止创建或修改前端 `style_profit` 代码。
7. 禁止新增 Alembic 迁移。
8. 禁止注册 `/api/reports/style-profit/` 路由。
9. 禁止进入 TASK-005C/TASK-006。

【必须输出】

新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-005B_款式利润口径冻结说明.md

可修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【必须冻结的利润口径】

## 1. 收入口径

冻结为双口径：

1. `estimated_revenue_amount`：来自 ERPNext `Sales Order` 已提交订单行，用于生产前/未开票场景。
2. `actual_revenue_amount`：来自 ERPNext `Sales Invoice` 已提交发票行，用于财务确认利润。
3. V1 报表默认展示 `actual_revenue_amount`；若无已提交 Sales Invoice，则展示 `estimated_revenue_amount`，并标记 `revenue_status=estimated`。
4. 不允许把 draft/cancelled Sales Invoice 计入实际收入。
5. 不允许同时把 Sales Order 和 Sales Invoice 重复计入收入。

## 2. 标准材料成本口径

冻结公式：

```text
standard_material_cost = sum(bom_exploded_required_qty * standard_unit_cost)
```

来源优先级：
1. ERPNext Item Price 中有效采购价格。
2. 若无 Item Price，使用 ERPNext Item valuation_rate。
3. 两者都缺失时，该物料标记为 `standard_cost_unresolved`，不得静默按 0 计算。

## 3. 标准工序成本口径

冻结公式：

```text
standard_operation_cost = sum(bom_operation_rate * planned_qty)
```

规则：
1. 本厂工序使用 BOM 工序计件工价。
2. 外发工序标准成本使用 BOM 中 `subcontract_cost_per_piece`。
3. BOM 工序无工价时标记 `standard_operation_cost_unresolved`。

## 4. 实际材料成本口径

冻结为 ERPNext `Stock Ledger Entry` 口径：

```text
actual_material_cost = sum(abs(stock_value_difference))
```

范围：
1. 只统计与生产计划 / Work Order / Stock Entry 关联的材料消耗类库存台账。
2. 只统计 submitted 单据产生的 SLE。
3. 不直接用 Purchase Receipt 作为实际材料成本；Purchase Receipt 仅作为采购成本参考和异常排查来源。
4. 无法关联到生产计划或 Work Order 时，标记 `actual_material_cost_unresolved`。

## 5. 实际工票成本口径

冻结公式：

```text
actual_workshop_cost = sum(net_ticket_qty * wage_rate_snapshot)
net_ticket_qty = register_qty - reversal_qty
```

规则：
1. 只统计与目标 Sales Order / Production Plan / Work Order / Job Card 关联的工票。
2. 工价必须使用工票登记时的工价快照或可追溯工价版本，不得使用当前最新工价覆盖历史。
3. 撤销工票必须参与净数量抵扣。
4. 无法归属到订单/款式/工单的工票不得进入利润快照，标记为 `workshop_cost_unresolved`。

## 6. 实际外发成本与扣款口径

冻结为结算优先、验货兜底的双状态口径：

1. 已结算或已锁定结算的外发明细，使用结算锁定净额。
2. 未结算但已验货的外发明细，可进入预估利润，使用验货净额，并标记 `subcontract_status=provisional`。
3. 未回料/未验货的外发单不得计入实际外发成本，只能作为未决风险项展示。
4. 扣款金额只作为明细展示，不得在已使用 `net_amount` 的情况下重复扣减。

公式：

```text
subcontract_gross_amount = accepted_qty * subcontract_unit_price
subcontract_deduction_amount = rejected_qty * deduction_amount_per_piece
subcontract_net_amount = subcontract_gross_amount - subcontract_deduction_amount
actual_subcontract_cost = sum(settlement_locked_net_amount or provisional_inspection_net_amount)
```

## 7. 费用分摊口径

V1 冻结为默认不纳入正式利润：

```text
allocated_overhead_amount = 0
```

规则：
1. V1 预留 `ly_cost_allocation_rule` 设计，但 TASK-005C 不强制实现费用分摊规则。
2. 若后续启用费用分摊，必须单独 ADR 冻结分摊基准。
3. 报表必须显示 `allocation_status=not_enabled`，避免用户误以为已含制造费用。

## 8. 利润公式

冻结公式：

```text
revenue_amount = actual_revenue_amount if revenue_status=actual else estimated_revenue_amount
actual_total_cost = actual_material_cost + actual_workshop_cost + actual_subcontract_cost + allocated_overhead_amount
standard_total_cost = standard_material_cost + standard_operation_cost
profit_amount = revenue_amount - actual_total_cost
profit_rate = profit_amount / revenue_amount
```

边界：
1. `revenue_amount = 0` 时，`profit_rate = null`，不得除零。
2. 任一 P1 成本项 unresolved 时，快照允许生成但必须标记 `snapshot_status=incomplete`。
3. 金额统一 Decimal，计算中保留 6 位小数，展示四舍五入到 2 位。

## 9. 快照不可变与重算

1. 利润快照创建后不可修改。
2. 重算必须生成新 `snapshot_no`，不得覆盖旧快照。
3. 快照明细必须保存公式版本、数据来源、来源单据号、金额和 unresolved 状态。
4. 快照生成必须写操作审计。
5. 快照删除 V1 不开放。

## 10. 幂等口径

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
3. 不允许用 created_at/operator/request_id 进入 hash。

## 11. 权限与审计口径

权限动作：
1. `style_profit:read`
2. `style_profit:snapshot_create`
3. `style_profit:export`

资源权限：
1. company
2. item_code
3. sales_order

规则：
1. 权限来源沿用 ERPNext Role / User Permission 聚合。
2. 权限源不可用必须 fail closed，返回 `PERMISSION_SOURCE_UNAVAILABLE`。
3. 401、403、503 必须写安全审计。
4. 快照生成、幂等 replay、幂等冲突、unresolved 快照必须写操作审计。
5. 日志不得写 Authorization/Cookie/token/password/secret 或原始 SQL 明文。

【必须输出的设计文档结构】

`TASK-005B_款式利润口径冻结说明.md` 必须包含：
1. 版本、更新时间、作者。
2. 冻结结论摘要。
3. 收入口径。
4. 标准材料成本口径。
5. 标准工序成本口径。
6. 实际材料成本口径。
7. 实际工票成本口径。
8. 实际外发成本和扣款口径。
9. 费用分摊口径。
10. 利润公式。
11. 快照不可变与重算规则。
12. 幂等规则。
13. 权限与审计规则。
14. unresolved 状态清单。
15. TASK-005C 输入清单。
16. 禁止实现范围。
17. 验收标准。

【禁止事项】
- 禁止新增或修改 `/07_后端/lingyi_service/app/models/style_profit.py`。
- 禁止新增或修改 `/07_后端/lingyi_service/app/schemas/style_profit.py`。
- 禁止新增或修改 `/07_后端/lingyi_service/app/routers/style_profit.py`。
- 禁止新增或修改 `/07_后端/lingyi_service/app/services/style_profit_service.py`。
- 禁止新增 Alembic 迁移。
- 禁止修改 `/07_后端/lingyi_service/app/main.py` 注册利润路由。
- 禁止新增或修改 `/06_前端/lingyi-pc/src/api/style_profit.ts`。
- 禁止新增或修改 `/06_前端/lingyi-pc/src/views/style_profit/**`。
- 禁止修改前端 router/store 加利润入口。
- 禁止进入 TASK-005C/TASK-006。

【验收标准】
□ `/03_需求与设计/01_架构设计/TASK-005B_款式利润口径冻结说明.md` 已创建。
□ 收入口径已明确区分 `estimated_revenue_amount` 和 `actual_revenue_amount`。
□ 实际材料成本已冻结为 `Stock Ledger Entry` 口径，Purchase Receipt 仅作参考。
□ 外发成本已明确结算优先、验货兜底，且扣款不重复扣减。
□ 费用分摊 V1 明确默认不纳入正式利润，显示 `allocation_status=not_enabled`。
□ 快照不可变和重算新快照已冻结。
□ `POST /snapshot` 幂等键和 request_hash 字段已冻结。
□ 权限动作、资源权限、安全审计和操作审计已冻结。
□ 文档明确 TASK-005C 才能进入数据模型/迁移，且需审计通过后另行下发。
□ `git diff --name-only -- 06_前端 07_后端 .github 02_源码` 无业务代码变更。
□ 未进入 TASK-006。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
