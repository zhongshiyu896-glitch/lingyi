# TASK-Y90B-03-IMPL /production/plans 生产计划主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y90B-03-IMPL`
- 路由: `/production/plans`
- 目标: 在既有生产计划页面中，仅对主列表交互区完成真实交互切片（查询、重置、分页、详情入口、状态/空态/错误态/权限态、guarded 写动作）。
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- 未改动:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`

## 3. 实现摘要
- 查询/重置/分页/详情主逻辑复用既有只读链路（未改 API/后端）:
  - 查询: `onSearch -> loadRows -> fetchProductionPlans(GET /api/production/plans?...)`
  - 重置: `onReset` 清空筛选并恢复 `page=1,page_size=20` 后 `loadRows()`
  - 分页与页大小: `onPageChange/onSizeChange -> loadRows()`
  - 详情入口: `goDetail(planId)` 跳转详情页（详情页通过既有 GET `/api/production/plans/{planId}` 读取详情）
- 本轮新增稳定交互锚点（`data-testid`）仅用于浏览器与审计证据对齐，未改变业务读写边界:
  - 页面/主区块: `production-plan-page`, `production-plan-main-section`
  - 主筛选区: `production-plan-query-form`
  - 主筛选字段: `production-plan-filter-sales-order`, `production-plan-filter-keyword`, `production-plan-filter-turnover-no`, `production-plan-filter-status`, `production-plan-filter-from-date`, `production-plan-filter-to-date`
  - 主动作: `production-plan-search`, `production-plan-reset`, `production-plan-filter`, `production-plan-clear`
  - 主表格/分页/详情: `production-plan-table`, `production-plan-pager`, `production-plan-pagination`, `production-plan-detail-*`
  - guarded 写动作与错误/权限态锚点: `production-plan-guarded-confirm`, `production-plan-error-alert`, `production-plan-no-permission`
- 写动作边界保持不变:
  - 写语义按钮仍走 `onGuardedAction(...)` 提示分支，不触发真实写请求。
  - 未新增 POST/PUT/PATCH/DELETE 路由或调用。

## 4. 保留语义检查
- 保留 `/production/plans` 既有主语义与下方历史只读区块（成本物料明细、销售预测明细、报价单、跟进模板、订单出入库数量、业务员绩效）。
- 保留权限态、空态、错误态、禁用态。
- 写动作、导出、打印等保持 guarded/提示型零副作用。

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 6. 浏览器回归证据
- route: `/production/plans`
- script: `/tmp/task_y90b_03_impl_browser_check.mjs`
- result_json: `/tmp/task_y90b_03_impl_20260508T051829Z_browser_results.json`
- screenshots_dir: `/tmp/task_y90b_03_impl_20260508T051829Z_screenshots`
- screenshots_count: `9`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `filters_present=true`
- `production_plan_fields_mapped=true`
- `query_get_triggered=true`
- `empty_filter_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `detail_get_triggered=true`
- `buttons_mapped=true`
- `status_tags_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过脚本注入一次 `GET /api/production/plans?...keyword=__simulate_error__` 的 503（expected）验证，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y90B-04` 或其他页面: PASS
- 未释放 parked blockers: PASS
