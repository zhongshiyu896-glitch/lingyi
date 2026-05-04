# TASK-Y23B-03-IMPL /sales-inventory/sales-orders 共享路由 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y23B-03-IMPL`
- ROLE: `B Engineer`
- route: `/sales-inventory/sales-orders`
- source baseline: `task_y23b_03_allowlist_baseline.json`
- shared_route: `YES`
- allowlist_mismatch: `NO`

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/sales-inventory/sales-orders` 保留 P0「订单」主语义（标题/筛选/列表/详情入口/权限态/错误态）前提下，补齐 `TASK-Y22B-P1-03` 对应的“订单生产加工数量对照表”只读语义。
- 前端补齐：
  - 新增 P1-03 区块（`P1 / TASK-Y22B-P1-03`）与筛选项：款号、款名关键词、仓库。
  - 新增对照表结构与字段：订单号、款号、仓库、订单数量、加工数量、完成率、状态。
  - 新增只读操作语义：查看（复用详情入口）、导出/更多（guarded 提示，不触发真实请求）。
  - 新增可承接错误态：`fulfillmentError` + `error-alert`。
- API 层补齐：
  - `sales_inventory.ts` 新增 `SalesOrderFulfillmentQuery` 并补入 `item_name` 查询参数。
- 本轮未新增真实写路由，未放宽现有写接口权限。

## ROUTE_API_BACKEND_MAPPING
- Frontend view:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
- Frontend API:
  - `06_前端/lingyi-pc/src/api/sales_inventory.ts`
- Backend router/schema/service（本轮未改）:
  - `07_后端/lingyi_service/app/routers/sales_inventory.py`
  - `07_后端/lingyi_service/app/schemas/sales_inventory.py`
  - `07_后端/lingyi_service/app/services/sales_inventory_service.py`

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y22B-P1-03` 对应语义，未启动 `TASK-Y22B-P1-04/P1-05` 与其他 P1/P2 页面。
- 未扩展到 `/production/plans`、`/dashboard/overview`、`/reports/style-profit`、`/warehouse`。
- P0 订单主语义保留：PASS。
- 详情入口 `/sales-inventory/sales-orders/detail` 保留：PASS。

## BROWSER_VALIDATION
- run_id: `20260503T233809Z`
- result_json: `/tmp/task_y23b_03_impl_20260503T233809Z_browser_results.json`
- screenshot_dir: `/tmp/task_y23b_03_impl_20260503T233809Z_screenshots`
- screenshots_count: `6`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - p1_03_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_sales_order_preserved_check: PASS
  - detail_entry_preserved_check: PASS
  - write_actions_guarded_check: PASS
- network/console:
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`（手动注入 503 验证错误态承接）
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## VALIDATION_COMMANDS
- `git diff --cached --name-only`: PASS（空）
- `git diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## WRITE_ACTION_BOUNDARY
- 本页新增“导出/更多”等写语义按钮均为 guarded/disabled/提示型，不触发 POST/PUT/PATCH/DELETE。
- 未放宽历史写接口权限。
- 未触发真实下载/导出/打印请求。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- other P1/P2 started: NO
- allowlist outside modified: NO
- real write routes added: NO
- write permission relaxed: NO
- download/export/print real requests: NO
- production/GitHub management actions: NO
- parked blockers released: NO
