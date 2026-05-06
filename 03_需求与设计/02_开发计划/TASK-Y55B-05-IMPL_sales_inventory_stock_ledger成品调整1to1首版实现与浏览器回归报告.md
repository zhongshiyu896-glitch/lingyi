# TASK-Y55B-05-IMPL /sales-inventory/stock-ledger 成品调整 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y55B-05-IMPL`
- 路由: `/sales-inventory/stock-ledger`
- 目标语义: `TASK-Y54B-P1-05 成品调整`（只读首版）
- 允许改动: `sales_inventory` allowlist 5 个产品文件 + 本报告 + 工程师会话日志
- 禁止项执行结果: 未执行 `git add/commit/push`，未触发 `PR/merge/tag/release/cleanup`，未启动后续 P1/P2 页面

## 2. 实现改动
- 前端视图: `src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - 新增区块：`成品调整（TASK-Y54B-P1-05）`，包含筛选、表格、状态标签、汇总、空态、错误态、权限/禁用态
  - guarded 动作：`调整确认提示`、`复核提示`、`差异处理提示`、`导出`、`打印`（仅提示/禁用，不触发真实写请求）
- 前端 API: `src/api/sales_inventory.ts`
  - 新增只读调用：`fetchSalesInventoryFinishedGoodsAdjustment`
  - 接口：`GET /api/sales-inventory/finished-goods-adjustment`
- 后端路由: `app/routers/sales_inventory.py`
  - 新增只读路由：`GET /api/sales-inventory/finished-goods-adjustment`
  - 位置：位于动态 `items/{item_code}` 路由之前，避免遮蔽
  - 权限：保持 `SALES_INVENTORY_READ` 只读权限边界
- 后端 schema/service:
  - `app/schemas/sales_inventory.py` 新增 `FinishedGoodsAdjustmentItem` / `FinishedGoodsAdjustmentData`
  - `app/services/sales_inventory_service.py` 新增 `get_finished_goods_adjustment` 只读聚合

## 3. preserved 检查
- P0 成品进销存主语义 preserved：PASS
- 既有库存流水筛选/列表/汇总结构 preserved：PASS
- Y45 系列已实现区块 preserved：PASS
- Y50 系列已实现区块 preserved：PASS
- `TASK-Y55B-01-IMPL` 客户退货申请 preserved：PASS
- `TASK-Y55B-02-IMPL` 客户退货入仓 preserved：PASS
- `TASK-Y55B-03-IMPL` 成品其他出仓 preserved：PASS
- `TASK-Y55B-04-IMPL` 成品盘点 preserved：PASS
- 权限态、空态、错误态、禁用态 preserved：PASS
- 写动作 guarded preserved：PASS
- 上传/下载/导出/打印 guarded preserved：PASS

## 4. 验证结果
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `git diff --cached --name-only`：空
- `git diff --cached --check`：PASS
- `git diff --check`：PASS

## 5. 浏览器回归证据
- 回归路由：`/sales-inventory/stock-ledger`
- result_json：`/tmp/task_y55b_05_impl_20260505T152516Z_browser_results.json`
- screenshots_count：`6`
- 核心断言：
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `finished_goods_adjustment_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码：PASS
- 未修改测试代码：PASS
- 未修改 A 控制流文件：PASS
- 未修改 C 审计记录：PASS
- 未执行 `git add/commit/push`：PASS
- 未执行 `PR/merge/tag/release`：PASS
- 未执行 `cleanup/reset/restore/clean/delete`：PASS
- 未释放 parked blockers：PASS
