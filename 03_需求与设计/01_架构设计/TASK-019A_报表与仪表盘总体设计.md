# TASK-019A 报表与仪表盘总体设计

- 任务编号：TASK-019A
- 任务名称：报表与仪表盘总体设计
- 文档状态：待审计
- 更新日期：2026-04-23
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结报表与仪表盘总体设计，统一指标口径、看板维度、数据来源、权限边界、缓存一致性、导出安全与前端门禁策略，作为后续报表模块实现与审计的唯一前置设计。

本任务只做设计冻结，不做后端接口实现，不做前端页面开发，不做 ERPNext 联调。

## 2. 报表模块总边界（5.1）

本任务仅冻结报表与仪表盘设计。
默认只读。
禁止实现接口。
禁止实现前端页面。
禁止引入任何 ERPNext 写入口。
禁止前端直连 ERPNext。
禁止把报表计算结果写回业务事实表。
TASK-014C 未完成前，不允许进入任何真实平台联调或生产发布。

补充约束：

1. 本文档结论不代表报表模块已实现。
2. 本文档结论不代表 Hosted Runner / required checks / Branch Protection 已闭环。
3. 报表相关写能力（若未来存在）必须单独任务、单独审计、单独放行。

## 3. 指标口径定义（5.2）

### 3.1 统一口径规则

1. 指标计算统一在后端完成，前端只展示；默认不允许前端重算。
2. 指标必须绑定资源权限过滤（至少 company + 业务维度）。
3. 外部依赖（ERPNext）不可用、响应畸形、关键字段缺失时，必须 fail-closed 或返回明确错误，不允许伪成功。
4. 财务相关指标禁止使用 stale 缓存作为正式事实输出。

### 3.2 生产进度指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 工单数量 | ERPNext Work Order + 本地工票关联 | 统计范围内工单总数 | company, work_order, item_code | 否 | 5 分钟缓存 | Work Order 读取失败/结构异常 |
| 已完成数量 | Work Order / Job Card | `status in completed` 或等价闭环状态数 | company, work_order | 否 | 5 分钟缓存 | 状态字段缺失或非法 |
| 在制数量 | Work Order | `总数 - 已完成 - 取消` | company, work_order | 否 | 5 分钟缓存 | 总量或状态口径不完整 |
| 延期数量 | Work Order 计划/实际日期 | `实际完成时间 > 计划完成时间` 或当前已超期未完成 | company, work_order | 否 | 5 分钟缓存 | 计划/实际日期缺失 |
| 完成率 | 上述聚合结果 | `已完成数量 / 工单数量`（总数为 0 则 0） | company | 否 | 与源指标同缓存 | 分母或源指标不可用 |

### 3.3 库存指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 当前库存 | ERPNext Stock Ledger Entry / Bin | 截止查询时点库存结存 | company, warehouse, item_code | 否 | 2 分钟缓存 | SLE/Bin 响应 malformed |
| 可用库存 | 当前库存 + 预留占用表 | `当前库存 - 已预留数量` | company, warehouse, item_code | 否 | 2 分钟缓存 | 预留数据缺失且无法校验 |
| 安全库存差额 | 安全库存配置 + 可用库存 | `可用库存 - 安全库存` | company, warehouse, item_code | 否 | 2 分钟缓存 | 安全库存阈值缺失 |
| 库存周转 | SLE + 成本/出入库汇总 | 周转口径按审计版公式（期间出库成本/平均库存） | company, warehouse, item_code | 否 | 15 分钟缓存 | 成本字段缺失或类型非法 |
| 呆滞库存 | SLE 最后动销时间 | 超过阈值天数无动销判定为呆滞 | company, warehouse, item_code | 否 | 30 分钟缓存 | posting_date 缺失 |

