# TASK-Y95B-02-IMPL /workshop/tickets 车间工票查询主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y95B-02-IMPL`
- 路由: `/workshop/tickets`
- 目标: 在单页主列表内完成真实交互切片（查询/重置/分页/汇总详情/状态映射/空态/错误态/权限或禁用态/guarded 写动作）。
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`
- 本轮未改动（按边界保持）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现摘要
- 查询与重置:
  - 新增 `applyPrimaryQuery()`：点击查询前强制 `page=1`，然后触发真实 `GET /api/workshop/tickets`。
  - 新增 `resetPrimaryFilters()`：清空 `employee/job_card/item_code/process_name/operation_type/from_date/to_date`，恢复 `page=1,page_size=20` 并触发真实 GET。
- 列表与状态可审计锚点:
  - 新增稳定 `data-testid` 覆盖筛选区、查询/重置按钮、主表、状态标签、同步状态、分页、汇总入口、汇总弹窗、错误态、空态、无权限态与 guarded 动作区。
  - 新增 `operationTypeLabel`、`syncStatusLabel`，将类型与同步状态映射为可读标签。
- 错误态与空态:
  - 新增 `errorMessage` 和 `el-alert`，列表 GET 失败时显式展示错误态。
  - 保留并增强空态显示，确保 `rows.length===0` 时有稳定空态证据。
- 汇总详情:
  - 保持只读汇总链路，点击“汇总”调用现有 `GET /api/workshop/job-cards/{job_card}/summary` 并打开汇总弹窗。
- 写动作 guarded:
  - 将“工票登记”“批量导入”“重试同步”改为只读 guard 提示，不触发 POST/PUT/PATCH/DELETE。
  - 保留“日薪统计”“工价档案”只读导航，不引入写请求。

## 4. 保留语义检查
- 保留 `/workshop/tickets` 主列表既有只读语义与 GET 契约。
- 保留分页、详情、状态展示主流程。
- 保留无权限态、空态、错误态、禁用或提示态。
- 本轮未触碰前序已审计页面（`SubcontractOrderList.vue`）。

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: EMPTY
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 6. 浏览器回归证据
- route: `/workshop/tickets`
- script: `/tmp/task_y95b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y95b_02_impl_20260508T075148Z_browser_results.json`
- screenshots_dir: `/tmp/task_y95b_02_impl_20260508T075148Z_screenshots`
- screenshots_count: `8`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `query_get_triggered=true`
- `empty_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `summary_get_triggered=true`
- `summary_dialog_opened=true`
- `status_tags_or_sync_status_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过可控 `employee=__simulate_error__` 注入一次 503 验证，已归类 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y95B-03` 或其他页面: PASS
- 未释放 parked blockers: PASS
