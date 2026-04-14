# TASK-005D 利润快照计算服务工程任务单

- 任务编号：TASK-005D
- 模块：款式利润报表 / 利润快照计算服务
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 07:59 CST
- 作者：技术架构师
- 审计来源：TASK-005C4 审计结论通过；当前 HEAD `67a995c2933fac3bb269e3f668252a03b93d1238` 已纳入 TASK-005C~C3 本地基线
- 前置依赖：TASK-005B/B1、TASK-005C~C4 全部审计通过；ADR-079、ADR-080、ADR-081、ADR-082、ADR-083、ADR-084 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.9；`ADR-085`
- 任务边界：只做后端利润快照计算服务、服务级 DTO 适配和测试；不注册 API；不改前端；不新增迁移；不进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D
模块：利润快照计算服务
优先级：P0（利润计算核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
基于 TASK-005C 已落库的利润快照、明细、来源映射和费用分摊表，实现后端 `StyleProfitService`，支持生成不可变利润快照、幂等 replay、幂等冲突识别、明细落库和 unresolved 追溯。

【允许新增】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_idempotency.py

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py（仅限补服务入参/出参 DTO）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py（仅限补只读来源聚合 helper，不得放宽 C1/C2 状态和 include_in_profit 规则）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py（仅限补回归用例）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-006 文件

【必须实现的服务】

## 1. `StyleProfitService.create_snapshot()`

建议签名：

```python
create_snapshot(session, request, operator) -> StyleProfitSnapshotResult
```

入参必须包含：

| 字段 | 规则 |
| --- | --- |
| `company` | 非空，资源维度 |
| `item_code` | 非空，表示款式成品编码 |
| `sales_order` | V1 推荐非空；为空时必须标记 unresolved |
| `from_date` | 非空 |
| `to_date` | 非空，且不得早于 `from_date` |
| `revenue_mode` | `actual_first / actual_only / estimated_only` |
| `include_provisional_subcontract` | boolean |
| `formula_version` | V1 固定 `STYLE_PROFIT_V1` |
| `idempotency_key` | 非空，长度不超过 128 |

处理规则：
1. 计算 `request_hash`，必须包含 `company / item_code / sales_order / from_date / to_date / revenue_mode / include_provisional_subcontract / formula_version`。
2. `request_hash` 必须排除 `created_at / operator / request_id / snapshot_no`。
3. 幂等唯一键为 `company + idempotency_key`。
4. 若存在相同 `company + idempotency_key` 且 `request_hash` 相同，返回首次快照结果，不新增 snapshot/detail/source_map。
5. 若存在相同 `company + idempotency_key` 但 `request_hash` 不同，返回或抛出 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
6. 首次请求必须新建不可变 snapshot，生成唯一 `snapshot_no`。
7. 服务内不得调用 `session.commit()`；只允许 `flush()`，由上层调用方控制 commit/rollback。
8. 任意写入失败必须抛出可被上层映射为 `DATABASE_WRITE_FAILED` 的异常，不得吞错返回成功对象。

## 2. 收入计算

使用 `StyleProfitSourceService` 的来源结果，按以下口径计算：

1. `revenue_mode=actual_first`：优先使用已提交 `Sales Invoice` 行；无已提交发票时使用已提交 `Sales Order` 行。
2. `revenue_mode=actual_only`：只使用已提交 `Sales Invoice` 行；没有则收入为 0，并写 unresolved。
3. `revenue_mode=estimated_only`：只使用已提交 `Sales Order` 行。
4. draft/cancelled/unknown 状态来源不得纳入。
5. `Sales Invoice` 与 `Sales Order` 不得重复计入收入。
6. 收入来源必须写入 detail 和 source_map，保留 `source_doctype/source_name/source_line_no/qty/unit_rate/amount/source_status`。

输出字段：
- `estimated_revenue_amount`
- `actual_revenue_amount`
- `revenue_amount`
- `revenue_status=actual/estimated/unresolved`

## 3. 标准成本计算

1. 标准材料成本：`standard_material_cost = sum(bom_required_qty_with_loss * standard_unit_cost)`。
2. `standard_unit_cost` 来源优先级：ERPNext Item Price 有效采购价 -> ERPNext Item valuation_rate -> unresolved。
3. 标准工序成本：`standard_operation_cost = sum(bom_operation_rate * planned_qty)`。
4. 标准总成本：`standard_total_cost = standard_material_cost + standard_operation_cost`。
5. 标准价或工价缺失时必须写 unresolved detail/source_map，不得静默按 0 当作完整数据。

## 4. 实际成本计算

### 4.1 实际材料成本

1. 只允许使用 ERPNext `Stock Ledger Entry` 来源。
2. 金额公式：`actual_material_cost = sum(abs(stock_value_difference))`。
3. SLE 必须已提交，且能通过 `work_order / production_plan / sales_order / BOM 物料范围` 归属目标款式和订单。
4. `Purchase Receipt` 只能写参考来源，不得进入 `actual_material_cost`。
5. 无法归属或状态未知必须 unresolved，不得纳入利润。

### 4.2 实际工票成本

1. 工票净数量：`net_ticket_qty = register_qty - reversal_qty`。
2. 实际工票成本：`actual_workshop_cost = sum(net_ticket_qty * wage_rate_snapshot)`。
3. 必须按 `company + item_code + sales_order/work_order/job_card` 归属。
4. 工价缺失、历史脏工价或无法归属必须 unresolved。

### 4.3 实际外发成本