### 3.4 财务指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 应收余额 | ERPNext Sales Invoice / Payment Entry / GL | 审计口径净额（仅财务事实） | company, customer, account, cost_center | 否 | 默认不缓存或 1 分钟且标记 stale | 任一财务源不可用 |
| 应付余额 | ERPNext Purchase Invoice / Payment Entry / GL | 审计口径净额（仅财务事实） | company, supplier, account, cost_center | 否 | 默认不缓存或 1 分钟且标记 stale | 任一财务源不可用 |
| 毛利 | 本地款式利润快照 + 销售事实 | `收入 - 成本`（按审计口径） | company, item_code, sales_order | 否 | 10 分钟缓存 | 收入或成本源缺失 |
| 净利 | 毛利 + 费用口径数据 | `毛利 - 期间费用` | company, account, cost_center | 否 | 10 分钟缓存 | 费用数据不可用 |
| 账龄 | AR/AP 明细 + 到期日 | 按账龄区间聚合 | company, customer/supplier | 否 | 5 分钟缓存（结果标注时点） | due_date 缺失或异常 |

### 3.5 采购指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 采购订单金额 | ERPNext Purchase Order | 期间 PO 金额汇总 | company, supplier, purchase_order | 否 | 10 分钟缓存 | PO 结构异常 |
| 到货数量 | Purchase Receipt | 期间收货数量汇总 | company, supplier, item_code, warehouse | 否 | 10 分钟缓存 | PR 缺关键字段 |
| 未到货数量 | PO 与 PR 对比 | `PO 数量 - 已到货数量`（下限 0） | company, supplier, item_code, purchase_order | 否 | 10 分钟缓存 | PO/PR 关联键缺失 |
| 供应商交付及时率 | PO 计划到货 + PR 实际到货 | `按时到货单数/总到货单数` | company, supplier | 否 | 30 分钟缓存 | 计划/实际到货时间缺失 |

### 3.6 质量指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 检验数量 | 本地质量检验主表 | 期间检验单或检验批次数量 | company, item_code, supplier, warehouse | 否 | 5 分钟缓存 | 检验主键/状态字段缺失 |
| 合格数量 | 本地质量检验明细 | accepted_qty 汇总 | company, item_code, supplier, warehouse | 否 | 5 分钟缓存 | accepted_qty 类型非法 |
| 不合格数量 | 本地质量检验明细 | rejected_qty 汇总 | company, item_code, supplier, warehouse | 否 | 5 分钟缓存 | rejected_qty 类型非法 |
| 缺陷数量 | 本地质量缺陷表 | defect_qty 汇总 | company, item_code, supplier, warehouse | 否 | 5 分钟缓存 | defect 关联字段缺失 |
| 合格率 | 质量聚合结果 | `合格数量 / 检验数量`（分母为 0 则 0） | company | 否 | 与源指标同缓存 | 源指标缺失或不一致 |

### 3.7 外发加工指标

| 指标 | 数据来源 | 计算口径 | 权限过滤字段 | 前端重算 | 缓存策略 | fail-closed 条件 |
|---|---|---|---|---|---|---|
| 外发数量 | 本地外发单据 | 期间外发数量汇总 | company, supplier, item_code, statement_status | 否 | 10 分钟缓存 | 外发单据缺关键字段 |
| 回料数量 | 外发回料/验货记录 | 期间回料数量汇总 | company, supplier, item_code | 否 | 10 分钟缓存 | 回料关联字段缺失 |
| 扣款金额 | 加工厂对账单 | 期间扣款金额汇总 | company, supplier, statement_status | 否 | 10 分钟缓存 | 金额字段异常 |
| 加工费 | 加工厂对账单 | 期间加工费汇总 | company, supplier, statement_status | 否 | 10 分钟缓存 | 加工费字段异常 |
| 对账状态 | 加工厂对账单状态 | 按状态分布统计 | company, supplier, statement_status | 否 | 10 分钟缓存 | 状态码缺失或非法 |

## 4. 看板维度定义（5.3）

