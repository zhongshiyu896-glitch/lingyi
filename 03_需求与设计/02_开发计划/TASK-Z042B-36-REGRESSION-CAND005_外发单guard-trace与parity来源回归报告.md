# TASK-Z042B-36-REGRESSION-CAND005 回归报告

## 基线

- task_id: TASK-Z042B-36-REGRESSION-CAND005
- role: B Engineer
- candidate_id: Z042-CAND-005
- code_modified_in_this_task: false
- HEAD: 2be2fcf067cfdb8ef1b087ab19a6d6f7c5e934ed
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true

## 范围复核

- changed_files_observed:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- allowed_files_only: true
- api_subcontract_touched: false
- backend_api_added: false
- real_write_action_added: false
- read_only_boundary_preserved: true

## 运行态回归

- routes_checked:
  - /subcontract/list: 200
  - /subcontract/detail: 200
  - /materialPurchase/materialPurchaseProcess: 200
- material_purchase_parity_recorded: true
- materialPurchase final: /subcontract/list?parity=material-purchase
- list_screenshot: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/z042_cand005_subcontract_list_guard_trace_regression.png
- list_screenshot_png_dimensions: 1440x1200 PNG
- detail_screenshot: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/z042_cand005_subcontract_detail_guard_trace_regression.png
- detail_screenshot_png_dimensions: 1440x1200 PNG
- anchors_observed_count: 8
- anchors_all_observed: true

## Guard 与写请求观测

- guarded_entries_covered: true
- covered entries: 新建外发单、发料、回料、验货、结算预览、同步重试、导出、打印
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false
- auth_401_count: 3
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false
- guarded_readonly_not_write_success: true

## 验证

- typecheck_command: npm run typecheck
- typecheck_workdir: 06_前端/lingyi-pc
- typecheck_exit_code: 0
- worktree_check_pass: true
- dev_server_started: true
- dev_server_stopped: true
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## 风险字段保留

- current CAND005 baseline auth_401_count: 4
- current CAND005 B36 observed auth_401_count: 3
- Z042-CAND-004 fallback risk: auth_401_count=1
- Z042-CAND-003 fallback risk: auth_401_count=1
- Z042-CAND-002 fallback risk: auth_401_count=25
- Z042-CAND-001 fallback risk: preserved
- Z041/Z040/Z039/Z038 fallback risks: preserved
- B28 shell_wrapper_anomaly: preserved
- Z033 skipped_only: preserved
- Z035 screenshot_missing_risk: preserved
- remote_lifecycle_parked: true
- push_tag_pr_release: false
- production_readback: false
- go_live: false
- project_completion: false

## 证据

- route_evidence: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/route_evidence.json
- dom_anchors_evidence: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/dom_anchors_evidence.json
- guarded_readonly_state_evidence: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/guarded_readonly_state_evidence.json
- network_write_request_observation: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/network_write_request_observation.json
- screenshot_metadata: 04_测试与验收/测试证据/z042_cand005_subcontract_guard_trace_parity_regression/screenshot_metadata.json

next_task: TASK-Z042B-37-LEDGER-CAND005
