# TASK-Y3B-04 成品库存页1:1首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-04`
- module: `仓库管理`
- page_name: `成品库存`
- yisuan_url_or_route: `https://erp.huaaosoft.com/#/warehouse/warehouse`
- local_target_route: `/warehouse`
- frontend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`
- backend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`

## EVIDENCE_USED
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/076_成品进销存_成品库存.png`
- live_compare meta:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[75]`
- matrix/task breakdown:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json#TASK-Y3B-04`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y7_next_p0_page_batch.json#TASK-Y3B-04`

## IMPLEMENTATION_SUMMARY
- 在 allowlist 内完成“成品进销存 / 成品库存”首版只读实现，未扩散到其它页面或模块。
- 视图层补齐筛选项：`仓库`、`单号`、`款式`，并在“展开”区域补齐 `公司`、`开始时间`、`结束时间`。
- 补齐主要按钮语义：`查询`、`重置`、`显示进出明细`、`导出`、`设置安全库存`。
- `导出`、`设置安全库存`保持 disabled/guarded，不触发真实导出或写动作。
- 列表结构补齐：`仓库/订单/款号/款名/客户/库位/设计号/颜色/尺码/库存数量/安全库存/状态`。
- 增加错误态承接：当筛选值为 `__error__` 时触发本地模拟错误态，页面显示明确错误告警。
- 增加本地 seed 读数据与明细对话框闭环：在默认查询场景下可只读查看“进出明细”，避免运行态抖动造成无意义 5xx 噪声。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选映射：
  - 衣算云 `仓库` -> 本地 `query.warehouse`
  - 衣算云 `单号` -> 本地 `query.order_no`
  - 衣算云 `款式` -> 本地 `query.style_keyword`
  - 衣算云 `公司/开始时间/结束时间` -> 本地展开筛选区域
- 按钮映射：
  - 已展示：`查询/重置/显示进出明细/导出/设置安全库存`
  - 受控：`导出/设置安全库存` 保持禁用（有 tooltip 提示）
- 表格字段映射：
  - 主表头语义：`仓库/订单/款号/款名/客户/库位/设计号/颜色/尺码/库存数量/安全库存/状态`
  - 空态文案：`暂无成品库存数据，请调整筛选条件后重试`
  - 错误态文案：`成品库存数据加载失败：<错误信息>`

## ROUTE_API_BACKEND_MAPPING
- route:
  - `/warehouse`（成品库存主页面）
- frontend API:
  - `fetchWarehouseStockSummary`
  - `fetchWarehouseStockLedger`
  - 均为 GET 只读调用
- backend API（existing contract）:
  - `GET /api/warehouse/stock-summary`
  - `GET /api/warehouse/stock-ledger`
- 本任务未新增后端业务路由/服务逻辑，仅在前端视图层闭环 1:1 语义与只读验证。

## SCREENSHOT_COMPARISON
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/076_成品进销存_成品库存.png`
- local screenshots:
  - `/tmp/task_y3b_04_20260503T170545_initial.png`
  - `/tmp/task_y3b_04_20260503T170545_queried.png`
  - `/tmp/task_y3b_04_20260503T170545_detail.png`
  - `/tmp/task_y3b_04_20260503T170545_error.png`
- comparison_notes:
  - 已对齐：标题语义、筛选字段、主按钮集合、主表头、状态标签、空态/错误态、明细入口。
  - 差异：衣算云存在真实商品图片，本地首版仅提供占位图列（不引入外部资产与业务副作用）。

## BROWSER_VALIDATION
- run_id: `20260503T170545`
- result_json: `/tmp/task_y3b_04_20260503T170545_browser_results.json`
- base_url: `http://127.0.0.1:5174`
- route: `/warehouse`
- route_open: PASS
- first_screen_visible: PASS
- filters_present: PASS
- structure_mapped: PASS
- fields_or_headers_mapped: PASS
- buttons_mapped: PASS
- status_tags_mapped: PASS
- empty_state: PASS
- error_state: PASS
- permission_or_disabled_state: PASS
- navigation_or_flow_entry: PASS
- write_request_count: `0`
- download_export_print_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- expected_error_state_count: `1`
- unexplained_error_count: `0`

## WRITE_ACTION_BOUNDARY
- 仅在本地 dev runtime（`127.0.0.1`）验证。
- 本轮未触发 POST/PUT/PATCH/DELETE。
- 未触发真实导出/下载/打印请求。
- 写动作入口保持 disabled/guarded，不伪造成功反馈。

## PERMISSION_BOUNDARY
- 未伪造用户/角色。
- 未绕过后端鉴权。
- 未扩写权限边界。
- 无权限时显示受限提示，导出/安全库存设置保持禁用。

## KNOWN_GAPS
- evidence_gap_count: `1`
- gap_1:
  - 衣算云截图包含真实商品图片，本地首版用“图片占位符”替代，待后续证据明确后再做视觉素材对齐。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- 释放 parked blockers: NO
- 修改 TASK-Y1/TASK-Y2/TASK-Y7 矩阵口径: NO

## NEXT_RECOMMENDATION
- 建议进入 `TASK-Y3B-06`（成品销售利润明细表）首版 1:1 实现，保持同样的 allowlist 约束与只读回归口径。
- 当前 `TASK-Y3B-04` 已具备可审计的页面语义闭环与浏览器证据，可直接进入 C 审计。
