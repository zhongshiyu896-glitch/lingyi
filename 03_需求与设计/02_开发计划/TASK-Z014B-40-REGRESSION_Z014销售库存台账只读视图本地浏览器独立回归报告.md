# TASK-Z014B-40-REGRESSION｜Z014销售库存台账只读视图本地浏览器独立回归报告

## 范围

- selected_candidate_id: Z014-CAND-016
- module: 销售库存台账只读视图
- source_head: 0de9b4dad8d76032a5294e15276003fcff243bd7
- CODE_CHANGED: NO
- route: http://127.0.0.1:5173/sales-inventory/stock-ledger?parity=material-stock

本轮为本地浏览器 evidence-only 独立回归。未修改产品代码、后端代码或控制面；未 stage、未 commit、未 push。

## 回归证据

- B39 impl JSON/TSV: 22/22 PASS
- B40 regression JSON/TSV: 23/23 PASS
- route_hit_count: 1/1
- screenshot_count: 4
- screenshot_dir: /tmp/task_z014b40_sales_inventory_stock_ledger_regression_screenshots
- request_methods: ["GET"]
- write_request_count: 0
- unexpected_write_request_count: 0
- forbidden_request_count: 0
- blocking_console_error_count: 0
- blocking_response_error_count: 0
- network_error_count: 0
- export_download_print_sync_called: false
- sales_order_draft_write_called: false
- stock_adjustment_or_transfer_write_called: false

## 只读交互复核

- 筛选/查询: {"name":"filter_or_query","found":true,"clicked":true,"label":"查询"}
- 重置: {"name":"reset","found":true,"clicked":true,"label":"重置"}
- 分页: {"name":"pagination_next","found":true,"clicked":true,"label":"Next Month"}
- 详情抽屉: {"name":"detail_drawer","found":false,"clicked":false}
- guarded anchor count: 71
- guarded action handling: guard anchors inspected without clicking dangerous actions

## Expected Non-blocking

- response 500: http://127.0.0.1:5173/api/auth/me；local auth readback non-blocking only
- response 404: http://127.0.0.1:5173/favicon.ico；browser favicon request non-blocking only

上述仅为本地 auth/readback 或浏览器资源请求，不代表生产 readback、go-live、远端生命周期或真实业务闭合。

## 截图

- route_initial: /tmp/task_z014b40_sales_inventory_stock_ledger_regression_screenshots/01_route_initial.png
- after_filter_reset: /tmp/task_z014b40_sales_inventory_stock_ledger_regression_screenshots/02_after_filter_reset.png
- after_pagination_detail: /tmp/task_z014b40_sales_inventory_stock_ledger_regression_screenshots/03_after_pagination_detail.png
- guarded_anchors_readonly: /tmp/task_z014b40_sales_inventory_stock_ledger_regression_screenshots/04_guarded_anchors_readonly.png

## 禁止动作确认

- product code edits: NO
- backend edits: NO
- control-plane edits: NO
- POST / PUT / PATCH / DELETE: NO
- sales order draft write: NO
- stock adjustment or transfer write: NO
- export/download/print/sync side effect: NO
- stage/commit/push: NO
- PR/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- production account / ERPNext production / real business write: NO
- parked blockers released: NO
