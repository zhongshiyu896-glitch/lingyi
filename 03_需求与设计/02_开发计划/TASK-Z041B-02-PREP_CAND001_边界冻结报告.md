# TASK-Z041B-02-PREP CAND001 边界冻结报告

## 基本结论

- task_id: TASK-Z041B-02-PREP
- role: B Engineer
- status: READY_FOR_REVIEW
- source_task: TASK-Z041B-01-PREP-PRODUCT-POOL-FIX1
- candidate_id: Z041-CAND-001
- title: 车间工票工资三路由只读一致性二轮可见流
- page_scope: 车间工票查询、日薪统计、工价档案跨路由只读一致性
- read_only: true
- backend_allowed: false
- reused_committed_product_path: true

## 当前前提

- head: ee0d7d826d1f0bbf959321cbfc1d74915a36aa16
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- B01-FIX1 selected_candidate: Z041-CAND-001
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- remote_lifecycle_parked: true

## 复用来源

- source_batch: Z036
- source_candidate_id: Z036-CAND-004
- source_commit: b5e6ce57b28ef7d2ca4d2b58502049c2b7a5ae45
- reused_paths:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue
  - 06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue

## 允许文件

- 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue
- 06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue
- 06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue

核对结果：
- allowed_files_exist: true
- allowed_files_dirty: false
- allowed scope 与 historical dirty、log/control dirty、Z034 residual artifacts、runtime/cache/test-results、07_后端交集: []

## 路由边界

- /workshop/tickets
- /workshop/daily-wages
- /workshop/wage-rates

三条 route 均已在前端 router/source 中定位，可用于 B03 运行态证据采集。

## 可见验收目标

在三条已提交且当前 clean 的车间工票/工资路径上新增二轮跨路由一致性验收：统一只读状态、route 来源提示、权限边界说明、筛选与详情/汇总/工价表 guarded 可见性，且所有写入口不得形成真实写请求成功。

## 必须 anchors

- workshop-ticket-list-page
- workshop-ticket-filter-form
- workshop-ticket-guarded-actions
- workshop-ticket-summary-dialog
- workshop-daily-wage-page
- workshop-daily-wage-guarded-actions
- workshop-wage-rate-page
- workshop-ticket-wage-cross-route-guard

说明：当前只读源码定位中前 7 个已有静态定位；`workshop-ticket-wage-cross-route-guard` 是本轮二轮增量要求，必须在 B03 实施后源码与运行态 DOM 中 observed。

## Guarded 写入口

- 工票登记
- 批量导入
- Job Card 同步重试
- 日薪导出
- 生成日薪
- 同步日薪
- 新增工价
- 停用工价

冻结字段：
- write_request_success_allowed: false
- guarded_readonly_not_write_success: true
- pure_static_fallback_allowed: false

## B03 Evidence Requirement

- 必须采集 /workshop/tickets 页面截图。
- 必须采集 /workshop/tickets、/workshop/daily-wages、/workshop/wage-rates route evidence。
- 必须采集运行态 DOM anchors。
- 必须采集 guarded/readonly state evidence。
- 必须采集 write request observation。
- auth 401 只能记录为 readonly fallback risk，不得解释为权限通过或写链路成功。
- guarded_readonly 不等于写成功。

## 风险字段保留

- Z040 readonly fallback risk: auth_401_count=6, runtime_readonly_fallback_risk=true
- Z039-CAND-001 fallback risk retained
- Z038 fallback risks retained
- prior readonly fallback risks retained
- guarded_readonly_not_write_success: true
- B28 shell_wrapper_anomaly: retained
- Z033 skipped_only: retained
- Z035 screenshot_missing_risk: retained
- remote_lifecycle_parked: true

## 禁止动作确认

- code edits: false
- tests/browser/typecheck: false
- stage/commit/push: false
- cleanup/reset/restore: false
- implementation started: false
- remote lifecycle: false
