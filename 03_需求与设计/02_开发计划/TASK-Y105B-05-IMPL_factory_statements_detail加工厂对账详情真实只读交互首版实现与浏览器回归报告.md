# TASK-Y105B-05-IMPL /factory-statements/detail 加工厂对账详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y105B-05-IMPL`
- 路由: `/factory-statements/detail`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y105B-05-IMPL_factory_statements_detail加工厂对账详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`api/factory_statement.ts`、后端 `factory_statement` router/schema/service、测试文件、A 控制面文件、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 保留详情只读 GET 链路
- 保持详情读取链路：`fetchFactoryStatementDetail` -> `GET /api/factory-statements/{statement_id}`。
- `onMounted` 继续沿用既有权限加载顺序：`loadCurrentUser()` -> `loadModuleActions('factory_statement')` -> `loadDetail()`。

### 2.2 写动作与副作用动作收敛为 guarded/disabled/提示型
- 详情页写类入口全部改为 `guardedWriteAction(...)` 提示，不触发真实写动作：
  - `factory-statement-detail-action-confirm`
  - `factory-statement-detail-action-cancel`
  - `factory-statement-detail-action-payable-draft`
- 打印、导出入口全部收敛为只读提示：
  - `factory-statement-detail-action-print`
  - `factory-statement-detail-action-export`
- 页面内保留只读锚点与 fail-closed 语义：
  - `const hasPayableSummary`
  - `const summaryMissing`
  - `return '__unknown__'`
  - `!hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(...)`
  - `exportFactoryStatementDetailCsv`（仅保留锚点，不执行导出）
  - `/factory-statements/print`（仅保留只读提示锚点，不执行跳转）

### 2.3 data-testid 与状态锚点补齐
- 页面与主区块：
  - `factory-statement-detail-page`
  - `factory-statement-detail-main-card`
  - `factory-statement-detail-header`
  - `factory-statement-detail-title`
  - `factory-statement-detail-back`
- 主档字段与状态：
  - `factory-statement-detail-main-fields`
  - `factory-statement-detail-field-statement-no`
  - `factory-statement-detail-field-supplier`
  - `factory-statement-detail-status-tag`
- 只读明细区：
  - `factory-statement-detail-items-section`
  - `factory-statement-detail-items-table`
  - `factory-statement-detail-logs-section`
  - `factory-statement-detail-logs-table`
  - `factory-statement-detail-outbox-section`
  - `factory-statement-detail-outbox-status`
- 状态锚点：
  - `factory-statement-detail-missing-id-state`
  - `factory-statement-detail-empty-state`
  - `factory-statement-detail-error-state`
  - `factory-statement-detail-permission-state`
  - `factory-statement-detail-permission-or-disabled-state`
  - `factory-statement-detail-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y105b_05_impl_20260511T104516Z_browser_results.json`
- screenshots_dir: `/tmp/task_y105b_05_impl_20260511T104516Z_screenshots`
- screenshots_count: `9`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `items_table_mapped=true`
- `logs_table_mapped=true`
- `outbox_section_mapped=true`
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
- 错误态通过受控 `GET /api/factory-statements/1` 返回 503 验证，`expected_network_4xx_5xx_total=1`，不计入 unexplained。

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
- 未启动后续候选或并行页面任务: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 错误态与权限态使用浏览器受控桩响应进行可审计验证；联调环境的提示文案可能略有差异，但不影响本轮“只读 GET + 零副作用请求”验收口径。