| 维度 | 过滤语义 | 数据隔离语义 | 权限要求 | 空值处理 | 越权处理 |
|---|---|---|---|---|---|
| company | 按公司过滤所有数据域 | 公司级强隔离 | 必须有 company 访问权限 | 空值拒绝 | fail-closed + 安全审计 |
| date range | 期间窗口过滤 | 仅过滤，不改变资源权限 | 继承数据域权限 | 缺失则拒绝或默认安全窗口 | 非法范围拒绝 |
| item_code | 物料维度过滤 | 按物料归属隔离 | 需 item_code 资源权限 | 空值表示不过滤（受其他资源限制） | 越权返回统一拒绝 |
| supplier | 供应商维度过滤 | 供应商级隔离 | 需 supplier 资源权限 | 空值表示不过滤 | 越权 fail-closed |
| customer | 客户维度过滤 | 客户级隔离 | 需 customer 资源权限 | 空值表示不过滤 | 越权 fail-closed |
| warehouse | 仓库维度过滤 | 仓库级隔离 | 需 warehouse 资源权限 | 空值表示不过滤 | 越权 fail-closed |
| work_order | 工单维度过滤 | 工单级隔离 | 需 work_order 权限 | 空值表示不过滤 | 越权 fail-closed |
| sales_order | 销售订单维度过滤 | 订单级隔离 | 需 sales_order 权限 | 空值表示不过滤 | 越权 fail-closed |
| purchase_order | 采购订单维度过滤 | 订单级隔离 | 需 purchase_order 权限 | 空值表示不过滤 | 越权 fail-closed |
| quality_status | 质检状态过滤 | 仅作用于质量域 | 需 quality 读权限 | 空值表示不过滤 | 非法状态拒绝 |
| statement_status | 对账状态过滤 | 仅作用于对账域 | 需对账读取权限 | 空值表示不过滤 | 非法状态拒绝 |

维度通用规则：

1. 列表型报表先动作权限，再资源过滤。
2. 详情型报表先动作权限，再资源校验。
3. 对外响应不通过 403/404 差异泄露资源存在性。

## 5. 数据来源（5.4）

| 报表域 | 数据来源 | 只读/写入 | ERPNext Adapter | 本地表 | fail-closed 策略 |
|---|---|---|---|---|---|
| 生产进度 | ERPNext Work Order/Job Card + 本地工票映射 | 只读 | 必须（TASK-008） | 工票/生产关联表 | 外部不可用或结构异常即阻断 |
| 库存域 | ERPNext SLE/Bin/Warehouse/Item | 只读 | 必须（TASK-008） | 本地库存辅助表（如预留） | 关键字段缺失即阻断 |
| 财务域 | ERPNext GL/PI/SI/PE + 本地利润快照 | 只读 | 必须（TASK-008） | 款式利润快照 | 财务事实源不可用即阻断 |
| 采购域 | ERPNext PO/PR/Supplier/Item | 只读 | 必须（TASK-008） | 采购关联只读表 | PO/PR/Supplier 读取异常即阻断 |
| 外发域 | 本地外发单据、回料、对账单 | 只读 | 不适用（本地域） | 外发/对账业务表 | 关键事实不完整即阻断 |
| 质量域 | 本地质量检验/缺陷数据 | 只读 | 不适用（本地域） | 质量主表/明细/缺陷 | 关键字段缺失即阻断 |
| BOM 域 | 本地 BOM 数据 | 只读 | 不适用（本地域） | BOM 表 | 版本/主键缺失即阻断 |
| 权限审计域 | 本地权限审计日志 | 只读 | 不适用 | 安全审计表 | 审计源不可用返回明确错误 |
| 操作审计域 | 本地操作审计日志 | 只读 | 不适用 | 操作审计表 | 审计源不可用返回明确错误 |

## 6. 缓存与一致性边界（5.5）

1. 允许报表缓存，但必须分级：
   - 高频运营类：2~5 分钟。
   - 聚合分析类：10~30 分钟。
   - 财务类：默认不缓存，或极短 TTL 且明确 stale 标识。
