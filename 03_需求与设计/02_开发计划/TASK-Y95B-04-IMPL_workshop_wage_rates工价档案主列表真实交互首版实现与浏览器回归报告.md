# TASK-Y95B-04-IMPL /workshop/wage-rates 工价档案主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y95B-04-IMPL`
- 路由: `/workshop/wage-rates`
- 目标: 在单页主列表完成真实交互切片（查询/重置/分页/字段映射/只读导航/guarded 写动作/空态/错误态/权限或禁用态）。
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue`
- 本轮未改动（按边界保持）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现摘要
- 查询与重置:
  - 新增 `applyPrimaryQuery()`：点击查询前强制 `page=1`，触发真实 `GET /api/workshop/wage-rates`。
  - 新增 `resetPrimaryFilters()`：清空 `item_code/company/rate_scope/process_name/status`，恢复 `page=1,page_size=20` 并触发真实 GET。
- 稳定锚点:
  - 新增稳定 `data-testid`：页面、筛选区、查询/重置、表格、类型/状态标签、分页、返回工票列表、空态、错误态、无权限态、guarded 动作按钮。
- 字段与映射:
  - 类型列改为可审计标签映射（通用/款式专属）。
  - 状态列改为可审计标签映射（active/inactive/unknown）。
  - 保留并可视化展示款式、公司、工序、计件单价、生效区间等字段。
- 写动作边界:
  - “新增工价”“停用工价”改为只读 guarded 提示，不再触发 `createWorkshopWageRate` / `deactivateWorkshopWageRate` 写请求。
  - “返回工票列表”保持只读导航到 `/workshop/tickets`。
- 状态态势:
  - 新增 `errorMessage` + `el-alert` 错误态证据。
  - 新增独立空态锚点（无数据且无错误时显示）。

## 4. 保留语义检查
- 保留 `/workshop/wage-rates` 既有只读 GET 契约。
- 保留分页、筛选、列表展示主流程。
- 保留权限态、空态、错误态、禁用态。
- 本轮未触碰前序已审计页面：
  - `SubcontractOrderList.vue`
  - `WorkshopTicketList.vue`
  - `WorkshopDailyWage.vue`

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: EMPTY
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 6. 浏览器回归证据
- route: `/workshop/wage-rates`
- script: `/tmp/task_y95b_04_impl_browser_check.mjs`
- result_json: `/tmp/task_y95b_04_impl_20260508T083756Z_browser_results.json`
- screenshots_dir: `/tmp/task_y95b_04_impl_20260508T083756Z_screenshots`
- screenshots_count: `10`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `query_get_triggered=true`
- `empty_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `table_fields_mapped=true`
- `type_or_scope_tags_mapped=true`
- `status_tags_mapped=true`
- `create_action_guarded=true`
- `deactivate_action_guarded=true`
- `readonly_navigation_guarded_or_get_only=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过可控 `item_code=__simulate_error__` 注入一次 503 验证，归类 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y95B-05` 或其他页面: PASS
- 未释放 parked blockers: PASS
