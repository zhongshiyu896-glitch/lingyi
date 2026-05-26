# TASK-Z036B-04-REGRESSION-CAND001 报表目录只读可见流回归报告

## 基本结论

- cycle_id: Z036
- candidate_id: Z036-CAND-001
- source_task: TASK-Z036B-03-IMPL
- result: PASS
- HEAD: 9a75e862c5a911ac75dd77e150eaa584519dd719
- code_modified_in_this_task: false
- next_task: TASK-Z036B-05-LEDGER-CAND001
- run_this_task: false

## 回归范围

- changed_files_observed:
  - 06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue
- 当前候选相关代码 diff 仍只在授权 report 文件范围内。
- api/report.ts 未改，未强行纳入 changed_files。
- backend_changed: false
- tests_changed: false
- candidate_pool_changed: false
- historical_dirty_touched: false
- log_control_dirty_touched: false
- residual_artifacts_touched: false
- z035_committed_product_files_touched: false

## 验证命令

- typecheck_command: npm run typecheck
- typecheck_workdir: 06_前端/lingyi-pc
- typecheck_exit_code: 0
- typecheck_summary: vue-tsc --noEmit -p tsconfig.json completed with no diagnostics

## 运行态回归证据

- evidence_dir: 04_测试与验收/测试证据/z036_cand001_report_catalog_visible_flow_regression
- screenshot_reused_or_recaptured: recaptured
- screenshot: 04_测试与验收/测试证据/z036_cand001_report_catalog_visible_flow_regression/report_catalog_regression_fullpage.png
- screenshot_skip_reason:
- runtime_evidence: 04_测试与验收/测试证据/z036_cand001_report_catalog_visible_flow_regression/runtime_regression_evidence.json
- manifest: 04_测试与验收/测试证据/z036_cand001_report_catalog_visible_flow_regression/manifest.json

复核结果：
- /reports/catalog: PASS
- /financial/financialReport/customerReconciliationReport: PASS，redirect 到 /reports/catalog?parity=customer-reconciliation
- /reportManage/collaborationReport/factoryProductStockReport: PASS，redirect 到 /reports/catalog?parity=factory-product-stock

## Anchors

- report-catalog-page: PASS
- report-catalog-query-form: PASS
- report-catalog-table: PASS
- report-catalog-detail-preview: PASS
- report-catalog-export-guarded-button: PASS
- report-catalog-permission-state: PASS
- report-catalog-parity-hint: PASS on redirected parity routes

## 401 与只读 fallback

- console_401_errors_observed_count: 4
- network_401_responses_observed_count: 4
- 401 URLs:
  - http://127.0.0.1:5173/api/auth/me
  - http://127.0.0.1:5173/api/reports/catalog?source_module=finance&report_type=financial
  - http://127.0.0.1:5173/api/reports/employee-task-statistics
  - http://127.0.0.1:5173/api/reports/approval-reports
- runtime_readonly_fallback_risk: true
- classification: runtime_readonly_fallback_risk
- affects_visible_acceptance: false
- write_chain_success: false
- permission_misread_as_success: false

401 仅影响未登录态读取接口，页面回落到本地只读 fallback，报表目录、详情预览、员工任务统计、审批统计仍可见；导出、确认、审核、打印、上传等入口仍为 guarded 或 disabled，不构成写链路成功或权限通过。

## 风险保留

- B28 shell_wrapper_anomaly_preserved: true
- Z033 skipped-only risk: skipped_only_evidence=true, actual_passed_count=0, skipped_count=4
- screenshot_missing_risk_for_Z035: true

## 禁止动作确认

- stage/commit/push/tag/PR/release: false
- cleanup/reset/restore/checkout/stash/clean/delete: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false
- new_candidate_started: false
