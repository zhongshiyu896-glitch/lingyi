# TASK-Z036B-10-PREP CAND002 边界冻结报告

## Boundary

- source_task_id: TASK-Z036B-09-PREP
- selected_candidate_id: Z036-CAND-002
- implementation_workdir: `/Users/hh/Desktop/领意服装管理系统`
- frontend_workdir: `06_前端/lingyi-pc`
- candidate_title: 加工厂对账列表详情打印只读流
- page_scope: 加工厂对账
- routes:
  - `/factory-statements/list`
  - `/factory-statements/detail`
  - `/factory-statements/print`
- visible_acceptance_goal: 用户能在加工厂对账列表查看筛选、KPI、对账主表，并进入详情/打印视图查看单据主字段、状态、明细和只读写入口状态。
- read_only: true
- backend_allowed: false
- next_task: TASK-Z036B-11-IMPL
- run_this_task: false

## Expected Allowed File Scope

- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
- `06_前端/lingyi-pc/src/api/factory_statement.ts`

## Route Static Check

- `/factory-statements/list`: `06_前端/lingyi-pc/src/router/index.ts:110`, component `FactoryStatementList.vue`
- `/factory-statements/detail`: `06_前端/lingyi-pc/src/router/index.ts:116`, component `FactoryStatementDetail.vue`
- `/factory-statements/print`: `06_前端/lingyi-pc/src/router/index.ts:122`, component `FactoryStatementPrint.vue`
- route_static_check: PASS

## Field/Button/State Anchors

- `factory-statement-list-page`
- `factory-statement-kpi-grid`
- `factory-statement-query-form`
- `factory-statement-table`
- `factory-statement-detail-page`
- `factory-statement-status-tag`
- `factory-statement-print-page`
- `factory-statement-write-guard`

## Browser Evidence Plan

- 采集 `/factory-statements/list` 运行态截图或 DOM/route evidence
- 采集 `/factory-statements/detail` 运行态截图或 DOM/route evidence
- 采集 `/factory-statements/print` 运行态截图或 DOM/route evidence
- 采集 8 个 data-testid/DOM anchors
- 采集只读写入口 guard/disabled 状态
- 若无法截图，必须记录 `screenshot_skip_reason`，并提供运行态 DOM/route 替代证据

## Scope Check

- allowed_files_exist: all true
- allowed_files_dirty: all false
- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- intersections_with_z035_committed_product_files: []
- unknown_dirty: []
- must_block_before_continue: []

## Forbidden Scope

- `06_前端/lingyi-pc/src/api/report.ts`
- `06_前端` 中不属于 expected allowed file scope 的其他文件
- `07_后端` 全部
- backend app/tests 全部
- candidate pool
- historical dirty forbidden 16 个 product/test 文件
- 3 个 log/control dirty 文件
- 3 个 Z034 B37 residual artifacts
- Z035 committed product files
- runtime/cache/test-results
- remote lifecycle、production readback、go-live

## Risk Carry Forward

- CAND001 runtime_readonly_fallback_risk: true
- CAND001 console_401_errors_observed: 4
- CAND001 network_401_errors_observed: 4
- CAND001 write_chain_success: false
- CAND001 permission_misread_as_success: false
- B28 shell_wrapper_anomaly_preserved: true
- Z033 skipped_only_evidence: true
- Z033 actual_passed_count: 0
- Z033 skipped_count: 4
- screenshot_missing_risk_for_Z035: true

## Forbidden Actions

- code edits: false
- tests/browser/typecheck: false
- stage/commit/push/tag/PR/release: false
- cleanup/reset/restore/checkout/stash/clean/delete: false
- remote lifecycle: false
- CAND002 implementation started: false
- CAND003 started: false
