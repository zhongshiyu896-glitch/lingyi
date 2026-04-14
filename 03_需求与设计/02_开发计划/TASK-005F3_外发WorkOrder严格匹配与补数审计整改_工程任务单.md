# TASK-005F3 外发 Work Order 严格匹配与补数审计整改工程任务单

- 任务编号：TASK-005F3
- 模块：款式利润报表 / 外发加工管理
- 版本：V1.0
- 更新时间：2026-04-14 14:55 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F2 审计不通过，审计意见书第 105 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复 TASK-005F2 审计发现的 1 个高危和 3 个中危问题：

1. 外发成本在 `selector.work_order` 存在时必须严格匹配当前 Work Order。
2. 外发行缺失 `profit_scope_status` 必须 fail closed。
3. 外发来源期间过滤必须使用业务验货时间 `inspected_at`，不能使用系统 `created_at`。
4. 历史补数 execute 必须写操作审计，审计失败必须阻断并 rollback。

## 2. 报表粒度冻结

款式利润快照支持两个粒度：

| selector 字段 | 快照粒度 | 外发成本纳入规则 |
| --- | --- | --- |
| `sales_order + item_code`，不传 `work_order` | 销售订单 + 款式汇总 | 可纳入同一 `company + sales_order + item_code` 下所有 ready 外发成本 |
| `sales_order + item_code + work_order` | 工单级快照 | 必须同时匹配 `company + sales_order + item_code + work_order`，不能只靠同 SO 同款纳入 |

强制规则：只要请求/selector 带 `work_order`，外发成本必须匹配该 `work_order`。同一销售订单、同一款式但不同 Work Order 的外发成本必须排除或 unresolved，不得计入当前 Work Order 快照。

## 3. 本任务允许修改范围

### 3.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`（仅限复用现有操作审计接口，不得重构）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py`

### 3.2 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止新增或修改迁移文件，除非审计官明确要求
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止修改利润公式
- 禁止把错 Work Order 的外发成本计入当前 Work Order 快照

## 4. 必改问题 1：Work Order 严格匹配

### 4.1 问题

当前逻辑在 `company + item_code + sales_order` 匹配后提前 `mapped`，导致 `_match_scope_bridge()` 中的 `work_order` mismatch 校验不会执行。结果是同销售订单、同款式、不同 Work Order 的外发成本可能被计入当前 Work Order 快照。

### 4.2 修复要求

1. 抽出纯函数，例如 `match_subcontract_profit_scope(row, selector)`。
2. 匹配顺序必须为：
   - 先校验 `profit_scope_status == ready`。
   - 再校验 `company`。
   - 再校验 `item_code`。
   - 再校验 `sales_order`。
   - 如果 selector.work_order 非空，必须校验 `work_order`。
3. selector.work_order 非空时：
   - `row.work_order == selector.work_order`：允许继续金额口径判断。
   - `row.work_order` 为空但 `production_plan_id/job_card/subcontract_order` 可可信反查到 selector.work_order：允许继续金额口径判断。
   - `row.work_order` 为空且无法反查：unresolved，`SUBCONTRACT_WORK_ORDER_UNTRUSTED`。
   - `row.work_order` 非空且不等于 selector.work_order：excluded 或 unresolved，`SUBCONTRACT_WORK_ORDER_MISMATCH`，不得计入。
4. selector.work_order 为空时：
   - 只做销售订单 + 款式汇总。
   - 允许纳入同一 `company + sales_order + item_code` 下 ready 外发成本。
   - 如果外发行 work_order 指向其他 sales_order 或其他 item_code，仍不得纳入。
5. 不允许在 `sales_order` 匹配后提前返回 `mapped`，必须根据 selector 是否要求 work_order 继续校验。

## 5. 必改问题 2：profit_scope_status 缺失 fail closed

### 5.1 问题

当前服务层只有在 `row_profit_scope_status` 非空且不等于 `ready` 时才 unresolved。若未来调用直接传入缺 `profit_scope_status` 的外发行，只要 `company/item_code/sales_order` 匹配，就可能被计入利润。

### 5.2 修复要求

1. 外发来源必须满足 `profit_scope_status == 'ready'` 才能计入利润。
2. `profit_scope_status` 缺失、空字符串、空白字符串、null、未知值，一律 fail closed。
3. 缺失状态原因码：`SUBCONTRACT_SCOPE_STATUS_REQUIRED`。
4. 未 ready 状态原因码沿用或补齐：
   - `SUBCONTRACT_SCOPE_UNTRUSTED`
   - `SUBCONTRACT_SCOPE_AMBIGUOUS`
   - `SUBCONTRACT_SCOPE_INVALID`
5. 缺状态外发行必须进入 source_map unresolved，`include_in_profit=false`。

## 6. 必改问题 3：期间过滤使用 inspected_at

### 6.1 问题

外发 Adapter 现在按 `LySubcontractInspection.created_at` 过滤期间，但任务口径和索引都指向业务验货时间 `inspected_at`。延迟录入、历史导入会导致外发成本落入错误利润期间。

### 6.2 修复要求

