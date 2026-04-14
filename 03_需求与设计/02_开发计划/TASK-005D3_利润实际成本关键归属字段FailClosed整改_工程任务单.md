# TASK-005D3 利润实际成本关键归属字段 Fail Closed 整改工程任务单

- 任务编号：TASK-005D3
- 模块：款式利润报表 / 利润快照计算服务审计整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 10:56 CST
- 作者：技术架构师
- 审计来源：审计意见书第 94 份，TASK-005D2 有条件通过但仍有 1 个 P1 必改项
- 前置依赖：TASK-005D2 已交付并完成第 94 份审计；TASK-005E/API 层未放行；TASK-006 继续阻塞
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V1.2；`ADR-088`
- 任务边界：只修复 workshop/subcontract 关键归属字段缺失时的 fail closed 逻辑和测试；不注册 API；不改前端；不新增迁移；不进入 TASK-005E/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D3
模块：利润实际成本关键归属字段 Fail Closed 整改
优先级：P0（高危阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复第 94 份审计指出的高危问题：workshop/subcontract 来源缺 `company` 或缺 `item_code/style_item_code` 时，不得仅凭 `sales_order` 匹配就 mapped 计入利润。

【架构决策】
TASK-005D V1 中，workshop/subcontract 实际成本来源必须能验证 `company + item_code + sales_order` 三者全部匹配后才允许纳入利润。缺任一关键归属字段时，默认 fail closed 为 unresolved；只有通过可信桥接补全并验证三者全部匹配后，才允许 mapped。

可信桥接范围限定：
1. `work_order` 可作为桥接，但必须能解析出并验证 `company + item_code + sales_order`。
2. `job_card` 可作为桥接，但必须能解析出并验证 `company + item_code + sales_order`。
3. `production_plan_id` 可作为桥接，但必须能解析出并验证 `company + item_code + sales_order`。
4. `subcontract_order` 可作为桥接，但必须能解析出并验证 `company + item_code + sales_order`。
5. 当前 TASK-005D3 若没有真实桥接查询能力，不得假设桥接可信；必须 unresolved。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005E 文件
- 任意 TASK-006 文件

【必须修复】

## 1. P1：缺 company 不得仅凭 sales_order mapped

当前问题：workshop/subcontract 来源行缺 `company` 时，只要 `sales_order` 匹配当前快照，就会 mapped 并计入成本。

整改要求：
1. 来源行缺 `company` 时，默认 unresolved。
2. 缺 `company` 不得仅凭 `sales_order` mapped。
3. 缺 `company` 不得计入 `actual_workshop_cost` 或 `actual_subcontract_cost`。
4. 缺 `company` 必须写 source_map，`mapping_status=unresolved`。
5. 缺 `company` 必须 `include_in_profit=false`。
6. 缺 `company` 必须写明确原因，建议 `company_scope_missing`。
7. 若通过可信桥接补全 company，必须同时验证补全后的 company、item_code、sales_order 全部匹配，才允许 mapped。
8. 当前无真实桥接查询能力时，不得以 `work_order/job_card/subcontract_order` 字段存在为由直接 mapped。

## 2. P1：缺 item_code/style_item_code 不得仅凭 sales_order mapped

当前问题：workshop/subcontract 来源行缺 `item_code/style_item_code` 时，只要 `sales_order` 匹配当前快照，就会 mapped 并计入成本。

整改要求：
1. 来源行缺 `item_code/style_item_code` 时，默认 unresolved。
2. 缺 `item_code/style_item_code` 不得仅凭 `sales_order` mapped。
3. 缺 `item_code/style_item_code` 不得计入 `actual_workshop_cost` 或 `actual_subcontract_cost`。
4. 缺 `item_code/style_item_code` 必须写 source_map，`mapping_status=unresolved`。
5. 缺 `item_code/style_item_code` 必须 `include_in_profit=false`。
6. 缺 `item_code/style_item_code` 必须写明确原因，建议 `item_scope_missing`。
7. 若通过可信桥接补全 item_code，必须同时验证补全后的 company、item_code、sales_order 全部匹配，才允许 mapped。
8. 一个 Sales Order 多款式时，缺 item_code 的来源不得纳入任何单款式利润快照。

