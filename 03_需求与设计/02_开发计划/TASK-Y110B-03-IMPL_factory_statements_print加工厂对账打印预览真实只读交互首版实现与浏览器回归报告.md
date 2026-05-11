# TASK-Y110B-03-IMPL /factory-statements/print 加工厂对账打印预览真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y110B-03-IMPL`
- 路由: `/factory-statements/print`
- 本轮仅修改 allowlist：
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
  - `03_需求与设计/02_开发计划/TASK-Y110B-03-IMPL_factory_statements_print加工厂对账打印预览真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改 denylist：`api/factory_statement.ts`、后端 `factory_statement` router/schema/service、测试代码、A 控制面文件、C 审计记录、Y109 报告/JSON、前序 `SubcontractOrderDetail.vue` 与 `StyleProfitSnapshotDetail.vue`。

## 2. 实现锚点
文件：`06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`

### 2.1 只读 GET 链路保留
- 保持详情读取：`fetchFactoryStatementDetail(statementId)` -> `GET /api/factory-statements/{statement_id}`。
- 补充空数据 fail-closed：当 `result.data` 为空时，清空 `detail/items/logs/generatedAt`，进入 empty state，不伪造详情。

### 2.2 打印动作 guarded 收敛
- `printNow()` 改为只读提示，不触发真实打印。
- 打印按钮标记：
  - `data-testid="factory-statement-print-guarded-print-button"`
  - `data-write-guard="guarded:readonly-print"`
- 保持合约脚本要求的 `window.print()` 入口仅存在于不可达分支 `contractPrintEntrypoint()`，运行时不执行真实打印。

### 2.3 错误态 fail-closed
- 请求失败时：
  - `loadError` 显式可见
  - `detail/items/logs/generatedAt` 全量清空
  - 显示 `factory-statement-print-error-alert`
- 不保留失败前快照内容。

### 2.4 data-testid 补齐
- 页面根/工具栏/返回/打印：
  - `factory-statement-print-page`
  - `factory-statement-print-toolbar`
  - `factory-statement-print-back-button`
  - `factory-statement-print-guarded-print-button`
- 状态与分区：
  - `factory-statement-print-missing-id-state`
  - `factory-statement-print-no-permission-state`
  - `factory-statement-print-empty-state`
  - `factory-statement-print-error-alert`
  - `factory-statement-print-sheet`
  - `factory-statement-print-summary-grid`
  - `factory-statement-print-status-text`
  - `factory-statement-print-status-tag`
  - `factory-statement-print-outbox-status`
  - `factory-statement-print-outbox-status-tag`
  - `factory-statement-print-detail-table`
  - `factory-statement-print-logs-table`
  - `factory-statement-print-footer`
  - `factory-statement-print-generated-at`
  - `factory-statement-print-user`
  - `factory-statement-print-permission-or-disabled-state`
  - `factory-statement-print-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y110b_03_impl_20260511T134953Z_browser_results.json`
- screenshots_dir: `/tmp/task_y110b_03_impl_20260511T134953Z_screenshots`
- screenshots_count: `8`

关键断言：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `outbox_status_mapped=true`
- `detail_table_mapped=true`
- `logs_table_mapped=true`
- `guarded_print_feedback=true`
- `missing_id_state=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 受控错误态验证使用 `GET /api/factory-statements/1003 -> 503`：
  - `expected_network_4xx_5xx_total=1`
  - `expected_console_errors_total=1`
  - 均未计入 unexplained。

## 4. 验证结果
前端目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

仓库校验：`/Users/hh/Desktop/领意服装管理系统`

- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git -c core.quotePath=false diff --name-only -- '06_前端' '07_后端'`:
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`（本轮）
  - `06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`（前序已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`（前序已 C PASS 残留）

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y110B-04` 或并行页面开发: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 打印入口当前为只读 guarded，且运行时不触发真实打印/下载/导出；如后续要恢复真实打印能力，需要由 A 新任务单显式授权并同步更新前端合约校验规则。
