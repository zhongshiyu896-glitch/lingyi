# TASK-005C2 利润来源默认不纳入与字段契约收口整改工程任务单

- 任务编号：TASK-005C2
- 模块：款式利润报表 / 来源映射二次整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 01:59 CST
- 作者：技术架构师
- 审计来源：TASK-005C1 审计结论有条件通过，高危 1 / 中危 3
- 前置依赖：TASK-005C1 已交付并完成审计；ADR-081 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.6；`ADR-082`
- 任务边界：只修复 TASK-005C1 剩余问题；不得进入 TASK-005D 利润快照计算服务；不得注册 API；不得修改前端；不得进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005C2
模块：利润来源默认不纳入与字段契约收口整改
优先级：P0（审计阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭 TASK-005C1 审计剩余 4 个问题：`include_in_profit` 默认值仍为 true、source_map 字段 nullable/长度/source_status 非空约束未完全对齐、复合索引缺失、status-only 白名单需要架构收口。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/[timestamp]_alter_style_profit_c2_contracts.py（如不能原地修改迁移时使用）
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

【整改项 1：include_in_profit 默认 false】

`ly_style_profit_source_map.include_in_profit` 是利润来源 fail-closed 开关，默认必须为 false。

必须整改：
1. SQLAlchemy 模型中 `include_in_profit` 必须 `nullable=False, server_default=false`。
2. Alembic 迁移中 `include_in_profit` 必须 `nullable=False, server_default=false`。
3. Pydantic DTO 中 `include_in_profit` 默认值必须为 false。
4. source mapping 构造函数中，所有新来源初始值必须为 false。
5. 只有来源同时满足提交状态、资源归属、材料范围、未排除规则后，代码才允许显式设置 true。
6. `mapping_status` 默认建议为 `unresolved`，不得默认 `mapped`。
7. 测试必须覆盖数据库默认值和 DTO 默认值。

【整改项 2：source_map 字段契约收口】

`ly_style_profit_source_map` 字段必须按以下契约收口，模型、迁移、schema 三处一致。

| 字段 | 类型/长度 | nullable | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `snapshot_id` | bigint/int | false | 无 | FK -> snapshot.id |
| `detail_id` | bigint/int | true | null | FK -> detail.id |
| `company` | varchar(140) | false | 无 | 公司 |
| `sales_order` | varchar(140) | true | null | 销售订单 |
| `style_item_code` | varchar(140) | false | 无 | 款式成品编码 |
| `source_item_code` | varchar(140) | true | null | 来源物料/款式编码 |
| `source_system` | varchar(64) | false | 无 | `erpnext/fastapi/manual` |
| `source_doctype` | varchar(140) | false | 无 | 来源 DocType |
| `source_name` | varchar(140) | false | 无 | 来源单据号 |
| `source_line_no` | varchar(140) | false | 空字符串 | 来源行号 |
| `source_status` | varchar(64) | false | `unknown` | 来源状态；unknown 不允许纳入利润 |
| `qty` | numeric(18,6) | true | null | 数量 |
| `unit_rate` | numeric(18,6) | true | null | 单价 |
| `amount` | numeric(18,6) | false | 0 | 金额 |
| `currency` | varchar(16) | true | null | 币种 |
| `warehouse` | varchar(140) | true | null | 仓库 |
| `work_order` | varchar(140) | true | null | 工单 |
| `job_card` | varchar(140) | true | null | 工序卡 |
| `posting_date` | date/datetime | true | null | 过账日期 |
| `include_in_profit` | boolean | false | false | 默认不纳入利润 |
| `mapping_status` | varchar(32) | false | `unresolved` | `mapped/unresolved/excluded` |
| `unresolved_reason` | varchar(128) | true | null | 未解析原因 |
| `raw_ref` | JSON/JSONB | true | null | 脱敏来源快照 |
| `created_at` | datetime | false | now | 创建时间 |

必须补约束：
1. `source_system IN ('erpnext','fastapi','manual')`。
2. `mapping_status IN ('mapped','unresolved','excluded')`。
3. `source_status` 非空，不允许空字符串；空状态统一写 `unknown`。
4. `include_in_profit=true` 时，`mapping_status` 必须为 `mapped`。
5. `mapping_status != 'mapped'` 时，`include_in_profit` 必须为 false。

