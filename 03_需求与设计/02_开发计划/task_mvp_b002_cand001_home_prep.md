# TASK-MVP-B002-PREP

## SUMMARY
- head: e9c2f052688af4acd0e31aaaa3723016013db279
- branch: codex/sprint4-seal
- cached_empty: true
- selected_candidate: MVP-CAND-001
- module: 首页
- routes:
  - /home
  - /dashboard/overview
- next_task: TASK-MVP-B003-IMPL
- prep_only: true

## BOUNDARY
- candidate_id: MVP-CAND-001
- module_name: 首页
- title: 首页工作台六模块入口与状态面板
- page_scope: 在首页与总览面板提供六模块入口、状态、阻断原因和本地闭环指引。
- allowed_files:
  - 06_前端/lingyi-pc/src/views/HomePage.vue
  - 06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue
- current_page_files:
  - 06_前端/lingyi-pc/src/views/HomePage.vue
  - 06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue
- route_source_locations:
  - 06_前端/lingyi-pc/src/router/index.ts:34
  - 06_前端/lingyi-pc/src/router/index.ts:192
- contract_source:
  - type: ui_business_contract_source
  - description: 衣算云首页工作台强调“入口可达 + 状态可读 + 下一步可执行”，用于承接六模块本地可用闭环。
  - source_documents:
    - 首页/看板路由与入口约定
    - Z046 主线收口后的本地 reanchor 约束
- key_fields_required:
  - 模块名称
  - 入口路由
  - 当前可用状态
  - 阻断原因
  - 最近一次本地回读时间
- query_flow_required: 读取本地模块状态快照并在首页/总览回读展示，不依赖生产写入。
- local_write_loop_required: true
- local_write_loop_design:
  - 用户可调整首页工作台六模块状态/关注项/准备进度中的至少一项
  - 支持新增或更新本地草稿
  - 支持保存
  - 支持取消
  - 支持回读
  - 支持 rollback
  - 支持 zero_residual 校验
- local_write_storage:
  - mode: local-dev/sqlite/scenario_tag
  - scenario_tag_required: true
  - erpnext_production_write_forbidden: true
  - production_account_forbidden: true
- rollback_required: true
- zero_residual_required: true
- user_visible_frontend_improvement: true
- interaction_experience_improvement: true
- one_to_one_ui_contract_focus: true
- forbidden_scope:
  - 07_后端
  - ERPNext production API
  - production account/session
  - remote/prod-go-live
  - runtime/cache
  - test-results
  - Z034 residual
  - prior non-allowlisted summary/metadata
  - 当前历史 dirty 文件
  - 非 MVP-CAND-001 模块页面
  - MVP-CAND-002..006 future artifacts
- browser_evidence_requirement:
  - /home HTTP 200
  - /dashboard/overview HTTP 200
  - 首页截图 PNG 1440x1200
  - DOM anchors 覆盖六模块入口、状态面板、查询/筛选、本地保存、本地取消、本地回读、rollback、zero_residual
  - network/write observation 必须证明无生产写
  - local write loop 必须使用 scenario_tag
  - typecheck 必须记录 `npm run typecheck`（workdir=`06_前端/lingyi-pc`）

## DIRTY
- dirty_tracked_count: 19
- frontend_dirty_count: 6
- backend_dirty_count: 10
- log_control_dirty_count: 3
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## CHECKS
- git_diff_check: PASS
- product_code_changed=false
- validation_rerun=false
- staged_area_empty=true
- outputs_unstaged=true

## RESIDUAL_RISK
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false
- prior readonly fallback risks retained=true

## NEXT_RECOMMENDED_TASK
- TASK-MVP-B003-IMPL
