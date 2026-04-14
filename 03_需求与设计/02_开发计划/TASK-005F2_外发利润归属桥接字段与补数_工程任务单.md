# TASK-005F2 外发利润归属桥接字段与补数工程任务单

- 任务编号：TASK-005F2
- 模块：款式利润报表 / 外发加工管理
- 版本：V1.0
- 更新时间：2026-04-14 14:15 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F1 审计通过，审计意见书第 104 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审，复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

补齐外发加工事实与款式利润之间的可信归属桥接字段，让外发成本可以在满足 `company + item_code + sales_order/work_order/production_plan` 可信归属时计入款式利润；历史外发事实无法证明归属时，必须保留为 unresolved，不得伪装为 0 成本或强行计入利润。

本任务解决 TASK-005F1 审计通过后保留的核心风险：外发来源已经“可见且会 unresolved”，但因外发候选缺 `sales_order/work_order/production_plan_id` 桥接，外发成本不能宣称已完整计入利润。

## 2. 架构决策

采用“补桥接字段 + 安全补数 + 利润 Adapter 启用桥接”的方案，不采用“只在前端提示利润不完整”的软方案。

原因：款式利润报表面向财务和经营分析，外发加工费是服装工厂核心成本。长期让外发成本 unresolved 会导致利润系统性偏高，不能作为财务分析依据。

## 3. 本任务允许修改范围

### 3.1 允许新建

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py`

### 3.2 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py`（仅限传递/读取桥接字段，不得进入 TASK-006 对账单）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`

### 3.3 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止进入加工厂对账单功能实现
- 禁止修改利润公式
- 禁止把无法证明归属的外发成本强行计入利润
- 禁止 destructive migration，禁止 drop/recreate 外发表

## 4. 数据模型要求

### 4.1 外发单主表新增字段

在 `ly_schema.ly_subcontract_order` 增加以下字段：

| 字段 | 类型 | 是否可空 | 说明 |
| --- | --- | --- | --- |
| `sales_order` | String(140) | 可空 | ERPNext Sales Order 编号 |
| `sales_order_item` | String(140) | 可空 | ERPNext Sales Order Item 行标识 |
| `production_plan_id` | BigInteger | 可空 | 本地 `ly_production_plan.id` |
| `work_order` | String(140) | 可空 | ERPNext Work Order 编号 |
| `job_card` | String(140) | 可空 | ERPNext Job Card 编号，若外发工序来自工序卡 |
| `profit_scope_status` | String(32) | 非空，默认 `unresolved` | `ready/unresolved/ambiguous/invalid` |
| `profit_scope_error_code` | String(64) | 可空 | 归属失败原因 |
| `profit_scope_resolved_at` | DateTime(timezone=True) | 可空 | 最近一次归属解析时间 |

### 4.2 外发验货表新增快照字段

在 `ly_schema.ly_subcontract_inspection` 增加以下字段，作为验货事实发生时的利润归属快照：

| 字段 | 类型 | 是否可空 | 说明 |
| --- | --- | --- | --- |
| `sales_order` | String(140) | 可空 | 从外发单继承的 Sales Order |
| `sales_order_item` | String(140) | 可空 | 从外发单继承的 Sales Order Item |
| `production_plan_id` | BigInteger | 可空 | 从外发单继承的生产计划 ID |
| `work_order` | String(140) | 可空 | 从外发单继承的 Work Order |
| `job_card` | String(140) | 可空 | 从外发单继承的 Job Card |
| `profit_scope_status` | String(32) | 非空，默认 `unresolved` | 验货事实利润归属状态 |
| `profit_scope_error_code` | String(64) | 可空 | 验货事实归属失败原因 |

要求：

1. 新增验货记录时，必须从外发单复制上述桥接字段，形成事实快照。
2. 后续外发单桥接字段变化，不得自动重写历史验货事实；历史事实只能通过明确补数工具修复。
3. 外发结算锁定/释放不得修改这些桥接快照字段。

### 4.3 可选传播字段

如当前实现中 `ly_subcontract_receipt` 是验货前置事实，也允许同步增加相同桥接字段；但验收重点以 `ly_subcontract_order` 和 `ly_subcontract_inspection` 为准。

## 5. 索引要求

必须新增以下索引：

1. `idx_ly_subcontract_profit_scope_order(company, item_code, sales_order, work_order, profit_scope_status)`
2. `idx_ly_subcontract_inspection_profit_scope(company, item_code, sales_order, work_order, settlement_status, inspected_at)`
3. `idx_ly_subcontract_profit_plan(production_plan_id, work_order)`
4. 如增加 receipt 桥接字段，补 `idx_ly_subcontract_receipt_profit_scope(company, item_code, sales_order, work_order)`

## 6. 迁移要求

迁移文件：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`

