# TASK-Y60B-04-IMPL /factory-statements/list 银行取款 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y60B-04-IMPL`
- 路由: `/factory-statements/list`
- 目标语义: `TASK-Y59B-P1-04 银行取款`（只读首版）
- allowlist: `/factory-statements/list` 冻结的 5 个产品文件
- 约束: 仅 GET 只读、写动作与上传/下载/导出/打印均 guarded，禁止真实写请求

## 2. 实现摘要
- 前端页面（`FactoryStatementList.vue`）新增“银行取款（TASK-Y59B-P1-04）”只读区块：
  - 筛选项：取款单号、对账单号、开户行、账户名称、取款状态、复核状态、关键词、开始/结束日期。
  - 表格字段：取款单号、对账单号、公司、开户行、账户名称、账号、币种、取款金额、已出账金额、待出账金额、取款状态、复核状态、取款日期、凭证号、经办人、备注。
  - 操作按钮：取款确认提示、复核提示、出账校验、导出、打印，全部为 guarded/disabled/提示型。
- 前端 API（`factory_statement.ts`）新增：
  - `fetchFactoryStatementBankWithdrawals`
  - `GET /api/factory-statements/bank-withdrawals`
  - 对应 query/item/data 类型定义。
- 后端 router（`factory_statement.py`）新增只读路由：
  - `GET /api/factory-statements/bank-withdrawals`
  - 权限边界保持 `FACTORY_STATEMENT_READ`
  - 静态路由位于动态 `/{statement_id}` 之前（route shadowing guard 生效）
- 后端 schema/service 新增只读聚合：
  - schema: `FactoryStatementBankWithdrawalItem` / `FactoryStatementBankWithdrawalData`
  - service: `get_bank_withdrawals(...)`
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/factory-statements/list` 既有 P0 主语义 preserved: PASS
- 既有列表/筛选/汇总/详情入口 preserved: PASS
- `TASK-Y60B-02` 费用(报销)支付只读语义 preserved: PASS
- `TASK-Y60B-03` 银行存款只读语义 preserved: PASS
- 既有 API 调用与权限态 preserved: PASS
- 空态/错误态/权限禁用态 preserved: PASS
- 写动作 guarded preserved: PASS
- 上传/下载/导出/打印 guarded preserved: PASS
- 共享路由既有语义 preserved: PASS

## 4. 验证结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS

## 5. 浏览器回归证据
- 回归路由: `/factory-statements/list`
- result_json: `/tmp/task_y60b_04_impl_20260506T033808Z_browser_results.json`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `bank_withdrawal_fields_mapped=true`
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
  - 错误态采用可控 `keyword=__ERROR__` 注入验证，`500` 仅计入 expected，不计入 unexplained。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制流文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y59B-P1-05`: PASS
- 未释放 parked blockers: PASS
