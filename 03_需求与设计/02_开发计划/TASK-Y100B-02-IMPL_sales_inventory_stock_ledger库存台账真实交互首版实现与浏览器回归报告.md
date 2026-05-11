# TASK-Y100B-02-IMPL /sales-inventory/stock-ledger 库存台账真实交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y100B-02-IMPL`
- 路由: `/sales-inventory/stock-ledger`
- 来源候选: `TASK-Y99B-FE-02`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - `03_需求与设计/02_开发计划/TASK-Y100B-02-IMPL_sales_inventory_stock_ledger库存台账真实交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改前序残留 `QualityInspectionList.vue`、API 文件、后端文件、测试代码、A 控制面、C 审计记录。

## 2. 实现锚点
### 2.1 主区块与筛选交互
- 新增库存台账主区块锚点：`data-testid="stock-ledger-section"`。
- 主筛选字段改为 `item_code/company/warehouse/from_date/to_date`，并补齐稳定 `data-testid`：
  - `stock-ledger-item-code-input`
  - `stock-ledger-company-input`
  - `stock-ledger-warehouse-input`
  - `stock-ledger-from-date-input`
  - `stock-ledger-to-date-input`
  - `stock-ledger-query-button`
  - `stock-ledger-reset-button`

### 2.2 查询、必填 guard、分页
- 查询动作 `onSearch()`：先设置 `query.page = 1`，再执行 `loadRows()`。
- `loadRows()` 强制 `item_code` 必填；缺失时显示 `stock-ledger-required-item-code-guard`，不伪造 GET。
- 真实只读 GET 链路：
  - `fetchSalesInventoryStockSummary` -> `GET /api/sales-inventory/items/{item_code}/stock-summary`
  - `fetchSalesInventoryStockLedger` -> `GET /api/sales-inventory/items/{item_code}/stock-ledger`
- 分页/每页数量变更分别由 `onPageChange/onSizeChange` 触发 `loadRows()`。

### 2.3 重置与只读明细
- 重置动作 `onReset()`：清空 `item_code/company/warehouse/from_date/to_date`，恢复 `page=1/page_size=20`，并重置本地区块状态。
- 行内“明细”按钮打开只读抽屉 `stock-ledger-detail-drawer`，展示 voucher/warehouse/qty 等字段，不触发写请求。

### 2.4 状态与 guarded 动作
- 补齐状态锚点：
  - `stock-ledger-table`
  - `stock-ledger-summary-row`
  - `stock-ledger-pagination`
  - `stock-ledger-error-state`
  - `stock-ledger-permission-state`
- 写/副作用入口统一 guarded（`data-write-guard="true"`），仅提示，不触发 POST/PUT/PATCH/DELETE、导出、下载、打印请求。

## 3. 浏览器回归证据
- result_json: `/tmp/task_y100b_02_impl_20260511T023135Z_browser_results.json`
- screenshots_dir: `/tmp/task_y100b_02_impl_20260511T023135Z_screenshots`
- screenshots_count: `9`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `required_item_code_guarded=true`
- `query_get_triggered=true`
- `reset_state_verified=true`
- `pagination_or_size_get_triggered=true`
- `row_detail_opened=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态使用一次受控 expected `503` 验证（`expected_network_4xx_5xx_total=1`），未计入 unexplained。
- 本轮浏览器采证使用只读桩响应固定 `auth/me` 与 `auth/actions(sales_inventory)`，并约束 `sales_inventory` 只读 GET 返回结构化数据，仅用于本地交互证据稳定，不涉及产品代码改动。

## 4. 验证命令结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- '06_前端' '07_后端'`:
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`（前序 `TASK-Y100B-01-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`（本轮新增）

## 5. 禁止动作核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y100B-03-IMPL` 或其他页面: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态与权限态证据来自本地只读受控桩响应与受控 503 注入；联调环境的真实后端报错文案可能不同，但不影响本轮只读交互契约与零副作用门禁。
