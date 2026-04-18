# TASK-006 加工厂对账单开发前基线盘点（TASK-006A）

- 任务编号：TASK-006A
- 盘点日期：2026-04-15
- 盘点范围：开发前基线盘点与设计冻结（仅文档，不含后端/前端实现）
- 前置基线：TASK-002 外发对账数据出口；TASK-005 已允许标记为本地封版完成

## 1. TASK-002 外发对账出口现状

已完成且可复用的外发对账事实基础：

1. 事实来源已沉淀在 `ly_schema.ly_subcontract_inspection`，包含数量、不合格率、加工费、扣款、净额和结算状态。
2. 已有结算候选/预览/锁定/释放服务与路由（`/api/subcontract/settlement-candidates|preview|locks|locks/release`）。
3. 锁定幂等基础已具备：`idempotency_key + request_hash`，并带 append-only 操作记录表。
4. 权限已具备动作权限与资源权限基础框架，权限源不可用遵循 fail closed。
5. TASK-002 明确边界：不创建加工厂对账单主表，不创建 ERPNext `Purchase Invoice`。

## 2. 可作为对账来源的表/字段/状态（冻结）

### 2.1 唯一对账来源粒度（冻结结论）

冻结选择：**按验货记录粒度（`ly_subcontract_inspection` 一行一条对账来源明细）**。

冻结理由：

1. 已有审计通过的金额事实字段（`gross_amount/deduction_amount/net_amount`）。
2. 已有去重与锁定字段（`settlement_status/statement_id/statement_no/settlement_line_key`）。
3. 粒度稳定，可直接做“同一来源明细不可重复进入未取消对账单”的约束。
4. 相比“外发单汇总粒度”，验货明细能保留批次与质量差异，避免汇总口径掩盖风险。

### 2.2 可对账来源字段（冻结）

| 维度 | 冻结字段 |
| --- | --- |
| 主键与来源定位 | `inspection.id`, `inspection.subcontract_id`, `inspection.receipt_batch_no`, `inspection.settlement_line_key` |
| 资源边界 | `inspection.company`, `order.supplier` |
| 日期字段 | `inspection.inspected_at`（006B 主筛选）；`settled_at` 仅保留为后续扩展字段，不作为 006B 候选主筛选 |
| 来源状态 | `inspection.status`（需为已验货）、`inspection.settlement_status` |
| 锁定状态 | `settlement_status` + `statement_id/statement_no` |
| 金额事实 | `gross_amount`, `deduction_amount`, `net_amount`, `rejected_rate`, `inspected_qty`, `rejected_qty`, `accepted_qty` |

### 2.3 可对账来源条件（冻结）

必须同时满足：

1. `company` 命中请求公司且通过资源权限校验。
2. `supplier` 命中请求加工厂且通过资源权限校验。
3. `inspected_at` 落在 `[from_date, to_date]`。
4. 来源状态为可结算（已验货且未取消），`settlement_status = unsettled`。
5. 未被锁定到其他未取消对账单（`statement_id/statement_no` 不指向活动单据）。
6. 外发主单非草稿/非取消，且来源记录未进入 blocked scope。

### 2.4 不可作为对账来源字段（冻结）

以下字段禁止作为金额权威来源：

1. 前端传入明细金额与前端汇总金额。
2. `ly_subcontract_order` 的订单级汇总金额（仅展示，不作为对账明细权威）。
3. 历史临时字段、演示字段、未审计字段。
4. 旧错误公式派生值（例如 `net_amount = inspected_qty - deduction_amount`）。

## 3. 金额口径冻结

### 3.1 头表汇总公式（冻结）

1. `gross_amount = sum(statement_item.gross_amount)`
2. `deduction_amount = sum(statement_item.deduction_amount)`
3. `net_amount = gross_amount - deduction_amount`
4. `rejected_rate = total_rejected_qty / total_inspected_qty`

### 3.2 `inspected_qty = 0` 处理（冻结）

`total_inspected_qty = 0` 时，`rejected_rate` 冻结为 `0`（不得抛异常、不得返回 NaN/Inf）。

### 3.3 验收算例（冻结）

- 加工费：`5000`
- 扣款：`300`
- 实付：`net_amount = 5000 - 300 = 4700`

## 4. 幂等与重复对账防护冻结

### 4.1 幂等策略（冻结）

1. 生成草稿、确认、应付草稿、取消均要求 `idempotency_key`。
2. 服务端按关键请求字段生成 `request_hash`。
3. 同一操作类型下：
   - `idempotency_key` 相同且 `request_hash` 相同：返回第一次结果（replay）。
   - `idempotency_key` 相同但 `request_hash` 不同：返回冲突错误。

### 4.2 幂等冲突错误码（冻结）

