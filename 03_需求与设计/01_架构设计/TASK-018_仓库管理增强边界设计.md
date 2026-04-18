# TASK-018 仓库管理增强边界设计

- 任务编号：TASK-018
- 任务名称：仓库管理增强设计冻结
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计

## 1. 目标

冻结仓库增强模块的边界，包括 Stock Entry、库存盘点、库存预警、库存台账读取与 ERPNext 写入限制。

## 2. 总原则

1. 仓库写入会影响 Stock Ledger，必须高度审计。
2. Stock Entry 写入必须通过 outbox 与 fail-closed adapter。
3. 盘点、调拨、报废、领料、退料需要明确业务来源与资源归属。
4. 库存预警只读优先，不自动生成写入单据。
5. 未完成 ERPNext 生产联调前不得开放生产库存写入。

## 3. 范围矩阵

| 功能 | 本阶段定位 | 说明 |
|---|---|---|
| 库存台账 | 只读设计 | 读取 Stock Ledger Entry |
| 库存预警 | 只读设计 | 安全库存、缺料、超储 |
| Stock Entry | 写入设计 | 后续独立 outbox 设计 |
| 库存盘点 | 流程设计 | 盘盈盘亏需财务边界 |
| 调拨 | 流程设计 | 源仓/目标仓均需权限 |
| 报废 | 流程设计 | 需审批与原因码 |

## 4. 权限动作

| 动作 | 类型 | 说明 |
|---|---|---|
| `warehouse:read` | 读 | 库存查询、台账 |
| `warehouse:export` | 导出 | 库存导出，防公式注入 |
| `warehouse:diagnostic` | 诊断 | 管理员诊断，必须审计 |
| `warehouse:stock_entry_create` | 写 | 后续设计，默认冻结 |
| `warehouse:stock_entry_cancel` | 写 | 后续设计，默认冻结 |
| `warehouse:stock_count_create` | 写 | 盘点草稿，后续设计 |
| `warehouse:stock_count_confirm` | 写 | 盘点确认，后续设计 |

## 5. 资源字段

| 字段 | 说明 |
|---|---|
| company | 必填 |
| warehouse | 仓库权限 |
| source_warehouse | 调拨源仓 |
| target_warehouse | 调拨目标仓 |
| item_code | 物料权限 |
| work_order | 生产相关领退料 |
| batch_no / serial_no | 批次/序列号追踪 |
| source_type/source_id | 业务来源 |

## 6. ERPNext DocType 边界

| DocType | 本阶段能力 | 写入限制 |
|---|---|---|
| Warehouse | 只读 | 禁止修改 |
| Bin | 只读 | 禁止修改 |
| Stock Ledger Entry | 只读 | 禁止直接写 |
| Stock Entry | 设计 | 写入需 outbox + adapter |
| Stock Reconciliation | 设计 | 盘点差异需独立审计 |
| Batch / Serial No | 只读 | 修改需独立任务 |

## 7. Stock Entry 写入策略

后续 TASK-018B 必须设计：

1. 本地业务单据先落库。
2. outbox event_key 基于 company、source、items、warehouses、purpose。
3. worker 外调前复核仓库归属、物料归属、库存可用性。
4. ERPNext 返回 draft 后不得自动 submit，除非后续任务单明确允许。
5. submit / cancel / reversal 必须分任务审计。

## 8. 库存盘点策略

盘点建议状态：

```text
draft -> counted -> variance_review -> confirmed -> cancelled
```

盘点差异处理：

1. 盘盈盘亏不得直接写 GL。
2. Stock Reconciliation 需沙箱验证。
3. confirmed 后关键事实不可改。
4. 差异原因码必填。

## 9. 库存预警口径

| 指标 | 口径 |
|---|---|
| 可用库存 | Bin 或 SLE 聚合，只读 |
| 安全库存缺口 | reorder_level - projected_qty |
| 呆滞库存 | 最后出入库日期超过阈值 |
| 在途库存 | Purchase Order / Purchase Receipt 只读口径 |

## 10. 审计关注点

1. 是否出现未经审计的 Stock Entry 写入。
2. 是否直接写 Stock Ledger Entry。
3. 是否盘点差异影响财务但未纳入 TASK-016。
4. 是否前端绕过门禁发起写入。
5. 是否 source warehouse / target warehouse 权限不完整。

## 11. 结论

本设计建议进入 TASK-018A 审计。审计通过后，仅允许进入 Stock Entry Outbox 设计，不允许直接实现库存写入。
