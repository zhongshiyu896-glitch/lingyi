# TASK-Y60B-02-IMPL /factory-statements/list 费用(报销)支付 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y60B-02-IMPL`
- 路由: `/factory-statements/list`
- 目标语义: `TASK-Y59B-P1-02 费用(报销)支付`（只读首版）
- allowlist: `/factory-statements/list` 冻结的 5 个产品文件
- 本次收口性质: `TASK-Y60B-02-IMPL-EVIDENCE-FIX1` 证据补齐（不扩展新任务）

## 2. 实现锚点确认
- 前端区块（已存在并保留）:
  - `src/views/factory_statement/FactoryStatementList.vue`
  - 区块类名: `.expense-reimbursement-payment-section`
  - 标题: `费用(报销)支付（TASK-Y59B-P1-02）`
- 前端只读 API（已存在并保留）:
  - `src/api/factory_statement.ts`
  - `fetchFactoryStatementExpenseReimbursementPayments`
  - `GET /api/factory-statements/expense-reimbursement-payments`
- 后端只读路由（已存在并保留）:
  - `app/routers/factory_statement.py`
  - `GET /api/factory-statements/expense-reimbursement-payments`
  - 权限边界: `FACTORY_STATEMENT_READ`
  - 路由顺序: 静态 `/expense-reimbursement-payments` 位于动态 `/{statement_id}` 之前（route shadowing guard 生效）
- schema/service（已存在并保留）:
  - `app/schemas/factory_statement.py`
    - `FactoryStatementExpenseReimbursementPaymentItem`
    - `FactoryStatementExpenseReimbursementPaymentData`
  - `app/services/factory_statement_service.py`
    - `get_expense_reimbursement_payments(...)`
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/factory-statements/list` 既有 P0 主语义 preserved: PASS
- 既有列表/筛选/汇总/详情入口 preserved: PASS
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
- result_json: `/tmp/task_y60b_02_impl_20260506T015509Z_browser_results.json`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `expense_reimbursement_payment_fields_mapped=true`
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
  - 脚本包含一次可控 `__ERROR__` 场景用于验证错误态，因此 `console_errors_total=1`、`network_4xx_5xx_total=1`；
  - 该 500 为预期回归注入，不计入 unexplained 统计。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制流文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y60B-03` 与后续 P1/P2 页面: PASS
- 未释放 parked blockers: PASS