冲突统一返回：`FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。

### 4.3 重复对账防护（冻结）

1. 同一来源明细（`subcontract_id + inspection_id/settlement_line_key`）不得进入多个**未取消**对账单。
2. 同一范围（`company + supplier + from_date + to_date + request_hash`）不得生成多个未取消对账单。

## 5. 状态机冻结

冻结状态机：`draft -> confirmed -> payable_draft_created`，并允许 `cancelled`（受约束）。

### 5.1 状态定义

1. `draft`：草稿，可确认、可取消。
2. `confirmed`：已确认，金额锁定，等待应付草稿。
3. `payable_draft_created`：已创建 ERPNext 应付草稿（或已记录创建成功结果）。
4. `cancelled`：已取消，不参与活动对账与重复校验基线。

### 5.2 关键禁止操作（冻结）

1. `confirmed` 后禁止修改明细数量、加工费、扣款、实付金额。
2. `confirmed` 后若需调整，必须走“取消重建”或独立调整记录流程，不允许原地改金额。
3. `payable_draft_created` 后取消/反冲规则在 TASK-006E 细化前默认禁止隐式自动化。

## 6. 权限与审计冻结

### 6.1 动作权限（冻结）

1. `factory_statement:read`
2. `factory_statement:create`
3. `factory_statement:confirm`
4. `factory_statement:payable_draft`
5. `factory_statement:cancel`

### 6.2 资源权限（冻结）

1. 所有读写都必须叠加 `company + supplier` 资源权限。
2. 权限源（ERPNext User Permission / 权限聚合服务）不可用时，写操作 fail closed。
3. 资源权限不可解析时 fail closed，不得降级全量放开。

### 6.3 登录身份与确认人（冻结）

1. 所有接口必须登录鉴权。
2. `confirmed_by` 只能来自当前登录用户，不信任前端传值。

### 6.4 审计要求（冻结）

1. `create/confirm/payable_draft/cancel` 成功与失败都要写操作审计。
2. 403/503 权限相关失败写安全审计。
3. 日志需脱敏（token/cookie/secret/password 禁止入日志）。

## 7. ERPNext 边界冻结

### 7.1 必做校验（冻结）

1. `Supplier` 存在且可用。
2. `Account` 可用。
3. `Cost Center` 可用。

### 7.2 Fail Closed（冻结）

以下任一不可用均 fail closed：

1. ERPNext 连接不可用。
2. 权限源不可用。
3. Supplier/Account/Cost Center 校验失败。

推荐错误码：

- `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE`
- `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE`
- `FACTORY_STATEMENT_SUPPLIER_NOT_FOUND`

### 7.3 Purchase Invoice 边界（冻结）

1. **TASK-006A/006B/006C 禁止创建 ERPNext Purchase Invoice。**
2. `Purchase Invoice` 草稿创建能力仅在 TASK-006D 设计与审计通过后实现。
3. TASK-006D 需二选一冻结：同步 REST 或 outbox；在 006A 先建议优先 outbox（可重试、可审计、可恢复）。

## 8. 错误码规划冻结

| 错误码 | 场景 |
| --- | --- |
| `FACTORY_STATEMENT_PERMISSION_DENIED` | 动作权限或资源权限不足 |
| `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE` | 权限源不可用 |
| `FACTORY_STATEMENT_SUPPLIER_NOT_FOUND` | 供应商不存在/不可用 |
| `FACTORY_STATEMENT_SOURCE_NOT_FOUND` | 无可对账来源 |
| `FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED` | 来源明细已进入未取消对账单 |
| `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT` | 同幂等键请求哈希冲突 |
| `FACTORY_STATEMENT_STATUS_INVALID` | 状态不允许当前动作 |
| `FACTORY_STATEMENT_CONFIRMED_LOCKED` | 已确认金额锁定禁止修改 |
| `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE` | ERPNext 不可用 |
| `FACTORY_STATEMENT_DATABASE_READ_FAILED` | 数据库读取失败 |
| `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` | 数据库写入失败 |

## 9. 开发前剩余风险清单（进入 006B 前）

1. `settled_at` 是否纳入候选筛选的业务语义尚未启用，需在 006B 固化。
2. 对账单主表/明细表唯一索引最终 DDL 需在 006B 与迁移脚本一致化。
3. `payable_draft_created` 与取消/反冲的互斥规则需在 006E 细化。
4. ERPNext 主数据缓存策略（TTL/降级）需在 006D 做明确策略与压测。

## 10. TASK-006 后续拆分建议（冻结）

1. **TASK-006B**：后端模型/迁移 + 草稿生成/列表/详情（不写 ERPNext PI）。
2. **TASK-006C**：确认、金额锁定、取消规则与日志。
3. **TASK-006D**：ERPNext 应付草稿（Supplier/Account/Cost Center + outbox/sync 方案）。
4. **TASK-006E**：前端页面与交互权限（不改变后端冻结口径）。
5. **TASK-006F**：封版回归、证据收口、审计复核。

## 11. 结论

基线盘点与设计冻结结论：

1. 对账来源、金额公式、幂等、状态机、权限审计和 ERPNext 边界已形成可审计契约。
2. 本阶段未进入后端实现，不触达前端页面与迁移。
3. **建议进入 TASK-006B（仅在 TASK-006A 审计通过后）。**

