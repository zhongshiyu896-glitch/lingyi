# TASK-Z043B-10-PREP CAND002 报表目录导出资格说明边界冻结报告

## Boundary
- candidate_id: Z043-CAND-002
- title: 报表目录导出资格说明与 parity 分组只读可见流
- page_scope: 财务/协同报表 parity 入口与 /reports/catalog 导出资格说明
- routes: /financial/financialReport/customerReconciliationReport, /financial/financialProcess, /finance/bank-flow, /reportManage/collaborationReport/factoryProductStockReport, /reports/catalog
- allowed_files: 06_前端/lingyi-pc/src/router/index.ts, 06_前端/lingyi-pc/src/api/report.ts
- reused_source: Z042 / Z042-CAND-002 / 0fec11f8654d5c8ac6282a3d72ec1fb6fd831b15
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## Anchors And Guards
- required_anchors_count: 8
- required_anchors: report-parity-entry-page, report-parity-route-state, report-catalog-table, report-readonly-write-guard, z043-report-export-eligibility, z043-report-source-grouping, z043-report-disabled-download-reason, z043-report-final-route-link
- guarded_entries: 报表导出, 财务下载, 协同下载, 明细导出

## Evidence Requirement
- screenshot: /reports/catalog 页面截图
- route evidence: 4 条 parity routes 与 final catalog route evidence
- runtime DOM anchors: required 8/8
- guarded/readonly state: required
- write request observation: required; auth 401 only readonly fallback risk; guarded_readonly not write success
- typecheck: npm run typecheck, workdir=06_前端/lingyi-pc, exit_code recorded
- dev_server_started/dev_server_stopped recorded

## Legality
- allowed_files_status: {"06_前端/lingyi-pc/src/router/index.ts":{"exists":true,"dirty":false},"06_前端/lingyi-pc/src/api/report.ts":{"exists":true,"dirty":false}}
- route_source_status: {"/financial/financialReport/customerReconciliationReport":true,"/financial/financialProcess":true,"/finance/bank-flow":true,"/reportManage/collaborationReport/factoryProductStockReport":true,"/reports/catalog":true}
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- non_allowlisted_runtime_summary_continues_excluded: true

## Next
- next_task: TASK-Z043B-11-IMPL