必须满足：

1. 新库从迁移链自举成功。
2. 老库重复执行幂等升级不报错。
3. 只允许 `add_column/create_index`，不得 drop/recreate 外发表。
4. 默认 `profit_scope_status='unresolved'`。
5. 对已有数据不得强制填 sales_order/work_order。
6. downgrade 如项目已有规范则按规范实现；若无规范，至少不得破坏已有数据。

## 7. 新建/更新外发单规则

### 7.1 新建外发单

`SubcontractCreateRequest` 增加可选字段：

- `sales_order`
- `sales_order_item`
- `production_plan_id`
- `work_order`
- `job_card`

规则：

1. 新建外发单允许缺桥接字段，但必须标记 `profit_scope_status='unresolved'`，`profit_scope_error_code='SUBCONTRACT_SCOPE_UNTRUSTED'`。
2. 如果传入 `production_plan_id`，必须校验该生产计划存在，且 `company/item_code/bom_id` 与外发单一致。
3. 如果传入 `work_order`，必须能在 `ly_production_work_order_link` 中找到，并反查到同一 `company/item_code/sales_order`。
4. 如果传入 `sales_order`，必须与生产计划或 Work Order 映射一致；不能只信任前端传入。
5. 校验通过后，`profit_scope_status='ready'`。
6. 校验失败返回统一错误信封，不得落库半成品。

### 7.2 生产计划创建外发单

如果已有或后续存在从生产计划/工序创建外发单的入口，该入口必须自动写入：

- `sales_order`
- `sales_order_item`
- `production_plan_id`
- `work_order`
- `job_card`（如有）

不得让生产计划链路产生 unresolved 外发单。

## 8. 历史补数规则

新增 `SubcontractProfitScopeBackfillService`。

### 8.1 dry_run

必须支持 dry_run，且 dry_run 必须真正只读：

1. 不修改外发单。
2. 不修改验货记录。
3. 不写操作审计或补数日志，除非已有明确 dry-run 日志表且不落业务表。
4. 调用方后续 commit 也不得产生持久化变化。

### 8.2 execute

只在唯一可信匹配时回填：

1. 若外发单 `company + item_code + bom_id` 只能匹配一个 `LyProductionPlan`，且该计划能映射出唯一 Work Order，可回填。
2. 若匹配多个生产计划，必须保持 unresolved，原因 `SUBCONTRACT_SCOPE_AMBIGUOUS`。
3. 若没有匹配生产计划，保持 unresolved，原因 `SUBCONTRACT_SCOPE_UNTRUSTED`。
4. 若生产计划读取失败，返回 `DATABASE_READ_FAILED`，不得静默降级。
5. 若 Work Order 映射读取失败，返回 `DATABASE_READ_FAILED`。
6. 回填外发单后，允许回填同一外发单下未结算或未锁定的 inspection 桥接字段；已结算/已锁定 inspection 默认不得自动改，除非任务单另行明确。
7. execute 必须写操作审计。
8. 写失败必须 rollback 并返回 `DATABASE_WRITE_FAILED`。

## 9. 款式利润 Adapter 更新要求

TASK-005F2 完成后，款式利润外发来源采集规则调整为：

1. 只纳入 `profit_scope_status='ready'` 且匹配 `company + item_code + sales_order/work_order` 的外发验货事实。
2. 外发验货记录如果有 `sales_order/work_order` 快照字段，以 inspection 快照字段为准。
3. inspection 缺桥接但 order 已 ready 时，可以读取 order 桥接作为候选，但 source_map 必须记录 `bridge_source='subcontract_order'`。
4. inspection/order 都缺桥接时，生成 unresolved source_map，原因 `SUBCONTRACT_SCOPE_UNTRUSTED`，不计入利润。
5. 结算锁定金额优先。
6. 未结算时按验货净额兜底，但必须受 `include_provisional_subcontract` 控制。
7. `include_provisional_subcontract=false` 时，未结算外发不计入利润，并记录 `SUBCONTRACT_UNSETTLED_EXCLUDED`。

