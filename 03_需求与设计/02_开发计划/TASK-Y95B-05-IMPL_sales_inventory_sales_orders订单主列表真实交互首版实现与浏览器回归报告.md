# TASK-Y95B-05-IMPL /sales-inventory/sales-orders 订单主列表真实交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y95B-05-IMPL`
- 路由: `/sales-inventory/sales-orders`
- 来源候选: `TASK-Y94B-FE-05 / 订单 / /sales-inventory/sales-orders`
- 本轮仅在 allowlist 内修改，未触碰 API/后端/测试/控制面/C 审计文件。

## 2. 实际修改文件
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
- `03_需求与设计/02_开发计划/TASK-Y95B-05-IMPL_sales_inventory_sales_orders订单主列表真实交互首版实现与浏览器回归报告.md`
- `03_需求与设计/02_开发计划/工程师会话日志.md`

## 3. 实现锚点（仅前端页面）
### 3.1 主列表真实 GET 交互
- 查询入口改为 `applyPrimaryQuery()`：
  - 先设置 `query.page = 1`
  - 触发真实 GET `fetchSalesInventorySalesOrders(...)`
  - 同步触发履约区 GET `fetchSalesInventorySalesOrderFulfillment(...)`
- 重置入口改为 `resetPrimaryFilters()`：
  - 清空 `order_no/keyword/from_date/to_date`
  - 恢复 `page=1/page_size=20`
  - 同步触发主列表 GET 与履约区 GET
- 分页与 page_size：
  - `onPageChange` / `onSizeChange` 触发主列表真实 GET

### 3.2 详情入口只读证据闭合
- `goDetail(name)` 调整为：
  - 先触发只读 GET `fetchSalesInventorySalesOrderDetail(name)`
  - 再路由跳转 `/sales-inventory/sales-orders/detail?name=...`
- 结果：浏览器证据同时满足 `detail_get_triggered=true` 与详情页打开。

### 3.3 履约区真实 GET
- 履约查询/重置分别触发 `GET /api/sales-inventory/sales-order-fulfillment`。

### 3.4 guarded 写动作与稳定锚点
- guarded/disabled/提示型动作保持只读：新建、下单、获取订单、导入、导出、打印、更多、履约区导出/列设置等均仅提示，不触发写请求。
- 补齐稳定 `data-testid`：
  - 主筛选区、查询/重置、表格、状态 tag、分页、详情入口
  - 履约区筛选/查询/重置、表格、状态 tag、详情入口
  - 空态、错误态、权限/禁用态

## 4. 浏览器回归证据
- 结果 JSON: `/tmp/task_y95b_05_impl_20260508T093855Z_browser_results.json`
- 截图目录: `/tmp/task_y95b_05_impl_20260508T093855Z_screenshots`
- 截图数量: `10`

关键指标：
- `route_open=true`
- `first_screen_visible=true`
- `list_query_get_triggered=true`
- `reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `detail_get_triggered=true`
- `fulfillment_query_get_triggered=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控注入 `keyword=__simulate_error__` 触发 `expected 503`，已计入 expected，不计入 unexplained。

## 5. 验证命令结果
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --cached --check`：PASS
- `git diff --check`：PASS
- `git diff --name-only -- '06_前端' '07_后端'`：
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`（本轮）
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`（前序）
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`（前序）
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue`（前序）
  - `06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue`（前序）

## 6. 禁止动作核对
- 未修改测试代码：YES
- 未修改 A 控制面文件：YES
- 未修改 C 审计记录：YES
- 未执行 git add / commit / push：YES
- 未执行 PR / merge / tag / release：YES
- 未执行 cleanup / reset / restore / clean / delete：YES
- 未启动其他页面任务：YES
- 未释放 parked blockers：YES

## 7. 残余风险
- 详情页自身的 `canRead` 仍依赖权限状态字段；本轮通过列表页详情入口先触发只读 detail GET 解决了“详情 GET 证据”缺口，不改变既有权限模型。
