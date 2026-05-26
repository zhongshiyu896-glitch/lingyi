# TASK-Z040B-02-PREP CAND001 边界冻结报告

## Boundary

- candidate_id: Z040-CAND-001
- source_task: TASK-Z040B-01-PREP-PRODUCT-POOL
- title: 全局会话权限只读降级可见流
- page_scope: 应用 Shell 全局会话、权限与只读降级状态
- routes: /home, /permissions/governance, /reports/catalog
- read_only: true
- backend_allowed: false
- next_task: TASK-Z040B-03-IMPL
- run_this_task: false

## Allowed Scope

- 06_前端/lingyi-pc/src/App.vue
- 06_前端/lingyi-pc/src/stores/permission.ts
- 06_前端/lingyi-pc/src/api/auth.ts
- allowed_files_exist: true
- allowed_files_dirty: false

## Source Location

- App Shell: `App.vue` exposes the root `<router-view />`.
- Permission store: `permission.ts` exposes `loadCurrentUser`, `refreshCurrentUser`, `loadModuleActions`, guest fallback state and `buttonPermissions`.
- Auth API: `auth.ts` exposes `fetchCurrentUser` and `fetchModuleActions`.
- routes_for_runtime_evidence: /home, /permissions/governance, /reports/catalog

## Required Anchors

- global-readonly-shell
- global-permission-state
- global-auth-fallback-state
- global-route-readonly-badge
- global-permission-actions-preview
- global-auth-refresh-guard
- global-readonly-write-guard
- global-remote-lifecycle-parked

## Read/Guard Contract

- allowed_read_flows: fetchCurrentUser, fetchModuleActions
- guarded_write_entries: 权限刷新, 模块动作重载, 只读降级确认
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- auth_401_handling: readonly fallback risk only; must not be treated as permission pass or write success

## Evidence Requirement

- screenshot
- route evidence
- runtime DOM anchors
- guarded/readonly state
- write request observation

## Exclusions

- forbidden_scope: router/index.ts; views/**; api/report.ts; 07_后端; candidate pool; historical product/test dirty; log/control dirty; Z034 residual artifacts; Z035/Z036/Z037/Z038/Z039 committed product paths; runtime/cache/test-results; remote/prod/go-live
- dirty_intersections: empty
- unknown_dirty: []
- must_block_before_continue: []

## Risk Fields

- Z039-CAND-001 readonly fallback risk: auth_401_count=33, runtime_readonly_fallback_risk=true
- Z038 fallback risks 保留
- prior readonly fallback risks 保留
- guarded_readonly_not_write_success 保留
- B28 shell_wrapper_anomaly 保留
- Z033 skipped_only 保留
- Z035 screenshot_missing_risk 保留
- remote_lifecycle_parked=true

## Forbidden Actions

- code edits: false
- tests/browser/typecheck: false
- stage/commit/push: false
- cleanup/reset/restore: false
- implementation started: false
- remote lifecycle: false
