# TASK-Z012B-42-REGRESSION｜Z012 基础资料前端交互独立回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Z012B-42-REGRESSION`
- source_task_id: `TASK-Z012B-41-IMPL`
- source_head: `4382dcc316efd170f8fae0aff9dbe7ea1738307d`
- selected_candidate_id: `Z012-CAND-007`
- module: `基础资料`
- yisuan_page: `客户 / 供应商 / 加工厂 / 仓库管理`
- 本轮仅做独立只读回归与证据补充，不修改产品代码，不执行 stage/commit/push。

## 2. 回归执行摘要
### 2.1 B41 既有证据复核
- B41 impl result JSON/TSV: `PASS`（14/14）。
- B41 browser result JSON: PASS（可解析）。

### 2.2 本轮路由与交互回归
- 回归路由命中：`8/8`。
- 目标路由：
  - `http://127.0.0.1:5173/foundation/customer`
  - `http://127.0.0.1:5173/foundation/supplier`
  - `http://127.0.0.1:5173/foundation/factory`
  - `http://127.0.0.1:5173/foundation/warehouse`
  - `http://127.0.0.1:5173/sales-inventory/references?tab=customers&parity=foundation-customer`
  - `http://127.0.0.1:5173/factory-statements/list?parity=foundation-supplier`
  - `http://127.0.0.1:5173/factory-statements/list?parity=foundation-factory`
  - `http://127.0.0.1:5173/warehouse?parity=foundation-warehouse`
- 截图：`8` 张，路径存在 `PASS`。

### 2.3 网络与门禁
- request_methods=['GET']
- write_request_count=0
- unexpected_write_request_count=0
- forbidden_request_count=0
- blocking_console_error_count=0
- blocking_response_error_count=0
- network_error_count=0
- expected_non_blocking_response_errors: 9 条（已单独归类，不外推后端稳定性闭合）。

## 3. 证据文件
- regression result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_foundation_data_interaction_regression_result.json`
- regression result TSV:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_foundation_data_interaction_regression_result.tsv`
- regression browser result JSON:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_foundation_data_interaction_regression_browser_result.json`
- screenshots:
  - `/tmp/task_z012b42_foundation_data_regression_screenshots`

## 4. 状态口径保持
- `full_browser_route_smoke_closed=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
