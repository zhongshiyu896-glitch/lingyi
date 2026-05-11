# TASK-Y105B-02-IMPL /sales-inventory/sales-orders/detail 订单详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y105B-02-IMPL`
- 路由: `/sales-inventory/sales-orders/detail`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y105B-02-IMPL_sales_inventory_sales_orders_detail订单详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`api/sales_inventory.ts`、router、后端 `sales_inventory` router/schema/service、测试文件、控制面文件、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 详情与履约只读 GET 链路
- 保持详情读取链路：`fetchSalesInventorySalesOrderDetail` -> `GET /api/sales-inventory/sales-orders/{name}`。
- 增加只读履约区：`fetchSalesInventorySalesOrderFulfillment` -> `GET /api/sales-inventory/sales-order-fulfillment`，并按当前订单号过滤展示。
- `onMounted` 保持既有权限加载顺序（`loadCurrentUser`、`loadModuleActions('sales_inventory')`）后执行 `loadDetail()`。

### 2.2 写动作 guarded/disabled 提示型
- 新增 `guardedWriteAction(...)`，点击写类入口只提示，不触发写请求。
- 写类入口统一保留 `data-action-type="write"` 与 `data-write-guard="guarded:readonly"`：
  - `sales-order-detail-action-place-order`
  - `sales-order-detail-action-export`
  - `sales-order-detail-action-print`
- 当前详情页维持只读模式提示：`sales-order-detail-permission-disabled-state`。

### 2.3 浏览器可审计 data-testid 补齐
- 页面与头部：
  - `sales-order-detail-page`
  - `sales-order-detail-header`
  - `sales-order-detail-title`
  - `sales-order-detail-back`
- 主档字段与标签：
  - `sales-order-detail-main-fields`
  - `sales-order-detail-field-name`
  - `sales-order-detail-field-company`
  - `sales-order-detail-field-customer`
  - `sales-order-detail-status-tag`
  - `sales-order-detail-docstatus-tag`
- 列表与履约区：
  - `sales-order-detail-items-table`
  - `sales-order-detail-fulfillment-section`
  - `sales-order-detail-fulfillment-table`
  - `sales-order-detail-fulfillment-refresh`
- 状态锚点：
  - `sales-order-detail-missing-name-state`
  - `sales-order-detail-empty-state`
  - `sales-order-detail-error-state`
  - `sales-order-detail-permission-state`
  - `sales-order-detail-permission-disabled-state`
  - `sales-order-detail-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y105b_02_impl_20260511T092036Z_browser_results.json`
- screenshots_dir: `/tmp/task_y105b_02_impl_20260511T092036Z_screenshots`
- screenshots_count: `9`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `detail_table_visible=true`
- `fulfillment_get_triggered=true`
- `fulfillment_readonly_section_visible=true`
- `guarded_write_feedback=true`
- `missing_name_state=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控 503（`/api/sales-inventory/sales-orders/SO-ERROR-503`）验证，`expected_network_4xx_5xx_total=1`。
- 受控 503 产生的浏览器 console 资源错误已归类 expected，不计入 unexplained。

## 4. 验证命令结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS

## 5. 禁止动作核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y105B-03-IMPL` 或其他候选: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态与权限态采用浏览器受控桩响应做可审计验证；联调环境文案可与本地桩略有差异，但不影响只读 GET 链路和零副作用约束。
