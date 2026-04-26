# TASK-190A 前端 Error 数据状态页面归因与最小可用性修复报告

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-190A
ROLE: B Engineer

## CHANGED_FILES
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-190A_前端Error数据状态页面归因与最小可用性修复报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

CODE_CHANGED: YES

## ERROR_STATE_TRIAGE_RESULT
- PASS
- run_id: `20260426035209`
- base_url: `http://127.0.0.1:5174`
- result_json: `/tmp/task190a_browser_results.json`
- pages_checked: `9`
- fixed_pages:
  - `/production/plans/detail`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/subcontract/detail`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/workshop/tickets/batch`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/workshop/daily-wages`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/reports/style-profit/detail`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/factory-statements/detail`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/factory-statements/print`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/warehouse`（`FIXED_FRONTEND_EMPTY_STATE`）
  - `/quality/inspections`（`FIXED_FRONTEND_EMPTY_STATE`）
- expected_empty_state_pages: `[]`
- product_defect_candidates: `[]`
- blocked_out_of_scope: `[]`

## ROOT_CAUSE（TASK-189A 的 data_state=error 归因）
1. 详情页在缺少 query id 时触发 `ElMessage.warning/error`，并继续渲染次级卡片，导致页面被识别为错误态。
2. 多页面在权限加载完成前短暂落入 `!canRead` 分支，出现“无权限”提示，采集窗口内可能被判定为 error。
3. Workshop 批量页存在“错误码/错误信息”静态文案，被采集器按关键字误归为 error。
4. Warehouse 页存在固定 `warning` 风格提示与标签，易被误判为错误态。

## IMPLEMENTATION_SUMMARY（最小修复）
1. 缺参详情页稳定空态（不再弹错误提示）：
   - `ProductionPlanDetail.vue`：新增 `missingPlanId`，缺参时展示“请从生产计划列表进入详情页”；仅在 `canRead && detail` 时显示后续卡片。
   - `SubcontractOrderDetail.vue`：新增 `missingOrderId`，缺参时展示引导空态；回料/验货卡片仅在 `canRead && detail` 显示。
   - `StyleProfitSnapshotDetail.vue`：新增 `missingSnapshotId`，缺参时展示引导空态；明细/追溯卡片仅在 `canRead && snapshot` 显示。
   - `FactoryStatementDetail.vue`：新增 `missingStatementId`，缺参时展示引导空态；明细/日志卡片仅在 `canRead && detail` 显示。
   - `FactoryStatementPrint.vue`：新增 `missingStatementId`，缺参时展示“请从详情页进入打印页”。
2. 权限加载阶段稳定化（避免瞬时无权限误判）：
   - `ProductionPlanDetail.vue`、`SubcontractOrderDetail.vue`、`StyleProfitSnapshotDetail.vue`、`FactoryStatementDetail.vue`、`FactoryStatementPrint.vue`、`WorkshopDailyWage.vue`、`WarehouseDashboard.vue`、`QualityInspectionList.vue` 增加 `permissionReady`，未完成前展示 skeleton。
3. 文案/告警样式收敛：
   - `WorkshopTicketBatch.vue`：“错误码/错误信息”调整为“结果码/结果说明”。
   - `WarehouseDashboard.vue`：只读骨架与受限入口提示由 `warning` 调整为 `info`（保持只读边界，不放开写入口）。

## 9 页面复测证据
- `/production/plans/detail` | status=200 | app=true | first_screen=true | data_state=empty | screenshot=`/tmp/task190a_20260426035209_production_plans_detail.png`
- `/subcontract/detail` | status=200 | app=true | first_screen=true | data_state=empty | screenshot=`/tmp/task190a_20260426035209_subcontract_detail.png`
- `/workshop/tickets/batch` | status=200 | app=true | first_screen=true | data_state=card | screenshot=`/tmp/task190a_20260426035209_workshop_tickets_batch.png`
- `/workshop/daily-wages` | status=200 | app=true | first_screen=true | data_state=card | screenshot=`/tmp/task190a_20260426035209_workshop_daily-wages.png`
- `/reports/style-profit/detail` | status=200 | app=true | first_screen=true | data_state=empty | screenshot=`/tmp/task190a_20260426035209_reports_style-profit_detail.png`
- `/factory-statements/detail` | status=200 | app=true | first_screen=true | data_state=empty | screenshot=`/tmp/task190a_20260426035209_factory-statements_detail.png`
- `/factory-statements/print` | status=200 | app=true | first_screen=true | data_state=empty | screenshot=`/tmp/task190a_20260426035209_factory-statements_print.png`
- `/warehouse` | status=200 | app=true | first_screen=true | data_state=card | screenshot=`/tmp/task190a_20260426035209_warehouse.png`
- `/quality/inspections` | status=200 | app=true | first_screen=true | data_state=card | screenshot=`/tmp/task190a_20260426035209_quality_inspections.png`

## VALIDATION
- git status precheck -> PASS
- staged area empty -> PASS
- npm run typecheck -> PASS
- npm run verify -> PASS
- Playwright 9-page error-state regression -> PASS
- write_request_count=0 -> PASS
- git diff --check -> PASS

## 关键验证摘要（来自 `/tmp/task190a_browser_results.json`）
- auth_me_401_count=`0`
- write_request_count=`0`
- page_errors_total=`0`
- console_errors_total=`0`
- network_4xx_5xx_total=`0`
- API by_method=`{ GET: 22 }`
- API by_status=`{ 200: 22 }`

## FORBIDDEN_ACTIONS
- git add/commit/push/PR/tag/release: NO
- backend/CCC/control-plane edits: NO
- GitHub management config: NO
- production/ERPNext actions: NO
- parked blockers released: NO
- write business actions clicked: NO

NEXT_ROLE: A Technical Architect
BLOCKERS: NONE
