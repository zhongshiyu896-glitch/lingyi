# TASK-Z035B-26-PREP CAND004 边界冻结报告

## 边界

- source_task_id: TASK-Z035B-25-PREP
- selected_candidate_id: Z035-CAND-004
- implementation_workdir: `/Users/hh/Desktop/领意服装管理系统`
- frontend_workdir: `06_前端/lingyi-pc`
- page_scope: 库存台账
- routes:
  - `/warehouse`
- title: 仓库看板与库存卡片可见收口
- visible_acceptance_goal: 用户能在仓库看板看到成品库存台账、KPI 卡片、仓库筛选、库存主表、库存预警与禁用写入口。
- read_only: true
- backend_allowed: false
- next_task: TASK-Z035B-27-IMPL
- run_this_task: false

## 后续允许实施文件

- `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- `06_前端/lingyi-pc/src/api/warehouse.ts`

## 静态路由与锚点核对

- route_static_check: PASS
- route evidence:
  - `06_前端/lingyi-pc/src/router/index.ts:152` path `/warehouse`
  - `06_前端/lingyi-pc/src/router/index.ts:154` component `@/views/warehouse/WarehouseDashboard.vue`
- current anchor evidence in `WarehouseDashboard.vue`:
  - `warehouse-page`
  - `warehouse-stock-summary-section`
  - `warehouse-stock-filters`
  - `warehouse-kpi-grid`
  - `warehouse-stock-main-table`
  - `warehouse-stock-open-ledger-button`
  - `warehouse-stock-export-guarded-button`

## 浏览器证据计划

- warehouse dashboard screenshot
- KPI DOM capture
- guarded button state capture

## 范围核对

- allowed_files_exist:
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`: true
  - `06_前端/lingyi-pc/src/api/warehouse.ts`: true
- allowed_files_dirty:
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`: false
  - `06_前端/lingyi-pc/src/api/warehouse.ts`: false
- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- unknown_dirty: []
- must_block_before_continue: []

## 禁止范围

- historical_dirty_forbidden_paths
- log_control_dirty_paths
- B37 residual artifacts
- `07_后端/lingyi_service/app`
- `07_后端/lingyi_service/tests`
- candidate pool files
- runtime/cache
- remote lifecycle

## 前置核对

- head: `d02d605e401bf1a7b07e83ed3e632ee5b6034eb6`
- branch: `codex/sprint4-seal`
- cached_empty: true
- head_tag_empty: true
- diff_check: PASS
- B25 selected_candidate: Z035-CAND-004
- B25 next_task: TASK-Z035B-26-PREP
- CAND001/CAND002/CAND003 archive: COMMITTED_AND_ARCHIVED_LOCAL_ONLY

## 风险保留

- shell_wrapper_anomaly_preserved: true
- z033_cand003_skipped_only_risk:
  - skipped_only_evidence: true
  - actual_passed_count: 0
  - skipped_count: 4

## 禁止动作确认

- code_edits: false
- tests_browser_typecheck: false
- stage_commit_push: false
- cleanup_reset_restore: false
- remote_lifecycle: parked
