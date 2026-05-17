# TASK-Z004B-03-IMPL CAND01 sales_inventory guarded-to-real 最小实现与浏览器回归报告

## 1. 任务与边界
- task_id: `TASK-Z004B-03-IMPL`
- source_head: `b83e708d99c83e4f5259f55d42cdb1e24715effe`
- source_subject: `chore: seal z003 local phase closeout gates`
- selected_candidate_id: `TASK-Z004B-CAND-01`
- candidate_type: `guarded_to_real_interaction_gap`
- module: `sales_inventory`
- boundary_source_task: `TASK-Z004B-02-PREP`
- remote_lifecycle_parked: `true`

本次仅在冻结边界内执行最小实现、浏览器回归、接口回归与零残留核对；未执行 stage/commit/push/PR/tag/release/cleanup/reset/restore/clean/delete/revert。

## 2. 产品改动范围（严格 allowlist）
仅修改以下 3 个前端 Vue 文件：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`

实现要点：
- 销售订单页将 `下单/获取订单` 从 guarded 按钮接通到现有本地 drafts create/read 流程。
- 新增 `库存台账回读`、`参考资料回读` 跳转（仅透传查询参数，不新增 API）。
- 台账页与参考页支持读取路由 query 预填，以支持从订单页的最小回读闭环。

## 3. 允许读写端点核对
allowed write endpoints（2）：
- `POST /api/sales-inventory/sales-orders/drafts`
- `POST /api/sales-inventory/sales-orders/drafts/{draft_id}/cancel`

allowed read endpoints（10）：
- `GET /api/sales-inventory/sales-orders`
- `GET /api/sales-inventory/sales-orders/{name}`
- `GET /api/sales-inventory/sales-order-fulfillment`
- `GET /api/sales-inventory/items/{item_code}/stock-summary`
- `GET /api/sales-inventory/items/{item_code}/stock-ledger`
- `GET /api/sales-inventory/aggregation`
- `GET /api/sales-inventory/customers`
- `GET /api/sales-inventory/warehouses`
- `GET /api/sales-inventory/material-transfers`
- `GET /api/sales-inventory/material-counts`

## 4. 浏览器真实回归结果
覆盖路由：
- `/sales-inventory/sales-orders`
- `/sales-inventory/stock-ledger`
- `/sales-inventory/references`

desktop/mobile 覆盖：
- 三条路由均有 desktop + mobile 截图。

写请求证据（浏览器）：
- browser_approved_write_request_count: `2`
  - create: `POST /api/sales-inventory/sales-orders/drafts`（201）
  - cancel: `POST /api/sales-inventory/sales-orders/drafts/{draft_id}/cancel`（200）
- unexpected_write_request_count: `0`
- forbidden_write_request_count: `0`
- ERPNext / worker / production / import-export-download-upload-print: 全部 `0`

回读闭环：
- create 后订单详情可读。
- cancel 后详情 `status=Cancelled`，`docstatus=2`，满足可逆闭合。

截图：
- screenshot_dir: `/tmp/task_z004b03_screenshots`
- screenshots_count(JSON): `8`
- PNG 文件数(目录): `8`

## 5. API 回归与 fail-closed
approved write（API）：
- api_regression_approved_write_request_count: `2`
  - 成功 create（201）
  - 成功 cancel（200）

fail-closed 用例：
- `FC-01-IDEMPOTENCY-MISMATCH`：409，`SALES_ORDER_IDEMPOTENCY_CONFLICT`
- `FC-02-OPERATION-MISMATCH`：409，`SALES_ORDER_IDEMPOTENCY_CONFLICT`
- `FC-03-COMPANY-MISMATCH`：409，`SALES_ORDER_IDEMPOTENCY_CONFLICT`
- fail_closed_case_count: `3`
- db_write_on_failed_gate_count: `0`

## 6. rollback / zero_residual
- cancel_cleanup_executed: `true`
- zero_residual_check_executed: `true`
- zero_residual: `true`
- residual_scan_result: `no_new_residual`
- residual 表计数：
  - non_cancelled_draft_count: `0`
  - pending_outbox_count: `0`
  - active_outbox_event_count: `0`
  - uncancelled_source_row_count: `0`

说明：`source_row_count=1` 且 `cancelled_count=1` 为已作废草稿留痕，不属于残留占用。

## 7. 质量门与验证
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS

## 8. 产物清单
- 主报告（本文件）
  `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z004B-03-IMPL_CAND01_sales_inventory_guarded_to_real最小实现与浏览器回归报告.md`
- 主证据 JSON
  `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_03_cand01_sales_inventory_guarded_to_real_evidence.json`
- 浏览器证据
  `/tmp/task_z004b03_browser_result.json`
- API 回归证据
  `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_03_cand01_api_regression_result.json`
- 零残留证据
  `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_03_cand01_zero_residual_result.json`
- 截图目录
  `/tmp/task_z004b03_screenshots/`

## 9. 合规声明
- 未修改 allowlist 外产品代码。
- 未修改 `src/api/**`、`router`、`stores`、后端、tests、worker、ERPNext、dist、request_id。
- 未执行 git add / commit / push / PR / tag / release / cleanup。
