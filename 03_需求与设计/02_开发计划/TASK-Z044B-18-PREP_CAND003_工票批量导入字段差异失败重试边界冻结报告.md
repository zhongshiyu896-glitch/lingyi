# TASK-Z044B-18-PREP CAND003 边界冻结报告

## Baseline
- head: d1add5325187e7838c64c71ed1f88452032a0130
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- git diff --check: PASS
- selected_candidate: Z044-CAND-003

## Boundary
- candidate_id: Z044-CAND-003
- title: 工票批量导入字段差异样例与失败重试锁定可见流
- page_scope: 车间工票批量导入模板、字段差异样例与失败重试只读锁定
- route:
  - /workshop/tickets/batch
- allowed_files:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- forbidden:
  - 06_前端/lingyi-pc/src/api/workshop.ts
  - current 19 tracked dirty files
  - historical product/test dirty
  - log/control dirty
  - Z034 residual artifacts
  - 07_后端
  - runtime/cache/test-results
  - remote/prod/go-live
  - prior non-allowlisted summary/metadata
  - candidate pool/control-plane outside this task
- reused_source: Z043 / Z043-CAND-003 / 20e12d99a7a2c51bd7928c6c4e9809e134a59002
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## Required Anchors
- z044-batch-template-version-readback
- z044-batch-field-diff-sample
- z044-batch-failed-row-locator
- z044-batch-retry-lock-reason
- z044-batch-readonly-request-context
- z044-batch-import-write-guard
- z044-batch-parse-submit-guard
- z044-batch-write-success-blocker

## Guarded Entries
- 批量导入
- 解析后提交
- 失败重试

## B19 Evidence Requirement
- /workshop/tickets/batch screenshot
- /workshop/tickets/batch route evidence
- runtime DOM anchors
- 批量导入/解析后提交/失败重试 guarded readonly state evidence
- network/write-request observation
- auth 401 只能记录为 readonly fallback risk
- 不得把 guarded_readonly 解释为写成功
- write_requests_observed_count 必须为 0 或无真实写成功
- typecheck 必须记录 command/workdir/exit_code
- dev server started/stopped 必须记录

## Readonly Checks
- allowed file exists: true
- allowed file dirty: false
- route_source_located: true
- route_source: 06_前端/lingyi-pc/src/router/index.ts
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## Risk Fields Preserved
- Z044-CAND-002 B11/B12 auth_401_count=25/25 readonly fallback risk
- Z044-CAND-001 B03/B04 auth_401_count=6/6 readonly fallback risk
- Z043 fallback risks: CAND005 4/4, CAND004 1/1, CAND003 1/1, CAND002 30/30, CAND001 2/2
- prior non-allowlisted summary/metadata 后续继续排除
- Z042/Z041/Z040/Z039/Z038 fallback risks
- B28 shell_wrapper_anomaly
- Z033 skipped_only
- Z035 screenshot_missing_risk
- remote_lifecycle_parked=true
- push_tag_pr_release=false
- production_readback=false
- go_live=false
- project_completion=false
- next_gate_blocked_pending_explicit_authorization=true

## Forbidden Actions
- code_changed: false
- validation_rerun: false
- stage_performed: false
- commit_performed: false
- push_tag_pr_release: false
- cleanup_reset_restore: false
- b19_implementation_started: false
- z044_cand004_started: false
- remote_lifecycle_released: false
