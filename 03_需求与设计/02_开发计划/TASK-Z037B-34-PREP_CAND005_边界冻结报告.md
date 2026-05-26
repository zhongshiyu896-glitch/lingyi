# TASK-Z037B-34-PREP CAND005 边界冻结报告

## 基本信息

- task_id: TASK-Z037B-34-PREP
- role: B Engineer
- cycle_id: Z037
- candidate_id: Z037-CAND-005
- title: 外发单履约列表详情只读可见流
- action: boundary freeze / PREP-only
- result: PASS
- next_task: TASK-Z037B-35-IMPL
- run_this_task: false

## 当前核对

- head: 1cfc74e7bd1343f527a062c89672b85181e1592a
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- B33 selected_candidate: Z037-CAND-005
- B33 next_task: TASK-Z037B-34-PREP

## 冻结字段

- candidate_id: Z037-CAND-005
- title: 外发单履约列表详情只读可见流
- routes:
  - /subcontract/list
  - /subcontract/detail
  - /materialPurchase/materialPurchaseProcess
- read_only: true
- backend_allowed: false
- expected_allowed_file_scope:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
  - 06_前端/lingyi-pc/src/api/subcontract.ts

## 路由静态核对

- /subcontract/list: located in 06_前端/lingyi-pc/src/router/index.ts, component SubcontractOrderList.vue
- /subcontract/detail: located in 06_前端/lingyi-pc/src/router/index.ts, component SubcontractOrderDetail.vue
- /materialPurchase/materialPurchaseProcess: located in 06_前端/lingyi-pc/src/router/index.ts, redirect to /subcontract/list with parity material-purchase
- routes_located: true

## 必须保留 anchors

- subcontract-list-page
- subcontract-filter-form
- subcontract-table
- subcontract-guarded-actions
- subcontract-detail-page
- subcontract-detail-main-fields
- subcontract-detail-guarded-actions
- subcontract-write-guard

## 写入口 guard 要求

- 新建外发单
- 发料
- 回料
- 验货
- 结算预览
- 同步重试
- 导出
- 打印

## B35 evidence 要求

- 必须采集 /subcontract/list 截图
- 必须采集 /subcontract/detail runtime route evidence
- 必须采集 /materialPurchase/materialPurchaseProcess redirect/route evidence
- 必须采集运行态 DOM anchors
- 必须采集 guarded write-control state
- 必须记录 write request observation
- 不允许纯静态 fallback

## Scope 核对

- allowed_files_exist: true
- allowed_files_dirty: false
- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- intersections_with_z035_committed_product_paths: []
- intersections_with_z036_committed_product_paths: []
- unknown_dirty: []
- must_block_before_continue: []

## 风险字段保留

- current/prior readonly fallback risks: preserved
- guarded_readonly_not_write_success: preserved
- B28 shell_wrapper_anomaly: preserved
- Z033 skipped_only: preserved
- Z035 screenshot_missing_risk: preserved

## 禁止动作

- code/test/candidate_pool edits: false
- tests/browser/typecheck: false
- stage/commit/push: false
- PR/tag/release: false
- cleanup/reset/restore/clean/delete: false
- B35 implementation started: false
- remote lifecycle released: false
