# TASK-Z036B-20-REGRESSION-CAND003 款式利润快照只读流回归报告

## 基本结论

- 任务: TASK-Z036B-20-REGRESSION-CAND003
- 角色: B Engineer
- 候选: Z036-CAND-003
- source_task: TASK-Z036B-19-IMPL
- HEAD: 268de6b57e70a225bdee128249a57d44b9719aa6
- 分支: codex/sprint4-seal
- 本任务代码修改: false
- cached: empty
- HEAD tag: empty
- git diff --check: PASS

## 回归范围

changed_files_observed:

- 06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue
- 06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue

当前候选相关代码 diff 仍只在授权 style_profit 文件范围内，api/style_profit.ts 未改且未强行纳入 changed_files。

## 运行态路由与截图

本轮重新采集截图，未复用 B19 截图。

- /reports/style-profit: 200, final_url=http://127.0.0.1:5174/reports/style-profit
- /reports/style-profit/detail?id=101&parity=style-profit: 200, final_url=http://127.0.0.1:5174/reports/style-profit/detail?id=101&parity=style-profit

截图:

- 04_测试与验收/测试证据/z036_cand003_style_profit_snapshot_readonly_flow_regression/style_profit_list_regression_fullpage.png, 1440x900 PNG
- 04_测试与验收/测试证据/z036_cand003_style_profit_snapshot_readonly_flow_regression/style_profit_detail_regression_fullpage.png, 1440x1378 PNG

## DOM Anchors

8 个 required anchors 均已在两路由 union 中 observed:

- style-profit-page
- style-profit-query-form
- style-profit-summary-grid
- style-profit-table
- style-profit-archive-button
- style-profit-detail-page
- style-profit-source-map-table
- style-profit-readonly-hint

## 只读边界

- write_requests_observed_count: 0
- auth_401_observed: true
- auth_401_count: 2
- runtime_readonly_fallback_risk: true
- 401 来源: GET /api/auth/me
- 权限 401 未被误判为写链路成功或权限通过。
- 归档、清空、确认、导出等入口保持 guarded/disabled/只读状态。
- read_only_boundary_preserved: true
- real_write_action_added: false

## 验证命令

- command: npm run typecheck
- workdir: 06_前端/lingyi-pc
- exit_code: 0
- summary: vue-tsc --noEmit -p tsconfig.json PASS

## Scope Guard

- backend_changed: false
- tests_changed: false
- candidate_pool_changed: false
- historical_dirty_touched: false
- log_control_dirty_touched: false
- residual_artifacts_touched: false
- z035_committed_product_files_touched: false

## 风险保留

- CAND001 runtime_readonly_fallback_risk: true
- CAND001 console_401_errors_observed: 4
- CAND001 network_401_errors_observed: 4
- CAND001 write_chain_success: false
- CAND001 permission_misread_as_success: false
- B28 shell_wrapper_anomaly_preserved: true
- Z033 skipped-only 风险继续保留
- screenshot_missing_risk_for_Z035: true

## 下一步

- next_task: TASK-Z036B-21-LEDGER-CAND003
- run_this_task: false
