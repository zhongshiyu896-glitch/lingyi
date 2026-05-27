# TASK-Z043B-18-PREP CAND003 工票批量导入模板字段定位边界冻结报告

## 边界结论

- task_id: TASK-Z043B-18-PREP
- role: B Engineer
- head: d26a2c8a0faadd1f2faccd265eda99de845a774c
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- git diff --check: PASS
- candidate_id: Z043-CAND-003
- next_task: TASK-Z043B-19-IMPL
- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## 冻结候选边界

- title: 工票批量导入模板示例与字段定位 guard 可见流
- page_scope: 车间工票批量导入只读模板、字段定位与失败重试 guard
- routes:
  - /workshop/tickets/batch
- allowed_files:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- reused_source: Z042 / Z042-CAND-003 / d592f5d712fc398113a68702460863ce3e18b88c
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## 禁止范围

- 06_前端/lingyi-pc/src/api/workshop.ts
- 07_后端
- current 19 tracked dirty files
- historical product/test dirty
- log/control dirty
- Z034 residual artifacts
- runtime/cache/test-results
- remote/prod/go-live
- CAND001 runtime_summary
- CAND002 screenshot_metadata/runtime_summary

## Required Anchors

- workshop-ticket-batch-page
- workshop-ticket-batch-json-input
- workshop-ticket-batch-readonly-preview
- workshop-ticket-batch-failed-items-table
- z043-batch-template-sample
- z043-batch-field-error-locator
- z043-batch-retry-preconditions
- z043-batch-readonly-request-context

## Guarded Write Entries

- 批量导入
- 解析后提交
- 失败重试

## B19 Evidence Requirement

- /workshop/tickets/batch 页面截图
- route evidence
- runtime DOM anchors
- 批量导入/解析提交/失败重试 guarded readonly state evidence
- network/write-request observation
- auth 401 只能记录为 readonly fallback risk
- 不得把 guarded_readonly 解释为写成功
- write_requests_observed_count 必须为 0 或无真实写成功
- typecheck 必须记录 command/workdir/exit_code
- dev server started/stopped 必须记录

## 前置合法性核对

- allowed file exists: true
- allowed file dirty: false
- route_source_located: true
- route_source: 06_前端/lingyi-pc/src/router/index.ts:74-76
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## 风险字段保留

- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 readonly fallback risk: B03/B04 auth_401_count=2/2
- CAND001 runtime_summary 与 CAND002 screenshot_metadata 为 non-allowlisted evidence summary/metadata，后续继续排除
- Z042/Z041/Z040/Z039/Z038 fallback risks
- B28 shell_wrapper_anomaly
- Z033 skipped_only
- Z035 screenshot_missing_risk
- remote_lifecycle_parked=true
- push_tag_pr_release=false
- production_readback=false
- go_live=false
- project_completion=false

## 禁止动作确认

- code_changed: false
- browser_typecheck_pytest_rerun: false
- stage_performed: false
- commit_performed: false
- cleanup_reset_restore: false
- b19_implementation_started: false
- z043_cand004_started: false
- remote_lifecycle_released: false
