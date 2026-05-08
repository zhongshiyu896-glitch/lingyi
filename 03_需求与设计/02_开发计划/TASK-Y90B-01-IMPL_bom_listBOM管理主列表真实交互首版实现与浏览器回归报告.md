# TASK-Y90B-01-IMPL /bom/list BOM管理主列表真实交互首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y90B-01-IMPL`
- 路由: `/bom/list`
- 目标: 在既有 BOM 主列表上完成一个小而完整的真实交互切片（查询、重置、分页/页大小、详情打开、写动作 guarded）
- allowlist 产品文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/bom.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`

## 2. 实际改动
- 实际产品改动文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`
- 未改动:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/bom.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`

## 3. 实现摘要
- 查询交互:
  - 新增 `runMainQuery()`，点击“查询”前将 `query.page=1`，然后触发 `loadList()`。
  - 主列表筛选输入（款式编码、状态）保持真实 GET `/api/bom/` 查询链路。
- 重置交互:
  - 新增 `resetMainQuery()`，恢复 `item_code=''`、`status=undefined`、`page=1`、`page_size=20`，并重新 GET。
- 分页与页大小:
  - 保持 `onPageChange`、`onSizeChange` 触发 `loadList()`，页大小切换触发真实 GET。
- 详情打开:
  - 新增 `openBomDetail(id)`，调用 `fetchBomDetail(id)`（GET `/api/bom/{bom_id}`）。
  - 主列表“详情”改为打开只读 `el-drawer`，不进入写流程。
- 只读状态提示与 guard:
  - 新建 BOM 按钮改为 `guardedReadonlyAction('新建 BOM')` 提示型 guarded。
  - 主列表新增 `listError` 告警区（`BOM主列表加载失败`），保留 empty/loading/permission 态。
- 稳定锚点:
  - 主列表 section/table/filter/detail drawer 增加稳定 `data-testid`（`bom-main-list-section`、`bom-main-table`、`bom-main-detail-drawer` 等）。

## 4. 保留语义检查
- `/bom/list` 下既有历史只读区块（面料、辅料/包材、物料加工类型等）未删除、未改路由，保持可读。
- 未新增任何 POST/PUT/PATCH/DELETE 路由或调用。
- 导出/打印/上传等副作用动作未新增真实请求链路。

## 5. 验证结果
- `python3 -m py_compile /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/bom.py /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run precheck:dev-runtime`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck`: PASS
- `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --check`: PASS
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --cached --name-only`: 空
- `git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- '06_前端' '07_后端'`: 仅 `BomList.vue`

## 6. 浏览器回归证据
- route: `/bom/list`
- script: `/tmp/task_y90b_01_impl_browser_check.mjs`
- result_json: `/tmp/task_y90b_01_impl_20260508T040632Z_browser_results.json`
- screenshots_dir: `/tmp/task_y90b_01_impl_20260508T040632Z_screenshots`
- screenshots_count: `8`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `bom_main_fields_mapped=true`
  - `query_get_triggered=true`
  - `reset_get_triggered=true`
  - `pagination_or_size_get_triggered=true`
  - `detail_get_triggered=true`
  - `detail_drawer_opened=true`
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
  - 错误态通过脚本对 `GET /api/bom/?item_code=__simulate_error__` 注入一次 503 验证，计入 expected，不计入 unexplained。

## 7. 禁止动作核对
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y90B-02` 或其他页面: PASS
- 未释放 parked blockers: PASS