## 10. API 与审计要求

1. 外发创建/更新桥接字段必须沿用 TASK-002 的鉴权、动作权限、资源权限和安全审计。
2. 款式利润 API 鉴权、资源权限、安全审计、操作审计不得回退。
3. 补数 execute 必须写操作审计。
4. 权限拒绝必须写安全审计。
5. 错误响应统一 `{code, message, data/detail}`。
6. 不得泄露 Authorization/Cookie/Token/Secret/Password。

## 11. 测试要求

必须补齐：

### 11.1 迁移和模型测试

1. 新表链迁移可创建桥接字段和索引。
2. 已存在表重复迁移不报错。
3. 默认 `profit_scope_status='unresolved'`。
4. inspection 创建时复制 order 桥接字段。

### 11.2 外发创建测试

1. 缺桥接字段创建外发单成功但 `profit_scope_status='unresolved'`。
2. 传入合法 `production_plan_id/work_order/sales_order` 时，状态为 `ready`。
3. 传入跨公司生产计划返回 403 或业务错误，不落库。
4. 传入跨款式生产计划返回业务错误，不落库。
5. 传入不匹配 Work Order 返回业务错误，不落库。

### 11.3 补数测试

1. dry_run 后 `session.new/dirty/deleted` 均为空，commit 后无变化。
2. 唯一匹配生产计划时可回填 order 桥接字段。
3. 多个匹配生产计划时保持 unresolved，原因 `SUBCONTRACT_SCOPE_AMBIGUOUS`。
4. 无匹配时保持 unresolved，原因 `SUBCONTRACT_SCOPE_UNTRUSTED`。
5. 数据库读取失败返回 `DATABASE_READ_FAILED`。
6. 写失败 rollback，返回 `DATABASE_WRITE_FAILED`。

### 11.4 利润外发采集测试

1. ready 外发验货匹配当前 sales_order/work_order 时计入外发成本。
2. unresolved 外发验货不计入外发成本，但写 source_map unresolved。
3. 外发跨销售订单不计入当前利润。
4. 外发跨 Work Order 不计入当前利润。
5. 未结算外发在 `include_provisional_subcontract=false` 时不计入。
6. 未结算外发在 `include_provisional_subcontract=true` 时按验货净额兜底。
7. 已结算/锁定金额优先于验货临时金额。
8. source_map 能显示桥接来源和未纳入原因。

## 12. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_subcontract_profit_scope_bridge.py tests/test_style_profit_subcontract_bridge.py tests/test_style_profit_api_source_adapter.py tests/test_style_profit_source_collector.py tests/test_style_profit_snapshot_calculation.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 13. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 .github 02_源码 03_需求与设计/02_开发计划/TASK-006*
```

预期：无前端、`.github`、`02_源码`、TASK-006 改动。

## 14. 验收标准

□ 外发单具备 `sales_order/sales_order_item/production_plan_id/work_order/job_card/profit_scope_status/profit_scope_error_code` 字段。  
□ 外发验货事实具备对应桥接快照字段。  
□ 迁移可自举、可幂等升级，不破坏历史数据。  
□ 新建外发单缺桥接时标记 unresolved，不强行计入利润。  
□ 新建外发单带合法生产计划/工单桥接时标记 ready。  
□ 历史补数 dry_run 真正只读。  
□ 历史补数 execute 只在唯一可信匹配时回填。  
□ 多匹配或无匹配保持 unresolved。  
□ 款式利润只纳入 ready 且匹配当前 sales_order/work_order 的外发成本。  
□ 外发 unresolved 会进入 source_map，不再让财务误以为外发成本为 0。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 15. 交付说明要求

工程师交付时必须说明：

1. 新增字段和索引清单。
2. 迁移执行策略和幂等策略。
3. 外发单创建时如何解析 production_plan/work_order/sales_order。
4. 历史补数 dry_run 和 execute 结果。
5. 款式利润外发成本纳入规则。
6. unresolved 原因码清单。
7. 测试命令和结果。
8. 禁改扫描结果。
9. 未进入前端、未进入 TASK-006。
