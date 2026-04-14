# TASK-005F1 利润 SLE 归属与外发来源阻断整改工程任务单

- 任务编号：TASK-005F1
- 模块：款式利润报表
- 版本：V1.0
- 更新时间：2026-04-14 13:50 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F 审计不通过，审计意见书第 103 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审，复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复 TASK-005F 审计发现的 3 个高危和 1 个中危问题：

1. SLE 不得由 Adapter 默认补 `docstatus=1/status=submitted`。
2. SLE 实际材料成本不得仅凭 BOM 物料白名单计入利润。
3. 外发成本来源不得静默返回空列表。
4. 补齐关键反向测试矩阵。

核心原则：BOM 白名单只能证明“这是本款 BOM 允许材料”，不能证明“这条库存流水属于本销售订单或生产工单”。实际材料成本必须同时满足“材料范围合法”和“销售/生产归属可信”。

## 2. 审计阻断问题

| 编号 | 严重程度 | 问题 | 必须整改 |
| --- | --- | --- | --- |
| P1-1 | 高 | Adapter 为 SLE 缺失状态默认补 `docstatus=1/status=submitted/is_cancelled=false` | 不得伪造状态；缺可信状态必须 unresolved 或 fail closed |
| P1-2 | 高 | SLE 命中 BOM 物料白名单后，即使无 sales_order/work_order 桥接也计入利润 | BOM 白名单只能做材料范围过滤，不能做归属桥接 |
| P1-3 | 高 | 外发成本 `load_subcontract_rows()` 静默返回空列表 | 必须读取外发候选事实；无法可信归属时落 unresolved，不得吞掉 |
| P2-1 | 中 | 缺少关键反向测试 | 补 SLE 缺状态、无桥接、外发候选未采集、ERPNext 结构异常等反向测试 |

## 3. 本任务允许修改范围

### 3.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`（仅限 source_map/unresolved 原因字段需要）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`

### 3.2 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止修改利润公式
- 禁止把 SLE 无归属桥接数据强行计入利润
- 禁止把外发成本缺失伪装成 0 成本

## 4. 架构决策：SLE 归属可信链路

### 4.1 SLE 入账必须同时满足两个条件

一条 `Stock Ledger Entry` 要计入 `actual_material_cost`，必须同时满足：

1. 材料范围合法：`item_code` 必须命中 active/default BOM 的 `allowed_material_item_codes`。
2. 归属桥接可信：必须能证明该 SLE 属于当前 `company + item_code + sales_order` 或当前 `company + item_code + work_order`。

只满足 BOM 物料白名单，不允许计入利润。

### 4.2 允许的归属桥接字段

按优先级识别以下桥接：

| 优先级 | 桥接方式 | 入账条件 |
| --- | --- | --- |
| 1 | SLE 明确带 `sales_order` 或 `custom_ly_sales_order` | 值必须等于 selector.sales_order |
| 2 | SLE 明确带 `work_order` 或 `custom_ly_work_order` | 值必须等于 selector.work_order，或能通过本地生产计划/Work Order 映射反查到 selector.sales_order + selector.item_code + selector.company |
| 3 | SLE 的 `voucher_type/voucher_no` 指向 ERPNext Work Order | voucher_no 必须能通过可信 Work Order adapter 或本地生产计划映射到 selector.sales_order + selector.item_code + selector.company |
| 4 | SLE 明确带 `production_plan` 或 `custom_ly_production_plan` | 必须能通过本地生产计划映射到 selector.sales_order + selector.item_code + selector.company |
| 5 | SLE 明确带 `job_card` 或 `custom_ly_job_card` | 必须能通过 Job Card/工票链路映射到 selector.work_order，再映射到 selector.sales_order + selector.item_code + selector.company |

如果以上桥接均不存在或解析失败，该 SLE 必须写入 source_map 为 unresolved，`include_in_profit=false`，不得计入 `actual_material_cost`。

### 4.3 SLE 状态口径

