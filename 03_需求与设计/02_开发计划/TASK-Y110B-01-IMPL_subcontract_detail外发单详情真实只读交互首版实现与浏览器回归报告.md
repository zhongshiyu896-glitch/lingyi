# TASK-Y110B-01-IMPL /subcontract/detail 外发单详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y110B-01-IMPL`
- 路由: `/subcontract/detail`
- 本轮仅修改 allowlist：
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y110B-01-IMPL_subcontract_detail外发单详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改 denylist：`api/subcontract.ts`、后端 `subcontract` router/schema/service、测试代码、A 控制面、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 真实只读 GET 链路保留
- 详情读取维持：`fetchSubcontractOrderDetail(orderId)` -> `GET /api/subcontract/{order_id}`。
- `loadDetail()` 中在合法 ID 条件下执行真实 GET；缺失 ID 时进入缺失态，不伪造详情数据。

### 2.2 错误态与状态锚点补齐
- 新增显式 `loadError`，请求异常时：
  - `detail.value = null`
  - `loadError = 外发单详情加载失败：...`
  - 页面展示 `subcontract-detail-error-state`。
- 补齐状态锚点：
  - `subcontract-detail-loading-state`
  - `subcontract-detail-permission-state`
  - `subcontract-detail-missing-id-state`
  - `subcontract-detail-empty-state`
  - `subcontract-detail-error-state`
  - `subcontract-detail-permission-or-disabled-state`

### 2.3 data-testid 与只读结构补齐
- 页面与主字段：
  - `subcontract-detail-page`
  - `subcontract-detail-main-card`
  - `subcontract-detail-header`
  - `subcontract-detail-title`
  - `subcontract-detail-back`
  - `subcontract-detail-main-fields`
  - `subcontract-detail-field-subcontract-no`
  - `subcontract-detail-status-tag`
  - `subcontract-detail-scope-blocked-tag`
  - `subcontract-detail-issue-sync-status`
  - `subcontract-detail-receipt-sync-status`
- 回料与验货区：
  - `subcontract-detail-receipt-section`
  - `subcontract-detail-receipt-table`
  - `subcontract-detail-receipt-sync-tag`
  - `subcontract-detail-inspection-section`
  - `subcontract-detail-inspection-table`
- guarded 区：
  - `subcontract-detail-guarded-actions`
  - `subcontract-detail-action-issue`
  - `subcontract-detail-action-receipt`
  - `subcontract-detail-action-inspection`
  - `subcontract-detail-action-settlement`
  - `subcontract-detail-action-retry-sync`
  - `subcontract-detail-action-export`
  - `subcontract-detail-action-print`
  - `subcontract-detail-guarded-feedback`

### 2.4 写类/副作用动作收敛
- 新增 `guardedWriteAction(actionName)`，统一输出只读提示：
  - 发料、回料、验货、结算、同步重试、导出、打印入口均为 guarded。
- 未新增 POST/PUT/PATCH/DELETE 调用。
- 未触发下载/导出/打印请求链路。

## 3. 浏览器回归证据
- result_json: `/tmp/task_y110b_01_impl_20260511T122738Z_browser_results.json`
- screenshots_dir: `/tmp/task_y110b_01_impl_20260511T122738Z_screenshots`
- screenshots_count: `8`

关键断言：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `receipt_table_mapped=true`
- `inspection_table_mapped=true`
- `sync_status_mapped=true`
- `missing_id_state=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `guarded_write_feedback=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控 `GET /api/subcontract/503` 返回 503 验证；
  - `expected_network_4xx_5xx_total=1`
  - `expected_console_errors_total=1`
  - 均未计入 unexplained。

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
- 未启动后续候选实现: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 浏览器成功态与错误态使用受控拦截响应保证可重复证据；联调环境真实后端返回文案可能不同，但不影响本轮“只读 GET + 零副作用请求”验收口径。
