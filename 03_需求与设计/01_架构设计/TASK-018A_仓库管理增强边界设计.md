# TASK-018A 仓库管理增强边界设计

- 任务编号：TASK-018A
- 任务名称：仓库增强边界设计冻结
- 文档状态：待审计
- 更新日期：2026-04-23
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

本任务只做仓库增强边界设计冻结，目标是把仓库主链对象、权限、资源、集成边界和门禁条件收敛到可审计口径。

明确非目标：

1. 不做前后端实现。
2. 不做测试实现。
3. 不做环境联调。
4. 不做任何 ERPNext 生产写入。
5. 不放行任何仓库实现任务。

## 2. 仓库增强总边界

本任务冻结对象与关系边界如下：

1. `Stock Entry`：候选写链对象，仅冻结流程边界与门禁，不放行实现。
2. 库存盘点：仅冻结盘点事实、差异复核、审批边界，不放行实现。
3. `Batch / Serial`：仅冻结主数据读取和一致性校验边界，不放行创建/写入。
4. 库存预警：仅冻结预警规则与审计边界，不放行自动写入或自动执行。
5. `Stock Ledger / Stock Reconciliation / Warehouse`：
   - `Stock Ledger Entry` 是库存结果事实；
   - `Stock Reconciliation` 是盘点差异承载对象之一；
   - `Warehouse` 是库存归属与权限约束主键；
   - 三者关系只冻结职责，不放行实现。

## 3. Stock Entry 边界

### 3.1 动作拆分

1. `stock_entry_draft_create`
2. `stock_entry_confirm`
3. `stock_entry_cancel`

三类动作必须拆分为独立受控入口，不允许合并为单一“库存写入入口”。

### 3.2 处理原则

1. 只允许定义候选写链，不允许同步直写 ERPNext。
2. 写链必须先 Outbox enqueue，再 Worker 调用 Adapter。
3. `idempotency_key` 用于请求幂等；`event_key` 用于业务事实去重，禁止混用。

### 3.3 状态机建议（冻结）

```text
draft -> pending_outbox -> processing -> succeeded
                               |             |
                               |             -> failed -> pending_outbox (retry)
                               |                           |
                               |                           -> dead
                               -> cancelled
```

## 4. 库存盘点边界

1. 盘点单仅冻结流程：草稿 -> 差异复核 -> 审批确认/取消。
2. 盘盈盘亏只冻结业务口径，不放行自动落账与自动写入。
3. 是否生成 `Stock Entry`：当前仅冻结候选关系，未放行实现。
4. 差异确认必须附带来源、责任、原因码，并可审计回放。

## 5. Batch / Serial 边界

1. `Batch` 与 `Serial` 当前仅允许读取、校验、追溯，不放行创建/修改。
2. 必须与 `item_code`、`warehouse`、`company` 保持归属一致。
3. 关键字段缺失、禁用、归属冲突时必须 fail-closed。
4. 日志和审计输出遵循最小暴露，禁止泄露敏感原始值。

## 6. 库存预警边界

1. 预警类型冻结：低库存、超储、呆滞、安全库存不足。
2. 数据来源冻结：ERPNext 只读事实 + 本地受控阈值配置。
3. 预警输出仅限诊断与建议，不允许自动写入 ERPNext。
4. 预警不替代库存事实和财务事实。

## 7. 权限动作矩阵（最小集合）

| 动作 | 层级 | 用途 | 当前放行 |
|---|---|---|---|
| `warehouse:read` | 只读 | 仓库与库存事实查询 | 是（只读） |
| `warehouse:export` | 只读 | 只读导出 | 是（只读） |
| `warehouse:stock_entry_draft` | 候选写 | Stock Entry 草稿动作 | 否（设计冻结） |
| `warehouse:stock_entry_confirm` | 候选写 | Stock Entry 确认动作 | 否（设计冻结） |
| `warehouse:stock_entry_cancel` | 候选写 | Stock Entry 取消动作 | 否（设计冻结） |
| `warehouse:inventory_count` | 候选写 | 盘点候选动作 | 否（设计冻结） |
| `warehouse:alert_read` | 只读 | 预警只读查看 | 是（只读） |
| `warehouse:diagnostic` | internal-only | 诊断与内部运维动作 | 否（普通前端） |

说明：未知动作默认拒绝（fail-closed）。

## 8. 资源字段矩阵（最小集合）