【整改项 3：复合索引补齐】

必须补齐以下索引，模型和迁移一致：
1. `idx_ly_style_profit_source_map_snapshot_status`：`snapshot_id, mapping_status`。
2. `idx_ly_style_profit_source_map_scope`：`company, sales_order, style_item_code`。
3. `idx_ly_style_profit_source_map_source_lookup`：`source_system, source_doctype, source_name`。
4. `idx_ly_style_profit_source_map_detail`：`detail_id`。

唯一约束必须保持：
- `uk_ly_style_profit_source_map_snapshot_source`：`snapshot_id, source_system, source_doctype, source_name, source_line_no`。

【整改项 4：status-only 白名单收口】

`docstatus` 是首选事实字段。status-only 只能作为 ERPNext API 投影缺少 docstatus 时的受控兜底，不允许通用放行。

统一规则：
1. `_is_submitted(row, source_doctype=None)` 必须优先判断 `docstatus`。
2. `docstatus` 存在时，只有 `int(docstatus) == 1` 返回 true。
3. `docstatus` 存在且不是 1，直接 false，不再看 status。
4. `is_cancelled=true` 直接 false。
5. `docstatus` 缺失时，必须识别 `source_doctype`；未知 doctype 一律 false。
6. `Stock Ledger Entry` 不允许 status-only 放行；必须有 `docstatus=1`。
7. `Purchase Receipt` 不允许进入利润成本，status-only 不得让它 include_in_profit=true。
8. `Sales Invoice` status-only 白名单仅允许：`paid`、`unpaid`、`overdue`、`partly paid`。
9. `Sales Order` status-only 白名单仅允许：`to deliver and bill`、`to bill`、`to deliver`、`completed`。
10. `closed`、`draft`、`cancelled`、`canceled`、`void`、`return`、`unknown`、空字符串一律 false。
11. 状态比较必须大小写不敏感，前后空白必须 trim。
12. 被 status-only 接受的来源必须在 DTO/source_map 中保留 `source_status` 原值或规范化值，便于审计。
13. 被拒绝来源必须记录 `not_submitted_or_cancelled` 或 `source_status_unknown`。

【必须补充测试】

至少新增或修改以下测试：
1. `include_in_profit` 数据库默认值为 false。
2. `include_in_profit` DTO 默认值为 false。
3. 新构造 source_map/source DTO 初始 `include_in_profit=false`。
4. mapped 通过完整校验后才显式 `include_in_profit=true`。
5. `mapping_status=unresolved/excluded` 时不能 `include_in_profit=true`。
6. `source_status` 缺失时保存为 `unknown`，且不得纳入利润。
7. `source_system/source_doctype/source_status` 非空约束测试。
8. `source_system` 枚举约束测试。
9. 四个复合索引存在性测试。
10. 唯一约束 `snapshot_id + source_system + source_doctype + source_name + source_line_no` 存在性测试。
11. 同一来源行在不同 snapshot 中可重复写入。
12. Sales Invoice `status=Paid` 且无 docstatus 时可通过。
13. Sales Invoice `status=Completed` 且无 docstatus 时不可通过。
14. Sales Order `status=Completed` 且无 docstatus 时可通过。
15. Sales Order `status=Closed` 且无 docstatus 时不可通过。
16. Stock Ledger Entry 无 docstatus 时不可通过，即使 status=Submitted。
17. Stock Ledger Entry `docstatus=1` 时可通过。
18. `docstatus=0,status=Paid` 必须 false。
19. `is_cancelled=true,docstatus=1` 必须 false。
20. Purchase Receipt 仍不进入 `actual_material_cost`。

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
□ `include_in_profit` 模型、迁移、DTO 默认值均为 false。
□ `mapping_status` 默认不为 mapped，默认建议 unresolved。
□ source_map nullable、长度、枚举、非空约束与任务单一致。
□ source_map 四个复合索引已补齐。
□ status-only 白名单按 doctype 收口，Stock Ledger Entry 不允许 status-only 放行。
□ Purchase Receipt 仍不进入 actual_material_cost。
□ 定向测试、全量 pytest、unittest、py_compile 通过。
□ 未注册利润 API，未修改前端，未进入 TASK-005D/TASK-006。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
