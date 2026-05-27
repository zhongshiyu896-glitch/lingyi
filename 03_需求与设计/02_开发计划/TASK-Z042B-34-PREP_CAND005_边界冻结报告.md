# TASK-Z042B-34-PREP CAND005 边界冻结报告

## 基本结论

- task_id: TASK-Z042B-34-PREP
- role: B Engineer
- candidate_id: Z042-CAND-005
- boundary_status: PASS
- head: 2be2fcf067cfdb8ef1b087ab19a6d6f7c5e934ed
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- next_task: TASK-Z042B-35-IMPL
- run_this_task: false

## 候选边界

- title: 外发单列表详情 guard trace 与 parity 来源二轮可见流
- page_scope: 外发单列表、详情与物料采购 parity route 的只读 guard trace
- routes:
  - /subcontract/list
  - /subcontract/detail
  - /materialPurchase/materialPurchaseProcess
- visible_acceptance_goal: 列表筛选、详情主字段、导出/打印/同步 guard、materialPurchase parity 来源说明与 readonly fallback 解释可见，所有写入口不得形成真实写请求成功
- read_only: true
- backend_allowed: false
- candidate_blocked: false
- reused_committed_product_path: true
- reused_source: Z037 / Z037-CAND-005 / a6d91ea165c8e870f449f06812e57a8df4a555da

## 允许与禁止范围

- allowed_files:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- allowed_files_exist: true
- allowed_files_dirty: false
- forbidden_scope:
  - 06_前端/lingyi-pc/src/api/subcontract.ts
  - historical product/test dirty
  - log/control dirty
  - Z034 residual artifacts
  - 07_后端
  - candidate pool outside this task
  - runtime/cache/test-results
  - remote/prod/go-live

## Required Anchors

- required_anchors_count: 8
- required_anchors:
  - subcontract-list-page
  - subcontract-filter-form
  - subcontract-table
  - subcontract-detail-page
  - subcontract-detail-main-fields
  - subcontract-write-guard
  - z042-subcontract-guard-trace
  - z042-subcontract-parity-source

## Guarded Entries

- guarded_entries:
  - 新建外发单
  - 发料
  - 回料
  - 验货
  - 结算预览
  - 同步重试
  - 导出
  - 打印
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true

## Evidence Requirement

B35 必须采集：

- list/detail 截图
- 三路由 route evidence
- runtime DOM anchors
- guarded/readonly state
- write request observation
- auth 401 只能记录为 readonly fallback risk，不得解释为权限通过或写成功

## Route Source

- route_source_located: true
- /subcontract/list: 06_前端/lingyi-pc/src/router/index.ts:46
- /subcontract/detail: 06_前端/lingyi-pc/src/router/index.ts:52
- /materialPurchase/materialPurchaseProcess: 06_前端/lingyi-pc/src/router/index.ts:252
- material_purchase_parity_recorded: true
- material_purchase_parity_detail: /materialPurchase/materialPurchaseProcess redirects to /subcontract/list with query parity=material-purchase

## 前置合法性

- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false
- remote_lifecycle_parked: true
- push_tag_pr_release: false
- production_readback: false
- go_live: false
- project_completion: false

## 风险字段保留

- Z042-CAND-004 fallback risk: auth_401_count=1
- Z042-CAND-003 fallback risk: auth_401_count=1
- Z042-CAND-002 fallback risk: auth_401_count=25
- Z042-CAND-001 fallback risk: preserved
- Z041/Z040/Z039/Z038 fallback risks: preserved
- B28 shell_wrapper_anomaly: preserved
- Z033 skipped_only: preserved
- Z035 screenshot_missing_risk: preserved
