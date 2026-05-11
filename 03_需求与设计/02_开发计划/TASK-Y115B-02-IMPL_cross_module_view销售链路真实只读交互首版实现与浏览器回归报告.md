# TASK-Y115B-02-IMPL /cross-module/view 销售链路真实只读交互首版实现与浏览器回归报告

## 1. 任务范围
- TASK_ID: `TASK-Y115B-02-IMPL`
- 路由: `/cross-module/view`
- 本轮仅修改 allowlist：
  - `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`
  - `03_需求与设计/02_开发计划/TASK-Y115B-02-IMPL_cross_module_view销售链路真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改：API/后端/测试/控制面/C 审计记录。

## 2. 实现锚点
文件：`06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`

### 2.1 销售链路锚点补齐
- 销售链路根区与表单锚点：
  - `cross-module-sales-order-tab`
  - `cross-module-sales-order-form`
  - `cross-module-sales-order-id-input`
  - `cross-module-sales-order-company-input`
  - `cross-module-sales-order-query-button`
- 结果区锚点：
  - `cross-module-sales-order-summary`
  - `cross-module-sales-order-delivery-table`
  - `cross-module-sales-order-quality-table`
  - `cross-module-sales-order-empty-state`
  - `cross-module-sales-order-error-state`
  - `cross-module-sales-order-guarded-state`

### 2.2 空销售单 guard 与可视状态
- `sales_order_id` 为空时：
  - 设置 `salesOrderGuardMessage='sales_order_id 不能为空'`
  - 清空错误与链路数据
  - 不触发销售链路 GET
- 新增状态变量：
  - `salesOrderGuardMessage`
  - `salesOrderErrorMessage`
  - `salesOrderQueried`
  - `salesOrderShowEmptyState`

### 2.3 查询链路与 fail-closed
- 有效销售单触发只读 GET：
  - `fetchSalesOrderTrail(sales_order_id, { company })`
  - `GET /api/cross-module/sales-order-trail/{sales_order_id}`
- 请求失败时：
  - `salesOrderTrail=null`
  - 展示 `salesOrderErrorMessage`
  - 不伪造链路事实数据
- 权限状态刷新后不可读时：
  - 清空销售链路 guard/error/queried/data（同时保留前序工单链路收敛语义）。

### 2.4 前序工单链路 preserved smoke
- 工单链路前序锚点、guard/error/empty 与 GET 行为保持可用。
- 浏览器证据包含工单链路 smoke（`WO-SMOKE-Y115`）验证。

## 3. 浏览器回归证据
- result_json: `/tmp/task_y115b_02_impl_20260511T165442Z/browser_results.json`
- screenshots_dir: `/tmp/task_y115b_02_impl_20260511T165442Z/screenshots`
- screenshots_count: `8`

关键断言：
- `route_open=true`
- `first_screen_visible=true`
- `sales_tab_switched=true`
- `required_sales_order_guarded=true`
- `query_get_triggered=true`
- `summary_mapped=true`
- `delivery_table_mapped=true`
- `quality_table_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `work_order_preserved_smoke=true`

零副作用指标：
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

受控 expected 说明：
- `expected_network_4xx_5xx_total=2`
  - `GET /api/cross-module/sales-order-trail/SO-ERROR-Y115` -> `503`（受控错误态验证）
  - `GET /api/auth/me` -> `401`（权限态验证）
- `expected_console_errors_total=2`（对应受控 401/503 资源错误提示）

## 4. 验证结果
前端目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

仓库校验：`/Users/hh/Desktop/领意服装管理系统`
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- '06_前端' '07_后端'`：仅 `CrossModuleView.vue`

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未释放 parked blockers: YES