| 资源字段 | 用途 | 约束 |
|---|---|---|
| `company` | 公司隔离主键 | 必填且必须匹配权限范围 |
| `warehouse` | 仓库归属主键 | 必填且归属一致 |
| `item_code` | 物料主键 | 必填且可追溯 |
| `batch_no` | 批次约束 | 按物料策略必填 |
| `serial_no` | 序列约束 | 按物料策略必填 |
| `stock_entry` | 库存分录对象键 | 候选写动作必校验 |
| `stock_reconciliation` | 盘点差异对象键 | 盘点链路必校验 |
| `purchase_receipt` | 采购收货关联键 | 仅关系校验，不放行实现 |
| `delivery_note` | 销售发货关联键 | 仅关系校验，不放行实现 |
| `work_order` | 生产关联键 | 仅关系校验，不放行实现 |
| `idempotency_key` | 请求幂等键 | 仅请求级幂等 |
| `event_key` | 事实去重键 | 仅事实级防重 |

说明：关键资源字段缺失或归属不匹配时一律 fail-closed。

## 9. ERPNext DocType 与 Adapter / Outbox 边界

### 9.1 DocType 边界

| 对象 | ERPNext DocType | 当前口径 |
|---|---|---|
| Stock Entry | `Stock Entry` | 候选写冻结，不放行实现 |
| 库存流水 | `Stock Ledger Entry` | 只读事实 |
| 库存盘点 | `Stock Reconciliation` | 候选写冻结，不放行实现 |
| 仓库主数据 | `Warehouse` | 只读 |
| 批次 | `Batch` | 只读 |
| 序列号 | `Serial No` | 只读 |
| 库存聚合 | `Bin` | 只读 |

### 9.2 Adapter / Outbox 分工

1. Adapter 只负责 ERPNext 外调归一和 fail-closed 判定。
2. Outbox 负责入队、claim、lease、retry、dead、状态流转。
3. Worker 调用 Adapter；Adapter 不直接改 Outbox 状态。
4. 写链顺序必须是“先 Outbox，后 Adapter”。
5. `internal-only` 路径不得前端化。

## 10. fail-closed 与审计要求

以下条件必须 fail-closed，禁止 `200 + 空数据` 伪成功：

1. 401/403
2. timeout
3. 5xx
4. malformed response
5. 资源归属不匹配（company/warehouse/item/batch/serial）
6. docstatus 缺失、非法或状态冲突

审计要求：

1. 操作审计最小集：create/update/confirm/cancel/retry/dead/diagnostic。
2. 安全审计最小集：权限拒绝、资源越权、external unavailable、internal-only 误入。
3. 日志脱敏：禁止 token/password/secret/DSN/Authorization/Cookie 泄露。

## 11. 三层能力冻结统一矩阵

| 对象/动作 | 只读能力 | 候选写能力 | 生产写能力 |
|---|---|---|---|
| Stock Entry query | 是 | 否 | 否 |
| Stock Entry draft/create | 否 | 是（冻结） | 否（冻结） |
| Stock Entry confirm/cancel | 否 | 是（冻结） | 否（冻结） |
| 库存盘点 query | 是 | 否 | 否 |
| 库存盘点 create/confirm/cancel | 否 | 是（冻结） | 否（冻结） |
| Batch / Serial query | 是 | 否 | 否 |
| Batch / Serial create/update | 否 | 否 | 否（冻结） |
| 库存预警 query | 是 | 否 | 否 |
| 库存预警自动落库/自动执行 | 否 | 否 | 否（冻结） |
| Stock Reconciliation query | 是 | 否 | 否 |
| Stock Reconciliation write | 否 | 是（冻结） | 否（冻结） |

统一口径：

1. 候选写能力不等于允许实现。
2. 生产写能力当前全部冻结。
3. 未经后续单独任务、单独审计、单独放行，不得进入实现。

## 12. 前端门禁

1. 不允许未审计写入口。
2. 不允许前端直连 ERPNext `/api/resource`。
3. 不允许前端绕过后端直接构造库存事实。
4. `warehouse:diagnostic` 与其他 internal-only 动作不得普通前端化。
5. 写入口必须遵循 `TASK-010` 门禁框架。

## 13. 结论边界与下一步门禁

1. `TASK-018A` 通过仅代表仓库增强边界设计冻结成立。
2. 不代表实现放行，不代表联调、提测、上线、生产写入放行。
3. 当前采购、财务、库存既有职责边界保持不变，不得跨链偷渡实现。
4. `TASK-018A` 通过后仅允许进入 `TASK-018B` 设计。
5. 不允许直接进入任何仓库实现任务。
