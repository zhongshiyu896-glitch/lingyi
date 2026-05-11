# TASK-Y95B-03-IMPL /workshop/daily-wages 车间工资日报主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y95B-03-IMPL`
- 路由: `/workshop/daily-wages`
- 目标: 在单页主列表完成真实交互切片（查询/重置/分页/工资合计映射/空态/错误态/权限或禁用态/只读导航）。
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue`
- 本轮未改动（按边界保持）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现摘要
- 查询与重置:
  - 新增 `applyPrimaryQuery()`：点击查询前强制 `page=1`，触发真实 `GET /api/workshop/daily-wages`。
  - 新增 `resetPrimaryFilters()`：清空 `employee/process_name/item_code/from_date/to_date`，恢复 `page=1,page_size=20` 并触发真实 GET。
- 状态与证据锚点:
  - 新增稳定 `data-testid`：筛选区、查询/重置按钮、表格、工资合计、分页、返回工票列表、空态、错误态、无权限态。
  - 工资合计提示保留并加审计锚点 `workshop-daily-wage-total-amount`。
- 错误态与空态:
  - 新增 `errorMessage` + 错误告警（`el-alert`），GET 异常时可视化错误态。
  - 增加独立空态 `el-empty`（无数据且无错误时显示）。
- 导航与只读边界:
  - “返回工票列表”保持只读导航到 `/workshop/tickets`。
  - 无新增写动作；不触发 POST/PUT/PATCH/DELETE，不触发导出/下载/打印请求。

## 4. 保留语义检查
- 保留 `/workshop/daily-wages` 既有只读 GET 契约。
- 保留工资合计展示、分页查询主流程。
- 保留权限态、空态、错误态、禁用或提示态。
- 本轮未触碰前序已审计页面：
  - `SubcontractOrderList.vue`
  - `WorkshopTicketList.vue`

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: EMPTY
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 6. 浏览器回归证据
- route: `/workshop/daily-wages`
- script: `/tmp/task_y95b_03_impl_browser_check.mjs`
- result_json: `/tmp/task_y95b_03_impl_20260508T080801Z_browser_results.json`
- screenshots_dir: `/tmp/task_y95b_03_impl_20260508T080801Z_screenshots`
- screenshots_count: `9`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `query_get_triggered=true`
- `empty_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `total_amount_mapped=true`
- `table_fields_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `readonly_navigation_guarded_or_get_only=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过可控 `employee=__simulate_error__` 注入一次 503 验证，归类 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y95B-04` 或其他页面: PASS
- 未释放 parked blockers: PASS
