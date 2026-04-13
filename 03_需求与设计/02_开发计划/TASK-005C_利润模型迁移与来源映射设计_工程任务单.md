# TASK-005C 利润模型迁移与来源映射设计工程任务单

- 任务编号：TASK-005C
- 模块：款式利润报表 / 模型迁移与来源映射设计
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 00:30 CST
- 作者：技术架构师
- 审计来源：审计意见书第 85 份，TASK-005B1 通过；TASK-005B/B1 可作为 TASK-005C 前置设计依据
- 前置依赖：TASK-005B/B1 利润口径冻结通过；ADR-079 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.4；`ADR-080`
- 任务边界：只做后端数据模型、迁移、来源映射适配器骨架和测试；不注册 API，不实现利润计算服务，不实现前端页面，不进入 TASK-005D/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005C
模块：利润模型迁移与来源映射设计
优先级：P0（数据地基）
════════════════════════════════════════════════════════════════════════════

【任务目标】
基于 ADR-079 创建款式利润报表 V1 的后端数据模型、Alembic 迁移和 ERPNext/本地来源映射骨架，为 TASK-005D 利润快照计算服务提供稳定数据地基。

【允许新增】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/[timestamp]_create_style_profit_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/__init__.py（如项目需要导出模型）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限测试建表/夹具需要）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-006 文件

【必须实现的数据表】

## 1. `ly_schema.ly_style_profit_snapshot`

用途：利润快照主表，不可变。

必备字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `id` | bigint / int | 主键 |
| `snapshot_no` | varchar(64) | 全局唯一 |
| `company` | varchar(140) | 非空，资源权限字段 |
| `sales_order` | varchar(140) | 可空但 V1 推荐非空 |
| `item_code` | varchar(140) | 非空，资源权限字段 |
| `revenue_status` | varchar(32) | `actual/estimated/unresolved` |
| `estimated_revenue_amount` | numeric(18,6) | 默认 0 |
| `actual_revenue_amount` | numeric(18,6) | 默认 0 |
| `revenue_amount` | numeric(18,6) | 实际优先，否则预计 |
| `standard_material_cost` | numeric(18,6) | 默认 0 |
| `standard_operation_cost` | numeric(18,6) | 默认 0 |
| `standard_total_cost` | numeric(18,6) | 标准材料 + 标准工序 |
| `actual_material_cost` | numeric(18,6) | SLE 口径 |
| `actual_workshop_cost` | numeric(18,6) | 工票净数 × 工价快照 |
| `actual_subcontract_cost` | numeric(18,6) | 结算优先、验货兜底 |
| `allocated_overhead_amount` | numeric(18,6) | V1 固定 0 |
| `actual_total_cost` | numeric(18,6) | 实际总成本 |
| `profit_amount` | numeric(18,6) | 收入 - 实际总成本 |
| `profit_rate` | numeric(18,6), nullable | 收入为 0 时 null |
| `snapshot_status` | varchar(32) | `complete/incomplete/failed` |
| `allocation_status` | varchar(32) | V1 固定 `not_enabled` |
| `formula_version` | varchar(32) | V1 固定 `STYLE_PROFIT_V1` |
| `include_provisional_subcontract` | boolean | 是否纳入未结算验货净额 |
| `idempotency_key` | varchar(128) | 非空 |
| `request_hash` | varchar(64) | SHA-256 hex |
| `created_by` | varchar(140) | 当前用户 |
| `created_at` | datetime/timestamp | 创建时间 |

必备约束：

1. `uk_style_profit_snapshot_no`：`snapshot_no` 唯一。
2. `uk_style_profit_snapshot_idempotency`：`company + idempotency_key` 唯一。
3. `ck_style_profit_revenue_status`：限定 `actual/estimated/unresolved`。
4. `ck_style_profit_snapshot_status`：限定 `complete/incomplete/failed`。
5. `ck_style_profit_allocation_status`：限定 `not_enabled/enabled`。

必备索引：

1. `idx_style_profit_company_item_order`：`company, item_code, sales_order`。
2. `idx_style_profit_created_at`：`created_at`。
3. `idx_style_profit_status`：`snapshot_status`。
4. `idx_style_profit_formula_version`：`formula_version`。

