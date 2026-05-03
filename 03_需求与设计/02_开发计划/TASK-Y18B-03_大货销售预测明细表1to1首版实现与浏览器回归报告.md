# TASK-Y18B-03 大货销售预测明细表 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y18B-03`
- 页面目标: `大货销售预测明细表`
- 目标路由: `/production/plans`
- 本轮范围: 仅实现 TASK-Y18B-03，保留 P0 大货跟进语义与已完成 `TASK-Y18B-02` 成本物料语义。

## EVIDENCE_USED
- 任务基线：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y17_next_p1_candidate_batch.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Y18B-02_大货成本物料明细表1to1首版实现与浏览器回归报告.md`
- 浏览器证据：
  - `/tmp/task_y18b_03_20260503T142809Z_browser_results.json`
- 截图证据：
  - `/tmp/task_y18b_03_20260503T142809Z_screenshots/01_overview_list.png`
  - `/tmp/task_y18b_03_20260503T142809Z_screenshots/02_sales_forecast_fields.png`
  - `/tmp/task_y18b_03_20260503T142809Z_screenshots/03_material_cost_preserved.png`
  - `/tmp/task_y18b_03_20260503T142809Z_screenshots/04_error_state.png`
  - `/tmp/task_y18b_03_20260503T142809Z_screenshots/05_guarded_action.png`

## IMPLEMENTATION_SUMMARY
- 前端（allowlist 内）：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- 后端（allowlist 内）：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
- 新增只读接口：`GET /api/production/sales-forecast-details`
  - 支持筛选：订单、关键字、翻单号、款号、客户、状态、日期区间、分页。
  - 仅只读聚合预测字段：`forecast_qty`、`forecast_unit_price`、`forecast_amount`、`delivery_date`。
  - 未新增写路由，未触发真实写动作。
- 页面新增 P1 区块：`大货销售预测明细表`，补齐筛选、表头字段、状态标签、空态、错误态、guarded 导出/列设置语义。
- preserved 校验：
  - P0 大货跟进区块保留。
  - `TASK-Y18B-02` 大货成本物料明细区块保留。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项：
  - `订单`、`款号`、`客户`、`关键字`、`状态`、`开始时间`、`结束时间`
- 销售预测关键字段/表头：
  - `生产制单`、`订单信息`、`款号`、`客户`
  - `预测数量`、`预测单价(元)`、`预测金额(元)`、`交期`
  - `状态`、`检查时间`
- 按钮语义：
  - 只读可用：`查看`
  - Guarded：`导出销售预测`、`销售预测列设置`、写语义按钮（保持禁用或提示，不执行真实写操作）

## ROUTE_API_BACKEND_MAPPING
- 路由：`/production/plans`
- 前端 API：
  - `fetchProductionPlans`（P0 保留）
  - `fetchProductionMaterialCostDetails`（Y18B-02 保留）
  - `fetchProductionSalesForecastDetails`（本轮新增）
- 后端：
  - `list_production_plans`（P0 保留）
  - `list_production_material_cost_details`（Y18B-02 保留）
  - `list_production_sales_forecast_details`（本轮新增，只读）

## SCREENSHOT_COMPARISON
- `/production/plans` 已形成三段并存结构：
  - `大货跟进（P0）`
  - `大货成本物料明细表（Y18B-02）`
  - `大货销售预测明细表（Y18B-03）`
- 本轮仅补齐销售预测语义，未覆盖前两段语义。

## BROWSER_VALIDATION
- run_id: `20260503T142809Z`
- result_json: `/tmp/task_y18b_03_20260503T142809Z_browser_results.json`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - sales_forecast_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_production_plan_preserved_check: PASS
  - y18b_02_material_cost_preserved_check: PASS
- counts:
  - screenshots_count: `5`
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`
- 说明：
  - 唯一 `503` 为受控注入，用于验证错误态承接；
  - 已纳入 `expected_error_state_count=1`，不计 unexplained 错误。

## WRITE_ACTION_BOUNDARY
- 未触发 `POST/PUT/PATCH/DELETE`（`write_request_count=0`）。
- 未触发真实导出/下载/打印请求（`download_export_print_request_count=0`）。

## PERMISSION_BOUNDARY
- 未伪造用户/角色。
- 未新增真实写路由，写语义按钮均为 guarded/disabled/提示型。
- 未扩大到 `/reports/style-profit`、`/dashboard/overview`、`/warehouse`。
- 未启动 `TASK-Y18B-04/05`。

## KNOWN_GAPS
- 当前为 P1 首版只读闭环，不包含销售预测写入或审批动作。
- 预测单价/金额来自本地只读估算，未接入外部实时价格体系。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- 启动 TASK-Y18B-04/05: NO
- 修改 allowlist 外产品代码: NO
- 新增真实写路由: NO
- 生产联调/GitHub 管理配置: NO
- 释放 parked blockers: NO

## NEXT_RECOMMENDATION
- 进入 C 审计 `TASK-Y18B-03`。
- 审计通过后，再由 A 决定是否进入 `TASK-Y18B-04`。
