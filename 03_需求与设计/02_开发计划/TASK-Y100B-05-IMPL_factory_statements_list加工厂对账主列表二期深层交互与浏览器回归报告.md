# TASK-Y100B-05-IMPL /factory-statements/list 加工厂对账主列表二期深层交互与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y100B-05-IMPL`
- 路由: `/factory-statements/list`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
  - `03_需求与设计/02_开发计划/TASK-Y100B-05-IMPL_factory_statements_list加工厂对账主列表二期深层交互与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`QualityInspectionList.vue`、`SalesInventoryStockLedger.vue`、`SalesInventoryReferenceList.vue`、`DashboardOverview.vue`、`api/factory_statement.ts`、后端文件、测试文件、控制面文件、C 审计记录。

## 2. 实现锚点
### 2.1 主列表查询/重置/分页真实 GET 保持
- 保持 `applyPrimaryQuery()`：查询前强制 `query.page = 1`，再调用 `loadRows()`。
- 保持 `resetPrimaryFilters()`：清空 `supplier/statement_status/from_date/to_date`，恢复 `page=1/page_size=20`，再调用 `loadRows()`。
- 保持 `onPageChange/onSizeChange` 分页触发 `loadRows()`。

### 2.2 详情入口改为本页只读详情 GET + 只读呈现
- 新增 `openReadonlyDetail(statementId)`：
  - 调用既有 `fetchFactoryStatementDetail(statementId)`（`GET /api/factory-statements/{id}`）。
  - 打开本页只读弹窗 `factory-statement-readonly-detail-dialog`。
- 列表“查看”按钮改为 `@click="openReadonlyDetail(scope.row.id)"`。
- 新增只读详情呈现锚点：
  - `factory-statement-detail-summary`
  - `factory-statement-detail-items-table`
  - `factory-statement-detail-loading`
  - `factory-statement-detail-error-alert`

### 2.3 打印与写/副作用入口 guarded
- 主列表“打印”按钮改为 guarded：
  - `data-action-type="write"`
  - `data-write-guard="readonly:print"`
  - `@click="showGuardedAction('打印')"`
- 不再跳转 `/factory-statements/print`，不触发 `window.print`。
- 导出、确认、取消、应付草稿、新建等入口保持 guarded 或 disabled。

### 2.4 样品过滤区与深层只读分区可审计锚点
- 样品过滤区补齐稳定 `data-testid`：
  - `factory-statement-sample-filter-form`
  - `factory-statement-sample-filter-order-no`
  - `factory-statement-sample-filter-style-code`
  - `factory-statement-sample-filter-factory`
  - `factory-statement-sample-filter-date-range`
  - `factory-statement-sample-filter-min-amount`
  - `factory-statement-sample-filter-max-amount`
  - `factory-statement-sample-filter-status`
  - `factory-statement-sample-filter-apply`
  - `factory-statement-sample-filter-reset`
  - `factory-statement-sample-filter-state`
- 新增 `sampleFilterStatus` 与 `sampleFilterStateText`，确保“筛选/重置”有可见前端状态变化。
- 深层交互证据分区采用 `factory-reconciliation-section`，补齐：
  - `factory-reconciliation-filter-form`
  - `factory-reconciliation-query-button`
  - `factory-reconciliation-reset-button`
  - `factory-reconciliation-table`
  - `factory-reconciliation-pagination`
  - `factory-reconciliation-error-alert`
  - `factory-reconciliation-no-permission`
- 分区交互仅复用既有 `loadFactoryReconciliations()`（既有 GET），未新增 API。

## 3. 浏览器回归证据
- result_json: `/tmp/task_y100b_05_impl_20260511T060430Z_browser_results.json`
- screenshots_dir: `/tmp/task_y100b_05_impl_20260511T060430Z_screenshots`
- screenshots_count: `11`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `detail_get_triggered=true`
- `detail_readonly_presented=true`
- `sample_filter_state_changed=true`
- `factory_reconciliation_get_triggered=true`
- `guarded_write_feedback=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控 expected 503（`supplier=__ERROR__`）注入验证，计入 `expected_network_4xx_5xx_total=1`，未计入 unexplained。

## 4. 验证命令结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- '06_前端' '07_后端'`：
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`（前序 `TASK-Y100B-01-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`（前序 `TASK-Y100B-02-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`（前序 `TASK-Y100B-03-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`（前序 `TASK-Y100B-04-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`（本轮新增）

## 5. 禁止动作核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y100B-06` 或其他页面: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态和权限态证据依赖本地浏览器受控桩响应；联调环境中错误文案可能不同，但不影响只读交互链路与零副作用约束。