## 2. `ly_schema.ly_style_profit_detail`

用途：利润快照明细，保存收入、材料、工票、外发、扣款、unresolved 项。

必备字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `id` | bigint / int | 主键 |
| `snapshot_id` | bigint / int | FK 到 snapshot |
| `line_no` | int | 明细行号 |
| `cost_type` | varchar(64) | `revenue/standard_material/standard_operation/actual_material/workshop/subcontract/deduction/overhead/unresolved` |
| `source_type` | varchar(64) | `Sales Order/Sales Invoice/Stock Ledger Entry/BOM/Workshop Ticket/Subcontract Inspection/Subcontract Settlement` |
| `source_name` | varchar(140) | 来源单据号 |
| `item_code` | varchar(140) | 可空 |
| `qty` | numeric(18,6) | 可空 |
| `unit_rate` | numeric(18,6) | 可空 |
| `amount` | numeric(18,6) | 非空，允许负数 |
| `formula_code` | varchar(64) | 公式编码 |
| `is_unresolved` | boolean | 默认 false |
| `unresolved_reason` | varchar(128) | 可空 |
| `raw_ref` | json/text | 脱敏后的来源摘要，不得存敏感头 |
| `created_at` | datetime/timestamp | 创建时间 |

必备约束/索引：

1. `fk_style_profit_detail_snapshot_id`。
2. `idx_style_profit_detail_snapshot`：`snapshot_id, line_no`。
3. `idx_style_profit_detail_cost_type`：`cost_type`。
4. `idx_style_profit_detail_source`：`source_type, source_name`。

## 3. `ly_schema.ly_style_profit_source_map`

用途：保存利润快照来源映射，避免后续计算服务无法追溯 SO/SI/SLE/工票/外发来源。

必备字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `id` | bigint / int | 主键 |
| `company` | varchar(140) | 非空 |
| `sales_order` | varchar(140) | 非空 |
| `item_code` | varchar(140) | 非空 |
| `production_plan_id` | bigint / int | 可空 |
| `work_order` | varchar(140) | 可空 |
| `job_card` | varchar(140) | 可空 |
| `source_type` | varchar(64) | 来源类型 |
| `source_name` | varchar(140) | 来源名称 |
| `source_line_id` | varchar(140) | 来源行 ID，可空 |
| `include_in_profit` | boolean | 默认 true |
| `mapping_status` | varchar(32) | `mapped/unresolved/excluded` |
| `unresolved_reason` | varchar(128) | 可空 |
| `created_at` | datetime/timestamp | 创建时间 |

必备唯一约束/索引：

1. `uk_style_profit_source_map_source`：`company + source_type + source_name + coalesce(source_line_id,'')` 唯一。
2. `idx_style_profit_source_map_order_item`：`company, sales_order, item_code`。
3. `idx_style_profit_source_map_work_order`：`work_order`。
4. `idx_style_profit_source_map_status`：`mapping_status`。

## 4. `ly_schema.ly_cost_allocation_rule`

用途：V1 只预留表结构，可不启用分摊。

必备字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `id` | bigint / int | 主键 |
| `company` | varchar(140) | 非空 |
| `rule_name` | varchar(140) | 非空 |
| `cost_type` | varchar(64) | `manufacturing_overhead/admin/other` |
| `allocation_basis` | varchar(64) | `qty/amount/work_hour/manual` |
| `status` | varchar(32) | `draft/active/disabled` |
| `created_by` | varchar(140) | 创建人 |
| `created_at` | datetime/timestamp | 创建时间 |
| `updated_at` | datetime/timestamp | 更新时间 |

V1 规则：
1. 表可以预留。
2. 默认不得影响利润计算。
3. 利润快照固定 `allocated_overhead_amount=0`、`allocation_status=not_enabled`。

【来源映射必须设计清楚】

## 1. Sales Invoice / Sales Order 行级映射

必须输出函数/类骨架，但不实现完整利润计算：

```text
StyleProfitSourceService.resolve_revenue_sources(company, sales_order, item_code)
```

