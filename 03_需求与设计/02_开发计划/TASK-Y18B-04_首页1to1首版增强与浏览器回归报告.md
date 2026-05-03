# TASK-Y18B-04 首页 1to1 首版增强与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y18B-04`
- 页面目标: `首页 / 首页（P1 首版增强）`
- 目标路由: `/dashboard/overview`
- 本轮范围: 仅实现 TASK-Y18B-04，保留 P0 大货看板语义。

## EVIDENCE_USED
- 任务与基线：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y17_next_p1_candidate_batch.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Y17B_P0十页本地完成态归档与P1候选冻结报告.md`
- 浏览器证据：
  - `/tmp/task_y18b_04_20260503T144324Z_browser_results.json`
- 截图证据：
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/01_overview.png`
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/02_enhanced_home_metrics.png`
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/03_todo_warning_business_summary.png`
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/04_guarded_action.png`
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/05_permission_disabled_state.png`
  - `/tmp/task_y18b_04_20260503T144324Z_screenshots/06_error_state.png`

## IMPLEMENTATION_SUMMARY
- 前端（allowlist 内）：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/dashboard.ts`
- 后端（allowlist 内）：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/dashboard.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/dashboard_service.py`
- 实现内容：
  - 在 `/dashboard/overview` 叠加 P1 首页增强区块：关键指标、待办/预警、经营概览、最近业务动态、销售预测趋势。
  - 补齐只读语义按钮（刷新、导出概览、新增待办）与 guarded 行为提示。
  - 增加 `home_overview` 前后端契约与服务聚合，不新增写接口。
  - 保留 P0 大货看板主区块（流程看板 + 消息表格）不被覆盖。

## FIELD_BUTTON_TABLE_MAPPING
- 首页关键指标：
  - `质检单量`、`库存总量`、`质检通过率`、`仓储预警`
- 待办/预警：
  - `待处理动态`、`超期订单`、`仓储预警`
- 经营概览与动态：
  - `经营概览`、`最近业务动态`
- 趋势展示字段：
  - `周期`、`预测销售额`、`预测成本`、`预测利润`
- 按钮语义：
  - 只读可用：`刷新指标`
  - Guarded：`导出概览`、`新增待办`、写语义按钮（仅提示，不触发写请求）

## ROUTE_API_BACKEND_MAPPING
- 路由：`/dashboard/overview`
- 前端 API：
  - `fetchDashboardOverview`
  - `DashboardOverviewData.home_overview`（新增）
- 后端服务：
  - `DashboardService.get_overview` 返回 `home_overview`
  - `_build_home_overview` 聚合只读首页增强数据

## SCREENSHOT_COMPARISON
- 本轮页面同时具备：
  - P0：`大货管理 / 大货看板`（流程节点 + 消息列表）
  - P1：`首页经营总览（P1）`（指标 + 待办预警 + 经营概览 + 趋势）
- 结论：P1 为增量叠加，P0 主语义保持。

## BROWSER_VALIDATION
- run_id: `20260503T144324Z`
- result_json: `/tmp/task_y18b_04_20260503T144324Z_browser_results.json`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - metrics_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - dashboard_home_fields_mapped: PASS
  - buttons_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_dashboard_overview_preserved_check: PASS
- counts:
  - screenshots_count: `6`
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `0`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `0`
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## WRITE_ACTION_BOUNDARY
- 未触发 `POST/PUT/PATCH/DELETE`（`write_request_count=0`）。
- 未触发真实导出/下载/打印请求（`download_export_print_request_count=0`）。

## PERMISSION_BOUNDARY
- 未伪造用户/角色，权限仍来自现有本地 dev runtime 语义。
- 未新增真实写路由，写动作保持 guarded/disabled。
- 未扩大到 `/warehouse`、`/production/plans`、`/reports/style-profit`。
- 未启动 `TASK-Y18B-05`。

## KNOWN_GAPS
- 当前为首页增强首版，趋势数据为本地只读聚合展示，不包含真实写入或审批动作。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- 启动 TASK-Y18B-05: NO
- 修改 allowlist 外产品代码: NO
- 新增真实写路由: NO
- 生产联调/GitHub 管理配置: NO
- 释放 parked blockers: NO

## NEXT_RECOMMENDATION
- 进入 C 审计 `TASK-Y18B-04`。
- 审计通过后，再由 A 决定是否进入 `TASK-Y18B-05`。
