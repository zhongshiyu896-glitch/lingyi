# TASK-Y45B-01-IMPL `/sales-inventory/stock-ledger` 物料调仓 1:1 首版实现与浏览器回归报告

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-Y45B-01-IMPL
ROLE: B Engineer

## SCOPE

- changed_files:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Y45B-01-IMPL_sales_inventory_stock_ledger物料调仓1to1首版实现与浏览器回归报告.md`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`
- allowlist_only: YES
- staged_area: EMPTY
- next_candidates_started: NO

## IMPLEMENTATION

- frontend_section:
  - 在 `SalesInventoryStockLedger.vue` 新增 `material-transfer-section`（物料调仓只读区块）。
  - 补齐筛选：物料编码、关键词、来源仓、目标仓、状态、开始日期、结束日期。
  - 补齐结构：列表、汇总标签、分页、空态、错误态、权限/禁用态。
- frontend_api:
  - 在 `sales_inventory.ts` 新增 `fetchSalesInventoryMaterialTransfers`，请求 `GET /api/sales-inventory/material-transfers`。
  - 新增 `MaterialTransferQuery/Item/Data` 类型定义。
- backend_route:
  - 在 `routers/sales_inventory.py` 新增只读接口 `GET /api/sales-inventory/material-transfers`。
  - 权限链路沿用 `SALES_INVENTORY_READ` 与 scope 校验。
- backend_schema_service:
  - 在 `schemas/sales_inventory.py` 新增 `MaterialTransferItem/MaterialTransferData`。
  - 在 `services/sales_inventory_service.py` 新增 `get_material_transfers()` 只读查询与本地只读 seed 数据。
- static_route_before_dynamic_route:
  - `@router.get("/material-transfers")` 行号 `307`，位于 `@router.get("/items/{item_code}/stock-summary")` 行号 `373` 与 `@router.get("/items/{item_code}/stock-ledger")` 行号 `428` 之前，未被动态路由遮蔽。
- write_routes_added: NO
- write_actions_guarded: YES
- shared_route_scope_expanded: NO

## PRESERVED_CHECKS

- p0_finished_goods_stock_ledger_preserved: true
- existing_stock_ledger_filters_table_summary_preserved: true
- api_permission_state_preserved: true
- empty_error_permission_state: true
- write_actions_guarded: true

## BROWSER_EVIDENCE

- 说明：本地 `mock_backend` 对 `sales_inventory` 模块权限回包固定为 `bom` 动作；浏览器回归脚本对 `GET /api/auth/actions?module=sales_inventory` 与只读数据端点进行了 route-level mock，仅用于 UI 回归取证，不修改产品代码与权限实现。
- result_json: `/tmp/task_y45b_01_impl_20260504T145531Z_browser_results.json`
- screenshots_dir: `/tmp/task_y45b_01_impl_20260504T145531Z_screenshots`
- screenshots_count: 6
- route_open: true
- first_screen_visible: true
- filters_present: true
- material_transfer_fields_mapped: true
- buttons_mapped: true
- status_tags_mapped: true
- empty_state: true
- error_state: true
- permission_or_disabled_state: true
- write_request_count: 0
- upload_download_export_print_request_count: 0
- unexplained_console_errors_total: 0
- unexplained_network_4xx_5xx_total: 0

## VALIDATION

- npm run precheck:dev-runtime: PASS
- npm run typecheck: PASS
- npm run verify: PASS
- git diff --check: PASS（本轮 allowlist 文件 + 报告 + 工程师日志）
- tag_at_head: EMPTY
- pr_list: `[]`
- release_list: EMPTY

## FORBIDDEN_ACTIONS

- git add/commit/push: NO
- PR/merge/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- parked_blockers_released: NO

NEXT_ROLE: A Technical Architect
