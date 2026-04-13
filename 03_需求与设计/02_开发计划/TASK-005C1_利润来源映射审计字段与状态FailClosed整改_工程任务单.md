# TASK-005C1 利润来源映射审计字段与状态 Fail Closed 整改工程任务单

- 任务编号：TASK-005C1
- 模块：款式利润报表 / 来源映射整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 01:28 CST
- 作者：技术架构师
- 审计来源：TASK-005C 审计结论有条件通过，高危 2 / 中危 3
- 前置依赖：TASK-005C 已交付并完成审计；ADR-079、ADR-080 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.5；`ADR-081`
- 任务边界：只修复 TASK-005C 审计问题；不得进入 TASK-005D 利润快照计算服务；不得注册 API；不得修改前端；不得进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005C1
模块：利润来源映射审计字段与状态 Fail Closed 整改
优先级：P0（审计阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭 TASK-005C 审计指出的 5 个问题：source_map 审计字段缺失、来源状态缺失默认放行、snapshot 复核字段缺失、费用分摊默认状态错误、SLE 款式/材料编码过滤语义错误。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/[timestamp]_alter_style_profit_c1_fields.py（如现有迁移不可原地修改时使用）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005D / TASK-006 文件

【整改项 1：source_map 审计追溯字段补齐】

必须把 `ly_style_profit_source_map` 调整为可追溯到具体快照和明细的审计表。

必备字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `snapshot_id` | bigint | 非空，FK -> `ly_style_profit_snapshot.id` |
| `detail_id` | bigint | 可空，FK -> `ly_style_profit_detail.id`；未入利润的 excluded/unresolved 来源可为空 |
| `company` | varchar(140) | 非空 |
| `sales_order` | varchar(140) | 可空 |
| `style_item_code` | varchar(140) | 非空，利润报表款式成品编码 |
| `source_item_code` | varchar(140) | 可空，来源行物料/款式编码；SLE 场景为材料编码 |
| `source_system` | varchar(64) | 非空，限定 `erpnext/fastapi/manual` |
| `source_doctype` | varchar(140) | 非空，如 `Sales Invoice`、`Sales Order`、`Stock Ledger Entry` |
| `source_name` | varchar(140) | 非空，来源单据号 |
| `source_line_no` | varchar(140) | 非空，无行号时用空字符串 |
| `source_status` | varchar(64) | 非空，保存 `submitted/draft/cancelled/unknown/...` |
| `qty` | numeric(18,6) | 可空 |
| `unit_rate` | numeric(18,6) | 可空 |
| `amount` | numeric(18,6) | 非空，默认 0 |
| `currency` | varchar(16) | 可空 |
| `warehouse` | varchar(140) | 可空 |
| `work_order` | varchar(140) | 可空 |
| `job_card` | varchar(140) | 可空 |
| `posting_date` | date/datetime | 可空 |
| `include_in_profit` | boolean | 非空，默认 false |
| `mapping_status` | varchar(32) | `mapped/unresolved/excluded` |
| `unresolved_reason` | varchar(128) | 可空 |
| `raw_ref` | JSON/JSONB | 可空，必须脱敏 |
| `created_at` | datetime | 非空 |

约束与索引：
1. `snapshot_id` 必须 FK 到 snapshot。
2. `detail_id` 必须 FK 到 detail，可空。
3. 唯一约束改为 `snapshot_id + source_system + source_doctype + source_name + source_line_no`。
4. 禁止继续使用全局 `company + source_type + source_name + source_line_id` 唯一约束，避免新快照复用同一来源时冲突。
5. 增加索引：`snapshot_id + mapping_status`、`company + sales_order + style_item_code`、`source_system + source_doctype + source_name`。
6. `raw_ref` 不得包含 Authorization、Cookie、token、password、secret、原始 SQL。

【整改项 2：_is_submitted() 必须 fail closed】

`StyleProfitSourceService._is_submitted()` 必须改为缺状态不放行。

规则：
1. `docstatus == 1` 才可判定为 submitted。
2. `docstatus` 存在但不是 1，必须返回 false。
3. `docstatus` 缺失时，只有 `status` 在显式白名单时才可返回 true。
4. `docstatus` 和 `status` 都缺失时，必须返回 false。
5. `status` 为 draft、cancelled、canceled、closed、void、return、unknown 或空字符串时必须 false。
6. `is_cancelled` 为 true 时必须 false。
7. 不允许“只要不是 draft/cancelled 就通过”的旧逻辑。
8. 被拒绝来源必须能在 DTO 或 source_map 中记录 `source_status_unknown` / `not_submitted_or_cancelled`。

