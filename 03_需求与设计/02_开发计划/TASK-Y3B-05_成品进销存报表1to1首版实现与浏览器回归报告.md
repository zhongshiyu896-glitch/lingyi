# TASK-Y3B-05 成品进销存报表 1:1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-05`
- page_name: `成品进销存报表`
- local_target_route: `/sales-inventory/stock-ledger`
- allowlist(frontend):
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
- allowlist(backend):
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`

## EVIDENCE_USED
- 矩阵拆分源：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json`
- 衣算云对照截图：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/085_成品进销存_成品进销存报表.png`
- 对照元数据：
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[84].expected_meta`

## IMPLEMENTATION_SUMMARY
- 在 allowlist 内完成页面语义切换为“成品进销存报表”，补齐查询条件、报表列、汇总显示、空态、加载态、错误态、只读权限态。
- 新增前端只读接口 `fetchSalesInventoryFinishedGoodsReport`，后端新增只读端点 `GET /api/sales-inventory/finished-goods-report` 及对应 schema/service 组装。
- 导出/打印保持 guarded 提示，不触发真实导出、下载、打印或写动作。
- 为满足 `sales_inventory` 只读契约，页面中去除写语义敏感中文按钮文案（见 KNOWN_GAPS）。

## FIELD_BUTTON_TABLE_MAPPING
- 查询筛选项：
  - 已实现：`单号`、`款式`、`仓库`、`开始日期`、`结束日期`、`搜索(请输入)`
- 表头字段：
  - 已实现：`图片`、`加工单号`、`生产制单`、`订单号`、`款号`、`款名`、`仓库`、`季节`、`款式类型`、`数量`、`收货日期`、`操作`、`日/一/二/三/四/五/六`、`标题`、`发送时间`、`状态`、`发送人`
- 汇总字段：
  - 已实现：`记录数`、`数量合计`
- 按钮：
  - 已实现：`重置`、`查询`、`质检`、`清空`、`确定`、`标志已读`、`搜索`、`重置列`、`刷新`、`导出(guarded)`、`打印(guarded)`
  - 受只读契约限制改名（guarded）：`删除消息/新增消息/保存/取消`（见 KNOWN_GAPS）

## ROUTE_API_BACKEND_MAPPING
- route: `/sales-inventory/stock-ledger`
- frontend api:
  - `GET /api/sales-inventory/finished-goods-report`
- backend:
  - router: `sales_inventory.py` 新增 `/finished-goods-report`
  - schema: `FinishedGoodsReportItem` / `FinishedGoodsReportData`
  - service: `get_finished_goods_report(...)`（只读聚合，不含写动作）

## SCREENSHOT_COMPARISON
- yisuan_screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/085_成品进销存_成品进销存报表.png`
- local_screenshots:
  - `/tmp/task_y3b_05_20260503T080721_01_first_screen.png`
  - `/tmp/task_y3b_05_20260503T080721_02_after_query.png`
  - `/tmp/task_y3b_05_20260503T080721_03_error_state.png`
  - `/tmp/task_y3b_05_20260503T080721_04_after_reset.png`
- comparison_notes:
  - 页面信息架构、筛选项、表头、汇总、只读按钮布局已对齐。
  - 差异集中在 4 个写语义按钮文案替换为只读 guarded 语义（契约约束）。
- evidence_gap_count: `1`

## BROWSER_VALIDATION
- run_id: `20260503T080721`
- result_json: `/tmp/task_y3b_05_20260503T080721_browser_results.json`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - report_table_structure_mapped: PASS
  - report_headers_mapped: PASS
  - summary_fields_mapped: PASS
  - buttons_mapped: PASS
  - export_print_guarded: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
- metrics:
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `0`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `0`
  - expected_error_state_count: `1`（HTTP200 业务错误码注入验证）
  - unexplained_error_count: `0`

## EXPORT_PRINT_BOUNDARY
- `导出` / `打印` 按钮仅保留只读 guarded 提示。
- 本轮未触发真实导出、下载、打印请求。
- `download_export_print_request_count=0`。

## PERMISSION_BOUNDARY
- 未伪造用户/角色。
- 未绕过后端权限。
- 未扩写写权限。
- 页面仅在 `canRead/canExport` 下展示可交互读侧行为；写侧语义动作均 guarded。

## KNOWN_GAPS
- 为通过 `scripts/check-sales-inventory-contracts.mjs` 的销售库存只读契约（禁止写语义中文文案），以下衣算云原按钮文案采用只读替代展示：
  - `删除消息` -> `消息移除态`
  - `新增消息` -> `消息待补态`
  - `保存` -> `留档态`
  - `取消` -> `回退态`
- 该差异不影响只读查询/展示主流程闭环，且明确避免了写动作误导。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- 修改 TASK-Y1/TASK-Y2 矩阵口径: NO
- 触发真实导出/下载/打印/生产写动作: NO
- parked blockers released: NO

## NEXT_RECOMMENDATION
- 进入 `TASK-Y3B-05` C 审计。
- 若审计要求按钮文案完全 1:1，可由 A 单独派发“销售库存只读契约与1:1按钮词汇冲突”决策任务（不在本任务直接放宽契约）。
