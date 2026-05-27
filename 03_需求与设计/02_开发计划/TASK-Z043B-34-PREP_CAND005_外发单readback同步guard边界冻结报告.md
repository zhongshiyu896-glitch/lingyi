# TASK-Z043B-34-PREP CAND005 边界冻结报告

## 基线

- head: 191fa25ebfa0d3e7979b3a1d0711069c858b5f9a
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## Boundary

- candidate_id: Z043-CAND-005
- title: 外发单列表详情 readback 对照与同步 guard 可见流
- page_scope: 外发单列表、详情与物料采购 parity 的 readback 对照
- routes:
  - /subcontract/list
  - /subcontract/detail
  - /materialPurchase/materialPurchaseProcess
- materialPurchase parity/redirect: /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase
- allowed_files:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- forbidden:
  - 06_前端/lingyi-pc/src/api/subcontract.ts
  - 07_后端
  - current 19 tracked dirty files
  - historical product/test dirty
  - log/control dirty
  - Z034 residual artifacts
  - runtime/cache/test-results
  - remote/prod/go-live
  - prior non-allowlisted summary/metadata
- reused_source: Z042 / Z042-CAND-005 / c0926d15a9a8ab88160b737672a17253a0bbc5cb
- read_only: true
- backend_allowed: false
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## Required Anchors

1. subcontract-list-page
2. subcontract-filter-form
3. subcontract-detail-page
4. subcontract-detail-main-fields
5. z043-subcontract-readback-compare
6. z043-subcontract-sync-retry-reason
7. z043-subcontract-export-print-disabled
8. z043-subcontract-material-parity-source

## Guarded Entries

- 新建外发单
- 发料
- 回料
- 验货
- 结算预览
- 同步重试
- 导出
- 打印

## B35 Evidence Requirement

- /subcontract/list 与 /subcontract/detail 页面截图
- /materialPurchase/materialPurchaseProcess parity route evidence
- 三路由 route evidence
- runtime DOM anchors evidence，8/8 anchors observed
- 新建/发料/回料/验货/结算预览/同步重试/导出/打印 guarded readonly state evidence
- network/write-request observation
- auth 401 只能记录为 readonly fallback risk
- 不得把 guarded_readonly 解释为写成功
- write_requests_observed_count 必须为 0 或无真实写成功
- typecheck 必须记录 command/workdir/exit_code
- dev server started/stopped 必须记录

## 前置合法性

- allowed_files_exist: true
- allowed_files_dirty: false
- routes_source_located: true
- material_purchase_parity_recorded: true
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## Risk Fields Preserved

- CAND004 B27/B28 auth_401_count=1/1 readonly fallback risk
- CAND003 B19/B20 auth_401_count=1/1 readonly fallback risk
- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 B03/B04 auth_401_count=2/2 readonly fallback risk
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

## Forbidden Actions

- code_changed: false
- browser_typecheck_pytest_rerun: false
- stage_performed: false
- commit_performed: false
- push_tag_pr_release: false
- cleanup_reset_restore: false
- started_b35_implementation: false
- remote_lifecycle_released: false

## Next

- next_task: TASK-Z043B-35-IMPL