2. 缓存 key 必须包含权限 scope（至少 user_id / role_hash / company_scope / 关键资源维度）。
3. 禁止跨用户复用可能越权的缓存结果。
4. ERPNext 不可用时可按策略展示旧缓存，但必须标注 `stale=true`、生成时间和风险提示。
5. 财务类报表默认不允许用过期缓存作为正式事实；仅可作为“参考快照”并显著标注。
6. 缓存刷新失败必须 fail-closed 或降级为明确错误信封，不得伪成功。
7. 缓存与权限变更必须联动失效，避免权限变更后继续返回旧授权结果。

## 7. 导出边界（5.6）

1. 导出必须校验 `report:export`，并复用同一资源过滤条件。
2. 导出动作必须写操作审计，记录导出人、导出时间、筛选条件摘要、结果规模。
3. CSV / Excel 导出必须做公式注入防护（前缀 `= + - @ \t \r \n` 等）。
4. 导出字段必须按最小化原则脱敏（如账号、税号、联系方式等）。
5. 导出行数必须设置上限（例如 10k 或按模块配置），超限走异步任务。
6. 大体量导出允许异步化，但异步结果同样受权限与审计约束。
7. 禁止导出越权数据；权限源异常时 fail-closed。
8. 禁止导出任何 secret/token/cookie/Authorization 等敏感凭据。

## 8. 前端门禁要求（5.7）

1. 报表模块禁止写入口。
2. 禁止前端直连 ERPNext `/api/resource`。
3. 禁止裸 `fetch/axios` 绕过统一 API client。
4. 禁止 runtime codegen。
5. 禁止 Worker / dynamic import 加载不可信代码。
6. CSV / Excel 导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。
8. 必须提供 positive / negative fixtures，并覆盖：
   - 写方法（POST/PUT/PATCH/DELETE）
   - ERPNext `/api/resource`
   - internal/run-once/diagnostic 暴露
   - 裸 fetch/axios
   - runtime injection / Worker / dynamic import 绕过

## 9. 权限与审计要求（5.8）

### 9.1 动作权限

- `report:read`
- `report:export`
- `report:dashboard`
- `report:diagnostic`

### 9.2 资源权限字段

- `company`
- `item_code`
- `supplier`
- `customer`
- `warehouse`
- `work_order`
- `sales_order`
- `purchase_order`

### 9.3 审计事件

- read
- export
- diagnostic
- permission denied
- ERPNext unavailable
- cache stale served
- cache refresh failed

审计约束：

1. 安全审计与操作审计必须统一脱敏。
2. 未认证、越权、权限源不可用必须写安全审计。
3. diagnostic 仅管理员可见，普通用户路径必须阻断并审计。

## 10. 生产发布前置条件（5.9）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 只读联调通过。
5. 报表指标口径审计通过。
6. 前端门禁审计通过。
7. 权限隔离审计通过。
8. 导出安全审计通过。

## 11. 后端统一响应与失败语义要求

1. 报表与看板接口必须使用统一响应信封，不允许返回“200 + 空数据”伪成功来掩盖权限或依赖问题。
2. 后端处理顺序必须固定为：动作权限校验 -> 资源字段过滤 -> 业务查询/聚合 -> 响应序列化。
3. 任一关键依赖失败（权限源、ERPNext只读源、核心字段、聚合口径）必须 fail-closed 并返回结构化错误码。
4. 诊断能力仅限 `report:diagnostic` 且保持管理员/内部诊断边界，不得向普通前端泛化。
5. 所有错误返回必须脱敏，禁止泄露 token/password/secret/DSN/Authorization/Cookie 等敏感信息。

## 12. 结论边界

1. 本文档仅冻结报表与仪表盘总体设计，不包含接口和页面实现。
2. 本文档不代表 ERPNext 已联调。
3. 本文档不代表平台 required checks 已闭环。
4. 本文档不代表生产发布完成。
5. `TASK-019A` 正式通过后，仅允许进入 `TASK-019B`（生产进度看板设计）阶段。
6. `TASK-019A` 正式通过后，不允许直接进入任何报表实现任务（含看板实现、导出实现、诊断实现、缓存刷新实现）。
