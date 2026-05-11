# TASK-Y100B-03-IMPL /sales-inventory/references 参考资料列表真实交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y100B-03-IMPL`
- 路由: `/sales-inventory/references`
- 来源候选: `TASK-Y99B-FE-03`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
  - `03_需求与设计/02_开发计划/TASK-Y100B-03-IMPL_sales_inventory_references参考资料列表真实交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改前序残留 `QualityInspectionList.vue`、`SalesInventoryStockLedger.vue`、API 文件、后端文件、测试代码、A 控制面、C 审计记录。

## 2. 实现锚点
### 2.1 双 tab 主区块与筛选交互
- 新增主区块标题与只读说明，主 tabs 锚点：`data-testid="references-tabs"`。
- 客户列表锚点补齐：
  - `references-customers-tab`
  - `references-customers-filter-form`
  - `references-customers-query-button`
  - `references-customers-reset-button`
  - `references-customers-table`
  - `references-customers-pagination`
- 仓库列表锚点补齐：
  - `references-warehouses-tab`
  - `references-warehouses-filter-form`
  - `references-warehouses-company-input`
  - `references-warehouses-query-button`
  - `references-warehouses-reset-button`
  - `references-warehouses-table`
  - `references-warehouses-pagination`

### 2.2 真实 GET 查询、重置、分页
- 客户查询 `onCustomerSearch()`：查询前强制 `page=1`，触发真实 `GET /api/sales-inventory/customers`。
- 客户重置 `onCustomerReset()`：恢复 `page=1/page_size=20`，触发真实 GET。
- 仓库查询 `onWarehouseSearch()`：带 `company` 条件触发真实 `GET /api/sales-inventory/warehouses`。
- 仓库重置 `onWarehouseReset()`：清空 `company`，恢复 `page=1/page_size=20`，触发真实 GET。
- 客户与仓库分页/页大小切换分别通过 `onCustomerPageChange/onCustomerSizeChange/onWarehousePageChange/onWarehouseSizeChange` 触发真实 GET。

### 2.3 只读明细、状态与错误态
- 新增只读明细抽屉：`references-readonly-detail-drawer`，支持客户/仓库行“明细”入口，仅读展示字段，不触发写请求。
- 补齐禁用状态标签锚点：
  - `references-customers-disabled-tag`
  - `references-warehouses-disabled-tag`
- 补齐空态/错误态/权限态锚点：
  - `references-customers-empty-state`
  - `references-warehouses-empty-state`
  - `references-customers-error-state`
  - `references-warehouses-error-state`
  - `references-permission-state`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y100b_03_impl_20260511T032333Z_browser_results.json`
- screenshots_dir: `/tmp/task_y100b_03_impl_20260511T032333Z_screenshots`
- screenshots_count: `10`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `customer_query_get_triggered=true`
- `customer_reset_get_triggered=true`
- `warehouse_query_get_triggered=true`
- `warehouse_reset_get_triggered=true`
- `pagination_or_size_get_triggered=true`
- `readonly_detail_opened=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控 expected `503` 注入验证（`expected_network_4xx_5xx_total=1`），未计入 unexplained。
- 浏览器采证对 `auth/me`、`auth/actions(sales_inventory)`、`customers/warehouses` 仅做本地只读桩响应，保证交互证据稳定，不涉及产品代码改动。

## 4. 验证命令结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- '06_前端' '07_后端'`:
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`（前序 `TASK-Y100B-01-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`（前序 `TASK-Y100B-02-IMPL` 已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`（本轮新增）

## 5. 禁止动作核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y100B-04-IMPL` 或其他页面: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态与权限态证据来自本地只读受控桩响应与受控 503 注入；联调环境的真实后端报错文案可能不同，但不影响本轮只读交互契约与零副作用门禁。
