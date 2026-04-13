# TASK-005 款式利润报表开发前基线盘点

- 任务编号：TASK-005A
- 模块：款式利润报表
- 版本：V1.0
- 更新时间：2026-04-13 23:40 CST
- 执行人：工程自动化代理（线程 B）
- 盘点范围：只读扫描与设计缺口分析（不写后端代码、不写前端代码、不建迁移、不新增接口）
- 阻塞声明：`TASK-004C13` GitHub 平台闭环未完成，`TASK-005B` 工程实现不得启动，`TASK-006` 继续阻塞。

---

## 0. 盘点方法与结论摘要

### 0.1 已读取的必需文档

1. `/Users/hh/Desktop/领意服装管理系统/README.md`
2. `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/00_总体架构概览.md`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/01_模块设计_BOM管理.md`
5. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md`
6. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/04_模块设计_工票车间管理.md`
7. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md`
8. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
9. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`

### 0.2 已扫描代码范围

- 后端：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models|schemas|routers|services`
- 迁移：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions`
- 测试：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests`
- 前端：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api|views|router|stores`

### 0.3 摘要结论

1. 当前仓库无 `style_profit` 相关后端模型、迁移、路由、服务和前端页面，`TASK-005` 尚未实现。
2. `TASK-001/002/003/004` 已形成可复用的 BOM、外发验货金额、工票工资、生产计划(SO/BOM/Work Order/Job Card)事实源。
3. 利润模块关键口径仍存在架构待决：销售收入（SO vs SI）、实际材料成本（Purchase Receipt vs Stock Ledger Entry）、外发扣款事实源（验货 vs 结算锁定）。
4. `TASK-004C13` 平台闭环未完成是硬门禁；在此之前仅允许做设计冻结与盘点，不允许进入 `TASK-005B` 工程实现。

---

## 1. 现有实现扫描结果

| 范围 | 是否存在利润相关实现 | 文件路径 | 可复用性 | 风险 |
| --- | --- | --- | --- | --- |
| 后端 `models` | 否（无 `ly_style_profit_*`） | `app/models/*.py` 仅有 `bom/subcontract/workshop/production` | 中 | 利润事实表需全新建模 |
| 后端 `routers` | 否（无 `/api/reports/style-profit`） | `app/routers` 仅有 `auth/bom/subcontract/workshop/production` | 低 | 路由与权限动作需新增 |
| 后端 `services` | 否（无 `style_profit_service`） | `app/services` 无利润计算服务 | 中 | 公式与快照策略需从零实现 |
| 后端迁移 | 否（无利润迁移） | `migrations/versions` 共 13 个，均非利润表 | 低 | 迁移链需新增并做空库/增量兼容 |
| 后端测试 | 否（无利润测试） | `tests/` 无 `style_profit` 测试文件 | 中 | 回归与审计门禁需从零补齐 |
| 前端 API | 否 | `src/api` 仅 `bom/subcontract/workshop/production/auth` | 中 | 报表 API 客户端需新增 |
| 前端页面 | 否 | `src/views` 无利润页面 | 中 | 列表/详情/对比页需新增 |
| 前端路由/权限 | 否 | `src/router/index.ts` 无利润路由；`src/stores/permission.ts` 无利润按钮权限 | 中 | 权限动作、菜单、按钮联动待补 |

### 1.1 关键字扫描结论

- `style_profit`：未命中业务代码（`app/`, `tests/`, `src/`）。
- `gross_margin`：未命中业务代码。
- `cost_allocation`：未命中业务代码。
- `profit`：未命中利润业务实现（仅文档语义层命中）。
- `Sales Order`：已在生产计划适配器与服务中落地读取与校验。
- `Purchase Receipt`：业务代码未命中。
- `Stock Ledger Entry`：业务代码未命中。
- `snapshot`：存在于 outbox/审计/生产物料检查快照语义，不是款式利润快照实现。

---

## 2. 上游依赖状态

| 依赖模块 | 当前状态 | 可用数据 | 缺口 | 是否阻塞 TASK-005B |
| --- | --- | --- | --- | --- |
| TASK-001 BOM 管理 | 已通过多轮审计整改 | BOM 主表/明细/工序、损耗率、工序单价、外发工序标记 | 标准采购单价口径未在 BOM 内固化 | 否（可先以候选口径推进） |
| TASK-002 外发加工管理 | 核心链路完成；`TASK-006` 仍阻塞 | 外发单、回料、验货、`gross/deduction/net`、结算锁定操作日志 | GitHub 平台证据门禁未清零，结算后续联动仍受阻 | 部分阻塞（可做设计，不可跨到 TASK-006） |
| TASK-003 工票/车间管理 | 已完成多轮审计整改 | 工票净数量、日薪汇总、工价档案、Job Card 同步事实 | 成本归集到“款式/订单”的分摊规则未定义 | 否（可通过设计补口径） |
| TASK-004 生产计划集成 | 业务契约完成，平台闭环待管理员动作 | SO/BOM/计划/Work Order/Job Card 映射、material snapshot | `TASK-004C13` 未闭环（remote/push/hosted runner/required check） | 是（硬阻塞工程实现） |
| ERPNext Sales Order | 已有读取适配器 | `docstatus/status/company/customer/items` | 收入口径是否采用 SO 仍待决 | 否（可作为候选事实源） |
| ERPNext Purchase Receipt | 代码侧未接入 | 无 | 实际材料成本缺少读取适配器和映射规则 | 是（若选择 PR 口径） |
| ERPNext Stock Ledger Entry | 代码侧未接入 | 无 | 实际材料成本/库存价值口径无法落地 | 是（若选择 SLE 口径） |

> 结论：`TASK-005B` 在流程门禁上被 `TASK-004C13` 阻塞；在数据门禁上受“实际材料成本口径未接入 ERPNext PR/SLE”影响。

---

## 3. 利润口径候选

| 成本/收入项 | 候选公式 | 数据来源 | 精度风险 | 是否需要架构决策 |
| --- | --- | --- | --- | --- |
| 销售收入 | `sales_qty * sales_unit_price` 或订单行金额汇总 | ERPNext `Sales Order Item` | SO 非最终确认收入，存在折让偏差 | 是 |
| 标准材料成本 | `BOM展开需求量 * 标准采购单价` | `ly_apparel_bom_item` + 标准价来源（待定） | 标准价来源不统一 | 是 |
| 标准工序成本 | `BOM工序单价 * 订单数量` | `ly_bom_operation` | 工序单价版本、生效期影响 | 是 |
| 实际材料成本 | `实际入库数量 * 实际入库单价` 或库存价值变动汇总 | ERPNext `Purchase Receipt` 或 `Stock Ledger Entry` | PR 与 SLE口径差异大 | 是（P1） |
| 实际工票成本 | `工票净数量 * 实际工价` | `ys_workshop_ticket` / `ys_workshop_daily_wage` | 跨款式、跨工单分摊规则缺失 | 是 |
| 实际外发加工费 | `验货金额净额`（优先用 inspection net） | `ly_subcontract_inspection.net_amount` | 与结算锁定口径可能不一致 | 是 |
| 扣款金额 | `rejected_qty * deduction_amount_per_piece` | `ly_subcontract_inspection.deduction_amount` | 扣款后调整/反冲口径待定 | 是 |
| 制造费用/其他费用 | 按规则分摊（数量/金额/工时） | 待建 `cost_allocation_rule` + 财务来源 | 分摊基准不一致 | 是（P2） |
| 利润金额 | `销售收入 - 实际总成本 - 其他分摊` | 汇总快照 | 依赖上游口径一致性 | 是 |
| 利润率 | `利润金额 / 销售收入` | 汇总快照 | 收入为 0 时边界处理 | 否（实现细则即可） |

建议优先冻结：收入口径、实际材料成本口径、外发扣款事实源口径。

---

## 4. 数据模型草案（仅草案，不建表）

### 4.1 `ly_schema.ly_style_profit_snapshot`

- 用途：利润快照主表（不可变版本）。
- 关键字段（建议）：
  - `id`, `snapshot_no`, `company`, `item_code`, `sales_order`, `sales_order_item`
  - `revenue_amount`, `standard_material_cost`, `standard_process_cost`
  - `actual_material_cost`, `actual_workshop_cost`, `actual_subcontract_cost`
  - `deduction_amount`, `other_allocated_cost`, `profit_amount`, `profit_rate`
  - `formula_version`, `as_of_date`, `filters_json`, `status`
  - `idempotency_key`, `request_hash`, `created_by`, `created_at`
- 唯一约束建议：
  - `uk_snapshot_no(snapshot_no)`
  - `uk_snapshot_idempotency(company, idempotency_key)`
- 索引建议：
  - `idx_snapshot_company_date(company, as_of_date)`
  - `idx_snapshot_item(item_code, as_of_date)`
  - `idx_snapshot_sales_order(sales_order, sales_order_item)`
- 数据来源：ERPNext SO + BOM + 工票 + 外发验货 +（后续）PR/SLE。
- 快照策略：必须不可变（重算生成新快照，不覆盖历史）。

### 4.2 `ly_schema.ly_style_profit_detail`

- 用途：快照明细分解（收入、材料、工票、外发、分摊项）。
- 关键字段（建议）：
  - `id`, `snapshot_id`, `line_type`, `cost_type`, `source_type`, `source_no`
  - `item_code`, `qty`, `unit_price`, `amount`, `currency`
  - `formula_code`, `meta_json`, `created_at`
- 唯一约束建议：
  - `uk_snapshot_line(snapshot_id, line_type, source_type, source_no, item_code)`
- 索引建议：
  - `idx_detail_snapshot(snapshot_id)`
  - `idx_detail_source(source_type, source_no)`
  - `idx_detail_item(item_code)`
- 数据来源：BOM/工票/外发/ERPNext 单据映射。
- 快照策略：与主快照同生命周期，不可单独变更。

### 4.3 `ly_schema.ly_cost_allocation_rule`

- 用途：费用分摊规则配置（制造/管理/其他）。
- 关键字段（建议）：
  - `id`, `rule_no`, `company`, `cost_type`, `allocation_basis`
  - `scope_json`（适用品类/款式/订单条件）
  - `effective_from`, `effective_to`, `status`, `version_no`
  - `created_by`, `created_at`, `updated_at`
- 唯一约束建议：
  - `uk_rule_no(rule_no)`
  - `uk_rule_effective(company, cost_type, version_no)`
- 索引建议：
  - `idx_rule_company_status(company, status)`
  - `idx_rule_effective(effective_from, effective_to)`
- 数据来源：运营/财务配置。
- 快照策略：规则版本不可覆盖历史快照解释。

---

## 5. API 草案（仅草案，不实现）

| 接口 | 方法 | 路径 | 用途 | 幂等要求 | 权限动作 |
| --- | --- | --- | --- | --- | --- |
| 款式利润列表 | GET | `/api/reports/style-profit/` | 分页查询快照摘要/筛选结果 | 不适用 | `style_profit:read` |
| 生成利润快照 | POST | `/api/reports/style-profit/snapshot` | 生成不可变快照 | 需要 `idempotency_key`（`company + idempotency_key`） | `style_profit:snapshot_create` |
| 快照详情 | GET | `/api/reports/style-profit/{snapshot_id}` | 查看快照明细分解 | 不适用 | `style_profit:read` |
| 快照对比 | GET | `/api/reports/style-profit/compare` | 标准 vs 实际、多快照差异 | 不适用 | `style_profit:read` |

### 5.1 `POST /snapshot` 幂等建议

- 必须包含 `idempotency_key`。
- 同 key + 同请求语义：返回首次快照结果。
- 同 key + 不同请求语义：返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。

---

## 6. 权限与审计缺口

1. 利润读取动作权限尚未定义（建议：`style_profit:read`）。
2. 利润快照生成动作权限尚未定义（建议：`style_profit:snapshot_create`）。
3. 资源级权限建议维度：`company + item_code + sales_order`。
4. 权限来源必须沿用 ERPNext `Role/User Permission` 聚合；不可新增静态权限为生产权威。
5. 权限源不可用必须 fail closed（503）。
6. 401/403/503 必须写安全审计（与现有模块一致）。
7. 快照生成、重算、回放命中必须写操作审计（含 before/after 摘要）。
8. 日志与错误信封须延续现有脱敏规范（禁止 token/cookie/authorization/sql 原文泄露）。

---

## 7. 前端页面缺口

| 检查项 | 现状 | 结论 |
| --- | --- | --- |
| 利润报表页面 | `src/views` 无 style profit 页面 | 缺口 |
| 利润报表路由 | `src/router/index.ts` 无 `/reports/style-profit` | 缺口 |
| API client | `src/api` 无 style profit client | 缺口 |
| 统一请求客户端 | 已有 `src/api/request.ts` | 可复用 |
| 筛选项 | 尚无利润页，不存在筛选实现 | 需新增（日期/款式/SO/客户/公司） |
| 导出/打印/钻取 | 无 | 需在 TASK-005G 设计与实现 |

---

## 8. 风险清单

| 风险等级 | 风险 | 影响 | 建议处理 |
| --- | --- | --- | --- |
| P1 | 收入口径选 `Sales Order` 还是 `Sales Invoice` 未冻结 | 利润会偏离财务确认口径 | `TASK-005B` 冻结唯一口径并记录 ADR |
| P1 | 实际材料成本取 `Purchase Receipt` 还是 `Stock Ledger Entry` 未实现 | 无法计算“实际材料成本” | 先做适配器 PoC，对比样本单据后冻结 |
| P1 | 外发扣款取“验货事实”还是“结算锁定事实”未冻结 | 报表与结算对不上 | 定义报表版本口径；结算口径独立字段标识 |
| P1 | `TASK-004C13` 平台闭环未完成 | `TASK-005B` 工程启动违反门禁 | 先完成 C13 平台动作与审计复核 |
| P2 | 工票撤销/补数可能影响历史快照一致性 | 历史利润不可复现 | 快照不可变 + 明细留痕 + 口径版本化 |
| P2 | 快照重算是否覆盖旧快照未定义 | 历史报表审计风险 | 强制“重算新快照，不覆盖旧快照” |
| P2 | 多公司资源权限跨单据链路复杂 | 越权读取利润数据风险 | 统一 `company/item_code/sales_order` 资源过滤策略 |
| P3 | 费用分摊规则（制造/管理费）来源不统一 | 结果可解释性弱 | V1 可先不纳入或固定规则，后续迭代 |

---

## 9. TASK-005B 拆分建议（只建议，不实现）

1. `TASK-005B` 利润口径设计冻结
   - 输出：口径 ADR、字段字典、边界案例、版本策略。
2. `TASK-005C` 后端数据模型与迁移
   - 输出：`snapshot/detail/rule` 三表迁移与索引约束。
3. `TASK-005D` 利润快照计算服务
   - 输出：计算编排、快照落库、幂等与重算策略。
4. `TASK-005E` 权限、审计与错误信封
   - 输出：动作权限、资源权限、安全审计、操作审计、错误码。
5. `TASK-005F` 前端利润报表页面
   - 输出：列表、详情、对比、筛选、权限按钮联动。
6. `TASK-005G` 报表导出与打印
   - 输出：导出格式、打印模板、审计水印与数据范围限制。
7. `TASK-005H` 回归测试与审计封版
   - 输出：后端/前端自动化测试、审计复核材料、上线门禁清单。

---

## 10. 启动门禁结论

- 当前结论：`TASK-005A`（盘点）可完成。  
- 当前禁止：`TASK-005B`（工程实现）不得启动。  
- 放行条件：`TASK-004C13` GitHub 平台闭环 + 审计复审通过。  
- 在放行前：`TASK-006` 继续阻塞。
