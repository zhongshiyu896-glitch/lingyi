# TASK-Z012B-27-IMPL｜Z012 成品进销存前端交互实现与本地回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Z012B-27-IMPL`
- source_task_id: `TASK-Z012B-26-PREP`
- source_head: `6a0854da243f6e7ca514ee4c06e95c43e0d3e301`
- selected_candidate_id: `Z012-CAND-005`
- module: `成品进销存`
- yisuan_page: `成品库存 / 成品进销存报表`
- route parity 基线：`/productStock/productStockList -> /warehouse?parity=product-stock`
- 本轮约束：
  - 仅改 allowlist 内前端文件；
  - GET-only + DEV_AUTH_LOCAL；
  - 不改后端，不做 stage/commit/push，不做生产/远端动作。

## 2. 代码实现摘要
### 2.1 路由语义
- 未修改 router 文件，保持既有入口语义：
  - `/productStock/productStockList -> /warehouse?parity=product-stock`
- 浏览器目标 1 最终落点仍为仓库页面 parity 场景。

### 2.2 成品库存只读交互壳层
- 修改文件：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- 关键实现：
  - 新增稳定选择器 `data-testid="finished-goods-stock-parity-hint"`，区分默认与 `parity=product-stock` 语义；
  - 增加 `DEV_AUTH_LOCAL` 只读说明告警（`data-testid="finished-goods-dev-auth-local-note"`）；
  - 写动作入口统一切换为 `data-write-guard="guarded:readonly-dev-only"`；
  - `createLocalStockEntryDraft` / `cancelLocalStockEntryDraft` 增加只读 guard 早返回，避免写请求；
  - `parity=product-stock` 场景允许读取只读壳层数据，`loadData` 强制走本地 seed，避免远端读失败成为阻断。

### 2.3 Allowlist 实际变更
- 实际产品 diff 仅 1 个文件：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- allowlist 但未改动：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`
- `07_后端`：无改动。

## 3. 本地回归与证据
### 3.1 类型与构建
- `npm run typecheck`: PASS
- `npm run build`: PASS

### 3.2 浏览器只读回归
- 请求目标（任务要求）：
  - `http://127.0.0.1:5173/productStock/productStockList`
  - `http://127.0.0.1:5173/warehouse?parity=product-stock`
  - `http://127.0.0.1:5173/warehouse`
- 运行目标（实际）：
  - `http://127.0.0.1:5180/productStock/productStockList`
  - `http://127.0.0.1:5180/warehouse?parity=product-stock`
  - `http://127.0.0.1:5180/warehouse`
- 浏览器证据文件：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_interaction_browser_result.json`
- 截图目录：
  - `/tmp/task_z012b27_finished_goods_stock_screenshots`
- 关键结果：
  - `request_methods=["GET"]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `network_error_count=0`
  - `finished_goods_parity_hint_status=PASS`
  - `filter_interaction_status=PASS`
  - `pagination_interaction_status=PASS`
  - `reset_interaction_status=PASS`
  - `kpi_list_linkage_status=PASS`
  - `readonly_dev_guard_status=PASS`
  - `empty_error_state_semantics_status=PASS`
  - `readonly_detail_panel_or_drawer_status=PASS`
  - `expected_response_error_count=4`（`/api/auth/me`，`DEV_AUTH_LOCAL` 非阻断预期）

## 4. 结果文件
- impl result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_interaction_impl_result.json`
- impl result TSV:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_interaction_impl_result.tsv`
- browser result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_interaction_browser_result.json`

## 5. 状态锚点保持
- `full_browser_route_smoke_closed=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
- `production_account_used=false`
- `remote_lifecycle_action_executed=false`
