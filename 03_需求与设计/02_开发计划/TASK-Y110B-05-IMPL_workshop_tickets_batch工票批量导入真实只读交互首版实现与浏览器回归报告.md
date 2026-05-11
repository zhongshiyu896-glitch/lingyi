# TASK-Y110B-05-IMPL /workshop/tickets/batch 工票批量导入真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y110B-05-IMPL`
- 路由: `/workshop/tickets/batch`
- 本轮仅修改 allowlist：
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`
  - `03_需求与设计/02_开发计划/TASK-Y110B-05-IMPL_workshop_tickets_batch工票批量导入真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止范围：API/后端/测试/控制面/C 审计记录。
- 前序残留（已 C PASS，不属于本轮改动）：
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
  - `06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`

## 2. 实现锚点
文件：`06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`

### 2.1 写动作收敛为只读 guarded
- 移除真实写调用路径：页面不再调用 `batchWorkshopTickets`，不发起 `POST /api/workshop/tickets/batch`。
- `submitBatch` 改为：
  1) 先执行本地 JSON 解析和字段校验；
  2) 权限判定；
  3) 统一输出 guarded 提示（只读模式），不伪造导入成功。
- 提交按钮固定写保护标记：
  - `data-testid="workshop-ticket-batch-submit-button"`
  - `data-write-guard="guarded:readonly-ticket-batch-submit"`

### 2.2 本地只读解析与校验
- 新增 `parsePayload`，本地完成：
  - 非数组 JSON 拦截；
  - 空数组拦截；
  - 缺字段拦截（`ticket_key/job_card/employee/process_name/qty/work_date`，`reversal` 额外校验 `original_ticket_id/reason`）。
- 输出只读预览与失败明细：
  - 预览统计：总行数/可预览/校验失败；
  - 失败明细表：行号、ticket_key、结果码、校验说明。

### 2.3 审计锚点补齐
- 补齐 `data-testid`：
  - 页面/头部/返回：`workshop-ticket-batch-page`、`...-header`、`...-title`、`...-back-button`
  - JSON 输入与动作：`...-json-input`、`...-parse-button`、`...-submit-button`
  - 校验与反馈：`...-validation-hint`、`...-guarded-feedback`、`...-permission-or-disabled-state`
  - 只读预览与失败明细：`...-readonly-preview`、`...-preview-table`、`...-failed-items-table`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y110b_05_impl_20260511T144207Z/browser_results.json`
- screenshots_dir: `/tmp/task_y110b_05_impl_20260511T144207Z/screenshots`
- screenshots_count: `8`

关键断言：
- `route_open=true`
- `first_screen_visible=true`
- `invalid_json_validation_visible=true`
- `empty_array_validation_visible=true`
- `missing_fields_validation_visible=true`
- `valid_json_preview_visible=true`
- `guarded_submit_feedback_visible=true`
- `permission_or_disabled_state=true`
- `back_to_list_triggered=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 浏览器回归在本地 `http://127.0.0.1:5175` 执行，页面动作全部限定为只读交互与 guarded 验证。
- `api/auth` 在浏览器脚本中以只读 mock 返回，用于稳定权限态验证，不涉及写动作。

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
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`（本轮）
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`（前序已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`（前序已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`（前序已 C PASS 残留）
  - `06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`（前序已 C PASS 残留）

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动新候选任务: YES
- 未释放 parked blockers: YES
