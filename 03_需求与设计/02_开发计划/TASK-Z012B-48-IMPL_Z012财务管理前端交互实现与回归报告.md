# TASK-Z012B-48-IMPL｜Z012 财务管理前端交互实现与本地只读验证报告

## 1. 任务与边界
- task_id: `TASK-Z012B-48-IMPL`
- source_task_id: `TASK-Z012B-47-PREP`
- source_head: `a1f712c1650a8141ca66fba937d610017c1ce350`
- selected_candidate_id: `Z012-CAND-008`
- module: `财务管理`
- yisuan_page: `银行流水 / 收付款相关页面`

本轮严格在 B47 allowlist 内实现前端只读交互与本地验证，不修改后端，不执行 `git add/commit/push`，不触发写请求。

## 2. 实际代码改动
变更文件（仅允许前端文件）：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`

未改动：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/*`

## 3. 实现说明
### 3.1 路由与 parity
- 新增/标准化财务只读入口别名：
  - `/finance/bank-flow -> /factory-statements/list?parity=finance-bank-ledger`
  - `/finance/receipts-payments -> /factory-statements/list?parity=finance-expense-payment`
  - `/finance/reconciliation -> /factory-statements/list?parity=finance-customer-reconciliation`
- 维持 `/factory-statements/list` 为财务只读语义承载页。

### 3.2 财务只读区块可测化
- 在 `FactoryStatementList.vue` 增加 finance parity 识别与归一化（canonical + 兼容）：
  - canonical：`finance-bank-ledger`、`finance-expense-payment`、`finance-customer-reconciliation`
  - 兼容：`finance-bank-flow`、`finance-receipts-payments`、`finance-reconciliation`
- 新增/稳定 parity hint testid：
  - `finance-bank-ledger-parity-hint`
  - `finance-expense-payment-parity-hint`
  - `finance-customer-reconciliation-parity-hint`
- 新增/稳定筛选 testid（查询/重置）：
  - `finance-bank-ledger-filter-form`、`finance-bank-ledger-query-button`、`finance-bank-ledger-reset-button`
  - `finance-expense-payment-filter-form`、`finance-expense-payment-query-button`、`finance-expense-payment-reset-button`
  - `finance-customer-reconciliation-filter-form`、`finance-customer-reconciliation-query-button`、`finance-customer-reconciliation-reset-button`
- 写动作 guard 统一为财务只读口径：
  - `guarded:readonly-finance`
  - create/cancel/payable-draft/confirm、导出、打印均禁用或只提示，不触发写请求。

## 4. 验证执行
- `npm run typecheck`: PASS
- `npm run build`: PASS
- 浏览器只读验证目标：
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-bank-ledger`
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-expense-payment`
  - `http://127.0.0.1:5173/factory-statements/list?parity=finance-customer-reconciliation`
  - `http://127.0.0.1:5173/finance/bank-flow`
  - `http://127.0.0.1:5173/finance/receipts-payments`
  - `http://127.0.0.1:5173/finance/reconciliation`
- 路由命中：`6/6 PASS`
- 网络门禁：
  - `request_methods=["GET"]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `blocking_response_error_count=0`
  - `network_error_count=0`
  - `export_endpoint_called=false`

## 5. 证据产物
- impl result JSON：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_impl_result.json`
- impl result TSV：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_impl_result.tsv`
- browser result JSON：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z012_frontend_interaction/z012_finance_interaction_browser_result.json`
- screenshots：
  - `/tmp/task_z012b48_finance_screenshots`

## 6. 说明与口径
- 本轮出现的本地 500 GET 错误已按 expected non-blocking 记录（`/api/auth/me` 与 `/api/factory-statements/*` 本地环境返回），未计入阻断指标。
- 状态锚点保持：
  - `full_browser_route_smoke_closed=false`
  - `production_readback_ready=false`
  - `go_live_ready=false`
  - `project_completion_claimed=false`
  - `remote_lifecycle_parked=true`