## 3. scope helper 必须拆分硬字段完整性和桥接匹配

整改要求：
1. 将 scope 校验拆成两步：`validate_required_scope_fields()` 与 `match_scope_bridge()`，或实现等价清晰逻辑。
2. 先校验硬字段：company、item_code/style_item_code、sales_order。
3. 硬字段存在但冲突时，必须 excluded。
4. 硬字段缺失时，必须 unresolved，除非可信桥接可补全并验证三字段。
5. 桥接只用于补全缺失字段或辅助验证，不得覆盖明确冲突字段。
6. helper 返回结果必须能区分：`mapped`、`excluded`、`unresolved`。
7. helper 返回 reason 必须可写入 source_map.unresolved_reason。

【防回潮要求】
1. 不得回退 TASK-005D2 已修复内容：错 company/item/sales_order 排除、保存点回滚兜底、sales_order 强制非空。
2. 不得回退 TASK-005D1 已修复内容：request_hash 来源输入、收入 unresolved、异常 SLE unresolved、缺工价 unresolved、真实 source_status、idempotency_key 长度校验。
3. 不得降低 TASK-005C1/C2 的状态 fail closed 和 include_in_profit=false 默认规则。
4. 不得恢复 Purchase Receipt 直接计入 actual_material_cost。
5. 不得注册 `/api/reports/style-profit/`。
6. 不得进入 TASK-005E/API 层。
7. 不得进入 TASK-006。

【必须新增或补齐测试】
1. 工票缺 company，即使 sales_order 匹配，也不得计入 `actual_workshop_cost`。
2. 工票缺 company 时写 unresolved source_map，`include_in_profit=false`，reason=`company_scope_missing` 或等价明确原因。
3. 工票缺 item_code/style_item_code，即使 sales_order 匹配，也不得计入 `actual_workshop_cost`。
4. 工票缺 item_code/style_item_code 时写 unresolved source_map，`include_in_profit=false`，reason=`item_scope_missing` 或等价明确原因。
5. 外发缺 company，即使 sales_order 匹配，也不得计入 `actual_subcontract_cost`。
6. 外发缺 company 时写 unresolved source_map，`include_in_profit=false`，reason=`company_scope_missing` 或等价明确原因。
7. 外发缺 item_code/style_item_code，即使 sales_order 匹配，也不得计入 `actual_subcontract_cost`。
8. 外发缺 item_code/style_item_code 时写 unresolved source_map，`include_in_profit=false`，reason=`item_scope_missing` 或等价明确原因。
9. 工票 company + item_code + sales_order 全匹配时仍可计入成本。
10. 外发 company + item_code + sales_order 全匹配时仍可计入成本。
11. 工票/外发明确错 company、错 item_code、错 sales_order 仍不得计入成本。
12. 缺关键字段导致 unresolved 时，snapshot_status=incomplete，unresolved_count 增加。
13. 保存点回滚兜底测试仍通过。
14. sales_order 强制非空测试仍通过。
15. request_hash 来源输入测试仍通过。
16. 禁改扫描确认未注册 API、未改前端、未新增迁移、未进入 TASK-005E/TASK-006。

【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py tests/test_style_profit_service.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_snapshot_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【禁改扫描】

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-005E' || true
```

要求：
1. 前两个禁改扫描必须无输出。
2. 第三个命令不得出现 TASK-006 文件。
3. 第四个命令不得出现 TASK-005E 文件。

【验收标准】
□ workshop/subcontract 缺 company 时不得 mapped，不得计入利润。
□ workshop/subcontract 缺 item_code/style_item_code 时不得 mapped，不得计入利润。
□ 缺关键归属字段时写 unresolved source_map，include_in_profit=false，reason 明确。
□ company + item_code + sales_order 三者全部可验证匹配时才允许 mapped。
□ 错 company、错 item_code、错 sales_order 的既有测试继续通过。
□ 保存点回滚、sales_order 强制非空、request_hash 来源输入等 D1/D2 修复项未回退。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-005E/TASK-006。
□ 工程师会话日志已追加执行记录。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
