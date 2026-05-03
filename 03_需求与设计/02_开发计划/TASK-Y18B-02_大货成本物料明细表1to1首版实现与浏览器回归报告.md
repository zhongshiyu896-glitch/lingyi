# TASK-Y18B-02 大货成本物料明细表 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y18B-02`
- 页面目标: `大货成本物料明细表`
- 目标路由: `/production/plans`
- 本轮范围: 仅实现 TASK-Y18B-02，保留 P0 `/production/plans` 大货跟进语义，不启动 `TASK-Y18B-03/04/05`。

## EVIDENCE_USED
- 任务与候选基线:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y17_next_p1_candidate_batch.json`
- 本轮浏览器结果:
  - `/tmp/task_y18b_02_20260503T140645Z_browser_results.json`
- 本轮截图:
  - `/tmp/task_y18b_02_20260503T140645Z_screenshots/01_overview_list.png`
  - `/tmp/task_y18b_02_20260503T140645Z_screenshots/02_empty_state.png`
  - `/tmp/task_y18b_02_20260503T140645Z_screenshots/03_material_cost_fields.png`
  - `/tmp/task_y18b_02_20260503T140645Z_screenshots/04_error_state.png`
  - `/tmp/task_y18b_02_20260503T140645Z_screenshots/05_guarded_action.png`

## IMPLEMENTATION_SUMMARY
- 前端（allowlist内）：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- 后端（allowlist内）：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
- 新增只读接口：`GET /api/production/material-cost-details`
  - 支持筛选：订单、关键字、翻单号、物料编码、供应商、状态、日期区间、分页。
  - 数据来源：优先 `ly_production_plan_material` 快照；若无快照则按 BOM 明细与计划数量计算 `required_qty`。
  - 价格/成本字段为只读估算字段：`estimated_unit_price`、`estimated_material_cost`（无单价时按 `0`）。
- 页面新增 P1 区块：`大货成本物料明细表`，补齐筛选、表头字段、状态标签、空态、错误态、guarded 按钮语义。
- P0 preserved：`大货跟进` 主区块保留，未覆盖原有跟进语义。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项：
  - `订单`、`物料编码`、`供应商`、`关键字`、`状态`、`开始时间`、`结束时间`
- 成本物料明细关键字段/表头：
  - `生产制单`、`订单信息`、`款号`、`物料编码`、`供应商`
  - `单件用量`、`损耗率`、`需求数量`
  - `估算单价(元)`、`估算成本(元)`、`状态`、`检查时间`
- 按钮语义：
  - 只读可用：`查看`
  - Guarded：`导出`、`列设置`、顶部写语义按钮（保持禁用或提示，不执行真实写动作）

## ROUTE_API_BACKEND_MAPPING
- 路由：`/production/plans`
- 前端 API：
  - `fetchProductionPlans`（P0）
  - `fetchProductionMaterialCostDetails`（本轮新增）
- 后端：
  - `list_production_plans`（P0 保留）
  - `list_production_material_cost_details`（本轮新增，只读）
  - `ProductionService.list_material_cost_details`（本轮新增，只读聚合）

## SCREENSHOT_COMPARISON
- 本地页面已形成“`大货跟进` + `大货成本物料明细（P1）`”并存结构。
- P1 明细字段与筛选语义已补齐；P0 主列表语义仍保留，未发生覆盖式替换。

## BROWSER_VALIDATION
- run_id: `20260503T140645Z`
- result_json: `/tmp/task_y18b_02_20260503T140645Z_browser_results.json`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - material_cost_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - p0_production_plan_preserved_check: PASS
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
  - `503` 为本轮受控注入，仅用于验证错误态承接；
  - 已纳入 `expected_error_state_count=1`，不计 unexplained 错误。

## WRITE_ACTION_BOUNDARY
- 未触发 `POST/PUT/PATCH/DELETE`。
- `write_request_count=0`。
- 未触发真实导出/下载/打印请求（`download_export_print_request_count=0`）。

## PERMISSION_BOUNDARY
- 未伪造用户/角色。
- 未新增真实写路由，写语义按钮均为 guarded/disabled/提示型。
- 未扩大到 `/reports/style-profit`、`/dashboard/overview`、`/warehouse`。

## KNOWN_GAPS
- 当前为 P1 首版只读闭环，不包含真实写入型成本调整流程。
- 物料单价来源依赖备注解析与本地只读估算，缺少统一主数据时默认 `0`。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- 启动 TASK-Y18B-03/04/05: NO
- 修改 allowlist 外产品代码: NO
- 新增真实写路由: NO
- 生产联调/GitHub 管理配置: NO
- 释放 parked blockers: NO

## NEXT_RECOMMENDATION
- 进入 C 审计 `TASK-Y18B-02`。
- 若审计 PASS，再由 A 决定是否进入 `TASK-Y18B-03`。
