# TASK-Z012B-03-IMPL｜Z012-CAND-001 大货管理/订单入口前端交互实现与本地回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Z012B-03-IMPL`
- candidate: `Z012-CAND-001`
- source_head: `76bba338772f0b49be4968d3103ee4c45063bfbf`
- 实现类型: `FRONTEND_INTERACTION_LOCAL`
- 约束保持:
  - `full_browser_route_smoke_closed=false`
  - `production_readback_ready=false`
  - `go_live_ready=false`
  - `project_completion_claimed=false`
  - `remote_lifecycle_parked=true`

## 2. 代码实现摘要
### 2.1 路由 parity 对齐
- 将 `/production/productOrder` 入口从 `/production/plans` 调整为 `/sales-inventory/sales-orders`，并保留 `parity=production-order`。
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

### 2.2 列表页语义与交互
- 新增 parity 提示：`data-testid="sales-order-parity-hint"`。
- 保持“订单 / 大货管理 / 订单”语义展示。
- 筛选与重置保持可交互（订单号、关键词、开始时间、结束时间）。
- 写动作按钮统一只读 guard：禁用或仅本地提示，附 `data-write-guard="guarded:readonly"`。
- 详情跳转携带 parity（无来源时默认 `production-order`），保障详情页可进入本地只读链路。
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`

### 2.3 详情页写动作文案
- 将“动作入口A/B/C”替换为业务可验收文案：
  - `提交审核`
  - `导出订单`
  - `打印单据`
- 保留 `data-write-guard="guarded:readonly"`。
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue`

## 3. 本地回归与证据
## 3.1 构建与类型
- `npm run typecheck`: PASS
- `npm run build`: PASS

## 3.2 浏览器 smoke
- 任务请求目标：
  - `http://127.0.0.1:5173/production/productOrder`
  - `http://127.0.0.1:5173/sales-inventory/sales-orders`
- 实际执行说明：
  - 本机 `5173` 被非本项目运行时占用（`/Users/hh/Desktop/风水/前端`）。
  - 本轮在同仓可用运行时 `http://127.0.0.1:5175` 执行等价回归并保留 requested/attempted 对照证据。
- 结果：
  - `request_methods=[GET]`
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `blocking_console_error_count=0`
  - `network_error_count=0`
  - `detail_navigation_status=PASS`
  - `list_discovered_name=SO-Z003-SALES-ORDER-20260518-578`
  - `detail_action_labels_verified=true`
  - `screenshot_count=3`
  - `valid_target_screenshot_count=3`

## 3.3 证据文件
- browser result:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_03_sales_order_interaction_browser_result.json`
- screenshot dir:
  - `/tmp/task_z012b03_sales_order_screenshots`
- 结构化结果：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_03_sales_order_interaction_impl_result.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z012b_03_sales_order_interaction_impl_result.tsv`

## 4. 约束与风险结论
- 本轮仅前端本地交互实现与回归，未改后端、未触发非 GET、未触发生产写入。
- 未执行 `git add/commit/push`，未执行 `PR/tag/release`。
- 本轮不外推全链路结论，保持状态锚点不变。
