# TASK-Y23B-01-IMPL /bom/list 物料图库 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y23B-01-IMPL`
- ROLE: `B Engineer`
- route: `/bom/list`
- source baseline: `task_y23b_01_bom_list_allowlist_baseline.json`
- allowlist_mismatch: `NO`

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/bom/list` 保留现有 BOM 列表语义与 `/bom/detail` 入口前提下，新增“物料图库（TASK-Y22B-P1-01）”只读区块。
- 前端新增：图库筛选（分类/款号/物料编码/颜色/规格）、图库表格字段、预览弹窗、写语义按钮 guarded 提示、图库空态/错误态承接。
- 后端新增：只读接口 `GET /api/bom/material-gallery`，按 `BOM_READ` 权限与 readable item scope 返回图库数据。
- 未新增或放宽任何写路由；历史写接口未新增触发入口。

## ROUTE_API_BACKEND_MAPPING
- Frontend view: `06_前端/lingyi-pc/src/views/bom/BomList.vue`
- Frontend API: `06_前端/lingyi-pc/src/api/bom.ts`
- Backend router: `07_后端/lingyi_service/app/routers/bom.py`
- Backend schema: `07_后端/lingyi_service/app/schemas/bom.py`
- Backend service: `07_后端/lingyi_service/app/services/bom_service.py`
- New readonly endpoint: `GET /api/bom/material-gallery`

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y22B-P1-01` 物料图库语义。
- 未启动/实现 `TASK-Y22B-P1-04` 或其他 P1/P2 页面语义。
- `/bom/detail` 入口保留并可跳转。
- 未扩展到 `/production/plans`、`/warehouse`、`/reports/style-profit`。

## BROWSER_VALIDATION
- run_id: `20260503T224340Z`
- result_json: `/tmp/task_y23b_01_impl_20260503T224340Z_browser_results.json`
- screenshot_dir: `/tmp/task_y23b_01_impl_20260503T224340Z_screenshots`
- screenshots_count: `7`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - material_gallery_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - bom_management_list_preserved_check: PASS
  - bom_detail_entry_preserved_check: PASS
  - write_actions_guarded_check: PASS
- network/console:
  - write_request_count: `0`
  - upload_download_export_print_request_count: `0`
  - console_errors_total: `1`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`（手动注入 503 验证错误态承接）
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## ROOT_CAUSE_NOTE
- 首次浏览器回归出现 `422 /api/bom/material-gallery`，经定位为本地 `8000` 旧 runtime 未加载新路由版本。
- 重启本地 dev runtime 后，`/api/bom/material-gallery` 返回 200，复跑浏览器回归全部闭合。

## WRITE_ACTION_BOUNDARY
- “选用/上传/编辑/删除”均为 guarded/提示型，不触发写请求。
- 本轮未触发 POST/PUT/PATCH/DELETE。
- 本轮未触发上传/下载/导出/打印真实请求。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- real write routes added: NO
- BOM write permission relaxed: NO
- production/GitHub management actions: NO
- parked blockers released: NO
