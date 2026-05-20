# TASK-Z012B-21-IMPL｜Z012 物料进销存交互实现与本地回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Z012B-21-IMPL`
- candidate: `Z012-CAND-004`（物料进销存 / 物料库存与物料进销存报表）
- source_head: `eac87c67f91d7b1336317f298e9d25e164ad1f5a`
- 实现类型: `FRONTEND_INTERACTION_LOCAL`
- 约束保持：
  - `full_browser_route_smoke_closed=false`
  - `production_readback_ready=false`
  - `go_live_ready=false`
  - `project_completion_claimed=false`
  - `remote_lifecycle_parked=true`
  - `production_account_used=false`
  - `remote_lifecycle_action_executed=false`

## 2. 代码实现摘要
### 2.1 路由与 parity 语义
- 本轮未修改 `router/index.ts`，保持既有映射链路：
  - `/materialStock/materialTypeStock -> /sales-inventory/stock-ledger?parity=material-stock`
- 通过浏览器目标 1 的最终 URL 复核映射仍生效。

### 2.2 物料库存只读交互壳层
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- 关键实现：
  - 新增稳定选择器 `data-testid="material-stock-parity-hint"`，展示“衣算云 / 物料进销存 / 物料库存（只读交互）”。
  - 新增并接入本地筛选字段：`keyword`、`status`，并补齐路由预填与重置恢复。
  - 列表数据切换为本地筛选结果 `stockLedgerFilteredRows`，并增加“当前筛选结果”统计。
  - 增加状态列（正常/低库存/缺货）与标签类型。
  - 分页在 parity 场景稳定可见（`hide-on-single-page` 在 parity 场景关闭隐藏）。
  - 写动作（下单草稿/作废草稿）加 `data-write-guard="guarded:readonly-dev-only"`，并在 parity 场景强制禁用。
  - 空态/错误态/权限文案改为物料库存专项语义。
  - 在 `!canRead && parity=material-stock` 时展示本地只读壳层提示，不触发写动作。

### 2.3 Allowlist 文件实际变更
- 实际前端产品 diff：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- allowlist 但未改动：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`

## 3. 本地回归与证据
### 3.1 构建与类型
- `npm run typecheck`: PASS
- `npm run build`: PASS

### 3.2 浏览器只读 smoke
- 请求目标（任务要求）：
  - `http://127.0.0.1:5173/materialStock/materialTypeStock`
  - `http://127.0.0.1:5173/sales-inventory/stock-ledger?parity=material-stock`
  - `http://127.0.0.1:5173/sales-inventory/stock-ledger`
- 实际执行说明：
  - 本机 `5173` 被非本项目运行时占用。
  - 本轮在同仓可用运行时 `http://127.0.0.1:5176` 执行等价回归，并在 browser result 保留 requested/attempted 对照。
- 结果：
  - `request_methods=[GET]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `network_error_count=0`
  - `material_stock_parity_hint_status=PASS`
  - `filter_interaction_status=PASS`
  - `pagination_interaction_status=PASS`
  - `reset_interaction_status=PASS`
  - `readonly_dev_guard_status=PASS`
  - `empty_error_state_semantics_status=PASS`
  - `screenshot_count=4`
  - `valid_target_screenshot_count=3`

### 3.3 证据文件
- 报告：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z012B-21-IMPL_Z012物料进销存交互实现与本地回归报告.md`
- 结构化结果：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_21_material_stock_interaction_impl_result.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_21_material_stock_interaction_impl_result.tsv`
- 浏览器证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_21_material_stock_interaction_browser_result.json`
  - `/tmp/task_z012b21_material_stock_screenshots`

## 4. 约束与风险结论
- 本轮仅实现本地前端只读交互壳层；未修改 `07_后端`，未触发非 GET 请求，未触发生产写入。
- 未执行 `git add/commit/push`，未执行 `PR/tag/release`。
- 本轮不外推为全链路闭合，状态锚点保持不变。
