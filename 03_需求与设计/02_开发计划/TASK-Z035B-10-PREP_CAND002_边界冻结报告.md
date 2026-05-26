# TASK-Z035B-10-PREP CAND002 边界冻结报告

## Boundary

- source_task_id: `TASK-Z035B-09-PREP`
- selected_candidate_id: `Z035-CAND-002`
- implementation_workdir: `/Users/hh/Desktop/领意服装管理系统`
- frontend_workdir: `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`
- routes: `/bom/list`, `/bom/detail`
- next_task: `TASK-Z035B-11-IMPL`
- run_this_task: false

## Candidate

- title: `BOM 列表与详情只读业务流`
- page_scope: `BOM`
- visible_acceptance_goal: 用户能在 BOM 列表筛选、查看 BOM 编号/状态，并进入详情 drawer 或详情页看到 BOM 主字段、状态、物料/工序区块与只读写入口状态。
- read_only: true
- backend_allowed: false

## Scope

- expected_allowed_file_scope:
  - `06_前端/lingyi-pc/src/views/bom/BomList.vue`
  - `06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
  - `06_前端/lingyi-pc/src/api/bom.ts`
- forbidden_scope:
  - `07_后端/**`
  - backend app/tests
  - candidate pool
  - historical dirty
  - log/control dirty
  - B37 residual artifacts
  - runtime/cache
  - real write actions
  - remote lifecycle

## Static Checks

- allowed_files_exist: all true
- allowed_files_dirty: all false
- route_static_check:
  - `/bom/list`: `06_前端/lingyi-pc/src/router/index.ts:14`
  - `/bom/detail`: `06_前端/lingyi-pc/src/router/index.ts:20`
- field_button_state_anchors:
  - `bom-main-list-section`
  - `bom-main-list-filters`
  - `bom-main-table`
  - `bom-main-detail-button`
  - `bom-main-detail-drawer`
  - `bom-detail-page`
  - `bom-detail-status-tag`
  - `bom-detail-actions`
- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- unknown_dirty: []
- must_block_before_continue: []

## Forbidden Actions

- code edits: not performed
- tests/browser/typecheck: not performed
- stage/commit/push: not performed
- cleanup/reset/restore: not performed
- remote lifecycle: parked
- B28 shell_wrapper_anomaly_preserved: true
- Z033 skipped-only risk preserved: `skipped_only_evidence=true`, `actual_passed_count=0`, `skipped_count=4`
