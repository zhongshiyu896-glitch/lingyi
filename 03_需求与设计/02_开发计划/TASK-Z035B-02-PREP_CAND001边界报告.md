# TASK-Z035B-02-PREP CAND001 边界报告

- cycle_id: Z035
- source_task: TASK-Z035B-01-PREP-PRODUCT-POOL
- candidate_id: Z035-CAND-001
- title: 首页 / 工作台可见收口
- page_scope: 首页 / 工作台
- routes: `/home`, `/dashboard/overview`, `/dashboard/workplace`
- visible_acceptance_goal: 用户能从首页进入工作台总览，看到会话信息、只读导航提示、核心入口、工作台指标卡片和消息表格。

## 只读核对

- HEAD: 18aa72bef01ea965c83b31b81178d93a086bcbeb
- cached_empty: true
- head_tag_empty: true
- diff_check_pass: true
- B01 selected_candidate: Z035-CAND-001
- candidate_original_fields_match_B01: true
- route_location_status: all_routes_located
- backend_allowed: false
- remote_lifecycle_parked: true

## Allowed File Scope

- `06_前端/lingyi-pc/src/views/HomePage.vue`: exists=true, dirty=false
- `06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`: exists=true, dirty=false
- `06_前端/lingyi-pc/src/api/dashboard.ts`: exists=true, dirty=false

## Scope Gate

- scope_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- out_of_scope_artifacts_status: untracked_not_staged_not_committed
- shell_wrapper_anomaly_preserved: true
- z033_cand003_skipped_only_evidence: true
- z033_cand003_actual_passed_count: 0
- z033_cand003_skipped_count: 4

## B03 Boundary

后续 B03 只允许围绕首页/工作台可见性、路由证据、只读状态、展示锚点做最小前端收口。B02 不实施、不运行浏览器、不跑测试。

允许后续 B03 文件范围：

- `06_前端/lingyi-pc/src/views/HomePage.vue`
- `06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
- `06_前端/lingyi-pc/src/api/dashboard.ts`

禁止范围：

- 真实写动作
- `07_后端`
- 后端测试
- historical dirty
- log/control dirty
- candidate pool
- runtime/cache
- remote lifecycle

## Lifecycle

- stage/commit/push/tag/PR/release: false
- production_readback: false
- go_live: false
- project_completion: false
- next_task: TASK-Z035B-03-IMPL
- run_this_task: false

## 本轮产物

- B02 report/json/tsv: not staged
