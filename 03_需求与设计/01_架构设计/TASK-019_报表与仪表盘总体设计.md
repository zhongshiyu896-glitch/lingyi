# TASK-019 报表与仪表盘总体设计

- 任务编号：TASK-019
- 任务名称：报表与仪表盘设计冻结
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计

## 1. 目标

冻结报表与仪表盘的总体口径，明确所有报表默认只读，不新增写接口，不绕过各模块已审计快照与权限边界。

## 2. 总原则

1. 报表与仪表盘只读优先。
2. 禁止报表页面触发业务写入、重算、生成、同步、提交。
3. 报表指标必须有来源、口径、时间范围、权限字段。
4. 导出必须防 CSV 公式注入。
5. 缓存和快照不得改变业务事实。

## 3. 报表范围

| 报表 | 来源 | 类型 |
|---|---|---|
| 生产进度看板 | Work Order / Job Card / Production records | 只读 |
| 库存趋势 | Stock Ledger Entry / Bin | 只读 |
| 款式利润趋势 | Style Profit Snapshot | 只读快照 |
| 加工厂对账统计 | Factory Statement | 只读汇总 |
| 销售库存视图 | Sales Inventory | 只读 |
| 质量统计 | Quality Inspection | 只读 |
| 财务摘要 | TASK-016 后续设计 | 只读 |

## 4. 权限动作

| 动作 | 类型 | 说明 |
|---|---|---|
| `report:read` | 读 | 报表浏览 |
| `report:export` | 导出 | 报表导出，必须审计 |
| `report:dashboard_read` | 读 | 仪表盘 |
| `report:diagnostic` | 诊断 | 管理员诊断 |
| `report:cache_refresh` | 管理 | 后续独立设计，默认冻结 |

## 5. 资源字段

| 字段 | 说明 |
|---|---|
| company | 全部报表必备 |
| from_date / to_date | 时间范围 |
| item_code | 款式/物料维度 |
| supplier | 供应商维度 |
| customer | 客户维度 |
| warehouse | 仓库维度 |
| source_module | 来源模块 |

## 6. 指标口径冻结

### 6.1 生产进度

| 指标 | 口径 |
|---|---|
| planned_qty | Work Order 计划数量 |
| completed_qty | 已完工数量 |
| progress_rate | completed_qty / planned_qty，分母为 0 时为 0 |

### 6.2 库存趋势

| 指标 | 口径 |
|---|---|
| opening_qty | 期初库存 |
| in_qty | 入库数量 |
| out_qty | 出库数量 |
| closing_qty | opening + in - out |

### 6.3 利润趋势

以已落库 style profit snapshot 为准，报表不得触发重算。

### 6.4 质量统计

以 quality inspection 记录为准，confirmed/cancelled 状态需区分展示。

## 7. 数据刷新策略

| 模式 | 本阶段允许 | 说明 |
|---|---|---|
| 在线只读查询 | 允许 | 必须分页与权限过滤 |
| 本地缓存 | 设计 | 不得改变事实 |
| 手动刷新 | 设计 | 不得触发业务写入 |
| 定时刷新 | 后续任务 | 需 outbox/worker 审计 |

## 8. 前端门禁

1. 报表模块必须接入 TASK-010 公共门禁。
2. 禁止出现 create/generate/recalculate/submit/sync 等写入口。
3. 禁止直连 ERPNext。
4. 导出工具必须统一调用安全 CSV 转义。
5. 每个模块必须有 positive / negative fixture。

## 9. 后端要求

1. 所有接口必须返回 `{code,message,data}`。
2. 读接口必须权限前置，避免存在性枚举。
3. 导出必须操作审计。
4. diagnostic 必须管理员权限与操作审计。
5. 不得新增业务写入接口。

## 10. 审计关注点

1. 报表是否触发重算或生成业务事实。
2. 是否绕过快照边界直接聚合敏感数据。
3. 是否导出公式注入风险。
4. 是否无权限仍能访问跨 company 数据。
5. 是否错误声明生产指标闭环。

## 11. 结论

本设计建议进入 TASK-019A 审计。审计通过后，只允许进入具体看板口径设计，不允许直接实现写接口。
