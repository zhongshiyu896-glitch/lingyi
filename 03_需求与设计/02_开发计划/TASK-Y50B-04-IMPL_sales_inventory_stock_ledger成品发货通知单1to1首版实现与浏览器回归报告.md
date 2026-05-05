# TASK-Y50B-04-IMPL /sales-inventory/stock-ledger 成品发货通知单 1:1 首版实现与浏览器回归报告

## 1. 执行范围与边界

- TASK_ID: `TASK-Y50B-04-IMPL`
- route: `/sales-inventory/stock-ledger`
- shared_route: `true`
- risk_level: `HIGH`
- allowlist 内改动: `YES`
- 非目标路由改动: `NO`

本轮仅在以下 5 个 allowlist 产品文件内实现：

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
3. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`

## 2. 实现摘要

- 新增“成品发货通知单（TASK-Y49B-P1-04）”只读区块：
  - 筛选项：通知单号、成品编码、发货仓库、通知状态、物流状态、关键词、开始/结束日期
  - 展示项：计划发货、已发货、待发货、通知状态、物流状态、通知日期、预计送达日期、经办人、关联单据
  - 状态态：空态、错误态、权限禁用态
- 前端 API 新增只读 GET：
  - `fetchSalesInventoryFinishedGoodsShippingNotices`
  - `GET /api/sales-inventory/finished-goods-shipping-notices`
- 后端新增只读查询接口与聚合：
  - router: `GET /api/sales-inventory/finished-goods-shipping-notices`
  - schema: `FinishedGoodsShippingNoticeItem`, `FinishedGoodsShippingNoticeData`
  - service: `get_finished_goods_shipping_notices(...)`
- 写动作保持 guarded：
  - 发货下发提示、发货复核提示、校验、导出、打印均为提示/禁用，不触发真实写请求

## 3. preserved checks

- P0 成品进销存报表主语义 preserved: `true`
- 既有库存流水筛选/列表/汇总结构 preserved: `true`
- 物料调仓 preserved: `true`
- 物料盘点 preserved: `true`
- 物料进销存报表 preserved: `true`
- 库存物料滞留报表 preserved: `true`
- 半成品库存 preserved: `true`
- 成品预约入仓 preserved: `true`
- write actions guarded: `true`
- upload/download/export/print guarded: `true`

## 4. 本地验证

- `npm run precheck:dev-runtime`: `PASS`
- `npm run typecheck`: `PASS`
- `npm run verify`: `PASS`
- `git diff --cached --name-only`: `EMPTY`
- `git diff --cached --check`: `PASS`
- `git diff --check`: `PASS`
- `git tag --points-at HEAD`: `EMPTY`
- `gh pr list --head codex/sprint4-seal --state all --json ...`: `[]`
- `gh release list --limit 20`: `EMPTY`

## 5. 浏览器回归证据

- 回归脚本：`/tmp/task_y50b_04_impl_browser_check.mjs`
- result_json：`/tmp/task_y50b_04_impl_20260505T085523Z_browser_results.json`
- screenshots_count：`6`
- screenshots_dir：`/tmp/task_y50b_04_impl_20260505T085523Z_screenshots`

关键指标：

- route_open: `true`
- first_screen_visible: `true`
- filters_present: `true`
- finished_goods_shipping_notice_fields_mapped: `true`
- buttons_mapped: `true`
- status_tags_mapped: `true`
- empty_state: `true`
- error_state: `true`
- permission_or_disabled_state: `true`
- write_request_count: `0`
- upload_download_export_print_request_count: `0`
- unexplained_console_errors_total: `0`
- unexplained_network_4xx_5xx_total: `0`

## 6. 禁止动作核对

- git add / commit / push: `NO`
- PR / merge / tag / release: `NO`
- cleanup / reset / restore / clean / delete: `NO`
- 启动 TASK-Y49B-P1-05: `NO`
- 修改测试代码/控制面/C审计记录: `NO`
- 释放 parked blockers: `NO`
