# TASK-Y115B-01-IMPL /cross-module/view 工单链路真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y115B-01-IMPL`
- 路由: `/cross-module/view`
- 本轮仅修改 allowlist：
  - `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`
  - `03_需求与设计/02_开发计划/TASK-Y115B-01-IMPL_cross_module_view工单链路真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止范围：API/后端/测试/控制面/C 审计记录。

## 2. 实现锚点
文件：`06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`

### 2.1 工单链路可审计锚点补齐
- 页面与主区块锚点：
  - `cross-module-work-order-section`
  - `cross-module-tabs`
  - `cross-module-work-order-tab`
- 查询表单锚点：
  - `cross-module-work-order-form`
  - `cross-module-work-order-id-input`
  - `cross-module-work-order-company-input`
  - `cross-module-work-order-query-button`
- 结果区锚点：
  - `cross-module-work-order-summary`
  - `cross-module-work-order-stock-table`
  - `cross-module-work-order-quality-table`
  - `cross-module-work-order-empty-state`
  - `cross-module-work-order-error-state`
  - `cross-module-work-order-guarded-state`
  - `cross-module-permission-disabled-state`

### 2.2 空工单 guard 与可视状态
- `work_order_id` 为空时：
  - 设置 `workOrderGuardMessage='work_order_id 不能为空'`
  - 显示 guarded 警告态
  - 不触发任何链路 GET
- 新增并接入状态变量：
  - `workOrderGuardMessage`
  - `workOrderErrorMessage`
  - `workOrderQueried`
  - `workOrderShowEmptyState`

### 2.3 查询链路与失败闭合
- 有效工单触发真实 GET：
  - `fetchWorkOrderTrail(work_order_id, { company })`
  - `GET /api/cross-module/work-order-trail/{work_order_id}`
- 请求失败时：
  - `workOrderTrail` 清空为 `null`
  - 记录并展示 `workOrderErrorMessage`
  - 不伪造详情数据
- 权限刷新后若不可读：
  - 清空工单/销售链路数据
  - 清空工单 guard/error/queried 状态

## 3. 浏览器回归证据
- result_json: `/tmp/task_y115b_01_impl_20260511T162056Z/browser_results.json`
- screenshots_dir: `/tmp/task_y115b_01_impl_20260511T162056Z/screenshots`
- screenshots_count: `8`

关键断言：
- `route_open=true`
- `first_screen_visible=true`
- `required_work_order_guarded=true`
- `query_get_triggered=true`
- `summary_mapped=true`
- `stock_table_mapped=true`
- `quality_table_mapped=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

受控 expected 说明：
- `expected_network_4xx_5xx_total=2`（仅用于错误态验证）：
  - `WO-REAL-Y115`：401（未登录链路受控验证）
  - `WO-ERROR-Y115`：503（受控服务不可用验证）
- `expected_console_errors_total=2`（对应上述受控网络错误的浏览器资源错误提示）

## 4. 验证结果
前端目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

仓库校验：`/Users/hh/Desktop/领意服装管理系统`

- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- '06_前端' '07_后端'`：
  - `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`（本轮）

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未释放 parked blockers: YES
