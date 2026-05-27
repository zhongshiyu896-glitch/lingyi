# TASK-Z044B-02-PREP CAND001 边界冻结报告

## 基线

- HEAD: e4dcf4dc774dca1a59882eb8dd64d194cef65671
- branch: codex/sprint4-seal
- cached: []
- HEAD tag: []
- git diff --check: PASS
- B01 selected_candidate: Z044-CAND-001

## Boundary

- candidate_id: Z044-CAND-001
- title: 全局本地门禁摘要与风险只读提示可见流
- page_scope: 应用 Shell 跨首页、报表目录与外发列表的本地门禁摘要
- routes: /home, /reports/catalog, /subcontract/list
- allowed_files: 06_前端/lingyi-pc/src/App.vue
- reused_source: Z043 / Z043-CAND-001 / e584624d9dee99c951de901b7864b0982db47a99
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

visible_acceptance_goal:

- 展示 Z044 本地门禁建议、当前 dirty/residual 摘要、远端/生产未授权提示与最近只读风险提示。
- 全局确认、刷新与继续入口不得形成真实写请求成功。

forbidden_scope:

- current 19 tracked dirty files
- historical product/test dirty
- log/control dirty
- Z034 residual artifacts
- 07_后端
- runtime/cache/test-results
- remote/prod/go-live
- prior non-allowlisted summary/metadata
- candidate pool/control-plane outside this task

## File And Route Status

- App.vue exists: true
- App.vue dirty: false
- /home located: 06_前端/lingyi-pc/src/router/index.ts:21
- /reports/catalog located: 06_前端/lingyi-pc/src/router/index.ts:92
- /subcontract/list located: 06_前端/lingyi-pc/src/router/index.ts:50

## Required Anchors

- z044-global-local-gate-summary
- z044-global-dirty-scope-readback
- z044-global-residual-risk-badge
- z044-global-remote-gate-disclaimer
- z044-global-readonly-action-guard
- z044-global-evidence-readiness-entry
- z044-global-next-prep-recommendation
- z044-global-write-success-blocker

required_anchors_count: 8

## Guarded Entries

- 全局确认
- 门禁刷新
- 继续准备说明

## B03 Evidence Requirement

- /home screenshot
- /home, /reports/catalog, /subcontract/list route evidence
- runtime DOM anchors
- 全局确认/门禁刷新/继续准备说明 guarded readonly state evidence
- network/write-request observation
- auth 401 only as readonly fallback risk
- guarded_readonly must not be interpreted as write success
- write_requests_observed_count must be 0 or no real write success
- typecheck command/workdir/exit_code must be recorded
- dev server started/stopped must be recorded

## Preconditions

- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## Risk Fields

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
- validation_rerun: false
- stage_performed: false
- commit_performed: false
- push/tag/PR/release: false
- cleanup/reset/restore: false
- B03 implementation started: false
- Z044-CAND-002 started: false
- remote_lifecycle_released: false

## Next

- next_task: TASK-Z044B-03-IMPL
- run_this_task: false
