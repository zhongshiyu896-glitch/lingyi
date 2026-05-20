# TASK-Z012B-28-REGRESSION｜Z012 成品进销存前端交互独立本地回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Z012B-28-REGRESSION`
- source_task_id: `TASK-Z012B-27-IMPL`
- selected_candidate_id: `Z012-CAND-005`
- module: `成品进销存`
- yisuan_page: `成品库存 / 成品进销存报表`
- 路由语义基线：`/productStock/productStockList -> /warehouse?parity=product-stock`
- 本轮约束：
  - 不修改产品代码；
  - 仅做独立回归与证据产出；
  - GET-only + DEV_AUTH_LOCAL；
  - 不做 stage/commit/push、不做生产或远端动作。

## 2. 独立回归执行摘要
### 2.1 B27 既有证据复核
- `z012_finished_goods_stock_interaction_impl_result.json` 可解析。
- `z012_finished_goods_stock_interaction_impl_result.tsv` 与 JSON entries 对齐：`13/13`。
- `z012_finished_goods_stock_interaction_browser_result.json` 可解析。
- B27 browser result 中截图路径 `4/4` 存在。

### 2.2 本轮 typecheck/build
- 在 `06_前端/lingyi-pc` 执行：
  - `npm run typecheck`: PASS
  - `npm run build`: PASS

### 2.3 本轮浏览器只读回归
- 请求目标（任务要求）：
  - `http://127.0.0.1:5173/productStock/productStockList`
  - `http://127.0.0.1:5173/warehouse?parity=product-stock`
  - `http://127.0.0.1:5173/warehouse`
- 运行目标（实际）：
  - `http://127.0.0.1:5181/productStock/productStockList`
  - `http://127.0.0.1:5181/warehouse?parity=product-stock`
  - `http://127.0.0.1:5181/warehouse`
- runtime 说明：
  - `5173` 为非本项目运行时占用，本轮回归切换到本项目 dev server `5181`。
- 浏览器证据：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_regression_browser_result.json`
- 截图目录：
  - `/tmp/task_z012b28_finished_goods_stock_regression_screenshots`
- 关键结果：
  - `request_methods=["GET"]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `blocking_response_error_count=0`
  - `network_error_count=0`
  - `parity_hint_status=PASS`
  - `filter_interaction_status=PASS`
  - `reset_interaction_status=PASS`
  - `kpi_list_linkage_status=PASS`
  - `readonly_detail_status=PASS`（`readonly_warning_path` 等价只读详情路径）
  - `guarded_write_actions_status=PASS`
  - `screenshot_count=4`，`valid_target_screenshot_count=3`
  - `expected_non_blocking_errors`：`/api/auth/me 500`（`DEV_AUTH_LOCAL` 预期非阻断）

## 3. 结果文件
- regression result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_regression_result.json`
- regression result TSV:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_regression_result.tsv`
- regression browser result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finished_goods_stock_regression_browser_result.json`

## 4. 状态口径保持
- `full_browser_route_smoke_closed=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