建议 status-only 白名单：
- `submitted`
- `paid`
- `unpaid`
- `overdue`
- `to bill`
- `to deliver`
- `to deliver and bill`
- `completed`

【整改项 3：snapshot 复核字段补齐】

`ly_style_profit_snapshot` 必须补齐 ADR-079 request_hash 和复核所需字段：

| 字段 | 类型建议 | 规则 |
| --- | --- | --- |
| `from_date` | date/datetime | 可空；有查询期间时必须保存 |
| `to_date` | date/datetime | 可空；有查询期间时必须保存 |
| `revenue_mode` | varchar(32) | 非空，默认 `actual_first` |
| `unresolved_count` | int | 非空，默认 0 |

约束与索引：
1. `revenue_mode` 限定 `actual_first/actual_only/estimated_only`。
2. 增加索引：`company + item_code + from_date + to_date`。
3. `request_hash` 测试必须覆盖 `from_date/to_date/revenue_mode` 已纳入 hash。

【整改项 4：费用分摊规则默认 disabled】

`ly_cost_allocation_rule.status` 默认值必须改为 `disabled`。

规则：
1. 模型 server_default 改为 `disabled`。
2. 迁移默认值改为 `disabled`。
3. 测试确认新建规则不传 status 时为 `disabled`。
4. `active` 仍保留为未来状态，但 TASK-005C1 不允许启用费用分摊。

【整改项 5：SLE 款式编码与材料编码语义拆分】

当前利润报表入参 `item_code` 表示款式成品编码，不等于 SLE 材料行的 `item_code`。不得用 SLE `row.item_code != style_item_code` 直接排除材料成本。

必须调整为：
1. `resolve_material_cost_sources()` 入参语义明确为 `style_item_code`。
2. SLE 行的 `item_code` 必须映射为 `source_item_code` 或 `material_item_code`。
3. 若 SLE 行能通过 `work_order / production_plan_id / sales_order` 归属到目标款式/订单，则允许纳入，即使 SLE `source_item_code != style_item_code`。
4. 若提供 BOM 物料集合 `allowed_material_item_codes`，则 SLE `source_item_code` 必须在集合内；不在集合内时排除并标记 `material_item_not_in_bom`。
5. 若既没有工单/生产计划/销售订单桥，也没有 BOM 物料集合可验证，则不得纳入，标记 `unable_to_link_order_or_material_scope`。
6. `Purchase Receipt` 仍只能进入 reference/excluded，不得进入 actual_material_cost。

【必须补充测试】

至少新增或修改以下测试：
1. source_map 模型包含 `snapshot_id/detail_id/source_system/source_doctype/source_status/qty/amount/style_item_code/source_item_code/raw_ref`。
2. source_map 唯一约束为 `snapshot_id + source_system + source_doctype + source_name + source_line_no`。
3. 同一来源单据行允许出现在两个不同 snapshot 中。
4. `_is_submitted({})` 返回 false。
5. `_is_submitted({'status': ''})` 返回 false。
6. `_is_submitted({'status': 'Unknown'})` 返回 false。
7. `_is_submitted({'docstatus': 1})` 返回 true。
8. `_is_submitted({'docstatus': 0})` 返回 false。
9. `_is_submitted({'docstatus': 1, 'is_cancelled': true})` 返回 false。
10. snapshot 模型包含 `from_date/to_date/revenue_mode/unresolved_count`。
11. request_hash 包含 `from_date/to_date/revenue_mode`，仍排除 `created_at/operator/request_id`。
12. cost_allocation_rule 默认 `status=disabled`。
13. SLE `source_item_code=MAT-A`、报表 `style_item_code=STYLE-A`、work_order 归属匹配时可纳入 actual_material_cost。
14. SLE 无桥接且不在 BOM 物料集合时不得纳入，标记 `unable_to_link_order_or_material_scope`。
15. SLE 在 BOM 物料集合外时排除，标记 `material_item_not_in_bom`。
16. Purchase Receipt 不直接计入 actual_material_cost。

【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

静态边界检查：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers
```

【验收标准】
□ `_is_submitted()` 缺少 `docstatus/status` 时 fail closed。
□ source_map 字段、FK、唯一约束、索引符合本任务单。
□ snapshot 已补 `from_date/to_date/revenue_mode/unresolved_count`。
□ cost_allocation_rule 默认 `disabled`。
□ SLE 款式编码与材料编码语义已拆分，真实材料行不会因不等于款式编码被误排除。
□ Purchase Receipt 仍不进入 actual_material_cost。
□ 定向测试、全量 pytest、unittest、py_compile 通过。
□ 未注册利润 API，未修改前端，未进入 TASK-005D/TASK-006。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
