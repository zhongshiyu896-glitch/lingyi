# TASK-Y65B-03-IMPL /factory-statements/list 客户应收账款汇总表 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y65B-03-IMPL`
- 路由: `/factory-statements/list`
- 目标语义: `TASK-Y64B-P1-03 客户应收账款汇总表`（只读首版）
- allowlist: `TASK-Y65B-03` baseline 冻结的 5 个 `/factory-statements/list` 承载文件
- 约束: 仅 GET 只读；写动作与上传/下载/导出/打印均 guarded，不触发真实写请求

## 2. 实现摘要
- 前端页面（`FactoryStatementList.vue`）新增“客户应收账款汇总表（TASK-Y64B-P1-03）”只读区块：
  - `data-testid="customer-receivable-summary-section"`
  - 筛选项：汇总单号、业务单号、客户名称、风险等级、复核状态、关键词、开始/结束日期。
  - 表格字段：汇总单号、关联业务单号、公司、客户名称、客户编码、币种、期初应收、本期应收、本期已收、期末应收、账龄30天内、账龄31-60天、账龄90天以上、风险等级、复核状态、汇总日期、经办人、备注。
  - 操作按钮：对账确认提示、复核提示、结算校验、导出、打印，全部为 guarded/提示型。
- 前端 API（`factory_statement.ts`）新增：
  - `fetchFactoryStatementCustomerReceivableSummaries`
  - `GET /api/factory-statements/customer-receivable-summaries`
  - 对应 query/item/data 类型定义。
- 后端 router（`factory_statement.py`）新增只读路由：
  - `GET /api/factory-statements/customer-receivable-summaries`
  - 权限边界保持 `FACTORY_STATEMENT_READ`
  - 静态路由位于动态 `/{statement_id}` 之前（route shadowing guard 生效）
- 后端 schema/service 新增只读聚合：
  - schema: `FactoryStatementCustomerReceivableSummaryItem` / `FactoryStatementCustomerReceivableSummaryData`
  - service: `get_customer_receivable_summaries(...)`
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/factory-statements/list` 既有 P0 主语义 preserved: PASS
- 既有列表/筛选/汇总/详情入口 preserved: PASS
- `TASK-Y60B-02` 费用(报销)支付只读语义 preserved: PASS
- `TASK-Y60B-03` 银行存款只读语义 preserved: PASS
- `TASK-Y60B-04` 银行取款只读语义 preserved: PASS
- `TASK-Y60B-05` 客户评估表只读语义 preserved: PASS
- `TASK-Y65B-01` 客户对账表只读语义 preserved: PASS
- `TASK-Y65B-02` 客户未收款报表只读语义 preserved: PASS
- 既有 API 调用与权限态 preserved: PASS
- 空态/错误态/权限禁用态 preserved: PASS
- 写动作 guarded preserved: PASS
- 上传/下载/导出/打印 guarded preserved: PASS
- 共享路由既有语义 preserved: PASS

## 4. 验证结果
- `python3 -m py_compile`（router/schema/service 三文件）: PASS
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS

## 5. 浏览器回归证据
- 回归路由: `/factory-statements/list`
- result_json: `/tmp/task_y65b_03_impl_20260506T080457Z_browser_results.json`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `customer_receivable_summary_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`
- 说明:
  - 错误态通过可控 `keyword=__ERROR__` 注入触发，`network_4xx_5xx_total=1` 属于 expected，不计入 unexplained。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制流文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y64B-P1-04/05`: PASS
- 未释放 parked blockers: PASS
