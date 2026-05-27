# TASK-Z044B-04-REGRESSION-CAND001 回归报告

## Summary

- candidate_id: Z044-CAND-001
- code_modified_in_this_task: false
- changed_files_observed: 06_前端/lingyi-pc/src/App.vue
- allowed_files_only: true
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## Route Evidence

- evidence: 04_测试与验收/测试证据/z044_cand001_global_local_gate_risk_notice_regression/route_evidence.json
- /home: HTTP 200, shell_visible=true
- /reports/catalog: HTTP 200, shell_visible=true
- /subcontract/list: HTTP 200, shell_visible=true

## Screenshot

- path: 04_测试与验收/测试证据/z044_cand001_global_local_gate_risk_notice_regression/home_regression_screenshot.png
- format: PNG
- dimensions: 1440x1200

## Runtime DOM Anchors

- evidence: 04_测试与验收/测试证据/z044_cand001_global_local_gate_risk_notice_regression/dom_anchors_evidence.json
- anchors_observed_count: 8
- anchors_all_observed: true

observed anchors:

- z044-global-local-gate-summary
- z044-global-dirty-scope-readback
- z044-global-residual-risk-badge
- z044-global-remote-gate-disclaimer
- z044-global-readonly-action-guard
- z044-global-evidence-readiness-entry
- z044-global-next-prep-recommendation
- z044-global-write-success-blocker

## Guarded Readonly State

- evidence: 04_测试与验收/测试证据/z044_cand001_global_local_gate_risk_notice_regression/guarded_readonly_state_evidence.json
- guarded_entries_covered: 全局确认, 门禁刷新, 继续准备说明
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false

## Network / Write Observation

- evidence: 04_测试与验收/测试证据/z044_cand001_global_local_gate_risk_notice_regression/network_write_request_observation.json
- auth_401_count: 6
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false

401 仅记录为 readonly fallback risk，不解释为权限通过或写成功。

## Typecheck

- command: npm run typecheck
- workdir: 06_前端/lingyi-pc
- exit_code: 0

## Dev Server

- dev_server_started: true
- requested_port: 5173
- actual_url: http://127.0.0.1:5174/
- dev_server_stopped: true

## Scope Guard

- backend_api_added: false
- real_write_action_added: false
- read_only_boundary_preserved: true
- cached_empty: true
- head_tag_empty: true
- git diff --check: PASS

## Risk Fields

- Z044-CAND-001 B03 auth_401_count: 6 readonly fallback risk.
- Z044-CAND-001 B04 observed auth_401_count: 6 readonly fallback risk.
- Z043 fallback risks preserved: CAND005 4/4, CAND004 1/1, CAND003 1/1, CAND002 30/30, CAND001 2/2.
- prior non-allowlisted summary/metadata: continue excluded.
- Z042/Z041/Z040/Z039/Z038 fallback risks: preserved.
- guarded_readonly_not_write_success: true.
- B28 shell_wrapper_anomaly: preserved.
- Z033 skipped_only: preserved.
- Z035 screenshot_missing_risk: preserved.
- remote_lifecycle_parked: true.
- push_tag_pr_release: false.
- production_readback: false.
- go_live: false.
- project_completion: false.
- next_gate_blocked_pending_explicit_authorization: true.

## Forbidden Actions

- code_changed: false
- stage_performed: false
- commit_performed: false
- push/tag/PR/release: false
- cleanup/reset/restore: false
- Z044-CAND-002 started: false
- remote_lifecycle_released: false
- prior non-allowlisted summary/metadata modified: false

## Next

- next_task: TASK-Z044B-05-LEDGER-CAND001
