# TASK-018A 仓库管理增强边界设计

- 任务编号：TASK-018A
- 任务名称：仓库管理增强边界设计冻结
- 文档状态：待审计
- 更新日期：2026-04-17
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结 Stock Entry、库存盘点、批次/序列号、库存预警的系统责任、权限边界、ERPNext 集成策略、Outbox 使用边界与审计要求，作为后续仓库增强任务的唯一前置设计。

本任务只做设计冻结，不做代码实现，不做环境联调，不做任何 ERPNext 写操作。

## 2. 仓库增强总边界（5.1）

本任务仅冻结仓库管理增强设计边界。
禁止实现 Stock Entry / 库存盘点 / 库存预警代码。
禁止连接生产 ERPNext。
禁止直接写 ERPNext 库存接口。
禁止绕过 TASK-008 Fail-Closed Adapter。
禁止绕过 TASK-009 Outbox 状态机。
TASK-014C 未完成前，不允许进入任何真实平台联调或生产发布。

补充冻结口径：

1. 本文档不代表仓库功能可上线。
2. 本文档不代表 Hosted Runner required checks 与 Branch Protection 已闭环。
3. 库存写入能力必须后续单独任务、单独审计、单独放行。

## 3. Stock Entry 边界（5.2）

### 3.1 类型范围与 Sprint 3 纳入情况

| Stock Entry 类型 | 是否纳入 Sprint 3 | 本阶段定位 | 生产写入 |
|---|---|---|---|
| Material Issue | 是 | 设计冻结，后续沙箱验证 | 冻结 |
| Material Receipt | 是 | 设计冻结，后续沙箱验证 | 冻结 |
| Material Transfer | 是 | 设计冻结，后续沙箱验证 | 冻结 |
| Manufacture | 是（受控） | 设计冻结，需与生产模块协同 | 冻结 |
| Repack | 预留 | 仅边界定义，不进本轮实现 | 冻结 |

说明：以上类型当前均不允许生产写入；仅允许后续独立任务在沙箱验证。

### 3.2 发起/审批/取消职责

1. 发起：`warehouse:stock_entry_draft`。
2. 审批确认：`warehouse:stock_entry_confirm`。
3. 取消：`warehouse:stock_entry_cancel`。
4. 普通只读角色不得触发发起、审批、取消。

### 3.3 ERPNext 集成方式

1. 只读查询走 Adapter（TASK-008）。
2. 写入草稿走 Outbox（TASK-009）。
3. 生产写入继续冻结。

### 3.4 幂等策略

1. `idempotency_key`：请求级重放与冲突判定。
2. `event_key`：业务事实级去重。
3. replay/conflict：同 key 同 hash replay；同 key 异 hash conflict；不同 key 同事实命中 event_key 防重。

### 3.5 状态机（冻结）

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

### 3.6 操作审计要求

1. create/update/confirm/cancel/retry/dead 必须写操作审计。
2. 权限拒绝、资源越权、ERPNext unavailable 必须写安全审计。
3. 审计日志必须脱敏，禁止 token/secret/password/DSN 泄露。

## 4. 库存盘点边界（5.3）

1. 盘点单创建范围：仅冻结流程，不实现创建接口。
2. 盘盈/盘亏处理路径：仅定义业务边界，不做自动落账与自动写入。
3. 是否允许生成 Stock Entry：本阶段不执行；后续仅可在独立任务中受控放行。
4. 盘点审批流程：草稿 -> 差异复核 -> 审批确认/取消，审批动作需权限与审计。
5. 盘点差异确认规则：差异必须有来源、责任与原因码，确认动作必须可追溯。
6. 资源校验：Item/Warehouse/Batch/Serial No 必须一致性校验并受资源权限约束。
7. 与 ERPNext Stock Ledger 一致性校验：差异复核需以可信只读事实校验，不允许本地主观覆盖。
8. ERPNext unavailable/malformed/timeout：必须 fail-closed，禁止伪成功。
9. 禁止前端自行调整库存事实。

## 5. 批次与序列号边界（5.4）

1. Batch No 使用范围：批次管控物料的入库、出库、盘点与追溯。
2. Serial No 使用范围：序列号管控物料的一物一码跟踪。
3. 批次/序列号本地创建：本阶段不允许；仅定义读取与校验边界。
4. 与 Item/Warehouse/Stock Ledger 的关系：
   - Batch/Serial 必须绑定 Item；
   - 变动必须可映射到 Warehouse；
   - 结果事实以 Stock Ledger 为准。
