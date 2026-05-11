# TASK-Y95B-01-IMPL /subcontract/list 外发单列表主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y95B-01-IMPL`
- 路由: `/subcontract/list`
- 目标: 主列表真实交互切片（查询/空筛选查询/重置/分页/详情/状态标签/空态/错误态/权限禁用态/guarded 写动作）
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
- 本轮未改动（按边界保持）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`

## 3. 实现摘要
- 查询交互增强:
  - 新增 `applyQuery()`：点击查询前强制 `query.page=1`，再触发 `loadOrders()`，确保真实 GET 走分页第一页。
  - 保留空筛选可查询路径，空筛选点击查询同样触发真实 GET。
- 重置交互补齐:
  - 新增 `resetQuery()`：清空 `supplier/status`，恢复 `page=1,page_size=20`，并触发真实 GET。
- 分页交互保持真实 GET:
  - `onPageChange` 与 `onSizeChange` 保持触发 `loadOrders()`，并在 size 变化时恢复 `page=1`。
- 详情交互:
  - 详情入口保持 `router.push('/subcontract/detail?id=...')`，详情页触发既有 `GET /api/subcontract/{id}`。
- 错误/空态/权限与禁用证据锚点:
  - 新增 `errorMessage`，请求失败时落地 `el-alert`（`data-testid=subcontract-error-state`）。
  - 新增显式空态 `el-empty`（`data-testid=subcontract-empty-state`）。
  - 无权限态保留并增加 `data-testid=subcontract-permission-empty-state`。
- guarded 写动作:
  - 页面头部新增提示型写动作按钮（新建外发单/发料/回料/验货/同步重试），统一走 `guardedAction()`，仅提示只读模式，不触发写请求。

## 4. 稳定锚点（data-testid）
- 页面与主区块: `subcontract-list-page`、`subcontract-main-card`
- 筛选区: `subcontract-filter-form`
- 筛选字段: `subcontract-filter-supplier`、`subcontract-filter-status`
- 查询/重置: `subcontract-query-btn`、`subcontract-reset-btn`
- 主表/状态/详情/分页: `subcontract-table`、`subcontract-status-tag`、`subcontract-detail-entry`、`subcontract-pagination`
- 错误/空态/权限/guarded: `subcontract-error-state`、`subcontract-empty-state`、`subcontract-permission-empty-state`、`subcontract-guarded-actions`

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: EMPTY
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 -c core.quotePath=false diff --name-only -- '06_前端' '07_后端'`: `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`

## 6. 浏览器回归证据
- route: `/subcontract/list`
- script: `/tmp/task_y95b_01_impl_browser_check.mjs`
- result_json: `/tmp/task_y95b_01_impl_20260508T072302Z_browser_results.json`
- screenshots_dir: `/tmp/task_y95b_01_impl_20260508T072302Z_screenshots`
- screenshots_count: `9`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `query_get_triggered=true`
- `empty_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `detail_get_triggered=true`
- `detail_page_or_panel_opened=true`
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
- 错误态通过可控 `supplier=__simulate_error__` 注入 `503` 验证，计入 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y95B-02`: PASS
- 未释放 parked blockers: PASS
