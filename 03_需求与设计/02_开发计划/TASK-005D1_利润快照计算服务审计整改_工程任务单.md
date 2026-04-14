# TASK-005D1 利润快照计算服务审计整改工程任务单

- 任务编号：TASK-005D1
- 模块：款式利润报表 / 利润快照计算服务审计整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 10:15 CST
- 作者：技术架构师
- 审计来源：审计意见书第 92 份，TASK-005D 有条件通过但仍有 3 个 P1、3 个 P2 必改项
- 前置依赖：TASK-005D 已交付并完成第 92 份审计；TASK-005E/API 层未放行；TASK-006 继续阻塞
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V1.0；`ADR-086`
- 任务边界：只修复 TASK-005D 利润快照计算服务审计问题和测试；不注册 API；不改前端；不新增迁移；不进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D1
模块：利润快照计算服务审计整改
优先级：P0（阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复第 92 份审计指出的 6 个阻断项，确保利润快照幂等、unresolved、SLE、缺工价、收入状态和 idempotency_key 校验全部 fail closed。

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

## 1. P1：request_hash 必须纳入来源输入

当前问题：`request_hash` 只包含 header 字段，不包含会影响利润结果的来源输入。相同 `company + idempotency_key` 下，来源行金额变化会 replay 旧快照。