1. 外发来源期间过滤必须使用 `inspected_at`。
2. `from_date/to_date` 均按 `inspected_at` 判断。
3. `inspected_at` 为空时，不得用 `created_at` 静默兜底计入。
4. `inspected_at` 为空的外发行应进入 unresolved，原因 `SUBCONTRACT_INSPECTED_AT_REQUIRED`。
5. 如果确需 fallback，必须通过显式配置开关，默认关闭；本任务默认不允许 fallback。
6. source_map 必须保留 `inspected_at`，便于财务复核期间。

## 7. 必改问题 4：补数 execute 操作审计

### 7.1 问题

`SubcontractProfitScopeBackfillService.execute()` 接收 `operator` 但当前丢弃，未写操作审计。补数会批量修改财务归属字段，属于敏感操作，必须可追溯。

### 7.2 修复要求

1. execute 路径必须写操作审计。
2. 审计内容至少包含：
   - `operator`
   - `dry_run=false`
   - `company`
   - `item_code` 或筛选条件
   - `total_scanned`
   - `ready_count`
   - `unresolved_count`
   - `ambiguous_count`
   - `untrusted_count`
   - `updated_count`
   - `request_id`（如有）
3. dry_run 默认不写业务操作审计；如果已有 dry-run 审计标准，则必须明确 action 为 preview，不得混同 execute。
4. 操作审计写失败必须 rollback 业务更新并返回/抛出 `AUDIT_WRITE_FAILED`。
5. 数据库写失败必须 rollback 并返回/抛出 `DATABASE_WRITE_FAILED`。
6. `updated_count` 必须表示 execute 实际写入条数；dry_run 应为 0。若需要展示计划更新数，另用 `planned_update_count`。

## 8. 测试要求

### 8.1 Work Order 严格匹配测试

必须补齐：

1. selector 带 `work_order=WO-1`，外发行 `sales_order=SO-1/item_code=ITEM-A/work_order=WO-1`，计入。
2. selector 带 `work_order=WO-1`，外发行 `sales_order=SO-1/item_code=ITEM-A/work_order=WO-2`，不计入，原因 `SUBCONTRACT_WORK_ORDER_MISMATCH`。
3. selector 带 `work_order=WO-1`，外发行 `sales_order=SO-1/item_code=ITEM-A/work_order=null` 且无法反查，unresolved，原因 `SUBCONTRACT_WORK_ORDER_UNTRUSTED`。
4. selector 不带 work_order，外发行 `sales_order=SO-1/item_code=ITEM-A/work_order=WO-2`，可计入销售订单+款式汇总。
5. selector 不带 work_order，但外发行指向其他 sales_order，不计入。
6. 不允许 `company + item_code + sales_order` 匹配后提前返回 mapped 的回归测试。

### 8.2 profit_scope_status 测试

必须补齐：

1. 外发行缺 `profit_scope_status` 不计入。
2. 外发行 `profit_scope_status=''` 不计入。
3. 外发行 `profit_scope_status=' '` 不计入。
4. 外发行 `profit_scope_status='unresolved'` 不计入。
5. 外发行 `profit_scope_status='ready'` 才进入后续范围匹配。

### 8.3 inspected_at 期间过滤测试

必须补齐：

1. `created_at` 在期间内但 `inspected_at` 不在期间内，不采集。
2. `created_at` 不在期间内但 `inspected_at` 在期间内，采集。
3. `inspected_at` 为空，不计入，原因 `SUBCONTRACT_INSPECTED_AT_REQUIRED`。
4. source_map 中能看到 `inspected_at` 或缺失原因。

### 8.4 补数操作审计测试

必须补齐：

1. execute 成功写操作审计。
2. 操作审计内容包含 operator、统计字段和筛选范围。
3. 审计写失败时 rollback 业务更新，返回/抛出 `AUDIT_WRITE_FAILED`。
4. 数据库写失败时 rollback，返回/抛出 `DATABASE_WRITE_FAILED`。
5. dry_run 不产生业务更新，`updated_count=0`。
6. dry_run 不写 execute 操作审计，或写 preview 审计但 action 必须区分。

## 9. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_bridge.py tests/test_subcontract_profit_scope_bridge.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_api_source_adapter.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 10. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 .github 02_源码 03_需求与设计/02_开发计划/TASK-006*
```

预期：无前端、`.github`、`02_源码`、TASK-006 改动。

## 11. 验收标准

□ selector 带 work_order 时，外发成本必须严格匹配该 work_order。  
□ 同 SO、同款式、错 Work Order 的外发成本不得计入当前 Work Order 快照。  
□ selector 不带 work_order 时，可按 SO + 款式汇总 ready 外发成本。  
□ 外发行缺 profit_scope_status/null/空白/未知状态一律不计入。  
□ 外发期间过滤使用 inspected_at，不使用 created_at 静默兜底。  
□ inspected_at 为空时不计入，并写稳定原因。  
□ 补数 execute 写操作审计。  
□ 审计写失败 rollback，返回/抛出 AUDIT_WRITE_FAILED。  
□ updated_count 表示实际写入条数，dry_run 为 0。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 12. 交付说明要求

工程师交付时必须说明：

1. Work Order 严格匹配的实现位置。
2. SO+款式汇总与 Work Order 快照的区别。
3. profit_scope_status fail-closed 处理。
4. inspected_at 期间过滤实现。
5. 补数 execute 操作审计字段。
6. 审计失败 rollback 测试结果。
7. 测试命令和结果。
8. 禁改扫描结果。
9. 未进入前端、未进入 TASK-006。
