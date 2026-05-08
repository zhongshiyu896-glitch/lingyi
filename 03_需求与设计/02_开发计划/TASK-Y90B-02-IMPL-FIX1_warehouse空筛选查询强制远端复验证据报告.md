# TASK-Y90B-02-IMPL-FIX1 /warehouse 空筛选查询强制远端复验证据报告

## 1. 任务与边界
- TASK_ID: `TASK-Y90B-02-IMPL-FIX1`
- 目标: 修复 `/warehouse` 空筛选点击“查询”未强制真实 GET 的问题，并完成浏览器复验证据。
- 本轮允许产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- 本轮实际产品改动:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`

## 2. 最小修复说明
- 修复点仅 1 处：`applyPrimaryQuery()`。
- 修复前:
  - `currentPage.value = 1`
  - `void loadData()`
- 修复后:
  - `currentPage.value = 1`
  - `void loadData({ forceRemote: true })`
- 结果:
  - 空筛选点击“查询”时，不再走本地 seed 分支，强制触发远端 GET。
  - 保留查询前 `page=1` 语义。
  - 未新增写动作、未新增写路由、未扩大到其他页面。

## 3. 回归验证
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS

## 4. 浏览器复验证据
- route: `/warehouse`
- script: `/tmp/task_y90b_02_impl_fix1_browser_check.mjs`
- result_json: `/tmp/task_y90b_02_impl_fix1_20260508T045941Z_browser_results.json`
- screenshots_dir: `/tmp/task_y90b_02_impl_fix1_20260508T045941Z_screenshots`
- screenshots_count: `7`

核心断言结果:
- `route_open=true`
- `first_screen_visible=true`
- `filters_present=true`
- `warehouse_stock_fields_mapped=true`
- `query_get_triggered=true`（空筛选点击“查询”后 GET 计数增加）
- `reset_get_triggered=true`
- `view_mode_switched=true`
- `row_select_worked=true`
- `detail_get_triggered=true`
- `detail_dialog_opened=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明:
- 错误态通过 1 次注入 `503`（expected）验证，`expected_network_4xx_5xx_total=1`，不计入 unexplained。

## 5. 范围与禁止动作核对
- 未修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`。
- 未修改仓库 API/后端文件。
- 未修改测试代码、A 控制面、C 审计记录。
- 未执行 `git add/commit/push`。
- 未执行 `PR/merge/tag/release`。
- 未执行 `cleanup/reset/restore/clean/delete`。
- 未启动 `TASK-Y90B-03` 或其他新页面。