1. 已结算/锁定的外发验货行优先使用结算锁定净额。
2. 未结算但已验货时，只有 `include_provisional_subcontract=true` 才允许使用验货净额，并标记 `subcontract_status=provisional`。
3. `include_provisional_subcontract=false` 时，未结算外发验货只能写 unresolved/excluded，不得计入成本。
4. 扣款金额只作为明细展示；若已使用净额，不得重复扣减。

## 5. 费用分摊和利润公式

1. V1 不启用费用分摊：`allocated_overhead_amount = 0`。
2. `allocation_status = not_enabled`。
3. `actual_total_cost = actual_material_cost + actual_workshop_cost + actual_subcontract_cost + allocated_overhead_amount`。
4. `profit_amount = revenue_amount - actual_total_cost`。
5. `profit_rate = profit_amount / revenue_amount`。
6. 收入为 0 时，`profit_rate = null`，不得除零。
7. `snapshot_status`：无 unresolved 为 `complete`；存在 unresolved 为 `incomplete`；计算异常为 `failed`。
8. `unresolved_count` 必须等于 unresolved detail/source_map 的可复核数量。

【明细与来源映射要求】

1. 每个纳入利润的收入/成本项必须生成 `ly_style_profit_detail`。
2. 每个 detail 必须至少有一条对应 `ly_style_profit_source_map`，除非是 V1 固定费用分摊 0。
3. source_map 初始 `include_in_profit=false`，只有最终纳入利润的来源才允许设为 true。
4. `mapping_status` 只能为 `mapped/unresolved/excluded`。
5. `source_status=unknown` 不得纳入利润。
6. `raw_ref` 必须脱敏，不得写 Authorization、Cookie、token、password、secret、原始 SQL。
7. detail `line_no` 必须稳定递增，便于审计比对。
8. source_map 不得违反 TASK-005C2 的字段、唯一约束和索引契约。

【错误码 / 异常口径】

| 场景 | 错误码 |
| --- | --- |
| 幂等 key 相同但 request_hash 不同 | `STYLE_PROFIT_IDEMPOTENCY_CONFLICT` |
| 入参日期非法 | `STYLE_PROFIT_INVALID_PERIOD` |
| `revenue_mode` 非法 | `STYLE_PROFIT_INVALID_REVENUE_MODE` |
| 公式版本非法 | `STYLE_PROFIT_INVALID_FORMULA_VERSION` |
| 来源读取失败 | `STYLE_PROFIT_SOURCE_READ_FAILED` |
| 数据库写入失败 | `DATABASE_WRITE_FAILED` |
| 未知异常 | `STYLE_PROFIT_INTERNAL_ERROR` |

说明：本任务不注册 API，上述错误码先用于 service exception 和测试断言，后续 TASK-005E API 层再映射为统一错误信封。

【事务边界】

1. `StyleProfitService` 不允许直接 `commit()`。
2. 服务可以 `flush()` 以获得主键和触发唯一约束。
3. 创建 snapshot、detail、source_map 必须在同一数据库事务内完成。
4. 幂等 replay 不得新增任何行。
5. 幂等冲突不得新增任何行。
6. 任何异常后不得留下半快照、半明细或半 source_map。
7. 本任务不得调用 ERPNext 写接口，不得创建 outbox。

【必须测试】

至少新增以下测试：

1. `actual_first` 有已提交 Sales Invoice 时使用实际收入，不重复计入 Sales Order。
2. `actual_first` 无 Sales Invoice 时回退 Sales Order 预计收入。
3. `actual_only` 无 Sales Invoice 时收入为 0，snapshot 为 `incomplete`，产生 unresolved。
4. draft/cancelled/unknown 来源不纳入利润。
5. SLE 使用 `abs(stock_value_difference)` 计实际材料成本。
6. Purchase Receipt 只写参考来源，不计入 `actual_material_cost`。
7. 工票成本按 `register_qty - reversal_qty` 乘工价快照。
8. 外发成本优先用结算锁定净额。
9. 未结算验货在 `include_provisional_subcontract=true` 时可 provisional 纳入。
10. 未结算验货在 `include_provisional_subcontract=false` 时不得纳入。
11. 费用分摊固定为 0，`allocation_status=not_enabled`。
12. `profit_amount = revenue_amount - actual_total_cost`。
13. 收入为 0 时 `profit_rate is None`。
14. 相同 `company + idempotency_key + request_hash` replay 返回同一 `snapshot_no`，不新增行。
15. 相同 `company + idempotency_key` 但不同 request_hash 返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
16. `request_hash` 不包含 `created_at/operator/request_id/snapshot_no`。
17. source_map 默认 `include_in_profit=false`，只有 mapped 且纳入利润的来源为 true。
18. `source_status=unknown` 不纳入利润。
19. 写入失败抛出 `DATABASE_WRITE_FAILED` 或等价数据库写异常，不返回成功。
20. 静态扫描确认未注册 `/api/reports/style-profit/`，未修改前端，未进入 TASK-006。

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
```

要求：上述扫描不得出现本任务禁止修改路径。

【验收标准】
□ `StyleProfitService.create_snapshot()` 可创建 snapshot/detail/source_map，且服务内不 commit。
□ 利润公式、收入模式、实际材料、工票、外发、费用分摊全部符合 ADR-079。
□ 幂等 replay 和幂等冲突均有测试覆盖。
□ unresolved 来源会写 detail/source_map，并影响 `snapshot_status/unresolved_count`。
□ source_map 遵守 include_in_profit fail closed、source_status fail closed 和 raw_ref 脱敏规则。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-006。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 工程师会话日志已追加执行记录。

【预计工时】
1.5-2.5 天

════════════════════════════════════════════════════════════════════════════
