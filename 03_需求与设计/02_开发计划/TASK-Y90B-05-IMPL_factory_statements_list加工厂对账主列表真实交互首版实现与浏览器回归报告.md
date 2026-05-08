# TASK-Y90B-05-IMPL /factory-statements/list 加工厂对账主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y90B-05-IMPL`
- 路由: `/factory-statements/list`
- 目标: 在既有加工厂对账主列表完成真实交互切片（查询/重置/分页/详情/状态标签/空态/错误态/权限禁用态/guarded 写动作）。
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- 本轮未改动（按边界保持）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`

## 3. 实现摘要
- 主查询交互补齐:
  - 新增 `applyPrimaryQuery()`：查询前强制 `query.page = 1`，再触发 `loadRows()`，确保查询行为稳定可审计。
  - 新增 `resetPrimaryFilters()`：清空 `supplier / statement_status / from_date / to_date`，恢复 `page=1,page_size=20` 并触发真实 GET。
- 主列表稳定锚点补齐（`data-testid`）:
  - 页面与主区块: `factory-statement-list-page`、`factory-statement-main-section`
  - 查询区: `factory-statement-query-form`
  - 筛选字段: `factory-statement-filter-supplier`、`factory-statement-filter-status`、`factory-statement-filter-from-date`、`factory-statement-filter-to-date`
  - 查询与重置按钮: `factory-statement-query-button`、`factory-statement-reset-button`
  - 主表与状态标签: `factory-statement-main-table`、`factory-statement-status-tag`
  - 详情入口与分页: `factory-statement-detail-button`、`factory-statement-pagination`
  - 错误/权限态: `factory-statement-error-alert`、`factory-statement-no-permission`
- 保留只读边界:
  - 继续复用既有 GET 列表接口 `GET /api/factory-statements/`。
  - 详情入口维持既有详情路由跳转，详情页读取既有 `GET /api/factory-statements/{id}`。
  - 导出/生成应付/确认/取消等动作保持 guarded 提示，不触发写请求。

## 4. 保留语义检查
- 保留 `/factory-statements/list` 主列表既有主语义。
- 保留状态标签映射、空态、错误态、权限/禁用态。
- 保留 guarded 写动作提示语义，未放开任何写接口。
- 未触碰前序已审计页面（`BomList.vue`、`WarehouseDashboard.vue`、`ProductionPlanList.vue`、`StyleProfitSnapshotList.vue`）。

## 5. 验证结果
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 6. 浏览器回归证据
- route: `/factory-statements/list`
- script: `/tmp/task_y90b_05_impl_browser_check.mjs`
- result_json: `/tmp/task_y90b_05_impl_20260508T060123Z_browser_results.json`
- screenshots_dir: `/tmp/task_y90b_05_impl_20260508T060123Z_screenshots`
- screenshots_count: `8`

核心断言:
- `route_open=true`
- `first_screen_visible=true`
- `filters_present=true`
- `query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `detail_route_opened=true`
- `detail_get_triggered=true`
- `status_tags_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `guarded_write_feedback=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过一次可控 `supplier=__simulate_error__` 注入 `503` 验证，归类为 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y90B-06` 或其他页面: PASS
- 未释放 parked blockers: PASS
