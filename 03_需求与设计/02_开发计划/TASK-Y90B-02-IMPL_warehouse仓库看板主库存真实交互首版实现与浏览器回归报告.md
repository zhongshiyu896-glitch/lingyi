# TASK-Y90B-02-IMPL /warehouse 仓库看板主库存真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y90B-02-IMPL`
- 路由: `/warehouse`
- 目标: 在既有仓库看板主库存区完成一个小而完整的真实交互切片（查询、重置、竖横视图切换、行选择、进出明细 GET 弹窗、guarded 写动作）
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- 未改动:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`

## 3. 实现摘要
- 稳定交互锚点:
  - 为主库存区、筛选区、查询/重置按钮、视图切换、主表格、分页、进出明细弹窗、guarded 按钮补齐 `data-testid`。
- 查询交互:
  - 查询按钮改为 `applyPrimaryQuery()`，先将 `currentPage=1`，再触发 `loadData()`。
  - 主筛选（仓库/单号/款式/公司/日期）仍走真实 GET 链路，触发 `/api/warehouse/stock-summary` 与 `/api/warehouse/stock-ledger`。
- 重置交互:
  - `resetQuery()` 增加页码归一（`page=1`、`pageSize=20`、清空选中行），并以 `loadData({ forceRemote: true })` 强制重新 GET。
- 分页与页大小:
  - 主库存区新增分页器（`el-pagination`）。
  - `handlePageChange`、`handlePageSizeChange` 均触发 `loadData()`，保证页码与页大小切换触发真实 GET。
- 竖横视图切换:
  - 保留 `displayMode` 并将当前模式绑定到主表格 class，切换产生真实前端状态变化（不触发写请求）。
- 行选择与进出明细:
  - 保留表格多选与 `onSelectionChange`。
  - `openLedgerDetail()` 调整为无论默认态或筛选态都通过 `fetchWarehouseStockLedger`（GET `/api/warehouse/stock-ledger`）加载明细；未勾选时提示不变。
- guarded 写动作:
  - 导出、设置安全库存等按钮继续 disabled/guarded 提示，不触发真实写请求、上传/下载/导出/打印请求。

## 4. 保留语义检查
- 保留 `/warehouse` 既有主语义与历史只读区块（仓库管理、物料库存、其他入仓、采购退料出仓、加工厂应退料报表、半成品出仓）。
- 未新增 POST/PUT/PATCH/DELETE 路由或调用。
- 未修改 `/bom/list`，仅保留前序已存在 dirty。

## 5. 验证结果
- `python3 -m py_compile /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: 空
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 -c core.quotePath=false diff --name-only -- '06_前端' '07_后端'`: `BomList.vue`（前序）+ `WarehouseDashboard.vue`（本轮）

## 6. 浏览器回归证据
- route: `/warehouse`
- script: `/tmp/task_y90b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y90b_02_impl_20260508T043809Z_browser_results.json`
- screenshots_dir: `/tmp/task_y90b_02_impl_20260508T043809Z_screenshots`
- screenshots_count: `7`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `warehouse_stock_fields_mapped=true`
  - `query_get_triggered=true`
  - `reset_get_triggered=true`
  - `view_mode_switched=true`
  - `row_select_worked=true`
  - `detail_get_triggered=true`
  - `detail_dialog_opened=true`
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
  - 错误态通过脚本注入一次 `GET /api/warehouse/stock-summary?warehouse=__simulate_error__` 的 503（expected）验证，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y90B-03` 或其他页面: PASS
- 未释放 parked blockers: PASS
