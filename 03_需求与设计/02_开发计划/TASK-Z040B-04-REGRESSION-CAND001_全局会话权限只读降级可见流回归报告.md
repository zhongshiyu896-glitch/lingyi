# TASK-Z040B-04-REGRESSION-CAND001 回归报告

## Scope

- candidate_id: Z040-CAND-001
- code_modified_in_this_task: false
- changed_files_observed: 06_前端/lingyi-pc/src/App.vue
- permission_store_changed: false
- auth_api_changed: false
- forbidden_router_or_views_touched: false
- read_only_boundary_preserved: true
- real_write_action_added: false
- backend_api_added: false

## Runtime Regression

- routes: /home, /permissions/governance, /reports/catalog
- route_status_by_route: all HTTP 200
- shell_visible_by_route: all true
- screenshot: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/home_global_readonly_shell_regression.png
- screenshot_size: 1440x1200 PNG
- route_evidence: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/route_evidence.json
- dom_anchors: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/dom_anchors.json
- guarded_state: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/guarded_state.json
- network_observation: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/network_observation.json
- runtime_summary: 04_测试与验收/测试证据/z040_cand001_global_readonly_shell_regression/runtime_summary.json

## Anchors

- anchors_observed: 8/8
- global-readonly-shell
- global-permission-state
- global-auth-fallback-state
- global-route-readonly-badge
- global-permission-actions-preview
- global-auth-refresh-guard
- global-readonly-write-guard
- global-remote-lifecycle-parked

## Guard And Network

- guarded_write_controls: 权限刷新; 模块动作重载; 只读降级确认
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false
- auth_401_count: 6
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false
- auth 401 仅作为 readonly fallback risk，不解释为权限通过或写成功。

## Verification

- typecheck_command: npm run typecheck
- typecheck_exit_code: 0
- git diff --check: PASS
- dev_server_started: true
- dev_server_stopped: true

## Risk Fields

- Z040 current readonly fallback risk: auth_401_count=6, runtime_readonly_fallback_risk=true
- Z039-CAND-001 fallback risk 保留
- Z038 fallback risks 保留
- prior readonly fallback risks 保留
- guarded_readonly_not_write_success 保留
- B28 shell_wrapper_anomaly 保留
- Z033 skipped_only 保留
- Z035 screenshot_missing_risk 保留
- remote_lifecycle_parked=true

## Forbidden Actions

- code edits: false
- router/views/report API edits: false
- backend edits: false
- candidate pool edits: false
- stage/commit/push: false
- cleanup/reset/restore: false
- remote lifecycle: false
