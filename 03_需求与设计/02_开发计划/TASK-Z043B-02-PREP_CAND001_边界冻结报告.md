# TASK-Z043B-02-PREP CAND001 边界冻结报告

## 基线

- task_id: TASK-Z043B-02-PREP
- role: B Engineer
- head: c0926d15a9a8ab88160b737672a17253a0bbc5cb
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- selected_candidate: Z043-CAND-001

## 候选边界

- candidate_id: Z043-CAND-001
- title: 全局只读操作轨迹与证据入口一致性可见流
- page_scope: 应用 Shell 跨首页、批量导入与外发单列表的全局只读操作轨迹
- routes:
  - /home
  - /workshop/tickets/batch
  - /subcontract/list
- visible_acceptance_goal: 展示当前 route 的只读操作轨迹、最近 guarded 入口、证据入口说明与 fallback 风险摘要；所有全局确认/刷新入口不得形成真实写请求成功
- read_only: true
- backend_allowed: false
- candidate_blocked: false
- reused_committed_product_path: true
- reused_source: Z042 / Z042-CAND-001 / 78fffac1d35cf7ccdeec2f46fcfceccc3423dbe9
- allowed_files:
  - 06_前端/lingyi-pc/src/App.vue

## 禁止范围

- current 19 tracked dirty files
- historical product/test dirty
- log/control dirty
- Z034 residual artifacts
- 07_后端
- candidate pool outside this task
- runtime/cache/test-results
- remote/prod/go-live

## required anchors

- global-readonly-shell
- global-route-readonly-badge
- global-auth-fallback-state
- global-readonly-write-guard
- z043-global-operation-trace
- z043-global-evidence-entry
- z043-global-guarded-action-log
- z043-global-next-gate-disclaimer

## guarded write entries

- 全局确认
- 权限刷新
- 降级说明入口

## 边界要求

- global route display 与 operation trace 只能是 read-only。
- 全局确认、权限刷新、降级说明入口必须 guarded/readonly。
- write_request_success_allowed: false
- real_write_action_allowed: false
- pure_static_fallback_allowed: false
- guarded_readonly_not_write_success: true
- B03 必须采集截图、三路由 evidence、runtime DOM anchors、guarded/readonly state、write request observation。
- B03 必须记录 auth 401 为 readonly fallback risk，不得解释为权限通过或写成功。

## 前置合法性

- allowed_files_exist: true
- allowed_files_dirty: false
- route_source_located: true
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- remote_lifecycle_parked: true
- push_tag_pr_release: false
- production_readback: false
- go_live: false
- project_completion: false
- next_task: TASK-Z043B-03-IMPL
- run_this_task: false

## 执行边界

- implementation_started: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## 风险字段

- Z042 fallback risks preserved:
  - CAND005 auth_401_count: 4/3
  - CAND004 auth_401_count: 1
  - CAND003 auth_401_count: 1
  - CAND002 auth_401_count: 25
  - CAND001 auth_401_count: 6
- Z041/Z040/Z039/Z038 fallback risks: preserved
- guarded_readonly_not_write_success: true
- B28 shell_wrapper_anomaly: true
- Z033 skipped_only: true
- Z035 screenshot_missing_risk: true
