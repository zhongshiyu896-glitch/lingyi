# TASK-Y18B-01-FIX1 订单款式利润预测明细表 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y18B-01-FIX1`
- 页面目标: `订单款式利润预测明细表`
- 目标路由: `/reports/style-profit`
- 本轮范围: 仅实现 TASK-Y18B-01，保留既有 P0 style-profit 语义，不启动 `TASK-Y18B-02/03/04/05`。

## EVIDENCE_USED
- 任务与候选基线:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y17_next_p1_candidate_batch.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Y17B_P0十页本地完成态归档与P1候选冻结报告.md`
- 衣算云矩阵证据:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`（index=56）
- 本轮浏览器结果:
  - `/tmp/task_y18b_01_fix1_20260503T214328_browser_results.json`
- 本轮截图:
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/01_permission_disabled_loading.png`
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/02_overview_list.png`
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/03_prediction_fields.png`
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/04_guarded_action.png`
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/05_detail_preserved.png`
  - `/tmp/task_y18b_01_fix1_20260503T214328_screenshots/06_error_state.png`

## IMPLEMENTATION_SUMMARY
- 前端仅在 allowlist 内调整：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
- 语义从“成品销售利润明细”收口为“订单款式利润预测明细”：
  - 筛选项改为款式/品牌/关键词/开始时间/结束时间；
  - 列表补齐预测相关字段（销售预测金额、成本预测金额、利润预测金额、利润预测率）与状态标签；
  - 详情页补齐预测字段展示与只读结构；
  - 新增预测汇总卡片（销售预测金额、成本预测金额、利润预测金额、平均利润率）。
- 导出/列设置/查看详情等按钮保持 guarded/只读语义，不触发写请求。
- 未修改后端路由、schema、service、API 文件，未新增写路由。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项: `款式`、`品牌`、`关键词`、`开始时间`、`结束时间`。
- 关键表头/字段:
  - `款号`、`款式名称`、`设计号`、`品牌`、`标题`
  - `销售预测金额`、`成本预测金额`、`利润预测金额`、`利润预测率`
  - `状态`、`发送人`、`发送时间`、`更新时间`
- 按钮语义:
  - 只读可用: `查看详情`
  - Guarded: `导出`、`列设置`（提示型，不触发真实下载/导出）

## ROUTE_API_BACKEND_MAPPING
- 路由: `/reports/style-profit`
- 本轮变更前端:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
- 本轮后端/API变更: 无
- P0 preserved check:
  - 已保留 `/reports/style-profit` 已有只读快照语义；
  - 未扩散到 `/production/plans`、`/dashboard/overview`、`/warehouse`。

## SCREENSHOT_COMPARISON
- 本地页面已具备“订单款式利润预测明细”首版 1:1 核心语义（筛选、预测字段、汇总、状态、只读详情）。
- 与衣算云证据相比，当前保持最小闭环实现，未引入创新交互或跨页扩展。

## BROWSER_VALIDATION
- run_id: `20260503T214328`
- result_json: `/tmp/task_y18b_01_fix1_20260503T214328_browser_results.json`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - profit_prediction_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_style_profit_preserved_check: PASS
- counts:
  - screenshots_count: `6`
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`
- 说明:
  - `console_errors_total=1` 与 `network_4xx_5xx_total=1` 来自刻意注入错误态验证；
  - 已被 UI 承接，且计入 `expected_error_state_count=1`，不属于 unexplained 错误。

## WRITE_ACTION_BOUNDARY
- 未触发任何 `POST/PUT/PATCH/DELETE` 请求。
- `write_request_count=0`。
- 导出/下载/打印真实请求未触发（`download_export_print_request_count=0`）。

## PERMISSION_BOUNDARY
- 未伪造生产权限，仍在本地 dev runtime/dev-auth 语义下验证。
- 写语义按钮均保持 guarded/disabled，不放宽权限边界。

## KNOWN_GAPS
- 当前为 P1 首版只读闭环，不包含真实写入型利润计算提交流程。
- 若后续需要实写链路，需单独任务授权并新增对应后端写契约与审计。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- 启动 TASK-Y18B-02/03/04/05: NO
- 修改 allowlist 外产品代码: NO
- 新增真实写路由: NO
- 生产联调/GitHub 管理配置: NO
- 释放 parked blockers: NO

## NEXT_RECOMMENDATION
- 进入 C 审计 `TASK-Y18B-01-FIX1`。
- 若 C PASS，再由 A 选择下一张 P1 页面任务单独入场。
