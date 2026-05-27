# TASK-Z043B-26-PREP CAND004 工票登记草稿差异撤销预览边界冻结报告

## 基线

- HEAD: 20e12d99a7a2c51bd7928c6c4e9809e134a59002
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- git diff --check: PASS
- selected_candidate: Z043-CAND-004
- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## 边界

- candidate_id: Z043-CAND-004
- title: 工票登记草稿差异校验与撤销预览 guard 可见流
- page_scope: 车间工票登记草稿、字段差异、撤销预览与只读确认
- route:
  - /workshop/tickets/register
- allowed_files:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue
- forbidden:
  - 06_前端/lingyi-pc/src/api/workshop.ts
  - 07_后端
  - current 19 tracked dirty files
  - historical product/test dirty
  - log/control dirty
  - Z034 residual artifacts
  - runtime/cache/test-results
  - remote/prod/go-live
  - prior non-allowlisted summary/metadata
- reused_source: Z042 / Z042-CAND-004 / 2be2fcf067cfdb8ef1b087ab19a6d6f7c5e934ed
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## required anchors

1. workshop-ticket-register-page
2. workshop-ticket-register-form
3. workshop-ticket-register-readonly-draft-preview
4. workshop-ticket-register-validation-hint
5. z043-register-field-diff-summary
6. z043-register-cancel-preview
7. z043-register-readonly-confirm-chain
8. z043-register-return-source-readback

## guarded write entries

- 提交登记
- 提交撤销
- 只读降级确认

## B27 evidence requirement

- /workshop/tickets/register 页面截图
- route evidence
- runtime DOM anchors
- 提交登记/提交撤销/只读降级确认 guarded readonly state evidence
- network/write-request observation
- auth 401 只能记录为 readonly fallback risk
- 不得把 guarded_readonly 解释为写成功
- write_requests_observed_count 必须为 0 或无真实写成功
- typecheck 必须记录 command/workdir/exit_code
- dev server started/stopped 必须记录

## 前置合法性

- allowed_files_exist: true
- allowed_files_dirty: false
- route_source_located: true
- route_source_reference: 06_前端/lingyi-pc/src/router/index.ts:68
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## 风险字段

- CAND003 B19/B20 auth_401_count=1/1 readonly fallback risk
- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 readonly fallback risk: B03/B04 auth_401_count=2/2
- prior non-allowlisted summary/metadata 后续继续排除
- Z042/Z041/Z040/Z039/Z038 fallback risks
- guarded_readonly_not_write_success=true
- B28 shell_wrapper_anomaly
- Z033 skipped_only
- Z035 screenshot_missing_risk
- remote_lifecycle_parked=true
- push_tag_pr_release=false
- production_readback=false
- go_live=false
- project_completion=false

next_task: TASK-Z043B-27-IMPL