1. Adapter 不得为 SLE 补 `docstatus=1`。
2. Adapter 不得为 SLE 补 `status=submitted`。
3. Adapter 不得为 SLE 补 `is_cancelled=false`。
4. ERPNext 返回缺少 `docstatus` 或取消字段时，该 SLE 不可信，必须 unresolved 或 fail closed。
5. `docstatus != 1` 的 SLE 不得计入利润。
6. `is_cancelled=true` 或状态为 cancelled/canceled 的 SLE 不得计入利润。
7. ERPNext 整体返回结构异常、非 JSON、缺 `data` 列表、分页异常时，必须返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE`，不得用空列表吞掉。

## 5. 外发来源整改要求

### 5.1 不得静默空返回

`load_subcontract_rows()` 不允许继续直接 `return []`。

必须执行以下其中一种策略：

1. 能读取到可信外发事实：返回 mapped 候选行。
2. 读取到候选外发事实但缺桥接：返回 unresolved 行，`include_in_profit=false`。
3. 外发表/字段不足以判断：返回明确 fail closed 错误或 unresolved，不得静默 0 成本。
4. 数据库读取失败：返回 `DATABASE_READ_FAILED`。

### 5.2 外发可信归属条件

外发成本计入利润必须满足：

1. `LySubcontractOrder.company == selector.company`
2. `LySubcontractOrder.item_code == selector.item_code`
3. 必须存在以下任一桥接：
   - `sales_order == selector.sales_order`
   - `work_order == selector.work_order`
   - `production_plan` 可映射到 selector.sales_order + selector.item_code + selector.company
   - 外发单关联的 BOM/Work Order 能映射回当前销售订单和款式
4. 结算锁定金额优先。
5. 未结算时，验货净额兜底，并受 `include_provisional_subcontract` 控制。
6. 已取消、已释放、跨公司、跨款式、缺桥接的外发事实不得计入利润。

### 5.3 如果现有外发表缺桥接字段

如果当前外发表没有 `sales_order/work_order/production_plan` 等可信桥接字段，则本任务不得假装完成外发成本采集。

处理方式：

1. 对同公司同款式同期间的外发候选事实，生成 unresolved source_map。
2. `include_in_profit=false`。
3. `mapping_status=unresolved`。
4. `unresolved_reason=SUBCONTRACT_SCOPE_UNTRUSTED` 或同等稳定错误码。
5. snapshot 标记为 incomplete 或 unresolved_count 增加。
6. 工程师在交付说明中明确“外发成本因缺销售/生产桥接暂未纳入”。

## 6. source_map 要求

### 6.1 SLE unresolved 原因码

至少支持以下稳定原因：

| 原因码 | 场景 |
| --- | --- |
| `SLE_STATUS_UNTRUSTED` | 缺 `docstatus`、缺取消字段、状态未知 |
| `SLE_SCOPE_UNTRUSTED` | 命中 BOM 物料，但无 sales_order/work_order/production_plan/job_card 桥接 |
| `SLE_MATERIAL_NOT_IN_BOM` | SLE 物料不在 BOM 白名单 |
| `SLE_CANCELLED` | SLE 已取消 |
| `SLE_DRAFT_OR_UNSUBMITTED` | SLE 非提交态 |

### 6.2 外发 unresolved 原因码

至少支持以下稳定原因：

| 原因码 | 场景 |
| --- | --- |
| `SUBCONTRACT_SCOPE_UNTRUSTED` | 外发事实缺 sales_order/work_order/production_plan 桥接 |
| `SUBCONTRACT_CANCELLED` | 外发单取消 |
| `SUBCONTRACT_COMPANY_MISMATCH` | 公司不匹配 |
| `SUBCONTRACT_ITEM_MISMATCH` | 款式不匹配 |
| `SUBCONTRACT_UNSETTLED_EXCLUDED` | 未结算且 `include_provisional_subcontract=false` |

## 7. 测试要求

必须补齐以下测试：

### 7.1 SLE 状态测试

1. ERPNext SLE 缺 `docstatus` 时，不计入 `actual_material_cost`。
2. ERPNext SLE 缺 `status` 或 `is_cancelled` 时，不得被 Adapter 默认补成 submitted。
3. `docstatus=0` 的 SLE 不计入利润。
4. `docstatus=2` 或 cancelled SLE 不计入利润。
5. 缺状态 SLE 必须出现在 source_map unresolved 或触发 fail closed，不能静默计入。

### 7.2 SLE 归属桥接测试

1. 同公司、同期间、同 BOM 物料，但无 `sales_order/work_order` 桥接，不计入利润。
2. 同公司、同期间、同 BOM 物料，`sales_order` 等于 selector.sales_order，计入利润。
3. 同公司、同期间、同 BOM 物料，`sales_order` 指向其他订单，不计入利润。
4. 同公司、同期间、同 BOM 物料，`work_order` 可映射到当前销售订单，计入利润。
5. `work_order` 映射失败或映射到其他订单，不计入利润。
6. BOM 白名单命中但桥接缺失时，snapshot 必须 incomplete 或 unresolved_count 增加。

### 7.3 外发来源测试

1. 外发候选事实存在但缺桥接时，不得静默返回空列表。
2. 外发缺桥接时生成 unresolved，且不计入利润。
3. 外发有可信 company + item_code + sales_order/work_order 桥接时，按结算金额计入。
4. 未结算外发仅在 `include_provisional_subcontract=true` 时按验货净额兜底。
5. `include_provisional_subcontract=false` 时未结算外发不计入，并生成稳定原因。
6. 外发跨公司、跨款式、取消单不得计入利润。

### 7.4 结构异常与审计测试

1. ERPNext 返回非 JSON，返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE`。
2. ERPNext 返回缺 `data` 列表，返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE`。
3. ERPNext 分页超过限制但未完整读取时，不得静默漏数。
4. 失败路径不创建 snapshot/detail/source_map 半成品。
5. 创建失败必须写操作失败审计。
6. 响应和日志不得泄露 Authorization、Cookie、Token、Secret、Password。

## 8. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_api_source_adapter.py tests/test_style_profit_source_collector.py tests/test_style_profit_source_mapping.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_api.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 9. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 .github 02_源码 07_后端/lingyi_service/migrations 03_需求与设计/02_开发计划/TASK-006*
```

预期：无 TASK-005F1 以外改动。

## 10. 验收标准

□ Adapter 不再给 SLE 默认补 `docstatus=1/status=submitted/is_cancelled=false`。  
□ SLE 缺可信状态不得计入利润。  
□ SLE 命中 BOM 物料但无销售/生产桥接不得计入利润。  
□ BOM 白名单只作为材料范围，不作为归属证明。  
□ 有可信 `sales_order/work_order/production_plan/job_card` 桥接的 SLE 才能计入实际材料成本。  
□ 外发来源不再静默空返回。  
□ 外发候选事实缺桥接时生成 unresolved，不计入利润。  
□ 外发有可信桥接时按结算优先、验货兜底口径采集。  
□ source_map 能追溯 SLE 和外发未纳入原因。  
□ 补齐 SLE 状态、SLE 无桥接、外发未采集、ERPNext 结构异常反向测试。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 11. 交付说明要求

工程师交付时必须说明：

1. SLE 归属桥接支持哪些字段。
2. SLE 缺桥接时如何进入 source_map unresolved。
3. 外发来源是否已能可信纳入；如果不能，必须说明缺少哪个桥接字段。
4. 新增测试清单和验证结果。
5. 禁改扫描结果。
6. 未进入前端、未进入迁移、未进入 TASK-006。
