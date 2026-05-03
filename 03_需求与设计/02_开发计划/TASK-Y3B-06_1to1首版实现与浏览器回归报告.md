# TASK-Y3B-06 成品销售利润明细表 1:1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-06`
- module: `财务管理`
- page_name: `成品销售利润明细表`
- yisuan_url_or_route: `https://erp.huaaosoft.com/#/financial/financialReport/factoryReconciliationReport`
- local_target_route: `/reports/style-profit`
- frontend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
- backend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`

## EVIDENCE_USED
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/096_财务管理_成品销售利润明细表.png`
  - `/Users/hh/Desktop/衣算云/证据数据/algo_probe_成品销售利润明细表.png`
- live_compare meta:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[95]`
- matrix/task breakdown:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json#TASK-Y3B-06`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y7_next_p0_page_batch.json#TASK-Y3B-06`

## IMPLEMENTATION_SUMMARY
- 在 allowlist 内完成“成品销售利润明细表”首版 1:1 语义补齐，未扩散到其它页面或模块。
- 列表页补齐筛选语义（加工厂/款号款名/业务单据/开始日期/结束日期/状态）与按钮语义集合（重置/查询/导出/列设置/清空/确定/标志已读/删除消息/新增消息/搜索/保存/取消/重置列）。
- 写语义按钮统一为 guarded 提示，不触发真实写请求、导出请求、下载请求、打印请求。
- 列表页补齐 1:1 结构字段映射：加工厂、业务单据、业务日期、业务类型、应付金额、实付金额、应收金额、未付金额、利润率、备注、状态、发送时间、发送人，并保留“详情”入口。
- 详情页补齐错误态承接、状态标签映射、发送时间/发送人展示。
- 前后端 contract 最小补齐：`StyleProfitSnapshotResult/StyleProfitSnapshotListItem` 增加 `created_by`、`created_at`，列表增加 `company_full_name`，用于页面字段闭环。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选映射：
  - `加工厂` -> `query.company`
  - `款号/款名` -> `query.item_code`
  - `业务单据` -> `query.sales_order`
  - `开始日期` -> `query.from_date`
  - `结束日期` -> `query.to_date`
  - `状态` -> `query.snapshot_status`
- 按钮映射：
  - 已展示：`重置/查询/导出/列设置/清空/确定/标志已读/删除消息/新增消息/搜索/保存/取消/重置列`
  - `导出/列设置/清空/确定/标志已读/删除消息/新增消息/保存/取消/重置列` 均为 guarded，点击仅提示，不触发写动作
- 表格字段映射：
  - 已实现：`加工厂/加工厂全称/业务单据/业务日期/业务类型/应付金额/实付金额/应收金额/未付金额/备注/日/一/二/三/四/五/六/标题/发送时间/状态/发送人`
  - 利润指标保留：`利润率`（并在详情页保留利润金额、成本、分摊状态等明细字段）
- 空态/错误态：
  - 空态文案：`暂无成品销售利润明细数据，请调整筛选条件后重试`
  - 错误态文案：`成品销售利润明细表数据加载失败：<message>`

## ROUTE_API_BACKEND_MAPPING
- route:
  - `/reports/style-profit`（列表页）
  - `/reports/style-profit/detail`（详情页）
- frontend API:
  - `GET /api/reports/style-profit/snapshots`
  - `GET /api/reports/style-profit/snapshots/{snapshot_id}`
- backend mapping:
  - router: `style_profit.py`（列表与详情返回字段补齐）
  - schema: `style_profit.py`（Result/ListItem 字段补齐）
  - service: `style_profit_service.py`（快照结果字段补齐）

## SCREENSHOT_COMPARISON
- yisuan_screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/096_财务管理_成品销售利润明细表.png`
- local_screenshots:
  - `/tmp/task_y3b_06_20260503T092400_initial.png`
  - `/tmp/task_y3b_06_20260503T092400_queried.png`
  - `/tmp/task_y3b_06_20260503T092400_detail.png`
  - `/tmp/task_y3b_06_20260503T092400_error.png`
  - `/tmp/task_y3b_06_20260503T092400_final.png`
- comparison_notes:
  - 已对齐：页面语义标题、筛选项、按钮集合、状态列/利润指标展示、详情入口、空态/错误态。
  - 差异：衣算云证据页标题为“加工厂对账表”，当前 TASK-Y3B-06 目标页为“成品销售利润明细表”；本轮按任务拆分源（Y2/Y7）优先闭合 style-profit 页面语义。
- evidence_gap_count: `1`

## BROWSER_VALIDATION
- run_id: `20260503T092400`
- result_json: `/tmp/task_y3b_06_20260503T092400_browser_results.json`
- base_url: `http://127.0.0.1:5174`
- route: `/reports/style-profit`
- route_open: PASS
- first_screen_visible: PASS
- filters_present: PASS
- structure_mapped: PASS
- fields_or_headers_mapped: PASS
- buttons_mapped: PASS
- status_tags_mapped: PASS
- empty_state: PASS
- error_state: PASS
- permission_or_disabled_state: PASS
- navigation_or_flow_entry: PASS
- write_request_count: `0`
- download_export_print_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- expected_error_state_count: `1`
- unexplained_error_count: `0`

## WRITE_ACTION_BOUNDARY
- 本轮验证仅使用本地 dev runtime（`127.0.0.1`）。
- 未触发 POST/PUT/PATCH/DELETE。
- 未触发真实导出/下载/打印请求。
- 写语义按钮全部保持 guarded 提示，不伪造成功，不越权放开写入口。

## PERMISSION_BOUNDARY
- user_or_role_faked: `NO`
- backend_permission_bypassed: `NO`
- write_permission_expanded: `NO`
- disabled_or_guarded_actions:
  - `导出/列设置/清空/确定/标志已读/删除消息/新增消息/保存/取消/重置列`
- evidence_summary:
  - 页面读取权限继续依赖 `permissionStore.loadModuleActions('style_profit')` 与 `canRead` 判定。
  - 无权限时显示 `无款式利润查看权限`，不会展示可执行写动作。

## KNOWN_GAPS
- `evidence_gap_count=1`
- 衣算云截图路由（`factoryReconciliationReport`）与 TASK-Y3B-06 拆分目标（`/reports/style-profit`）存在口径差异；当前已按 Y2/Y7 冻结任务闭合 style-profit 首版，后续如需“加工厂对账表”独立 1:1，需要 A 另开单页任务。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- 释放 parked blockers: NO
- 修改 TASK-Y1/TASK-Y2/TASK-Y7 矩阵口径: NO

## NEXT_RECOMMENDATION
- 建议进入 `TASK-Y3B-06` C 审计。
- 审计通过后，再进入 `TASK-Y3B-01`（P0 第二批第三页）实现，保持同一 allowlist 与证据口径。