整改要求：
1. `request_hash` 必须纳入所有影响快照计算结果的规范化输入。
2. 必须纳入：`sales_invoice_rows`、`sales_order_rows`、`bom_material_rows`、`bom_operation_rows`、`stock_ledger_rows`、`workshop_ticket_rows`、`subcontract_rows`、`allowed_material_item_codes`、`work_order`。
3. 每类来源只纳入计算相关字段，不纳入运行态字段。
4. 必须排除：`operator`、`request_id`、`created_at`、`updated_at`、`snapshot_no`、`audit_id`、数据库自增 `id`、Authorization、Cookie、token、password、secret。
5. 列表顺序不得影响 hash；同一批来源行应按稳定键排序后参与 hash。
6. Decimal、date、datetime、None 必须规范化，避免同语义不同字符串导致误冲突。
7. 同 `company + idempotency_key`、同 header、不同来源金额必须返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`，不得 replay。
8. 同来源行但顺序不同必须生成相同 `request_hash`。

建议稳定排序键：
- 收入：`source_doctype/source_name/source_line_no/item_code`
- BOM 物料：`item_code/material_item_code/uom`
- BOM 工序：`operation/process_name/sequence`
- SLE：`voucher_type/voucher_no/voucher_detail_no/item_code/posting_date/warehouse`
- 工票：`ticket_key/job_card/process_name/employee/date/color/size/operation_type`
- 外发：`subcontract_order/receipt_batch_no/inspection_id/settlement_id/item_code`

## 2. P1：收入 unresolved 必须落 detail/source_map

当前问题：`actual_first` 或 `estimated_only` 没有有效收入来源时，`revenue_status=unresolved`，但没有 unresolved detail/source_map，`snapshot_status` 仍可能是 `complete`。

整改要求：
1. 所有 `revenue_status=unresolved` 场景必须写 unresolved detail。
2. 所有收入 unresolved 场景必须写 source_map。
3. `snapshot_status` 必须为 `incomplete`。
4. `unresolved_count` 必须大于 0，且计数可复核。
5. 覆盖场景：`actual_first` 无 Sales Invoice 且无 Sales Order。
6. 覆盖场景：`actual_only` 无 Sales Invoice。
7. 覆盖场景：`estimated_only` 无 Sales Order。
8. 覆盖场景：收入来源全部 draft/cancelled/unknown。
9. 无真实来源行时，允许写 synthetic source_map，但必须可追溯原因。

synthetic source_map 建议：
- `source_system=manual`
- `source_doctype=Revenue Resolution`
- `source_name=UNRESOLVED_REVENUE`
- `source_line_no={revenue_mode}:{sales_order or empty}`
- `source_status=unknown`
- `mapping_status=unresolved`
- `include_in_profit=false`
- `unresolved_reason=no_valid_revenue_source`

## 3. P1：异常 SLE 必须 unresolved 持久化

当前问题：SLE 状态未知、缺 `docstatus`、未提交或无法通过归属门禁时，被放入 `excluded_sources` 后没有持久化，导致异常材料来源不可追溯，也不影响 `snapshot_status`。

整改要求：
1. `source_status_unknown` 的 SLE 必须进入 `unresolved_sources` 并持久化。
2. 缺 `docstatus` 的 SLE 必须进入 `unresolved_sources` 并持久化。
3. 未提交、取消或无法判断提交状态的 SLE 必须进入 `unresolved_sources` 并持久化。
4. 无法通过 `work_order / production_plan / sales_order / BOM 物料范围` 归属的 SLE 必须进入 `unresolved_sources` 并持久化。
5. 上述 unresolved SLE 不得纳入 `actual_material_cost`。
6. 上述 unresolved SLE 必须让 `snapshot_status=incomplete`。
7. `Purchase Receipt` reference-only 可继续保持 excluded/reference，不进入利润，也不强制影响 `snapshot_status`。
8. 明确非目标公司、非目标订单、非 BOM 物料范围的来源可以 excluded，但必须有 source_map 或测试证明不会静默丢失关键异常。

## 4. P2：缺标准工序工价、缺工票工价必须 unresolved

当前问题：标准工序成本缺工价、工票缺 `wage_rate_snapshot/wage_rate/unit_rate` 时，当前按 0 金额 mapped 且 `include_in_profit=true`。

整改要求：
1. 必须区分“字段缺失/非法”和“明确合法 0”。
2. 标准工序 `bom_operation_rate/operation_rate/rate` 缺失、空字符串、非法 Decimal 时，必须写 unresolved detail/source_map。
3. 工票净数量大于 0 且 `wage_rate_snapshot/wage_rate/unit_rate` 缺失、空字符串、非法 Decimal 时，必须写 unresolved detail/source_map。
4. 缺工价来源不得 mapped。
5. 缺工价来源 `include_in_profit=false`。
6. 缺工价来源必须使 `snapshot_status=incomplete`。
7. 缺工价不得静默按 0 计为完整成本。
8. 如果确实存在合法 0 工价，必须是来源字段显式存在且可解析为 Decimal(0)，并有测试覆盖。

## 5. P2：收入 source_map 必须保留真实 source_status

当前问题：收入 source_map 的 `source_status` 被硬编码为 `submitted`，没有保留 ERPNext 原始状态。

整改要求：
1. `StyleProfitRevenueSourceDTO` 必须补 `source_status`。
2. `StyleProfitSourceService._build_revenue_rows()` 必须传递规范化后的真实来源状态。
3. Sales Invoice status-only 场景应保留 `paid/unpaid/overdue/partly paid`。
4. Sales Order status-only 场景应保留 `to deliver and bill/to bill/to deliver/completed`。
5. `docstatus=1` 但原 status 缺失时，可写 `submitted`，但不得覆盖已有真实 status。
6. source_map 写入必须使用 DTO 的真实 `source_status`。
7. 测试必须覆盖 `Paid`、`Unpaid`、`To Bill` 等状态追溯。

## 6. P2：idempotency_key 长度必须服务级校验

当前问题：`idempotency_key` 未做长度不超过 128 的服务级校验，PostgreSQL 可能在落库阶段才报错。

整改要求：
1. DTO 使用 `Field(..., max_length=128)`，或 `_validate_payload()` 显式校验。
2. 空字符串仍必须拒绝。
3. 超过 128 字符必须抛业务异常，不得进入数据库写入。
4. 错误码建议为 `STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY`。
5. 超长 key 测试必须断言不落 snapshot/detail/source_map。

【防回潮要求】
1. 不得回退第 91 份中已指出的归属校验、保存点/半快照、空 sales_order、缺工价 unresolved 等问题。
2. 如果当前代码仍存在第 91 份问题，必须在本轮一并修复，不得留到 TASK-005E。
3. `TASK-005E` API 层在本任务通过审计前不得启动。
4. `TASK-006` 继续阻塞。

【必须新增或补齐测试】
1. 同 `company + idempotency_key`、同 header、不同 `sales_invoice_rows.amount` 返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
2. 同来源行不同列表顺序生成相同 `request_hash`。
3. `request_hash` 不包含 `operator/request_id/created_at/snapshot_no`。
4. `actual_first` 无发票且无 SO 时，snapshot incomplete，`unresolved_count>0`，存在 unresolved revenue detail/source_map。
5. `estimated_only` 无 SO 时，snapshot incomplete，存在 unresolved revenue detail/source_map。
6. 收入来源全部 draft/cancelled/unknown 时，snapshot incomplete，存在 unresolved revenue detail/source_map。
7. SLE 缺 `docstatus` 时不计入 `actual_material_cost`，并写 unresolved source_map。
8. SLE `source_status=unknown` 时不计入 `actual_material_cost`，并写 unresolved source_map。
9. SLE 无法归属订单/工单/BOM 物料范围时不计入成本，并写 unresolved source_map。
10. Purchase Receipt 仍只作为 reference/excluded，不计入 `actual_material_cost`。
11. 标准工序缺工价时 unresolved，不 mapped，不 `include_in_profit`。
12. 工票净数量大于 0 且缺工价时 unresolved，不 mapped，不 `include_in_profit`。
13. 明确合法 0 工价可按 0 纳入，但必须有字段存在性测试。
14. Sales Invoice `Paid/Unpaid/Overdue` 写入真实 source_status。
15. Sales Order `To Bill/To Deliver` 写入真实 source_status。
16. 超长 `idempotency_key` 返回 `STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY` 或等价业务异常，不落库。
17. 禁改扫描确认未注册 API、未改前端、未新增迁移、未进入 TASK-006。

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
```

要求：
1. 前两个禁改扫描必须无输出。
2. 第三个命令不得出现 TASK-006 文件。

【验收标准】
□ request_hash 纳入所有影响利润结果的规范化来源输入。
□ 同 header 不同来源金额触发幂等冲突，不 replay 旧快照。
□ 无有效收入来源时生成 unresolved detail/source_map，snapshot_status=incomplete。
□ unknown/缺 docstatus/无法归属 SLE 会持久化 unresolved source_map，不静默丢失。
□ 缺标准工序工价和缺工票工价均 unresolved，不 mapped，不 include_in_profit。
□ 收入 source_map 保留真实 source_status。
□ 超长 idempotency_key 在服务层拒绝，且不落库。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-005E/TASK-006。
□ 工程师会话日志已追加执行记录。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
