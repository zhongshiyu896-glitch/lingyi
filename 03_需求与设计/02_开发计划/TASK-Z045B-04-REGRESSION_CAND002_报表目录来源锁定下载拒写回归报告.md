# TASK-Z045B-04-REGRESSION-CAND002 回归报告

## 1. scope confirmation

- task_id: `TASK-Z045B-04-REGRESSION-CAND002`
- candidate_id: `Z045-CAND-002`
- branch: `codex/sprint4-seal`
- head: `0c114a3b8addc096aad1e976969d3c0e58df6e14`
- code_modified_in_this_task=false
- changed_files_observed:
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/api/report.ts`
- allowed_files_only=true
- `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue` touched=false
- backend_api_added=false
- real_write_action_added=false
- read_only_boundary_preserved=true
- stage_performed=false
- commit_performed=false
- remote_lifecycle_released=false

## 2. evidence check

- route evidence: 5/5 HTTP 200，final_path 均为 `/reports/catalog`
  - `/financial/financialReport/customerReconciliationReport`
  - `/financial/financialProcess`
  - `/finance/bank-flow`
  - `/reportManage/collaborationReport/factoryProductStockReport`
  - `/reports/catalog`
- route evidence file: `04_测试与验收/测试证据/z045_cand002_report_source_lock_download_denial_regression/route_evidence.json`
- screenshot: `04_测试与验收/测试证据/z045_cand002_report_source_lock_download_denial_regression/reports_catalog_regression_1440x1200.png`
- screenshot size: PNG 1440x1200
- runtime DOM anchors observed=8/8:
  - `z045-report-source-lock-readback`
  - `z045-report-download-denial-reason`
  - `z045-report-final-route-audit`
  - `z045-report-catalog-readonly-index`
  - `z045-report-export-safety-badge`
  - `z045-report-guarded-download-matrix`
  - `z045-report-network-write-blocker`
  - `z045-report-write-success-blocker`
- DOM evidence file: `04_测试与验收/测试证据/z045_cand002_report_source_lock_download_denial_regression/runtime_dom_anchors_evidence.json`
- guarded readonly covered:
  - 报表导出 guarded/readonly
  - 财务下载 guarded/readonly
  - 协同下载 guarded/readonly
  - 明细导出 guarded/readonly
- guarded top fields:
  - dataReadonlyBoundary=true
  - dataWriteRequestSuccessAllowed=false
  - dataRealWriteActionAdded=false
- guarded evidence file: `04_测试与验收/测试证据/z045_cand002_report_source_lock_download_denial_regression/guarded_readonly_state_evidence.json`
- network/write:
  - auth_401_count=25
  - runtime_readonly_fallback_risk=true
  - write_requests_observed_count=0
  - write_request_success_observed=false
  - write_request_success_allowed=false
- network evidence file: `04_测试与验收/测试证据/z045_cand002_report_source_lock_download_denial_regression/network_write_observation.json`
- typecheck:
  - command=`npm run typecheck`
  - workdir=`06_前端/lingyi-pc`
  - exit_code=0
- dev_server_started=true
- dev_server_stopped=true

## 3. direction compliance

- mainline_or_auxiliary=mainline
- user_visible_frontend_improvement=true
- interaction_experience_improvement: 报表目录 readback 继续可见来源分组、下载禁用原因、导出锁定提示与 final catalog route readback，用户可在目录上下文判断为什么不能下载或导出。
- one_to_one_ui_contract_focus: 对齐报表目录 UI 合同中的来源分组、禁用下载态、final route readback 与导出入口状态。
- guard_is_supporting_not_primary=true

## 4. residual risk

- Z045-CAND-002 B03 auth_401_count=25 readonly fallback risk preserved.
- Z045-CAND-002 B04 observed auth_401_count=25 readonly fallback risk.
- Z044 fallback risks preserved: CAND005 3/4, CAND004 1/1, CAND003 1/1, CAND002 25/25, CAND001 6/6.
- Z043 fallback risks preserved.
- Z042-Z038 fallback risks preserved.
- prior non-allowlisted summary/metadata 继续排除。
- B28 shell_wrapper_anomaly preserved.
- Z033 skipped_only preserved.
- Z035 screenshot_missing_risk preserved.
- guarded_readonly_not_write_success=true.
- remote_lifecycle_parked=true.
- push_tag_pr_release=false.
- production_readback=false.
- go_live=false.
- project_completion=false.
- next_gate_blocked_pending_explicit_authorization=true.

## 5. next_task

`TASK-Z045B-05-LEDGER-CAND002`
