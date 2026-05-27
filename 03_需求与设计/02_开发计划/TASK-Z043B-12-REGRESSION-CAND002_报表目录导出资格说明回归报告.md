# TASK-Z043B-12-REGRESSION-CAND002 报表目录导出资格说明回归报告

## Summary
- code_modified_in_this_task: false
- changed_files_observed: 06_前端/lingyi-pc/src/router/index.ts, 06_前端/lingyi-pc/src/api/report.ts
- allowed_files_only: true
- ReportCatalog.vue touched: false
- read_only_boundary_preserved: true

## Runtime Regression Evidence
- routes_checked: /financial/financialReport/customerReconciliationReport, /financial/financialProcess, /finance/bank-flow, /reportManage/collaborationReport/factoryProductStockReport, /reports/catalog
- route_http_statuses: {"/financial/financialReport/customerReconciliationReport":{"http_status":200,"final_path":"/reports/catalog","final_catalog_route":true,"z043_visible":true},"/financial/financialProcess":{"http_status":200,"final_path":"/reports/catalog","final_catalog_route":true,"z043_visible":true},"/finance/bank-flow":{"http_status":200,"final_path":"/reports/catalog","final_catalog_route":true,"z043_visible":true},"/reportManage/collaborationReport/factoryProductStockReport":{"http_status":200,"final_path":"/reports/catalog","final_catalog_route":true,"z043_visible":true},"/reports/catalog":{"http_status":200,"final_path":"/reports/catalog","final_catalog_route":true,"z043_visible":true}}
- screenshot: 04_测试与验收/测试证据/z043_cand002_report_parity_export_eligibility_regression/reports_catalog_z043_export_eligibility_regression.png (1440x1200, PNG)
- anchors_observed: 8/8
- guarded_entries_covered: 报表导出、财务下载、协同下载、明细导出
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false
- auth_401_count: 30
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false

## Typecheck And Git Checks
- typecheck: npm run typecheck, workdir=06_前端/lingyi-pc, exit_code=0
- cached_empty: true
- head_tag_empty: true
- git diff --check: PASS
- dev_server_started: true
- dev_server_stopped: true

## Risk Fields Preserved
- CAND002 B11 auth_401_count=30 readonly fallback risk
- CAND002 B12 auth_401_count=30 readonly fallback risk
- Z043-CAND-001 readonly fallback risk: B03/B04 auth_401_count=2/2
- CAND001 runtime_summary.json: non-allowlisted evidence summary, excluded
- Z042/Z041/Z040/Z039/Z038 fallback risks preserved
- guarded_readonly_not_write_success=true
- B28 shell_wrapper_anomaly; Z033 skipped_only; Z035 screenshot_missing_risk
- remote_lifecycle_parked=true; push_tag_pr_release=false; production_readback=false; go_live=false; project_completion=false
