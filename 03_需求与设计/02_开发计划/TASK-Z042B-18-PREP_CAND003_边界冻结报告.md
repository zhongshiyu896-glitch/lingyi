# TASK-Z042B-18-PREP CAND003 边界冻结报告

## 结论

- candidate_id: Z042-CAND-003
- title: 工票批量导入失败解释与重试 guard 二轮可见流
- routes:
  - /workshop/tickets/batch
- allowed_files:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- allowed_files_exist: true
- allowed_files_dirty: false
- route_source_located: true
- next_task: TASK-Z042B-19-IMPL
- run_this_task: false

## Scope

- page_scope: 车间工票批量导入只读预览、失败明细与重试 guard
- visible_acceptance_goal: JSON 解析摘要、失败原因分组、只读重试 guard 与 request_id/scenario_tag 说明可见，批量导入与失败重试不得形成真实写请求成功
- read_only: true
- backend_allowed: false
- candidate_blocked: false
- reused_committed_product_path: true
- reused_source: Z038 / Z038-CAND-002 / 138700cf418fc2453b88bffe930d07cee115c02a

## Required Anchors

- workshop-ticket-batch-page
- workshop-ticket-batch-json-input
- workshop-ticket-batch-readonly-preview
- workshop-ticket-batch-failed-items-table
- workshop-ticket-batch-submit-button
- z042-batch-parse-summary
- z042-batch-failure-explanation
- z042-batch-retry-guard

## Guarded Write Entries

- 批量导入
- 解析后提交
- 失败重试

## Read/Write Boundary

- JSON parse 与 preview 只能是本地/read-only。
- 批量导入、解析后提交、失败重试必须 guarded/readonly。
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- B19 evidence requirement: screenshot, route evidence, runtime DOM anchors, guarded/readonly state, write request observation
- Auth 401 handling: readonly fallback risk only; not permission pass or write success.

## Forbidden Scope

- historical product/test dirty
- log/control dirty
- Z034 residual artifacts
- 07_后端
- candidate pool outside this task
- runtime/cache/test-results
- remote/prod/go-live

## Preconditions

- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## Lifecycle And Risks

- remote_lifecycle_parked: true
- push_tag_pr_release: false
- production_readback: false
- go_live: false
- project_completion: false
- Z042-CAND-002 readonly fallback risk: auth_401_count=25, runtime_readonly_fallback_risk=true
- Z042-CAND-001 fallback risk: preserved
- Z041/Z040/Z039/Z038 fallback risks: preserved
- guarded_readonly_not_write_success: true
- B28 shell_wrapper_anomaly: preserved
- Z033 skipped_only: preserved
- Z035 screenshot_missing_risk: preserved
