# TASK-Y3B-02 订单页 1:1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-02`
- module: `大货管理`
- page_name: `订单`
- yisuan_url_or_route: `https://erp.huaaosoft.com/#/production/productOrder`
- local_target_route: `/sales-inventory/sales-orders`
- frontend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
- backend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`

## EVIDENCE_USED
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/050_大货管理_订单.png`
- live_compare meta:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[49]`
- matrix/task breakdown:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json`

## IMPLEMENTATION_SUMMARY
- 在 allowlist 内完成订单页首版对齐，未扩散到其它模块。
- 订单页视图调整为“订单号/关键词/开始时间/结束时间”筛选入口，补齐“筛选/新建/下单/获取订单/导入/导出”按钮区（未接入写动作，保持只读边界）。
- 补充页面级 error alert，确保后端 4xx/5xx 时非白屏且有可见反馈。
- API/后端列表接口新增 `order_no`、`keyword` 查询参数映射，服务层增加最小本地过滤逻辑（不改权限模型）。
- 修复页面权限判定回退：当 `button_permissions.sales_inventory_read/export` 未下发时，回退使用 `actions` (`sales_inventory:read/export`) 判定，避免按钮误禁用。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项映射：
  - 衣算云 `订单号` -> 本地 `query.order_no`（前后端同名参数）
  - 衣算云 `款号/款名/客户款号` -> 本地 `query.keyword`（映射为后端 `keyword`）
  - 衣算云 `开始时间/结束时间` -> 本地 `from_date/to_date`
- 主要按钮映射：
  - `筛选/新建/下单/获取订单/导入/导出` 已展示
  - 写动作未接入，统一提示“本地首版暂未接入，仅保留按钮与状态对齐”
- 表格表头映射：
  - `订单号/客户/单位/下单日期/交期/状态/数量/金额/币种/操作`
- 状态与空态：
  - 空态文案：`暂无订单数据，请调整筛选条件后重试`
  - 错误态：`订单列表加载失败：<错误信息>`
  - 权限态：`无销售库存查看权限`

## ROUTE_API_BACKEND_MAPPING
- route:
  - `/sales-inventory/sales-orders`（列表页）
  - `/sales-inventory/sales-orders/detail`（详情页跳转入口保留）
- frontend API:
  - `fetchSalesInventorySalesOrders(query)` 增加 `order_no`、`keyword`
  - `fetchSalesInventorySalesOrderDetail(name)` 保持只读
- backend API:
  - `GET /api/sales-inventory/sales-orders` 新增 `order_no`、`keyword` 查询参数
  - `GET /api/sales-inventory/sales-orders/{name}` 保持只读
- backend service:
  - 对 `order_no` 做订单号本地匹配
  - 对 `keyword` 做最小关键词匹配（保持只读）

## SCREENSHOT_COMPARISON
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/050_大货管理_订单.png`
- local screenshots:
  - `/tmp/task_y3b_02_20260503T142730_orders_initial.png`
  - `/tmp/task_y3b_02_20260503T142730_orders_after_search.png`
  - `/tmp/task_y3b_02_20260503T142730_orders_final.png`
- comparison_notes:
  - 已对齐：页面标题语义、筛选字段语义、主按钮集合、空态/错误态可见反馈。
  - 差异保留：衣算云为卡片主视图，本地首版仍为表格主视图；详情跳转依赖真实订单数据，本轮运行态下未命中可跳详情记录。

## BROWSER_VALIDATION
- run_id: `20260503T150226`
- result_json: `/tmp/task_y3b_02_fix1_20260503T150226_browser_results.json`
- base_url: `http://127.0.0.1:5174`
- route: `/sales-inventory/sales-orders`
- route_open: PASS
- first_screen_visible: PASS
- filters_present: PASS
- table_headers_mapped: PASS
- buttons_mapped: PASS
- empty_state: PASS
- error_state: PASS
- permission_or_disabled_state: PASS
- navigation_to_detail: PASS
- write_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- explained_error_state_count: `1`
- 说明：本轮使用本地测试语义模拟（200 + `code!=0`）触发错误态，页面通过 error alert 承接；无未解释 console/page/network 错误。

## WRITE_ACTION_BOUNDARY
- 所有浏览器回归均限定本地 dev runtime（127.0.0.1）。
- 未触发 POST/PUT/PATCH/DELETE。
- 未触碰生产/ERPNext 真实业务动作。
- 权限边界未放宽：`sales_inventory:read/export` 来自 `/api/auth/actions?module=sales_inventory` 的后端动作集；仅当动作存在时用于页面展示判定回退，未新增任何写权限动作。

## KNOWN_GAPS
- evidence_gap_count: `1`
- gap_1: 衣算云“订单”主视图为卡片布局，本地首版保留表格布局（语义对齐优先，样式 1:1 延后）。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- parked blockers released: NO
- 修改 TASK-Y1/TASK-Y2 矩阵口径: NO

## NEXT_RECOMMENDATION
- 建议下一任务仅补 `TASK-Y3B-02` 数据可读样本回归（不扩模块），重点验证：
  - 明细跳转链路（详情页打开/返回）
  - 订单号筛选命中率
  - 卡片视图 1:1 结构是否需要进入后续增强批次
