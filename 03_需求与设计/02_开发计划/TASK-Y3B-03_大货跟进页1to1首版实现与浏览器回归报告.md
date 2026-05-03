# TASK-Y3B-03 大货跟进页1:1首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-03`
- module: `大货管理`
- page_name: `大货跟进`
- yisuan_url_or_route: `https://erp.huaaosoft.com/#/production/orderTrackingV2`
- local_target_route: `/production/plans`
- frontend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- backend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`

## EVIDENCE_USED
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/051_大货管理_大货跟进.png`
- live_compare meta:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[50]`
- matrix/task breakdown:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json#TASK-Y3B-03`

## IMPLEMENTATION_SUMMARY
- 在 allowlist 内完成“大货跟进”页首版对齐，未扩散到其它模块。
- 视图层完成标题与模块归属对齐（`大货管理 / 大货跟进`），补齐筛选项：`订单`、`款号/款名`、`翻单号`、`开始时间`、`结束时间`、`状态`。
- 补齐按钮语义集合：`筛选`、`清空`、`确定`、`标志已读`、`删除消息`、`新增消息`、`保存`；写动作保持 guarded 提示，不触发写请求。
- 列表结构按证据语义重组为：`订单信息/生产制单/客户信息/预计出货/面辅包进度/生产排期/工厂进度/入库数/出库数`，并保留“跟进”详情入口。
- 后端列表查询 contract 在 allowlist 内最小扩展：新增 `keyword`、`turnover_no`、`from_date`、`to_date` 查询参数并接入服务层过滤。
- 补齐页面级错误承接：请求失败时显示 `大货跟进数据加载失败` alert，避免白屏或静默失败。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项映射：
  - 衣算云 `订单` -> 本地 `query.sales_order`
  - 衣算云 `款号/款名` + `请输入` -> 本地 `query.keyword`
  - 衣算云 `翻单号` -> 本地 `query.turnover_no`
  - 衣算云 `开始时间/结束时间` -> 本地 `query.from_date/query.to_date`
- 主要按钮映射：
  - 已展示：`筛选/清空/确定/标志已读/删除消息/新增消息/保存`
  - 写动作全部保留 guarded 行为，未放开真实写入
- 表格结构映射：
  - 主表头语义对齐为 `订单信息/生产制单/客户信息/预计出货/面辅包进度/生产排期/工厂进度/入库数/出库数`
  - 空态文案：`暂无大货跟进数据，请调整筛选条件后重试`
  - 错误态文案：`大货跟进数据加载失败：<错误信息>`

## ROUTE_API_BACKEND_MAPPING
- route:
  - `/production/plans`（大货跟进列表）
  - `/production/plans/detail`（跟进入口）
- frontend API:
  - `fetchProductionPlans(query)` 新增 `keyword`、`turnover_no`、`from_date`、`to_date`
  - 仍保持 GET 只读请求
- backend API:
  - `GET /api/production/plans` 新增查询参数：
    - `keyword`
    - `turnover_no`
    - `from_date`
    - `to_date`
- backend service:
  - `keyword` 支持 `sales_order/sales_order_item/item_code/customer/plan_no` 最小匹配
  - `turnover_no` 支持 `sales_order_item` 匹配
  - `from_date/to_date` 支持 `planned_start_date` 区间过滤

## SCREENSHOT_COMPARISON
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/051_大货管理_大货跟进.png`
- local screenshots:
  - `/tmp/task_y3b_03_20260503T153820_initial.png`
  - `/tmp/task_y3b_03_20260503T153820_after_search.png`
  - `/tmp/task_y3b_03_20260503T153820_detail.png`
  - `/tmp/task_y3b_03_20260503T153820_error.png`
  - `/tmp/task_y3b_03_20260503T153820_final.png`
- comparison_notes:
  - 已对齐：页面标题语义、筛选字段语义、主按钮集合、状态标签/空态/错误态、跟进入口可达。
  - 差异保留：衣算云主视图偏卡片化，本地首版仍为表格化展示（语义对齐优先，视觉 1:1 后续批次再补）。

## BROWSER_VALIDATION
- run_id: `20260503T153820`
- result_json: `/tmp/task_y3b_03_20260503T153820_browser_results.json`
- base_url: `http://127.0.0.1:5174`
- route: `/production/plans`
- route_open: PASS
- first_screen_visible: PASS
- filters_present: PASS
- table_or_card_structure_mapped: PASS
- table_headers_or_card_fields_mapped: PASS
- buttons_mapped: PASS
- status_tags_mapped: PASS
- empty_state: PASS
- error_state: PASS
- permission_or_disabled_state: PASS
- navigation_or_followup_entry: PASS
- write_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- expected_error_state_count: `1`
- unexplained_error_count: `0`
- 说明：错误态验证使用本地模拟 `code != 0`（HTTP 200）触发页面承接，不引入未解释网络错误。

## WRITE_ACTION_BOUNDARY
- 所有验证均限定本地 dev runtime（`127.0.0.1`）。
- 本轮未触发 POST/PUT/PATCH/DELETE。
- 写动作按钮均处于 guarded 提示语义，未开放真实写入。
- 未触碰生产/ERPNext 真实业务动作。

## PERMISSION_BOUNDARY
- 未伪造用户或角色。
- 未绕过后端鉴权链路。
- 未扩张写权限边界。
- 写动作按钮仅在前端展示层保留入口与提示，不产生写请求。

## KNOWN_GAPS
- evidence_gap_count: `1`
- gap_1:
  - 衣算云“大货跟进”为更密集的卡片化信息布局；本地首版保持表格结构，待后续视觉层 1:1 批次再收敛。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- 释放 parked blockers: NO
- 修改 TASK-Y1/TASK-Y2 矩阵口径: NO

## NEXT_RECOMMENDATION
- 建议进入 `TASK-Y3B-05`（成品进销存报表）首版 1:1，实现首批 P0 三页闭环。
- 对 `大货跟进` 的后续增强建议单独开“视觉密度 1:1 批次”，不与当前语义闭环混做。