5. 资源权限与数据隔离：必须受 `company/item_code/warehouse/batch_no/serial_no` 限定。
6. 缺失、禁用、归属不一致：一律 fail-closed。
7. 敏感业务字段脱敏：序列号/批次号明细在日志和审计中按最小暴露原则处理。

## 6. 库存预警边界（5.5）

### 6.1 预警类型

- 低库存
- 超储
- 呆滞库存
- 安全库存不足

### 6.2 预警数据来源

1. ERPNext 只读库存事实（如 Stock Ledger/Bin 等）。
2. 本地策略阈值配置（只读配置源）。

### 6.3 预警触发方式

1. 查询时计算（按需计算）。
2. 定时任务（后续任务定义）。
3. 事件驱动（后续任务定义）。

### 6.4 通知与建议边界

1. 是否允许发送通知：允许后续任务定义通知，但不默认开启。
2. 是否允许自动生成采购建议/调拨建议：仅允许“建议”输出，不允许自动落地写入。
3. 禁止自动写入 ERPNext。

### 6.5 审计与事实边界

1. 预警计算口径必须可审计（阈值、时间窗、来源、计算参数可追溯）。
2. 预警不应替代财务或库存事实。

## 7. ERPNext 集成策略（5.6）

| 仓库能力 | ERPNext DocType | 只读/写入 | Adapter | Outbox | 是否允许生产 |
|---|---|---|---|---|---|
| 库存分录 | Stock Entry | 生产只读；写入仅后续沙箱设计 | 必须（TASK-008） | 写入必须（TASK-009） | 否（当前冻结） |
| 库存流水 | Stock Ledger Entry | 只读 | 必须（TASK-008） | 不适用（当前只读） | 否 |
| 仓库主数据 | Warehouse | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 物料主数据 | Item | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 批次 | Batch | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 序列号 | Serial No | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 库存聚合 | Bin | 只读 | 必须（TASK-008） | 不适用 | 否 |
| 采购收货关联 | Purchase Receipt | 只读（仓库侧） | 必须（TASK-008） | 写入如需放行必须（TASK-009） | 否（当前冻结） |
| 销售发货关联 | Delivery Note | 只读（仓库侧） | 必须（TASK-008） | 写入如需放行必须（TASK-009） | 否（当前冻结） |
| 生产工单关联 | Work Order | 只读（仓库侧） | 必须（TASK-008） | 写入如需放行必须（TASK-009） | 否（当前冻结） |

总原则：

1. ERPNext 访问统一经 Adapter。
2. 写链路统一经 Outbox。
3. 未明确放行即默认 fail-closed。

## 8. 权限与审计要求（5.7）

### 8.1 动作权限（冻结）

- `warehouse:read`
- `warehouse:export`
- `warehouse:stock_entry_draft`
- `warehouse:stock_entry_confirm`
- `warehouse:stock_entry_cancel`
- `warehouse:inventory_count`
- `warehouse:alert_read`
- `warehouse:diagnostic`

### 8.2 资源权限字段（冻结）

- `company`
- `item_code`
- `warehouse`
- `batch_no`
- `serial_no`
- `work_order`
- `purchase_receipt`
- `delivery_note`
- `stock_entry`

规则：

1. 列表先动作权限，再资源过滤。
2. 详情与写动作先动作权限，再资源校验。
3. 关键资源缺失默认拒绝（fail-closed）。

### 8.3 审计事件（冻结）

操作审计事件：

- create
- update
- confirm
- cancel
- export
- dry-run
- diagnostic
- stock variance approved

安全审计事件：

- ERPNext unavailable
- resource access denied
- 401/403/internal API 访问拒绝

## 9. 前端门禁要求（5.8）

1. 所有写入口默认禁止。
2. `warehouse:diagnostic` 不得暴露给普通前端菜单。
3. 前端禁止直连 ERPNext `/api/resource`。
4. 前端禁止裸 `fetch/axios` 绕过 API client。
5. 前端禁止自行计算库存事实并提交。
6. CSV / Excel 导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。

## 10. 生产发布前置条件（5.9）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 生产联调只读验证通过。
5. 沙箱写入验证通过。
6. Stock Entry / 盘点 / 预警写入必须单独设计、单独审计、单独放行。
7. 生产写入必须由总调度书面批准。

## 11. 结论边界

1. 本文档仅冻结仓库管理增强边界，不包含仓库功能实现。
2. 本文档不代表库存写入能力可用。
3. 本文档不代表 ERPNext 生产联调完成。
4. 本文档不代表生产发布完成。