映射规则：
1. 优先查 submitted Sales Invoice 行，匹配 `sales_order + item_code`。
2. 若无 Sales Invoice，回退 submitted Sales Order 行，匹配 `sales_order + item_code`。
3. draft/cancelled 单据排除。
4. 多张 Sales Invoice 时按行金额汇总，不得重复计入 Sales Order。
5. 映射结果必须带 `source_type/source_name/source_line_id/revenue_status`。

## 2. Stock Ledger Entry 纳入/排除规则

必须输出函数/类骨架：

```text
StyleProfitSourceService.resolve_material_cost_sources(company, sales_order, item_code, work_order=None)
```

纳入规则：
1. 只纳入 submitted 库存单据产生的 SLE。
2. 只纳入能通过 `work_order / production_plan / stock_entry / voucher_no` 关联到目标订单或工单的材料消耗。
3. 金额使用 `abs(stock_value_difference)`。
4. SLE 必须保留 `voucher_type/voucher_no/item_code/warehouse/actual_qty/stock_value_difference/posting_date` 摘要。

排除规则：
1. draft/cancelled 来源单据。
2. 无法归属订单/工单的 SLE。
3. 成品销售出库或非生产材料消耗，除非后续 ADR 明确纳入。
4. Purchase Receipt 不直接计入实际材料成本。

无法确定时：
1. 生成 `actual_material_cost_unresolved` 来源映射。
2. 不静默按 0 处理。

## 3. 本地来源映射

必须输出骨架查询策略：
1. BOM 标准材料与工序来源。
2. Workshop Ticket / Daily Wage 实际工票来源。
3. Subcontract Inspection / Settlement 实际外发来源。
4. Production Plan / Work Order / Job Card 关联桥。

【必须测试】

新增测试至少覆盖：
1. snapshot 模型字段存在。
2. snapshot 唯一约束：`snapshot_no`。
3. snapshot 幂等唯一约束：`company + idempotency_key`。
4. detail 可关联 snapshot。
5. source_map 唯一约束：`company + source_type + source_name + source_line_id`。
6. cost_allocation_rule 默认不影响利润，模型字段存在。
7. request_hash 不包含 `created_at/operator/request_id`。
8. Sales Invoice 优先于 Sales Order 的映射规则测试。
9. 无 Sales Invoice 时回退 Sales Order 的映射规则测试。
10. draft/cancelled Sales Invoice 不计入实际收入。
11. Stock Ledger Entry 使用 `abs(stock_value_difference)`。
12. Purchase Receipt 不直接计入 actual_material_cost。
13. 无法关联订单/工单的 SLE 标记 unresolved。
14. 敏感字段不进入 raw_ref。

【禁止事项】
- 禁止注册 `/api/reports/style-profit/` 路由。
- 禁止实现 `POST /api/reports/style-profit/snapshot`。
- 禁止实现完整利润计算服务 `style_profit_service.py`。
- 禁止新增前端页面或 API client。
- 禁止修改 `app/main.py`。
- 禁止调用 ERPNext 写接口。
- 禁止进入 TASK-005D/TASK-006。

【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

如环境缺依赖，必须记录真实失败原因，不得伪造通过。

【验收标准】
□ 已新增 `app/models/style_profit.py`。
□ 已新增 `app/schemas/style_profit.py`，仅包含模型/来源映射 DTO，不包含 API 请求处理逻辑。
□ 已新增 `app/services/style_profit_source_service.py`，只做来源映射骨架和纯读取策略，不做完整利润快照计算。
□ 已新增 Alembic 迁移，创建 `ly_style_profit_snapshot/detail/source_map/cost_allocation_rule`。
□ 迁移支持空库创建，并尽量保持幂等升级。
□ snapshot/detail/source_map/cost_allocation_rule 字段、约束、索引符合本任务单。
□ Sales Invoice / Sales Order 行级映射规则有测试。
□ Stock Ledger Entry 纳入/排除规则有测试。
□ Purchase Receipt 不直接计入 actual_material_cost 有测试。
□ `git diff --name-only -- 06_前端 .github 02_源码` 无变更。
□ 未注册路由，未修改 `app/main.py`。
□ 未进入 TASK-005D/TASK-006。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
