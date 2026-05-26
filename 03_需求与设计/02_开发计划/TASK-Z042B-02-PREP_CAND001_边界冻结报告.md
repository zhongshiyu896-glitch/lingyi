# TASK-Z042B-02-PREP CAND001 边界冻结报告

## 基本结论

- task_id: TASK-Z042B-02-PREP
- role: B Engineer
- candidate_id: Z042-CAND-001
- source_task: TASK-Z042B-01-PREP-PRODUCT-POOL
- title: 全局只读 Shell 路由上下文二轮可见流
- page_scope: 应用 Shell 跨首页、报表目录与车间工票的全局只读上下文
- routes:
  - /home
  - /reports/catalog
  - /workshop/tickets
- read_only: true
- backend_allowed: false
- reused_committed_product_path: true
- reused_source: Z040-CAND-001 / ee0d7d826d1f0bbf959321cbfc1d74915a36aa16
- allowed_files:
  - 06_前端/lingyi-pc/src/App.vue
- allowed_files_exist: true
- allowed_files_dirty: false
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- next_task: TASK-Z042B-03-IMPL
- run_this_task: false

## Visible Acceptance Goal

在已提交且当前 clean 的全局 Shell 上新增二轮可见验收：跨三条路由展示当前 route 分类、只读 fallback 原因、remote parked 状态与 guarded 权限刷新入口，刷新入口不得形成真实写请求成功。

## Required Anchors

- global-readonly-shell
- global-route-readonly-badge
- global-auth-fallback-state
- global-permission-state
- global-readonly-write-guard
- z042-global-route-context
- z042-global-fallback-explanation
- z042-global-guarded-refresh

## Guarded Entries

- 权限刷新
- 只读确认
- 其他全局权限刷新/降级入口

## Evidence Requirement

- 必须采集 /home 页面截图
- 必须采集 /reports/catalog 与 /workshop/tickets route evidence
- 必须采集运行态 DOM anchors
- 必须采集 guarded/readonly state evidence
- 必须采集 write request observation
- write_request_success_allowed=false
- pure_static_fallback_allowed=false
- auth 401 只能记录为 readonly fallback risk，不得解释为权限通过或写成功

## Forbidden Scope

- historical product/test dirty
- log/control dirty
- Z034 residual artifacts
- runtime/cache/test-results
- 07_后端
- candidate pool
- remote/prod/go-live
- cleanup/reset/restore
- stage/commit/push

## Risk Fields Preserved

- Z041 readonly fallback risk: auth_401_count=4, runtime_readonly_fallback_risk=true
- Z040/Z039/Z038 fallback risks preserved
- prior readonly fallback risks preserved
- guarded_readonly_not_write_success preserved
- B28 shell_wrapper_anomaly preserved
- Z033 skipped_only preserved
- Z035 screenshot_missing_risk preserved
- remote_lifecycle_parked=true
