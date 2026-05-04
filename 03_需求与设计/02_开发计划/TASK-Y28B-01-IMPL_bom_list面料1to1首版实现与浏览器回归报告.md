# TASK-Y28B-01-IMPL /bom/list 面料 1:1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y28B-01-IMPL`
- ROLE: `B Engineer`
- route: `/bom/list`
- source baseline: `task_y28b_01_bom_list_fabric_allowlist_baseline.json`
- shared_route: `YES`
- allowlist_mismatch: `NO`

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/bom/list` 保留 BOM 管理列表、`TASK-Y23B-01-IMPL` 物料图库、`TASK-Y23B-04-IMPL` 物料采购单以及 `/bom/detail` 入口语义的前提下，补齐 `TASK-Y27B-P1-01` 面料只读语义。
- 前端补齐：
  - 新增“面料（TASK-Y27B-P1-01）”只读区块与筛选项（款号、面料编码、面料名称、颜色、规格、供应商、状态）。
  - 新增面料表格字段（面料编码、面料名称、款号、颜色、规格、供应商、单件用量、损耗率、单位、来源 BOM、状态）。
  - 新增查看/选用/导出语义按钮；写语义均为 guarded/提示型，不触发写请求。
  - 补齐面料区块空态、错误态、权限态与状态标签承接。
- 后端补齐：
  - 新增只读接口 `GET /api/bom/fabrics`。
  - 新增面料只读查询 schema/service 组合，不新增真实写路由，不放宽既有写权限。
  - 路由顺序校验：`/fabrics` 定义在 `/{bom_id}` 动态路由之前，避免被动态路由误匹配。

## ROUTE_API_BACKEND_MAPPING
- Frontend view: `06_前端/lingyi-pc/src/views/bom/BomList.vue`
- Frontend API: `06_前端/lingyi-pc/src/api/bom.ts`
- Backend router: `07_后端/lingyi_service/app/routers/bom.py`
- Backend schema: `07_后端/lingyi_service/app/schemas/bom.py`
- Backend service: `07_后端/lingyi_service/app/services/bom_service.py`
- New readonly endpoint: `GET /api/bom/fabrics`

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y27B-P1-01` 面料语义，未启动 `TASK-Y27B-P1-02/03/04/05`。
- 未扩展至任何非 `/bom/list` 路由。
- preserved checks：
  - BOM 管理列表 preserved: PASS
  - 物料图库 preserved: PASS
  - 物料采购单 preserved: PASS
  - `/bom/detail` 入口 preserved: PASS

## BROWSER_VALIDATION
- run_id: `20260504T014814Z`
- result_json: `/tmp/task_y28b_01_impl_20260504T014814Z_browser_results.json`
- screenshot_dir: `/tmp/task_y28b_01_impl_20260504T014814Z_screenshots`
- screenshots_count: `7`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - fabric_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - bom_management_list_preserved_check: PASS
  - material_gallery_preserved_check: PASS
  - purchase_order_preserved_check: PASS
  - bom_detail_entry_preserved_check: PASS
  - write_actions_guarded_check: PASS
- network/console:
  - write_request_count: `0`
  - upload_download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`（手动注入 503 验证错误态承接）
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## VALIDATION_COMMANDS
- `git diff --cached --name-only`: PASS（空）
- `git diff --check`: PASS（本轮允许文件无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## WRITE_ACTION_BOUNDARY
- “选用/导出/上传/编辑/删除/新增/保存”等写语义均为 guarded 或 disabled，不触发真实写动作。
- 本轮未新增 POST/PUT/PATCH/DELETE 写路由。
- 本轮未触发真实上传/下载/导出/打印请求。
- BOM 既有写权限链路未放宽。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- TASK-Y27B-P1-02/03/04/05 started: NO
- allowlist outside modified: NO
- real write routes added: NO
- production/GitHub management actions: NO
- parked blockers released: NO
