# TASK-Z035B-34-PREP CAND005 边界冻结报告

## Boundary

- source_task_id: TASK-Z035B-33-PREP
- selected_candidate_id: Z035-CAND-005
- implementation_workdir: /Users/hh/Desktop/领意服装管理系统
- frontend_workdir: /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
- candidate_id: Z035-CAND-005
- title: 生产计划详情只读端到端锚点
- page_scope: 生产计划
- routes:
  - /production/plans/detail
- visible_acceptance_goal: 用户能在生产计划详情看到计划单号、状态、款式、Work Order 映射、物料检查快照、工序卡映射与写入口状态。
- read_only: true
- backend_allowed: false
- expected_allowed_file_scope:
  - 06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
  - 06_前端/lingyi-pc/src/api/production.ts
- forbidden_scope:
  - 06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
  - historical_dirty_forbidden_paths
  - log_control_dirty_paths
  - B37 residual artifacts
  - 07_后端
  - candidate pool
  - runtime/cache/test-results
  - remote lifecycle
- next_task: TASK-Z035B-35-IMPL
- run_this_task: false

## Field / Button / State Anchors

- production-plan-detail-page
- production-plan-detail-main-fields
- production-plan-detail-status-tag
- production-plan-detail-work-order-mapping
- production-plan-detail-material-snapshot-table
- production-plan-detail-job-card-table
- production-plan-detail-write-entry-status

## Browser Evidence Plan

- production detail screenshot
- DOM field capture
- guarded write-entry state capture

## Scope Check

- allowed_files_exist:
  - 06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue: true
  - 06_前端/lingyi-pc/src/api/production.ts: true
- allowed_files_dirty:
  - 06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue: false
  - 06_前端/lingyi-pc/src/api/production.ts: false
- route_static_check:
  - found: true
  - router_path: 06_前端/lingyi-pc/src/router/index.ts
  - route: /production/plans/detail
  - component: @/views/production/ProductionPlanDetail.vue
- production_plan_list_excluded: true
- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- unknown_dirty: []
- must_block_before_continue: []

## Risk Notes

- B28 shell_wrapper_anomaly_preserved: true
- Z033 CAND003 skipped-only 风险继续保留:
  - skipped_only_evidence: true
  - actual_passed_count: 0
  - skipped_count: 4

## Forbidden Actions

- code edits: false
- tests/browser/typecheck: false
- stage/commit/push: false
- cleanup/reset/restore: false
- remote lifecycle: false
