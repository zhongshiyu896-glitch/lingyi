# TASK-022B 成本快照本地计算与只读明细基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-022B
- 任务名称：成本快照本地计算与只读明细基线
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：TASK-022A 审计通过（审计意见书第 214 份）

## 2. 任务目标

基于 `TASK-022A` 已冻结的成本核算边界，以及当前仓库中已存在的 `style_profit` 模块代码，输出第一张成本核算实现子任务，范围限定为“本地成本快照计算 + 只读列表 / 详情 / 来源映射基线”收口：

1. 保留并收口本地成本快照创建、列表、详情和来源映射查询能力。
2. 允许标准成本、实际成本、未归属成本（`unresolved`）以本地快照与只读明细形式呈现，但不得把这些结果升级为财务写入事实。
3. 明确快照创建只能消费受控只读来源，不得允许客户端直传利润来源明细，也不得暴露财务写入候选能力。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-022A` 已于审计意见书第 214 份通过，允许进入成本核算实现任务拆分。
2. `TASK-021B -> TASK-021D` 生产管理链路已完成审计收口，但该链路的第 233 份状态对账阻塞已被后续共享状态收敛，不再构成当前成本链路前置门禁。
3. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
4. 即使 `TASK-022B` 任务单通过，也只表示门禁定义完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-022B` 直接相关的成本快照基础代码已存在，不得按“从零新建模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

已核实的真实入口与现状：

1. 路由已存在 `GET /api/reports/style-profit/snapshots`，当前使用 `STYLE_PROFIT_READ` 读取快照列表。
2. 路由已存在 `GET /api/reports/style-profit/snapshots/{snapshot_id}`，当前返回快照、明细和来源映射。
3. 路由已存在 `POST /api/reports/style-profit/snapshots`，当前使用 `STYLE_PROFIT_SNAPSHOT_CREATE` 创建本地快照，并显式禁止客户端提交来源明细字段。
4. 前端已存在成本快照列表 / 详情页与对应 API 封装，且详情页已展示 `unresolved_count`、`actual_total_cost`、`standard_total_cost`、`profit_amount`、`profit_rate`。

因此本任务的核心是：

1. 按 `TASK-022A` 把现有成本模块收口到“本地快照计算 + 只读列表 / 详情 / 来源映射”边界。
2. 保持标准成本、实际成本和 `unresolved` 显式标记语义一致，不得静默吞掉无法归属或无法读取的成本来源。
3. 保持快照创建只消费受控只读来源，不允许客户端提交来源明细，也不允许把只读结果回写财务事实。
4. 不触碰 `GL Entry / Journal Entry / Payment Entry / AP / AR` 候选写入、Outbox worker、平台发布语义。

## 2.3 设计依据

1. `TASK-022A` 已明确：`Account / Cost Center / Stock Ledger Entry / Purchase Receipt / Purchase Invoice` 当前仅允许通过 `TASK-008 Adapter` 只读访问。
2. `TASK-022A` 已明确：`GL Entry`、`Payment/AP/AR` 当前仅允许只读关联分析，禁止直接写入。
3. `TASK-022A` 已明确：成本核算结果当前只能作为本地快照和候选分析输出，不得直接成为财务事实。
4. `TASK-022A` 已明确：普通前端不得暴露 `cost:diagnostic`、`cost:worker`，只读展示不得演变为财务写入。
5. `Sprint3_主执行计划.md` 明确成本核算实现子任务顺序为 `022B -> 022C -> 022D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
3. 允许补充与成本快照计算、来源映射、权限审计和 API 错误包络相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改任何财务写入候选或真实写入文件，包括但不限于 `GL Entry / Journal Entry / Payment Entry / AP / AR` 相关写链路。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 与任何成本相关 worker 的真实执行语义。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py` 的付款 / 应付写入语义。
4. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
5. 禁止允许客户端直传 `sales_invoice_rows`、`sales_order_rows`、`bom_material_rows`、`stock_ledger_rows`、`purchase_receipt_rows` 等利润来源明细。
6. 禁止把 `unresolved` 静默归零、静默过滤或伪造成 `complete`。
7. 禁止在普通前端路径暴露 `cost:diagnostic`、`cost:worker`、财务调整候选写入口。
8. 禁止修改 `.github/**`、`02_源码/**`、新增并行成本核算独立仓库或独立前端工程。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 成本快照创建、列表、详情和来源映射继续可用，并保持统一错误包络和 fail-closed 语义。
2. `company + item_code + sales_order` 等资源维度校验必须继续生效；缺失或越权必须 fail-closed。
3. `unresolved_count`、`unresolved_reason`、`mapping_status` 必须继续显式可见，不得静默吞掉无归属成本或来源读取失败。
4. 快照创建必须继续使用受控的 `idempotency_key / request_hash` 语义，且客户端不得直接提交利润来源明细。
5. 标准成本、实际成本、来源映射只能作为本地快照与只读明细输出，不得升级为 `GL Entry / Journal Entry / Payment Entry` 写入事实。
6. 普通前端路径不得暴露 `cost:diagnostic`、`cost:worker` 或任何财务写入候选入口。

## 6. 验收标准

1. 任务实现候选范围仅限成本快照读侧 / 本地计算侧，不包含财务写链路、worker、outbox 公共状态机、`.github/**`、`02_源码/**`。
2. `POST /api/reports/style-profit/snapshots` 仍只创建本地快照，不要求也不允许财务写入；且客户端提交来源明细时继续被拒绝。
3. 快照列表 / 详情继续能返回 `actual_total_cost`、`standard_total_cost`、`profit_amount`、`profit_rate`、`unresolved_count` 和来源映射。
4. `unresolved` 继续显式保留，不存在“读取失败但返回成功+空明细”或“complete 且 unresolved_count=0”的伪成功。
5. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在普通前端暴露 `cost:diagnostic / cost:worker`。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "STYLE_PROFIT_READ|STYLE_PROFIT_SNAPSHOT_CREATE|/snapshots|idempotency_key|request_hash|CLIENT_SOURCE_FORBIDDEN" \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/services/style_profit_service.py' \
  '07_后端/lingyi_service/app/services/style_profit_source_service.py'
rg -n "unresolved_count|unresolved_reason|mapping_status|actual_total_cost|standard_total_cost|profit_amount|profit_rate" \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue'
rg -n "(/api/resource|cost:diagnostic|cost:worker|sales_invoice_rows|sales_order_rows|bom_material_rows|stock_ledger_rows|purchase_receipt_rows)" \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py'
npm --prefix '06_前端/lingyi-pc' run typecheck
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/services/style_profit_service.py' \
  '07_后端/lingyi_service/app/services/style_profit_source_service.py' \
  '07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py' \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit' \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-022B 执行完成。
结论：待审计
是否仍限定为本地成本快照计算 + 只读列表/详情/来源映射：是 / 否
是否允许客户端直传利润来源明细：否
是否保留 unresolved 显式标记：是 / 否
是否写入 GL Entry / Journal Entry / Payment Entry / AP / AR：否
是否直连 ERPNext/Frappe：否
是否修改 .github / 02_源码：否
是否 push/remote/PR：否
```
