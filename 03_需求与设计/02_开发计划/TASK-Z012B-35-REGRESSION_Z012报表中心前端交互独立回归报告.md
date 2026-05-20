# TASK-Z012B-35-REGRESSION｜Z012 报表中心前端交互独立本地回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Z012B-35-REGRESSION`
- source_task_id: `TASK-Z012B-34-IMPL`
- source_head: `1583bf3c8c7f5180578a83e4de77a39b7a75bfc8`
- selected_candidate_id: `Z012-CAND-006`
- module: `报表中心`
- yisuan_page: `资金计划报表 / 员工任务统计表 / 加工成品库存报表`
- 本轮约束：
  - 不修改产品代码；
  - 仅做独立回归与证据产出；
  - GET-only；
  - 不做 stage/commit/push、不做生产或远端动作。

## 2. 独立回归执行摘要
### 2.1 B34 既有证据复核
- `z012_report_center_interaction_impl_result.json` 可解析。
- `z012_report_center_interaction_impl_result.tsv` 与 JSON entries 对齐：`15/15`。
- `z012_report_center_interaction_browser_result.json` 可解析。
- B34 browser result 中截图路径 `6/6` 存在。

### 2.2 本轮 typecheck/build
- 在 `06_前端/lingyi-pc` 执行：
  - `npm run typecheck`: PASS
  - `npm run build`: PASS

### 2.3 本轮浏览器只读回归
- 请求目标（任务要求）：
  - `http://127.0.0.1:5173/financial/financialReport/customerReconciliationReport`
  - `http://127.0.0.1:5173/financial/financialProcess`
  - `http://127.0.0.1:5173/reportManage/collaborationReport/factoryProductStockReport`
  - `http://127.0.0.1:5173/reports/catalog?parity=customer-reconciliation`
  - `http://127.0.0.1:5173/reports/catalog?parity=factory-product-stock`
- 运行目标（实际）：
  - `http://127.0.0.1:5182/financial/financialReport/customerReconciliationReport`
  - `http://127.0.0.1:5182/financial/financialProcess`
  - `http://127.0.0.1:5182/reportManage/collaborationReport/factoryProductStockReport`
  - `http://127.0.0.1:5182/reports/catalog?parity=customer-reconciliation`
  - `http://127.0.0.1:5182/reports/catalog?parity=factory-product-stock`
- runtime 说明：
  - 本轮使用独立本地回归运行时 `5182`（避免复用未知来源的 `5173` 现有进程）。
- 浏览器证据：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_report_center_regression_browser_result.json`
- 截图目录：
  - `/tmp/task_z012b35_report_center_regression_screenshots`
- 关键结果：
  - `request_methods=["GET"]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `blocking_response_error_count=0`
  - `network_error_count=0`
  - `customer_reconciliation_parity_hint=PASS`
  - `factory_product_stock_parity_hint=PASS`
  - `finance_catalog_filter_interaction=PASS`
  - `report_detail_preview=PASS`
  - `employee_task_filter_interaction=PASS`
  - `employee_task_detail_preview=PASS`
  - `guarded_export_print_upload_actions=PASS`
  - `empty_state_or_error_state_semantics=PASS`
  - `export_endpoint_called=false`
  - `screenshot_count=6`，`valid_target_screenshot_count=5`

## 3. 结果文件
- regression result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_report_center_regression_result.json`
- regression result TSV:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_report_center_regression_result.tsv`
- regression browser result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_report_center_regression_browser_result.json`

## 4. 状态口径保持
- `full_browser_route_smoke_closed=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
