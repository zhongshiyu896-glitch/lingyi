# TASK-Z012B-49-REGRESSION｜Z012 财务管理前端交互独立回归报告

## 1. 任务与边界
- task_id: `TASK-Z012B-49-REGRESSION`
- source_task_id: `TASK-Z012B-48-FIX1`
- source_head: `a1f712c1650a8141ca66fba937d610017c1ce350`
- selected_candidate_id: `Z012-CAND-008`

本轮仅执行独立只读回归与证据补充，不修改产品代码，不执行 `git add/commit/push`，不触发远端与生产动作。

## 2. 回归输入复核
- B48 FIX1 result JSON/TSV 对齐：`14/14 PASS`
- B48 browser result JSON 可解析：PASS
- B48 canonical parity 与截图目录修复已生效：
  - parity canonical：`finance-bank-ledger`、`finance-expense-payment`、`finance-customer-reconciliation`
  - 截图目录：`/tmp/task_z012b48_finance_screenshots`

## 3. 本轮回归路由覆盖
- canonical direct:
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-bank-ledger`
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-expense-payment`
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-customer-reconciliation`
- alias entry:
  - `http://127.0.0.1:5173/finance/bank-flow`
  - `http://127.0.0.1:5173/finance/receipts-payments`
  - `http://127.0.0.1:5173/finance/reconciliation`

回归命中结果：
- `route_hit_count=6/6`
- `canonical_route_checks=true`
- `alias_routes_to_canonical_parity=true`

## 4. 网络与副作用门禁
- `request_methods=["GET"]`
- `write_request_count=0`
- `unexpected_write_request_count=0`
- `forbidden_request_count=0`
- `blocking_console_error_count=0`
- `blocking_response_error_count=0`
- `network_error_count=0`
- `export_endpoint_called=false`

说明：本地 `/api/auth/me` 与 `/api/factory-statements/*` 的 500 已记录为 expected non-blocking response errors，不外推为生产 readback 闭合。

## 5. 截图与证据
- 回归截图目录：`/tmp/task_z012b49_finance_regression_screenshots`
- 截图数量：6（路径均存在）
- browser evidence：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_regression_browser_result.json`

## 6. 产物清单
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z012B-49-REGRESSION_Z012财务管理前端交互独立回归报告.md`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_regression_result.json`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_regression_result.tsv`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_regression_browser_result.json`
- `/tmp/task_z012b49_finance_regression_screenshots`

## 7. 状态锚点
- `full_browser_route_smoke_closed=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
