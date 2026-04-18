# TASK-017 采购管理边界设计

- 任务编号：TASK-017
- 任务名称：采购管理设计冻结
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计

## 1. 目标

冻结采购管理模块的边界，明确 Purchase Request、Purchase Order、Purchase Receipt、Supplier 主数据与 ERPNext 的读写职责，为后续采购流程设计与实现建立安全基线。

## 2. 总原则

1. 采购写入必须先设计、后审计、再实现。
2. ERPNext 生产写入默认禁止。
3. Purchase Order / Purchase Receipt 的创建与提交必须区分草稿、确认、提交。
4. Supplier / Item / Warehouse / Cost Center 均需资源归属校验。
5. 前端不得直连 ERPNext `/api/resource`。

## 3. 模块范围

| 模块 | 本阶段定位 | 说明 |
|---|---|---|
| Supplier 管理 | 只读优先 | 供应商主数据读取与权限过滤 |
| Purchase Request | 设计冻结 | 需求来源、审批、转换路径 |
| Purchase Order | 设计冻结 | 草稿创建、审批、提交边界 |
| Purchase Receipt | 设计冻结 | 到货入库与 Stock Ledger 影响 |
| Purchase Invoice | 财务模块管辖 | 仅引用，不在本模块直接创建 |

## 4. 权限动作

| 动作 | 类型 | 说明 |
|---|---|---|
| `purchase:read` | 读 | 采购列表/详情 |
| `purchase:export` | 导出 | CSV/Excel 导出，必须防公式注入 |
| `purchase:diagnostic` | 诊断 | 管理员诊断，必须审计 |
| `purchase:request_create` | 写 | 后续设计，不在 TASK-017A 实现 |
| `purchase:order_create` | 写 | 后续设计，不在 TASK-017A 实现 |
| `purchase:receipt_create` | 写 | 后续设计，不在 TASK-017A 实现 |
| `purchase:cancel` | 写 | 后续设计，需状态机与审计 |

## 5. 资源字段

| 字段 | 说明 |
|---|---|
| company | 必填，采购资源归属公司 |
| supplier | 供应商权限 |
| item_code | 物料权限与主数据一致性 |
| warehouse | 到货/入库仓库归属 |
| cost_center | 成本归属 |
| source_type/source_id | 需求来源追踪 |

## 6. ERPNext DocType 边界

| DocType | 本阶段 | 后续写入要求 |
|---|---|---|
| Supplier | 只读 | 修改需单独任务 |
| Item | 只读 | 修改需单独任务 |
| Purchase Request | 设计 | 写入需 outbox + adapter |
| Purchase Order | 设计 | 创建/提交分离，生产写入冻结 |
| Purchase Receipt | 设计 | 入库影响库存，必须单独审计 |
| Stock Ledger Entry | 只读 | 不直接写 |
| Purchase Invoice | 财务边界 | 交给 TASK-016 |

## 7. 状态机建议

采购单据建议状态：

```text
draft -> pending_approval -> approved -> submitted -> cancelled
```

约束：

1. 只有 draft 可编辑关键事实。
2. approved 后生成 ERPNext 草稿需 outbox。
3. submitted 表示 ERPNext docstatus=1，必须由独立任务批准。
4. cancelled 后不可恢复，需反冲或重建策略。

## 8. Outbox 与幂等

采购写入必须继承 TASK-009：

1. `event_key` 基于业务事实：company、supplier、source、items、target doctype。
2. `idempotency_key` 只用于请求重放，不进入 event_key。
3. 外调前重新校验 supplier/item/warehouse/company。
4. failed/dead 重建策略单独任务。

## 9. 审计要求

1. 创建/确认/取消/导出/诊断均需操作审计。
2. 权限失败与资源越权需安全审计。
3. ERPNext 失败不得伪成功。
4. 导出不得泄露敏感字段。

## 10. 前端门禁

1. 新模块接入必须先定义 `fixture.positive` / `fixture.negative`。
2. 禁止未审计的创建、提交、取消按钮。
3. 禁止前端出现 ERPNext 直连。
4. 禁止 diagnostic 对普通角色可见。

## 11. 结论

本设计建议进入 TASK-017A 审计。审计通过后，仅允许进入 Purchase Order 创建流程设计，不允许直接实现。
