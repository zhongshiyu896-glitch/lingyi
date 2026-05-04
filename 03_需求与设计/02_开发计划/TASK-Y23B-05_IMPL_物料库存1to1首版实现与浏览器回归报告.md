# TASK-Y23B-05-IMPL /warehouse 物料库存 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y23B-05-IMPL`
- ROLE: `B Engineer`
- route: `/warehouse`
- source baseline: `task_y23b_05_warehouse_allowlist_baseline.json`
- shared_route: `YES`
- allowlist_mismatch: `NO`

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/warehouse` 中新增 `TASK-Y22B-P1-05`「物料库存」只读语义区块，未覆盖既有 P0「成品库存」与 P1 `TASK-Y18B-05`「仓库管理」语义。
- 前端补齐：
  - 新增“物料进销存 / 物料库存（TASK-Y22B-P1-05）”区块。
  - 新增筛选项：物料关键字、分类、仓库、库位、状态。
  - 新增物料库存表格字段：物料编码、物料名称、分类、仓库、库位、库存数量、库存金额、状态、操作。
  - 新增按钮语义：查询物料、调拨、盘点、导出；写语义均为 guarded 提示，不触发写请求。
  - 新增物料库存空态与错误态（`__material_error__` 受控注入）。
- 前后端只读 contract 补齐：
  - `warehouse` stock summary 响应新增 `material_inventory` 字段。
  - 后端服务按库存汇总数据生成物料库存只读行（分类、库位、金额、状态），未新增写路由。

## ROUTE_API_BACKEND_MAPPING
- Frontend view: `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- Frontend API: `06_前端/lingyi-pc/src/api/warehouse.ts`
- Backend router: `07_后端/lingyi_service/app/routers/warehouse.py`（本轮未改）
- Backend schema: `07_后端/lingyi_service/app/schemas/warehouse.py`
- Backend service: `07_后端/lingyi_service/app/services/warehouse_service.py`
- Readonly source endpoint: `GET /api/warehouse/stock-summary`

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y22B-P1-05` 物料库存语义，未启动其他 P1/P2 页面。
- 未扩展到 `/bom/list`、`/factory-statements/list`、`/sales-inventory/sales-orders`、`/production/plans`、`/dashboard/overview`、`/reports/style-profit`。
- P0 成品库存 preserved：PASS。
- P1 `TASK-Y18B-05` 仓库管理 preserved：PASS。
- 历史写接口未放宽，未新增真实写路由：PASS。

## BROWSER_VALIDATION
- run_id: `20260504T003121Z`
- result_json: `/tmp/task_y23b_05_impl_20260504T003121Z_browser_results.json`
- screenshot_dir: `/tmp/task_y23b_05_impl_20260504T003121Z_screenshots`
- screenshots_count: `7`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - material_inventory_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_finished_goods_stock_preserved_check: PASS
  - y18b_05_warehouse_management_preserved_check: PASS
  - write_actions_guarded_check: PASS
- metrics:
  - write_request_count: `0`
  - upload_download_export_print_request_count: `0`
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`
  - console_errors_total: `0`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `0`

## VALIDATION_COMMANDS
- `git diff --cached --name-only`: PASS（空）
- `git diff --check`: PASS（本轮实现文件与报告文件无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## WRITE_ACTION_BOUNDARY
- 本轮写语义按钮（调拨/盘点/导出等）均为 guarded/提示型。
- 本轮未触发 POST/PUT/PATCH/DELETE 请求。
- 本轮未触发真实上传/下载/导出/打印请求。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- other P1/P2 started: NO
- allowlist outside modified: NO
- real write routes added: NO
- warehouse write permission relaxed: NO
- upload/download/export/print real requests: NO
- production/GitHub management actions: NO
- parked blockers released: NO
