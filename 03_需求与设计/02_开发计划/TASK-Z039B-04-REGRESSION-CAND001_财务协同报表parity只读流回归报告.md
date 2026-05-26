# TASK-Z039B-04-REGRESSION-CAND001 财务协同报表 parity 只读流回归报告

## 任务结论

- task_id: TASK-Z039B-04-REGRESSION-CAND001
- candidate_id: Z039-CAND-001
- code_modified_in_this_task: false
- read_only_boundary_preserved: true
- real_write_action_added: false
- backend_api_added: false
- remote_lifecycle_parked: true

## 范围复核

- 当前候选相关 diff 仍只包含允许文件:
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/api/report.ts`
- `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue` touched=false
- 未修改 `07_后端`
- 未修改 candidate pool
- 未 stage / commit / push

## 运行态回归证据

- dev_server_started: true
- dev_server_stopped: true
- base_url: `http://127.0.0.1:5174`
- final_catalog_route: `/reports/catalog`
- final_catalog_route_status: HTTP 200
- screenshot: `04_测试与验收/测试证据/z039_cand001_report_parity_readonly_regression/report_parity_regression_fullpage.png`
- screenshot_format: PNG
- screenshot_size: 1440x2791
- runtime evidence: `04_测试与验收/测试证据/z039_cand001_report_parity_readonly_regression/report_parity_regression_dom_guard_network.json`

## Route 回归

以下 6 条 parity routes 均 HTTP 200，并最终进入 `/reports/catalog`:

- `/financial/financialReport/customerReconciliationReport`
- `/financial/financialProcess`
- `/finance/bank-flow`
- `/finance/receipts-payments`
- `/finance/reconciliation`
- `/reportManage/collaborationReport/factoryProductStockReport`

## Anchors 与 Guard

- anchors_observed: 8/8
- anchors_all_observed: true
- guarded_write_controls:
  - `guarded:readonly-report-export`
  - `guarded:readonly-report-action`
  - `guarded:readonly-report-print`
  - `guarded:readonly-report-upload`
  - `guarded:report-finance-download-readonly`
  - `guarded:report-collaboration-download-readonly`
  - `guarded:report-detail-export-readonly`
  - `dataReadonlyBoundary=true`
  - `dataWriteRequestSuccessAllowed=false`

## 写请求观察

- auth_401_count: 33
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false
- guarded_readonly_not_write_success: true

## 验证命令

- `npm run typecheck`，workdir=`06_前端/lingyi-pc`，exit_code=0
- `git diff --check` PASS

## 风险字段保留

- current auth_401_count=33 仅作为 readonly fallback risk，不解释为权限通过或写成功
- Z038-CAND-001/Z038-CAND-002 fallback risks 保留
- prior readonly fallback risks 保留
- guarded_readonly_not_write_success 保留
- B28 shell_wrapper_anomaly 保留
- Z033 skipped_only 保留
- Z035 screenshot_missing_risk 保留
