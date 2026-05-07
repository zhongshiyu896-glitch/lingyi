# TASK-Y70B-03-IMPL /factory-statements/list 供应商对账表 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y70B-03-IMPL`
- 路由: `/factory-statements/list`
- 目标语义: `TASK-Y69B-P1-03 供应商对账表`（只读首版）
- allowlist: `TASK-Y70B-03` baseline 冻结的 5 个 `/factory-statements/list` 承载文件
- 约束: 仅 GET 只读；写动作与上传/下载/导出/打印均 guarded，不触发真实写请求

## 2. 实现摘要
- 前端页面（`FactoryStatementList.vue`）新增“供应商对账表（TASK-Y69B-P1-03）”只读区块：
  - `data-testid="supplier-reconciliation-section"`
  - 筛选项：对账单号、关联业务单号、供应商、供应商编码、结算状态、复核状态、关键词、开始/结束日期
  - 表格字段：对账单号、关联业务单号、公司、供应商、供应商编码、币种、对账金额、已结算金额、待结算金额、结算状态、复核状态、跟进状态、对账日期、到期日期、经办人、备注
  - 操作按钮：对账确认提示、复核提示、对账校验、导出、打印，全部为 guarded/提示型
  - 新增 `loadSupplierReconciliations`、`resetSupplierReconciliationFilters`、`onSupplierReconciliationPageChange`、`onSupplierReconciliationSizeChange`，并在 `onMounted` 接入加载
- 前端 API（`factory_statement.ts`）新增并对接：
  - `fetchFactoryStatementSupplierReconciliations`
  - `GET /api/factory-statements/supplier-reconciliations`
  - 对应 query/item/data 类型保持只读
- 后端 router（`factory_statement.py`）新增只读路由：
  - `GET /api/factory-statements/supplier-reconciliations`
  - 权限边界保持 `FACTORY_STATEMENT_READ`
  - 静态路由位于动态 `/{statement_id}` 之前（`2293 < 2410`，route shadowing guard 生效）
- 后端 schema/service 新增只读聚合：
  - schema: `FactoryStatementSupplierReconciliationItem` / `FactoryStatementSupplierReconciliationData`
  - service: `get_supplier_reconciliations(...)`
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/factory-statements/list` 既有 P0 主语义 preserved: PASS
- 既有列表/筛选/汇总/详情入口 preserved: PASS
- `Y60B-02/03/04/05` 已实现只读语义 preserved: PASS
- `Y65B-01/02/03/04/05` 已实现只读语义 preserved: PASS
- `Y70B-01` 加工厂应付账款汇总表 preserved: PASS
- `Y70B-02` 供应商评估表 preserved: PASS
- 既有 API 调用与权限态 preserved: PASS
- 空态/错误态/权限禁用态 preserved: PASS
- 写动作 guarded preserved: PASS
- 上传/下载/导出/打印 guarded preserved: PASS
- 共享路由既有语义 preserved: PASS

## 4. 验证结果
- `python3 -m py_compile`（router/schema/service 三文件）: PASS
- `npm run precheck:dev-runtime`（在 `06_前端/lingyi-pc` 目录执行）: PASS
- `npm run typecheck`（在 `06_前端/lingyi-pc` 目录执行）: PASS
- `npm run verify`（在 `06_前端/lingyi-pc` 目录执行）: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS

## 5. 浏览器回归证据
- 回归路由: `/factory-statements/list`
- result_json: `/tmp/task_y70b_03_impl_20260506T124403Z_browser_results.json`
- screenshots_dir: `/tmp/task_y70b_03_impl_20260506T124403Z_screenshots`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `supplier_reconciliation_fields_mapped=true`
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
  - 错误态通过可控 `keyword=__ERROR__` 注入触发，`network_4xx_5xx_total=1` 与 `console_errors_total=1` 属于 expected，不计入 unexplained。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制流文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y69B-P1-04/05`: PASS
- 未释放 parked blockers: PASS
